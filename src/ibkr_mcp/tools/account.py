"""Account tools — summary, balances, positions, P&L."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def account_summary(account: str = "") -> list[dict[str, Any]]:
        """Get account summary (net liquidation, buying power, cash, etc.).

        Leave account blank to use the first managed account.
        """
        ib = await core.get_ib()
        acct = account or ib.managedAccounts()[0]
        summary = await ib.accountSummaryAsync(acct)
        return [
            {"tag": s.tag, "value": s.value, "currency": s.currency}
            for s in summary
        ]

    @mcp.tool()
    async def account_values(account: str = "") -> list[dict[str, Any]]:
        """Get all account values (detailed key-value pairs)."""
        ib = await core.get_ib()
        acct = account or ib.managedAccounts()[0]
        vals = ib.accountValues(acct)
        return [
            {
                "tag": v.tag,
                "value": v.value,
                "currency": v.currency,
                "account": v.account,
            }
            for v in vals
        ]

    @mcp.tool()
    async def account_pnl(account: str = "") -> dict[str, Any]:
        """Get real-time P&L for the account."""
        ib = await core.get_ib()
        acct = account or ib.managedAccounts()[0]
        pnl_list = ib.pnl(acct)
        if not pnl_list:
            # Subscribe and wait briefly
            sub = ib.reqPnL(acct)
            await ib.sleep(1)
            return {
                "account": acct,
                "dailyPnL": sub.dailyPnL,
                "unrealizedPnL": sub.unrealizedPnL,
                "realizedPnL": sub.realizedPnL,
            }
        p = pnl_list[0]
        return {
            "account": acct,
            "dailyPnL": p.dailyPnL,
            "unrealizedPnL": p.unrealizedPnL,
            "realizedPnL": p.realizedPnL,
        }

    @mcp.tool()
    async def managed_accounts() -> list[str]:
        """List all managed accounts."""
        ib = await core.get_ib()
        return ib.managedAccounts()
