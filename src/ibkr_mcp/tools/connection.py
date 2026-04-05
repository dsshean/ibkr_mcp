"""Connection & health-check tools — equivalent to tv_health_check / tv_launch."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def ib_connect(
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        readonly: bool = False,
    ) -> dict:
        """Connect to TWS or IB Gateway.

        Ports: 7496=TWS live, 7497=TWS paper, 4001=Gateway live, 4002=Gateway paper.
        """
        return await core.connect(host, port, client_id, readonly)

    @mcp.tool()
    async def ib_disconnect() -> dict:
        """Disconnect from TWS / IB Gateway."""
        return await core.disconnect()

    @mcp.tool()
    async def ib_health_check() -> dict:
        """Check connection status and return account info."""
        return await core.health_check()

    @mcp.tool()
    async def ib_status() -> dict:
        """Return current connection state, managed accounts, and server version."""
        return await core.health_check()
