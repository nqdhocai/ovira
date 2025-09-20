import asyncio

from agents.base_agent import BaseAgent, CoralParams
from prompts.agents import *

# data_curator = BaseAgent(
#     system_prompt=DATA_CURATOR_PROMPT,
#     agent_params=CoralParams(
#         agentId="data-curator",
#         agentDescription="Data Curator Agent responsible for receiving raw pool data (JSON format) and converting them into cleaned feature_cards",
#     ),
# )

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
    agent_tools=[],
)

critic_agent = BaseAgent(
    system_prompt=CRITIC_PROMPT,
    agent_params=CoralParams(
        agentId="critic",
        agentDescription="Critic Agent that receives feedback from Verifier and evaluates PlanCandidate from Planner, provides guidance and change requests to improve the plan.",
    ),
)

# final_agent = BaseAgent(
#     system_prompt=FINAL_PROMPT,
#     agent_params=CoralParams(
#         agentId="finalizer",
#         agentDescription="The Finalizer Agent aggregates all information, summarizes the discussion from Critic, Planner, and Verifier, and returns the final JSON containing both the strategy and the conversation summary.",
#     ),
# )

# summarize_agent = BaseAgent(
#     system_prompt=REASONING_TRACE_PROMPT,
#     agent_params=CoralParams(
#         agentId="reasoning-trace",
#         agentDescription="An agent that collects and summarizes the reasoning traces from Planner, Critic, and Verifier into a concise format.",
#     ),
# )


async def start_agents_tasks():
    tasks = [
        # data_curator.run_loop(),
        planner_agent.run_loop(),
        verifier_agent.run_loop(),
        critic_agent.run_loop(),
        # final_agent.run_loop(),
        # summarize_agent.run_loop(),
    ]
    return [asyncio.create_task(c) for c in tasks]


# if __name__ == "__main__":
#     asyncio.run(start_agents())
