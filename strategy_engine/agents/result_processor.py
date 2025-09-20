import html
import json
import logging
import re
from typing import Any, Literal

# App-specific deps
from agents.models import AgentMessage, AgentStatus, FinalStrategy, Strategy, TraceItem
from database.mongodb import MongoDB
from utils.helpers import extract_json_blocks, json_to_key_value_str

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResultProcessor:
    async def process_result(self, result: dict[str, Any]) -> FinalStrategy:
        output = result.get("output", "")
        parsed_reasoning_trace: list[TraceItem] = self.build_reasoning_trace(
            result, include_tool_calls=False
        )
        try:
            parsed = extract_json_blocks(output)[0]

        except Exception:
            parsed = json.loads(output.replace("```json", "").replace("```", ""))

        strategy_str = json.dumps(parsed.get("strategy", ""), ensure_ascii=False)
        strategy = Strategy.model_validate_json(strategy_str)
        thread_ids = [item.thread_id for item in parsed_reasoning_trace]
        thread_id = set(thread_ids).pop() if thread_ids else None

        if not thread_id:
            reasoning_trace = []
        else:
            mongo = MongoDB()
            messages = await mongo.get_reasoning_trace(thread_id)
            reasoning_trace = [
                AgentMessage(
                    role=msg.role.lower(),
                    content=msg.content,
                    status=msg.status.value,
                )
                for msg in messages
            ]

        return FinalStrategy(strategy=strategy, reasoning_trace=reasoning_trace)

    def _save_to_file(self, data: dict[str, Any]) -> None:
        try:
            with open("final_strategy.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _safe_json_loads(self, s: str) -> Any:
        try:
            return json.loads(s)
        except Exception:
            return None

    def _extract_resolved_blocks(self, observation_str: str) -> list[dict]:
        RESOLVED_RE = re.compile(
            r'<ResolvedMessage\s+id="(?P<id>[^"]+)"\s+threadName="[^"]*"\s+threadId="(?P<thread>[^"]+)"\s+senderId="(?P<sender>[^"]+)"\s+content="(?P<content>.*?)"\s+timestamp="(?P<ts>\d+)">'
        )
        out = []
        for m in RESOLVED_RE.finditer(observation_str):
            msg_id = m.group("id")
            thread_id = m.group("thread")
            sender = m.group("sender")
            ts = int(m.group("ts"))
            content_escaped = m.group("content")
            # content HTML-escaped → unescape
            content_unescaped = html.unescape(content_escaped)
            out.append({
                "message_id": msg_id,
                "thread_id": thread_id,
                "sender": sender,
                "timestamp_ms": ts,
                "content_unescaped": content_unescaped,
                "raw": m.group(0),
                "json_payload": self._safe_json_loads(content_unescaped),
            })
        return out

    def _map_sender_to_role(
        self,
        sender: str,
    ) -> Literal["planner", "verifier", "critic", "orchestrator", "system", "tool"]:
        sender = sender.lower()
        if sender == "planner":
            return "planner"
        if sender == "critic":
            return "critic"
        if sender == "verifier":
            return "verifier"
        if sender == "orchestrator":
            return "orchestrator"
        return "system"  # fallback

    def build_reasoning_trace(
        self, agent_payload: dict, include_tool_calls: bool = False
    ) -> list[TraceItem]:
        """
        - Iterate through intermediate_steps ([(ToolAgentAction, observation), ...]).
        - Extract all ResolvedMessage (planner/critic/verifier/orchestrator) with original content.
        - Record verifier timeout if any.
        - (Optional) Include tool-calls logs (tool, input, raw output) in trace.
        """
        trace: list[TraceItem] = []
        steps = agent_payload.get("intermediate_steps", [])

        for step in steps:
            if not (isinstance(step, (list, tuple)) and len(step) >= 2):
                continue
            logger.debug(f"This is a step: {step}")

            tool_act, observation = step[0], str(step)
            if include_tool_calls:
                try:
                    tool_name = getattr(tool_act, "tool", None)
                    tool_input = getattr(tool_act, "tool_input", None)

                    tool_output = observation if isinstance(observation, str) else None
                    trace.append(
                        TraceItem(
                            role="tool",
                            tool_name=tool_name,
                            status=None,
                            tool_input=tool_input,
                            tool_output=tool_output,
                            content=f"[TOOL CALL] {tool_name} input={tool_input}",
                            raw=str(observation)[:20000],
                            thread_id=None,
                            message_id=None,
                            timestamp_ms=None,
                        )
                    )
                except Exception:
                    pass

            if isinstance(observation, str):
                for msg in self._extract_resolved_blocks(observation):
                    logger.debug(f"Message: {msg}")
                    role = self._map_sender_to_role(msg["sender"])
                    content_raw = msg["content_unescaped"]
                    payload = msg["json_payload"]

                    if payload is not None:
                        try:
                            content_text = json.dumps(
                                payload, ensure_ascii=False, indent=2
                            )
                            content_text = json_to_key_value_str(content_text, indent=2)
                        except Exception:
                            content_text = content_raw
                    else:
                        content_text = content_raw

                    try:
                        status = (
                            payload.get("status") if isinstance(payload, dict) else None
                        )

                        if status is not None and str(status).upper() in [
                            e.value for e in AgentStatus
                        ]:  # type: ignore
                            status = AgentStatus(str(status).upper())  # type: ignore
                    except Exception:
                        status = None

                    trace.append(
                        TraceItem(
                            role=role,
                            content=content_text,
                            status=status,
                            raw=msg["raw"],
                            thread_id=msg["thread_id"],
                            message_id=msg["message_id"],
                            timestamp_ms=msg["timestamp_ms"],
                            tool_name=None,
                            tool_input=None,
                            tool_output=None,
                        )
                    )

        if "output" in agent_payload:
            content = agent_payload["output"]
            logger.debug(f"This is the content: {content}")
            try:
                json_blocks = extract_json_blocks(content)
                if json_blocks:
                    content = json_to_key_value_str(
                        json.dumps(json_blocks[0], ensure_ascii=False, indent=2),
                        indent=2,
                    )
            except Exception:
                pass

        logger.debug(f"Trace: {trace}")

        return trace
