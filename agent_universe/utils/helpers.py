import json

from langchain.tools import BaseTool


def get_tools_description(tools: list[BaseTool]):
    return "\n".join(
        f"Tool: {tool.name}, Schema: {json.dumps(tool.args).replace('{', '{{').replace('}', '}}')}"
        for tool in tools
    )
