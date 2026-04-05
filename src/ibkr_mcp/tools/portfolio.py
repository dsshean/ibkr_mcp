"""Portfolio tools — positions, portfolio items, P&L per position."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def positions() -> list[dict[str, Any]]:
        """Get all positions across all accounts."""
        ib = await core.get_ib()
        pos_list = ib.positions()
        if not pos_list:
            pos_list = await ib.reqPositionsAsync()
        return [
            {
                "account": p.account,
                "symbol": p.contract.symbol,
                "secType": p.contract.secType,
                "exchange": p.contract.exchange,
                "currency": p.contract.currency,
                "position": float(p.position),
                "avgCost": p.avgCost,
                "conId": p.contract.conId,
            }
            for p in pos_list
        ]

    @mcp.tool()
    async def portfolio_items(account: str = "") -> list[dict[str, Any]]:
        """Get portfolio items with market value, unrealized P&L, etc."""
        ib = await core.get_ib()
        acct = account or ib.managedAccounts()[0]
        items = ib.portfolio(acct)
        return [
            {
                "symbol": pi.contract.symbol,
                "secType": pi.contract.secType,
                "conId": pi.contract.conId,
                "position": float(pi.position),
                "marketPrice": pi.marketPrice,
                "marketValue": pi.marketValue,
                "averageCost": pi.averageCost,
                "unrealizedPNL": pi.unrealizedPNL,
                "realizedPNL": pi.realizedPNL,
                "account": pi.account,
            }
            for pi in items
        ]

    @mcp.tool()
    async def position_pnl(
        con_id: int,
        account: str = "",
    ) -> dict[str, Any]:
        """Get real-time P&L for a single position by contract ID."""
        ib = await core.get_ib()
        acct = account or ib.managedAccounts()[0]
        pnl_single = ib.reqPnLSingle(acct, "", con_id)
        await ib.sleep(1)
        return {
            "conId": con_id,
            "account": acct,
            "dailyPnL": pnl_single.dailyPnL,
            "unrealizedPnL": pnl_single.unrealizedPnL,
            "realizedPnL": pnl_single.realizedPnL,
            "position": float(pnl_single.position) if pnl_single.position else 0,
            "value": pnl_single.value,
        }
