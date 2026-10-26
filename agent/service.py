from contextlib import AsyncExitStack
from pathlib import Path
import sys

from agents import Agent, OpenAIResponsesModel, RunConfig, Runner
from openai import AsyncOpenAI

from agent.data_access import SportsDataAccess
from agent.prompts import SPORTS_ASSISTANT_INSTRUCTIONS
from agent.tools.sports_data import make_sports_tools
from agents.mcp import MCPServerStdio


async def run_sports_assistant(
    message: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
    access: SportsDataAccess,
    tool_transport: str = "function",
    history: list[dict[str, str]] | None = None,
) -> str:
    if tool_transport not in {"function", "mcp_stdio"}:
        raise ValueError("Unsupported agent tool transport")
    # Credentials stay server-side; disable OpenAI tracing for the B.AI provider.
    async with AsyncOpenAI(
        api_key=api_key, base_url=base_url, timeout=40.0, max_retries=0
    ) as client, AsyncExitStack() as stack:
        servers = []
        if tool_transport == "mcp_stdio":
            server = MCPServerStdio(
                params={"command": sys.executable, "args": ["-m", "agent.mcp_server"],
                        "cwd": str(Path(__file__).resolve().parents[1]), "env": {}},
                name="hk-sports-data", cache_tools_list=True,
                client_session_timeout_seconds=90,
            )
            servers.append(await stack.enter_async_context(server))
        assistant = Agent(
            name="HK SportFinder",
            instructions=SPORTS_ASSISTANT_INSTRUCTIONS,
            model=OpenAIResponsesModel(model=model, openai_client=client),
            tools=make_sports_tools(access) if tool_transport == "function" else [],
            mcp_servers=servers,
        )
        result = await Runner.run(
            assistant,
            [*(history or []), {"role": "user", "content": message}],
            max_turns=8,
            run_config=RunConfig(tracing_disabled=True),
        )
        return str(result.final_output)
