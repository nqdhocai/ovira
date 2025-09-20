import json
import re
from typing import Any

from langchain.tools import BaseTool


def json_to_key_value_str(json_str: str, indent: int = 2) -> str:
    """
    Convert JSON string to KEY: value format
    - Supports nested objects and lists
    - indent: number of spaces to indent each level
    """

    def format_value(value, level=0):
        prefix = " " * (level * indent)
        if isinstance(value, dict):
            lines = []
            for k, v in value.items():
                if k == "status":
                    continue
                if isinstance(v, (dict, list)):
                    lines.append(f"**{prefix}{k.upper()}**:")
                    lines.append(format_value(v, level + 1))
                    lines.append("\n")  # Add a blank line after nested structures
                else:
                    lines.append(f"{prefix}{k.upper()}: {v}")
            return "\n".join(lines)
        elif isinstance(value, list):
            lines = []
            for idx, item in enumerate(value, start=1):
                lines.append(format_value(item, level + 1))
            return "\n".join(lines)
        else:
            return f"{prefix}{value}"

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    return format_value(data)


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
