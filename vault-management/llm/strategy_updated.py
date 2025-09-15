import os

import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel

from mongo.schemas import UpdatedInfo, VaultsStrategy

_ = load_dotenv()  # take environment variables from .env.

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


def get_strategy_changes(
    new_strategy: VaultsStrategy, last_strategy: VaultsStrategy
) -> UpdatedInfo:
    prompt = f"""
    You are a precise differ that compares TWO DeFi strategies and emits recent actions for a UI table.

    SCHEMA OF EACH INPUT
    {
        "strategy": {
            "risk_label": "balanced|conservative|aggressive|...",
            "allocations": [{"pool_name": "string", "weight_pct": "float number" }]
        },
        "reasons": [ "string", ... ],
        "critic_notes": [ "string", ... ]
    }

    INPUT
    last_strategy:
    {last_strategy.model_dump()}

    new_strategy:
    {new_strategy.model_dump()}

    TASK
    Return ONLY a JSON object with this exact shape:
    {
        "actions": [
        {
            "action": "Rebalance"|"Add Pool"|"Remove Pool"|"Risk Profile Change"|"Rationale Update"|"No Changes",
            "details": "string"
        }
    ]
    }

    RULES
    1) Build allocation maps by pool_name (trim spaces; compare case-insensitively).
    2) Added pools (in new but not in last):
    Emit one item per pool:
    {"action": "Add Pool", "details": "+<INT%> to <pool_name>" }.
    3) Removed pools (in last but not in new):
    Emit one item per pool:
    {"action": "Remove Pool", "details": "-<INT%> from <pool_name>" }.
    4) Weight changes for common pools:
    delta = new.weight_pct - last.weight_pct. Ignore if |delta| < 0.01.
    Emit ONE "Rebalance" item summarizing the biggest changes (max 3 clauses), comma-separated, ordered by |delta| desc:
    • Positive: "+X% to <pool_name>"
    • Negative: "-X% from <pool_name>"
    If >3 changes, append ", and N more".
    Round X to nearest integer and include the % sign.
    5) Risk label change:
    If strategy.risk_label differs → {
        "action": "Risk Profile Change", "details": "<old> → <new>" }.
    6) Reasons / critic_notes change:
    If the concatenated texts differ after lowercasing & collapsing whitespace, emit:
    {"action": "Rationale Update", "details": "rationale/notes updated" }.
    Keep it short; do NOT invent content.
    7) If there are no differences at all:
    Emit exactly one item: {"action": "No Changes", "details": "Strategy unchanged" }.
    8) Style:
    - Use the pool_name from input; never invent names.
    - Keep details crisp, trader-style (e.g., "+5% to ABCD-test").
    9) Output MUST be valid JSON. Do NOT include code fences, explanations, markdown, or extra keys.

    NOW RETURN THE JSON ONLY.

    """
    response = model.generate_content(prompt=prompt)
    return UpdatedInfo.model_validate(response.json())
