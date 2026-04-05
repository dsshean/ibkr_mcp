"""Contract tools — search, details, qualification, option chains."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def _contract_to_dict(c) -> dict[str, Any]:
    return {
        "conId": c.conId,
        "symbol": c.symbol,
        "secType": c.secType,
        "exchange": c.exchange,
        "primaryExchange": getattr(c, "primaryExchange", ""),
        "currency": c.currency,
        "localSymbol": c.localSymbol,
        "tradingClass": getattr(c, "tradingClass", ""),
        "multiplier": getattr(c, "multiplier", ""),
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def contract_search(
        pattern: str,
    ) -> list[dict[str, Any]]:
        """Search for contracts by name or symbol pattern (e.g. 'AAPL', 'Euro', 'crude oil')."""
        ib = await core.get_ib()
        matches = await ib.reqMatchingSymbolsAsync(pattern)
        if not matches:
            return []
        results = []
        for m in matches:
            c = m.contract
            results.append(
                {
                    "conId": c.conId,
                    "symbol": c.symbol,
                    "secType": c.secType,
                    "primaryExchange": c.primaryExchange,
                    "currency": c.currency,
                    "derivativeSecTypes": list(m.derivativeSecTypes) if m.derivativeSecTypes else [],
                }
            )
        return results

    @mcp.tool()
    async def contract_details(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        con_id: int = 0,
    ) -> list[dict[str, Any]]:
        """Get full contract details including trading hours, min tick, valid exchanges."""
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency, con_id=con_id)
        details = await ib.reqContractDetailsAsync(contract)
        if not details:
            return []
        results = []
        for d in details:
            results.append(
                {
                    "contract": _contract_to_dict(d.contract),
                    "longName": d.longName,
                    "category": d.category,
                    "subcategory": d.subcategory,
                    "minTick": d.minTick,
                    "validExchanges": d.validExchanges,
                    "tradingHours": d.tradingHours,
                    "liquidHours": d.liquidHours,
                    "marketName": d.marketName,
                    "orderTypes": d.orderTypes,
                }
            )
        return results

    @mcp.tool()
    async def contract_qualify(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        expiry: str = "",
        strike: float = 0.0,
        right: str = "",
    ) -> dict[str, Any]:
        """Qualify a contract — fill in conId and missing fields via IB lookup."""
        contract = core.build_contract(
            symbol, sec_type, exchange, currency, expiry=expiry, strike=strike, right=right
        )
        qualified = await core.qualify_contract(contract)
        return _contract_to_dict(qualified)

    @mcp.tool()
    async def option_chain(
        symbol: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Get the option chain parameters (expirations and strikes) for an underlying."""
        ib = await core.get_ib()
        stock = core.build_contract(symbol, "STK", exchange, currency)
        stock = await core.qualify_contract(stock)
        chains = await ib.reqSecDefOptParamsAsync(
            stock.symbol, "", stock.secType, stock.conId
        )
        if not chains:
            return {"symbol": symbol, "chains": []}
        results = []
        for ch in chains:
            results.append(
                {
                    "exchange": ch.exchange,
                    "underlyingConId": ch.underlyingConId,
                    "tradingClass": ch.tradingClass,
                    "multiplier": ch.multiplier,
                    "expirations": sorted(ch.expirations),
                    "strikes": sorted(ch.strikes)[:50],  # cap for context size
                    "totalStrikes": len(ch.strikes),
                }
            )
        return {"symbol": symbol, "chains": results}

    @mcp.tool()
    async def matching_symbols(pattern: str) -> list[dict[str, Any]]:
        """Quick symbol lookup — returns matching symbols with security types."""
        ib = await core.get_ib()
        matches = await ib.reqMatchingSymbolsAsync(pattern)
        if not matches:
            return []
        return [
            {
                "symbol": m.contract.symbol,
                "secType": m.contract.secType,
                "primaryExchange": m.contract.primaryExchange,
                "currency": m.contract.currency,
            }
            for m in matches
        ]
