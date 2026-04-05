"""Scanner tools — market scanners and fundamental data."""

from __future__ import annotations

from typing import Any

from ib_async import ScannerSubscription
from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def scanner_run(
        scan_code: str = "TOP_PERC_GAIN",
        instrument: str = "STK",
        location_code: str = "STK.US.MAJOR",
        above_price: float = 1.0,
        below_price: float = 0.0,
        above_volume: int = 100000,
        number_of_rows: int = 20,
    ) -> list[dict[str, Any]]:
        """Run a market scanner.

        Common scan_codes: TOP_PERC_GAIN, TOP_PERC_LOSE, MOST_ACTIVE,
        HOT_BY_VOLUME, HIGH_VS_52W_HL, LOW_VS_52W_HL,
        TOP_OPEN_PERC_GAIN, TOP_OPEN_PERC_LOSE, HIGH_OPT_IMP_VOLAT,
        TOP_TRADE_COUNT, TOP_TRADE_RATE, TOP_PRICE_RANGE.
        """
        ib = await core.get_ib()
        sub = ScannerSubscription(
            instrument=instrument,
            locationCode=location_code,
            scanCode=scan_code,
            abovePrice=above_price,
            numberOfRows=number_of_rows,
        )
        if below_price > 0:
            sub.belowPrice = below_price
        if above_volume > 0:
            sub.aboveVolume = above_volume

        results = await ib.reqScannerDataAsync(sub)
        return [
            {
                "rank": r.rank,
                "symbol": r.contractDetails.contract.symbol,
                "secType": r.contractDetails.contract.secType,
                "exchange": r.contractDetails.contract.primaryExchange,
                "currency": r.contractDetails.contract.currency,
                "longName": r.contractDetails.longName,
                "distance": r.distance,
                "benchmark": r.benchmark,
                "projection": r.projection,
                "legsStr": r.legsStr,
            }
            for r in results
        ]

    @mcp.tool()
    async def scanner_parameters() -> str:
        """Get the XML document describing all available scanner parameters.

        Returns a (large) XML string — use to discover valid scan codes,
        instrument types, and location codes.
        """
        ib = await core.get_ib()
        xml = await ib.reqScannerParametersAsync()
        # Truncate to avoid overwhelming context
        if len(xml) > 10000:
            return xml[:10000] + "\n... [truncated — full XML is very large]"
        return xml

    @mcp.tool()
    async def fundamental_data(
        symbol: str,
        report_type: str = "ReportSnapshot",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> str:
        """Get fundamental data for a stock.

        report_type options:
            ReportSnapshot — company overview
            ReportsFinSummary — financial summary
            ReportRatios — financial ratios
            ReportsOwnership — ownership data
            RESC — analyst estimates
            CalendarReport — upcoming events
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, "STK", exchange, currency)
        contract = await core.qualify_contract(contract)
        data = await ib.reqFundamentalDataAsync(contract, reportType=report_type)
        if data and len(data) > 15000:
            return data[:15000] + "\n... [truncated]"
        return data or "No fundamental data available"

    @mcp.tool()
    async def news_headlines(
        symbol: str = "",
        provider_codes: str = "BZ+FLY",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent news headlines, optionally filtered by symbol.

        provider_codes: BZ (Benzinga), FLY (Fly On The Wall), DJ (Dow Jones), etc.
        """
        ib = await core.get_ib()
        if symbol:
            contract = core.build_contract(symbol, "STK", "SMART", "USD")
            contract = await core.qualify_contract(contract)
            headlines = await ib.reqHistoricalNewsAsync(
                contract.conId, provider_codes, "", "", max_results
            )
        else:
            headlines = await ib.reqNewsProvidersAsync()
            return [{"code": p.code, "name": p.name} for p in headlines]

        return [
            {
                "time": str(h.time),
                "providerCode": h.providerCode,
                "articleId": h.articleId,
                "headline": h.headline,
            }
            for h in headlines
        ]

    @mcp.tool()
    async def news_article(
        provider_code: str,
        article_id: str,
    ) -> dict[str, Any]:
        """Get the full text of a news article by provider code and article ID."""
        ib = await core.get_ib()
        article = await ib.reqNewsArticleAsync(provider_code, article_id)
        return {
            "articleType": article.articleType,
            "articleText": article.articleText[:10000] if article.articleText else None,
        }
