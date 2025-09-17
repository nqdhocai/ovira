from __future__ import annotations

import html
import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Literal

# App-specific deps
from agents.model import get_llm_model
from agents.models import AgentMessage, FinalStrategy, Strategy, TraceItem
from config.settings import mcp_config
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
from langchain_core.prompts import MessagesPlaceholder
from langchain_mcp_adapters.client import MultiServerMCPClient
from prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from pydantic import BaseModel, Field
from utils.helpers import extract_json_blocks, json_to_key_value_str
from utils.singleton_base import SingletonBase

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =========================
# Config
# =========================
@dataclass
class Config:
    coral_sse_url: str
    agent_id: str
    timeout_ms: int

    @staticmethod
    def load() -> "Config":
        load_dotenv()

        cfg = Config(
            coral_sse_url=mcp_config.CORAL_SSE_URL,
            agent_id="orchestrator",
            timeout_ms=int(mcp_config.TIMEOUT_MS or 60000),
        )

        return cfg


# =========================
# Tools
# =========================
class ToolsManager:
    @staticmethod
    def get_tools_description(tools: list[Any]) -> str:
        descs = []
        for tool in tools:
            schema = (
                json.dumps(getattr(tool, "args", {}))
                .replace("{", "{{")
                .replace("}", "}}")
            )
            descs.append(f"Tool: {tool.name} | Schema: {schema}")
        return "\n".join(descs)

    @staticmethod
    async def prepare_coral_tools(coral_tools: list[Any]) -> list[Any]:
        tools_by_name = {t.name: t for t in coral_tools}
        if "wait_for_mentions" in tools_by_name:
            wait_real = tools_by_name["wait_for_mentions"]
            wait_fixed = ToolsManager._create_wait_tool_wrapper(wait_real)
            return [
                wait_fixed if t.name == "wait_for_mentions" else t for t in coral_tools
            ]
        return coral_tools

    @staticmethod
    def _create_wait_tool_wrapper(wait_real):
        class WaitArgs(BaseModel):
            threadId: str | None = Field(
                default=None, description="Thread ID (optional)"
            )
            timeoutMs: int | None = Field(
                default=60000, description="Timeout in ms (INTEGER)"
            )

        async def wait_wrapper(
            threadId: str | None = None, timeoutMs: int | None = 60000
        ):
            args: dict[str, Any] = {}
            if threadId:
                args["threadId"] = threadId
            args["timeoutMs"] = int(timeoutMs if timeoutMs is not None else 60000)
            return await wait_real.ainvoke(args)

        return StructuredTool.from_function(
            coroutine=wait_wrapper,
            name="wait_for_mentions",
            description="Wait for mentions; 'timeoutMs' MUST be integer milliseconds (e.g., 60000).",
            args_schema=WaitArgs,
        )


