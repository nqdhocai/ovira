import asyncio
import logging
import re
import urllib.parse

from agents.model import get_llm_model
from agents.result_processor import ResultProcessor
from config.settings import mcp_config
from database.models import AgentMessages
from database.mongodb import MongoDB
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.globals import set_verbose
from langchain.prompts import ChatPromptTemplate
from langchain.tools import BaseTool, StructuredTool
from langchain_core.tools.base import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field
from utils.helpers import get_tools_description, json_to_key_value_str

set_verbose(True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CoralParams(BaseModel):
    agentId: str
    agentDescription: str


class SSEParams(BaseModel):
    transport: str = "sse"
    url: str
    timeout: int = 60000
    sse_read_timeout: int = 60000


class BaseAgent:
    def __init__(
        self,
        system_prompt: str,
        agent_params: CoralParams,
        mcp_server: dict[str, SSEParams] | None = None,
        agent_tools: list[BaseTool] | None = None,
    ):
        self.system_prompt: str = system_prompt.strip()
        self.agent_params: CoralParams = agent_params
        self.mcp_server: dict[str, SSEParams] | None = mcp_server
        self.agent_tools: list[BaseTool] | None = agent_tools

    async def create_agent(
        self, coral_tools: list[BaseTool], agent_tools: list[BaseTool]
    ):
        coral_tools_description = get_tools_description(coral_tools)
        agent_tools_description = get_tools_description(agent_tools)
        combined_tools = coral_tools + agent_tools

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                self.system_prompt.format(
                    coral_tools_description=coral_tools_description,
                    agent_tools_description=agent_tools_description,
                ),
            ),
            ("placeholder", "{agent_scratchpad}"),
        ])

        model = get_llm_model()

        agent = create_tool_calling_agent(model, combined_tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=combined_tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=50,
            return_intermediate_steps=True,
        )

    async def run_loop(self):
        base_url: str = mcp_config.CORAL_SSE_URL

        query_string: str = urllib.parse.urlencode(self.agent_params.model_dump())

        CORAL_SERVER_URL = f"{base_url}?{query_string}"
        timeout = mcp_config.TIMEOUT_MS if mcp_config.TIMEOUT_MS else 60_000

        mcp_connections: dict[str, dict[str, str | int]] = {
            "coral": {
                "transport": "sse",
                "url": CORAL_SERVER_URL,
                "timeout": timeout,
                "sse_read_timeout": timeout,
            }
        }
        if self.mcp_server:
            for server_name, params in self.mcp_server.items():
                mcp_connections[server_name] = {
                    "transport": params.transport,
                    "url": params.url,
                    "timeout": params.timeout,
                    "sse_read_timeout": params.sse_read_timeout,
                }

        client = MultiServerMCPClient(connections=mcp_connections)

        logger.info(
            f"Multi Server Connection of {self.agent_params.agentId} Initialized"
        )

        coral_tools: list[BaseTool] = await client.get_tools(server_name="coral")
        _tools_by_name = {t.name: t for t in coral_tools}
        if "wait_for_mentions" in _tools_by_name:
            _wait_real = _tools_by_name["wait_for_mentions"]

            class _WaitArgs(BaseModel):
                threadId: str | None = Field(
                    default=None, description="Thread ID (optional)"
                )
                timeoutMs: int | None = Field(
                    default=60000, description="Timeout in ms (INTEGER)"
                )

            async def _wait_wrapper(
                threadId: str | None = None, timeoutMs: int | None = 60000
            ):
                args = {}
                if threadId:
                    args["threadId"] = threadId
                # ÉP KIỂU: nếu LLM đưa 60000.0 → int(60000.0) = 60000
                args["timeoutMs"] = int(timeoutMs if timeoutMs is not None else 60000)
                return await _wait_real.ainvoke(args)

            wait_fixed = StructuredTool.from_function(
                coroutine=_wait_wrapper,
                name="wait_for_mentions",  # GIỮ NGUYÊN TÊN để LLM vẫn gọi đúng
                description="Wait for mentions; 'timeoutMs' MUST be integer milliseconds (e.g., 60000).",
                args_schema=_WaitArgs,
            )

            # Thay tool gốc bằng wrapper
            coral_tools = [
                wait_fixed if t.name == "wait_for_mentions" else t for t in coral_tools
            ]

        if "send_message" in _tools_by_name:
            _send_real = _tools_by_name["send_message"]

            class _SendArgs(BaseModel):
                threadId: str | None = Field(description="Thread ID (REQUIRED)")
                content: str = Field(
                    default="", description="Content to send (REQUIRED)"
                )
                mentions: list[str] = Field(
                    default=[], description="List of agent IDs to mention (REQUIRED)"
                )

            async def _send_wrapper(
                threadId: str, content: str = "", mentions: list[str] = []
            ):
                if content == "answer":
                    return "Tool call is error, please retry with the strategy | verifier | critic | planner content."
                args = {}
                args["threadId"] = threadId
                args["content"] = content
                args["mentions"] = mentions

                timestamp = int(asyncio.get_event_loop().time() * 1000)
                status = re.search(r'"status"\s*:\s*"([^"]+)"', content)
                if status:
                    status = status.group(1).replace('"status": ', "")

                try:
                    content = json_to_key_value_str(content)
                except Exception:
                    pass

                mongo_client = MongoDB()
                _ = await mongo_client.insert_agent_messages([
                    AgentMessages(
                        role=self.agent_params.agentId.upper(),
                        content=content,
                        timestamp=timestamp,
                        thread_id=threadId,
                        message_id="agent-" + str(timestamp),
                        status=status if status else "DRAFT",
                    )
                ])
                return await _send_real.ainvoke(args)

            send_fixed = StructuredTool.from_function(
                coroutine=_send_wrapper,
                name="send_message",
                description="Send a message; 'threadId', 'content' and 'mentions' MUST be provided.",
                args_schema=_SendArgs,
            )

            coral_tools = [
                send_fixed if t.name == "send_message" else t for t in coral_tools
            ]

        agent_tools: list[BaseTool] = self.agent_tools or []

        for server_name in mcp_connections.keys():
            if server_name != "coral":
                tools = await client.get_tools(server_name=server_name)
                agent_tools.extend(tools)

        logger.info(
            f"Coral tools count: {len(coral_tools)}, Agent tools count: {len(agent_tools)}"
        )

        agent_executor = await self.create_agent(coral_tools, agent_tools)
        while True:
            try:
                logger.info("Starting new agent invocation")
                output = await agent_executor.ainvoke({"agent_scratchpad": []})
                reasoning_trace = ResultProcessor().build_reasoning_trace(
                    agent_payload=output.get("output", ""),
                    include_tool_calls=False,
                )
                logger.info(output.get("output", ""))
                mongo_client = MongoDB()
                _ = await mongo_client.insert_agent_messages([
                    AgentMessages(
                        role=m.role,
                        content=m.content,
                        timestamp=m.timestamp_ms,
                        thread_id=m.thread_id,
                        message_id=m.message_id,
                        status=m.status.value,
                    )
                    for m in reasoning_trace
                    if (
                        m.timestamp_ms is not None
                        and m.thread_id is not None
                        and m.message_id is not None
                        and m.status is not None
                    )
                ])
                logger.info("Completed agent invocation, restarting loop")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                await asyncio.sleep(15)
