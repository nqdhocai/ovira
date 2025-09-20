from __future__ import annotations

import json
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any, Literal

# App-specific deps
from agents.model import get_llm_model
from agents.models import FinalStrategy
from agents.result_processor import ResultProcessor
from config.settings import mcp_config
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
from langchain_core.prompts import MessagesPlaceholder
from langchain_mcp_adapters.client import MultiServerMCPClient
from prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from pydantic import BaseModel, Field
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

    @staticmethod
    def _create_send_tool_wrapper(send_real):
        class SendArgs(BaseModel):
            threadId: str = Field(description="Thread ID (REQUIRED)")
            content: str = Field(description="Message content (REQUIRED)")
            mentions: list[str] | None = Field(
                default=None, description="List of agent IDs to mention (REQUIRED)"
            )

        async def send_wrapper(
            threadId: str, content: str, mentions: list[str] | None = None
        ):
            args: dict[str, Any] = {
                "threadId": threadId,
                "content": content,
                "mentions": mentions or [],
            }
            return await send_real.ainvoke(args)

        return StructuredTool.from_function(
            coroutine=send_wrapper,
            name="send_message",
            description="Send a message to a thread; 'threadId', 'mentions' and 'content' are REQUIRED.",
            args_schema=SendArgs,
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
            max_iterations=50,
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

        return await self.result_processor.process_result(result)

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