# =========================
# Prompt
# =========================
class PromptBuilder:
    @staticmethod
    def _escape_curly(text: str) -> str:
        return text.replace("{", "{{").replace("}", "}}")

    @staticmethod
    def make_prompt(coral_tools_description: str) -> ChatPromptTemplate:
        system_text_raw = ORCHESTRATOR_SYSTEM_PROMPT.format(
            coral_tools_description=coral_tools_description,
        )
        system_text = PromptBuilder._escape_curly(system_text_raw)
        return ChatPromptTemplate.from_messages([
            ("system", system_text),
            ("human", "{user_input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])


# =========================
# Policy
# =========================
class PolicyBuilder:
    @staticmethod
    def create_policy(
        risk: Literal["conservative", "balanced", "aggressive"],
    ) -> dict[str, Any]:
        return {
            "risk_label": risk,
            "rules": {
                "tvl_usd_min": 1_000_000,
                "sigma_max": 0.20,
                "weight_pct_per_pool_max": 50.0,
                "n_pools_min": 2,
                "n_pools_max": 6,
            },
        }


# =========================
# Result handling
# =========================
class ResultProcessor:
    def process_result(self, result: dict[str, Any]) -> FinalStrategy:
        output = result.get("output", "")
        parsed_reasoning_trace: list[TraceItem] = self.build_reasoning_trace(
            result, include_tool_calls=False
        )
        try:
            parsed = json.loads(output)

        except Exception:
            parsed = extract_json_blocks(output)[0]

        strategy_str = json.dumps(parsed.get("strategy", ""), ensure_ascii=False)
        strategy = Strategy.model_validate_json(strategy_str)
        reasoning_trace = [
            AgentMessage(role=i.role, content=i.content)
            for i in parsed_reasoning_trace
            if i.role in ("planner", "critic", "verifier")
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
            ts = m.group("ts")
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
        self, agent_payload: dict, include_tool_calls: bool = True
    ) -> list[TraceItem]:
        """
        - Iterate through intermediate_steps ([(ToolAgentAction, observation), ...]).
        - Extract all ResolvedMessage (planner/critic/verifier/orchestrator) with original content.
        - Record verifier timeout if any.
        - (Optional) Include tool-calls logs (tool, input, raw output) in trace.
        """
        trace: list[TraceItem] = []
        steps = agent_payload.get("intermediate_steps", [])
        verifier_timeout_seen = False

        for step in steps:
            if not (isinstance(step, (list, tuple)) and len(step) >= 2):
                continue

            tool_act, observation = step[0], step[1]

            if include_tool_calls:
                try:
                    tool_name = getattr(tool_act, "tool", None)
                    tool_input = getattr(tool_act, "tool_input", None)

                    tool_output = observation if isinstance(observation, str) else None
                    trace.append(
                        TraceItem(
                            role="tool",
                            tool_name=tool_name,
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
                if "No new messages received within the timeout period" in observation:
                    verifier_timeout_seen = True

                for msg in self._extract_resolved_blocks(observation):
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

                    trace.append(
                        TraceItem(
                            role=role,
                            content=content_text,
                            raw=msg["raw"],
                            thread_id=msg["thread_id"],
                            message_id=msg["message_id"],
                            timestamp_ms=msg["timestamp_ms"],
                            tool_name=None,
                            tool_input=None,
                            tool_output=None,
                        )
                    )
        has_verifier_msg = any(t.role == "verifier" for t in trace)
        if verifier_timeout_seen and not has_verifier_msg:
            trace.append(
                (
                    TraceItem.model_validate({
                        "role": "verifier",
                        "content": "[TIMEOUT] No new messages received within the timeout period",
                    })
                )
            )
        if "output" in agent_payload:
            content = agent_payload["output"]
            try:
                json_blocks = extract_json_blocks(content)
                if json_blocks:
                    content = json_to_key_value_str(
                        json.dumps(json_blocks[0], ensure_ascii=False, indent=2),
                        indent=2,
                    )
            except Exception:
                pass

            trace.append(
                TraceItem(
                    role="orchestrator",
                    content=content,
                    raw="",
                    thread_id=None,
                    message_id=None,
                    timestamp_ms=None,
                    tool_name=None,
                    tool_input=None,
                    tool_output=None,
                )
            )

        return trace


# =========================
# Orchestrator
# =========================
class OrchestratorAgent(SingletonBase):
    def __init__(self):
        self.cfg: Config | None = None
        self.client: MultiServerMCPClient | None = None
        self.executor: AgentExecutor | None = None

        self.tools_manager = ToolsManager()
        self.prompt_builder = PromptBuilder()
        self.policy_builder = PolicyBuilder()
        self.result_processor = ResultProcessor()

    async def initialize(self) -> None:
        self.cfg = Config.load()
        await self._setup_coral_client()
        await self._setup_agent_executor()

    async def _setup_coral_client(self) -> None:
        assert self.cfg is not None
        coral_params = {
            "agentId": self.cfg.agent_id,
            "agentDescription": "Orchestrator - An agent that takes user input and interacts with other agents to fulfill requests",
        }
        coral_server_url = (
            f"{self.cfg.coral_sse_url}?{urllib.parse.urlencode(coral_params)}"
        )

        self.client = MultiServerMCPClient(
            connections={
                "coral": {
                    "transport": "sse",
                    "url": coral_server_url,
                    "timeout": self.cfg.timeout_ms,
                    "sse_read_timeout": self.cfg.timeout_ms,
                }
            }
        )

    async def _setup_agent_executor(self) -> None:
        assert self.client is not None
        coral_tools = await self.client.get_tools(server_name="coral")
        prepared_tools = await self.tools_manager.prepare_coral_tools(coral_tools)
        tools_desc = self.tools_manager.get_tools_description(prepared_tools)

        model = get_llm_model()

        prompt = self.prompt_builder.make_prompt(tools_desc)
        agent = create_tool_calling_agent(model, prepared_tools, prompt)

        self.executor = AgentExecutor(
            agent=agent,
            tools=prepared_tools,
            verbose=True,
            return_intermediate_steps=True,
            max_iterations=300,
        )

    async def execute_strategy(
        self,
        pools_data: list[dict[Any, Any]],
        policy: dict[str, Any] | str | None = None,
        risk: Literal["conservative", "balanced", "aggressive"] = "balanced",
    ) -> FinalStrategy:
        if not self.executor:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        user_input = self._prepare_user_input(pools_data, policy, risk)

        result = await self.executor.ainvoke({
            "user_input": user_input,
            "agent_scratchpad": [],
        })
        return self.result_processor.process_result(result)

    def _prepare_user_input(
        self,
        pools_data: list[dict[Any, Any]],
        policy: dict[str, Any] | str | None = None,
        risk: Literal["conservative", "balanced", "aggressive"] = "balanced",
    ) -> str:
        payload: dict[str, Any] = {"pools": pools_data, "risk_label": risk}
        if policy:
            payload["policy"] = policy

        return "Here is the pools data : \n" + json.dumps(payload, ensure_ascii=True)


# =========================
# Entry
# =========================
async def generate_strategy(
    pools_data: list[dict[Any, Any]],
    policy: dict[str, Any] | str | None = None,
    risk: Literal["conservative", "balanced", "aggressive"] = "balanced",
) -> FinalStrategy:
    orchestrator = OrchestratorAgent()
    await orchestrator.initialize()
    return await orchestrator.execute_strategy(pools_data, policy, risk)
