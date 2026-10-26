"""Run with: python -m agent.mcp_server (local stdio only)."""
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from agent.data_access import SportsDataAccess
from agent.tools.sports_data import make_sports_queries
from backend.app.config.container import build_container
from backend.app.config.settings import get_settings


class _Lazy:
    """Forward attribute access to a service that only exists once the server loop is running."""

    def __init__(self, resolve):
        self._resolve = resolve

    def __getattr__(self, name):
        return getattr(self._resolve(), name)


_container = None


@asynccontextmanager
async def lifespan(_server):
    global _container
    _container = await build_container(get_settings())
    try:
        yield
    finally:
        await _container.aclose()
        _container = None


access = SportsDataAccess(
    venues=_Lazy(lambda: _container.venues),
    bookings=_Lazy(lambda: _container.bookings),
    programmes=_Lazy(lambda: _container.programmes),
)

server = MCPServer("hk-sports-data", lifespan=lifespan, instructions=(
    "Read-only Hong Kong LCSD/CSDI sports data. Discover filters with get_sports_catalog. "
    "Missing availability is unknown, never full. No bookings, payments or navigation estimates."))
for query in make_sports_queries(access):
    server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                           idempotentHint=True, openWorldHint=True))(query)

if __name__ == "__main__":
    server.run(transport="stdio")
