# llm/strategy_updated.py

import json
import os
from string import Template

import google.generativeai as genai
from dotenv import load_dotenv

from configs import get_logger
from mongo.schemas import UpdatedInfo, VaultsStrategy

_ = load_dotenv()
logger = get_logger("strategy_changes_by_llm")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


model = genai.GenerativeModel(
    "gemini-2.0-flash", generation_config={"response_mime_type": "application/json"}
)

PROMPT_TPL = Template(
    """
You are a precise differ that compares TWO DeFi strategies and emits recent actions for a UI table.

SCHEMA OF EACH INPUT
{
  "strategy": {
    "risk_label": "balanced|conservative|aggressive|...",
    "allocations": [{"pool_name": "string", "weight_pct": "float number"}]
  },
  reasoning_trace: [{"role": "string", "content": "string"}]
}

INPUT
last_strategy:
$last

new_strategy:
$new

TASK
Return ONLY a JSON object with this exact shape:
{
  "action": "Rebalance"|"Add Pool"|"Remove Pool"|"Risk Profile Change"|"Rationale Update"|"No Changes",
  "details": "string"    
}

RULES
1) Build allocation maps by pool_name (trim spaces; compare case-insensitively).
2) Added pools → one item per pool: {"action":"Add Pool","details":"+<INT%> to <pool_name>"}.
3) Removed pools → one item per pool: {"action":"Remove Pool","details":"-<INT%> from <pool_name>"}.
4) Weight changes for common pools (ignore |delta| < 0.01):
   Emit ONE "Rebalance" item summarizing up to 3 biggest changes, comma-separated, ordered by |delta| desc:
   • Positive: "+X% to <pool_name>"
   • Negative: "-X% from <pool_name>"
   If >3 changes, append ", and N more". Round X to nearest integer and include %.
5) Risk label change → {"action":"Risk Profile Change","details":"<old> → <new>"}.
6) Reasons/critic_notes changed (after lowercasing & whitespace collapsing) → {"action":"Rationale Update","details":"rationale/notes updated"}.
7) If no differences → exactly {"action":"No Changes","details":"Strategy unchanged"}.
8) Style: use pool_name from input; keep details crisp (e.g., "+5% to ABCD-test").
9) Output MUST be valid JSON only (no code fences, no markdown, no extra keys).
"""
)


def get_strategy_changes(
    new_strategy: VaultsStrategy, last_strategy: VaultsStrategy
) -> UpdatedInfo:
    try:
        prompt = PROMPT_TPL.substitute(
            last=json.dumps(last_strategy.strategy.model_dump(), ensure_ascii=False),
            new=json.dumps(new_strategy.strategy.model_dump(), ensure_ascii=False),
        )
        resp = model.generate_content(prompt)
        data = json.loads(resp.text)
        return UpdatedInfo.model_validate(data)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
