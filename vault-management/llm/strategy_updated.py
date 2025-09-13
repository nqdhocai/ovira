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
    You are a concise formatter that compares two DeFi strategies and emits recent actions for a UI table.

    INPUT
    last_strategy:
    {last_strategy.model_dump()}

    new_strategy:
    {new_strategy.model_dump()}

    TASK
    Compare the two strategies and output ONLY the differences as a JSON object with this exact shape:
    {
        "action": "Rebalance"|"Add Pool"|"Remove Pool"|"Risk Profile Change"|"Audit Update"|"No Changes",
        "details": "string (Note: max 20 words)"
    }
    
    

    RULES
    1) Consider allocations as maps pool_id -> weight_pct.
    2) Added pools (in new but not in last):
    - For each, emit: {
        "action": "Add Pool", "details": "+<INT %> to <pool_id or pool_name>" }.
    3) Removed pools (in last but not in new):
    - For each, emit: {
        "action": "Remove Pool", "details": "-<INT %> from <pool_id or pool_name>" }.
    4) Changed weights (pool appears in both):
    - delta = new.weight_pct - last.weight_pct.
    - Ignore float noise if |delta| < 0.01.
    - Emit ONE "Rebalance" action summarizing the top changes (max 3 clauses), comma-separated, ordered by |delta| desc.
        • Positive delta: "+X% to <label>"
        • Negative delta: "-X% from <label>"
        • If >3 changes, append ", and N more".
    5) Risk label changed (strategy.risk_label):
    - Emit: {"action": "Risk Profile Change", "details": "<old> → <new>" }.
    6) Audit changes (audit.summary or audit.rules_verification text differs):
    - Emit: {"action": "Audit Update", "details": "policy/audit text updated" }.
    7) If nothing changed at all:
    - Emit exactly one item: {"action": "No Changes", "details": "Strategy unchanged" }.
    8) Style for details:
    - Use trader-style, crisp phrases (e.g., "+5% to USDC Kamino", "-10% from CLMM").
    - Round percentages to nearest integer; always include the '%' sign.
    - Do NOT invent pools; if you don’t know a friendly name, use the pool_id from input.
    9) Output MUST be valid JSON. Do NOT include code fences, explanations, or extra keys. Return ONLY the JSON object.

    NOW PRODUCE THE JSON.
    """
    response = model.generate_content(prompt=prompt)
    return UpdatedInfo.model_validate(response.json())
