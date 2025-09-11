import asyncio

from agents.base_agent import BaseAgent, CoralParams
from prompts.system_prompts import *

data_curator = BaseAgent(
    system_prompt=DATA_CURATOR_PROMPT,
    agent_params=CoralParams(
        agentId="data-curator",
        agentDescription="Data Curator Agent responsible for receiving raw pool data (JSON format) and converting them into cleaned feature_cards",
    ),
)

planner_agent = BaseAgent(
    system_prompt=PLANNER_PROMPT,
    agent_params=CoralParams(
        agentId="planner",
        agentDescription="Planner Agent that receives feature_cards data and policy to create PlanCandidate; and receives feedback from Critic to adjust PlanCandidate. (receives data in JSON format)",
    ),
)

verifier_agent = BaseAgent(
    system_prompt=VERIFIER_PROMPT,
    agent_params=CoralParams(
        agentId="verifier",
        agentDescription="Verifier Agent that receives JSON PlanCandidate data from Planner, checks validity and policy compliance, then responds back to Critic with identified issues for Critic to provide improvement strategies.",
    ),
)

critic_agent = BaseAgent(
    system_prompt=CRITIC_PROMPT,
    agent_params=CoralParams(
        agentId="critic",
        agentDescription="Critic Agent that receives feedback from Verifier and evaluates PlanCandidate from Planner, provides guidance and change requests to improve the plan.",
    ),
)

final_agent = BaseAgent(
    system_prompt=FINAL_PROMPT,
    agent_params=CoralParams(
        agentId="finalizer",
        agentDescription="Finalizer Agent that synthesizes discussion information from Critic + Planner + Verifier and returns final json format of strategy",
    ),
)


async def main():
    tasks = [
        data_curator.run_loop(),
        planner_agent.run_loop(),
        verifier_agent.run_loop(),
        critic_agent.run_loop(),
        final_agent.run_loop(),
    ]

    _ = await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
