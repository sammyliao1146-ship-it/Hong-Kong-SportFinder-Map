import json
from collections.abc import Callable
from typing import Any

from agents import FunctionTool, function_tool


def make_data_status_tool(provider: Callable[[], dict[str, Any]]) -> FunctionTool:
    @function_tool
    def inspect_data_status() -> str:
        """Check which facility and booking data are actually connected."""
        return json.dumps(provider(), ensure_ascii=False)

    return inspect_data_status
