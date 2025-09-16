import json
import re
from typing import Any

from langchain.tools import BaseTool


def get_tools_description(tools: list[BaseTool]):
    return "\n".join(
        f"Tool: {tool.name}, Schema: {json.dumps(tool.args).replace('{', '{{').replace('}', '}}')}"
        for tool in tools
    )


def extract_json_blocks(text: str) -> list[dict[str, Any]]:
    BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.IGNORECASE | re.DOTALL)

    results = []
    for match in BLOCK_RE.finditer(text):
        inner = match.group(1).strip()
        raw = match.group(0)
        parsed = None
        err = None
        try:
            parsed = json.loads(inner)
        except Exception as e:
            err = str(e)
        results.append({"raw": raw, "inner": inner, "parsed": parsed, "error": err})

    return [i["parsed"] for i in results if i["parsed"] is not None]
