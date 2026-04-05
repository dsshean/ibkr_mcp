"""Market data tools — quotes, historical bars, ticker snapshots."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def quote_get(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Get a real-time quote snapshot (bid, ask, last, volume, etc.)."""
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        ticker = ib.reqMktData(contract, snapshot=True)
        await ib.sleep(2)  # allow data to arrive
        ib.cancelMktData(contract)
        return {
            "symbol": symbol,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "close": ticker.close,
            "high": ticker.high,
            "low": ticker.low,
            "open": ticker.open,
            "volume": ticker.volume,
            "time": str(ticker.time) if ticker.time else None,
        }

    @mcp.tool()
    async def data_get_ohlcv(
        symbol: str,
        duration: str = "1 D",
        bar_size: str = "5 mins",
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        summary: bool = True,
    ) -> dict[str, Any]:
        """Get historical OHLCV bar data.

        Args:
            symbol: Ticker symbol (e.g. AAPL, EURUSD, ES)
            duration: Time span — "1 D", "1 W", "1 M", "1 Y", "60 S", etc.
            bar_size: Bar granularity — "1 min", "5 mins", "15 mins", "1 hour", "1 day", etc.
            what_to_show: TRADES, MIDPOINT, BID, ASK, HISTORICAL_VOLATILITY, OPTION_IMPLIED_VOLATILITY
            use_rth: Regular trading hours only
            summary: If true, return stats + last 5 bars instead of full history
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
        )
        if not bars:
            return {"symbol": symbol, "bars": [], "count": 0}

        bar_dicts = [
            {
                "date": str(b.date),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "average": b.average,
                "barCount": b.barCount,
            }
            for b in bars
        ]

        if summary and len(bar_dicts) > 5:
            closes = [b.close for b in bars]
            highs = [b.high for b in bars]
            lows = [b.low for b in bars]
            volumes = [b.volume for b in bars]
            return {
                "symbol": symbol,
                "count": len(bar_dicts),
                "range": f"{bar_dicts[0]['date']} → {bar_dicts[-1]['date']}",
                "stats": {
                    "high": max(highs),
                    "low": min(lows),
                    "avgClose": round(sum(closes) / len(closes), 4),
                    "totalVolume": sum(volumes),
                },
                "lastBars": bar_dicts[-5:],
            }

        return {"symbol": symbol, "count": len(bar_dicts), "bars": bar_dicts}

    @mcp.tool()
    async def market_data_subscribe(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Subscribe to streaming market data for a symbol.

        Returns the current ticker state. Data continues updating in background.
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        ticker = ib.reqMktData(contract)
        await ib.sleep(2)
        return {
            "symbol": symbol,
            "subscribed": True,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "volume": ticker.volume,
        }

    @mcp.tool()
    async def market_data_unsubscribe(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Cancel streaming market data for a symbol."""
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        ib.cancelMktData(contract)
        return {"symbol": symbol, "unsubscribed": True}

    @mcp.tool()
    async def realtime_bars_subscribe(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
    ) -> dict[str, Any]:
        """Subscribe to 5-second real-time bars.

        Returns confirmation. Bars update continuously in background.
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        bars = ib.reqRealTimeBars(contract, 5, what_to_show, use_rth)
        await ib.sleep(6)  # wait for first bar
        if bars:
            b = bars[-1]
            return {
                "symbol": symbol,
                "subscribed": True,
                "latestBar": {
                    "time": str(b.time),
                    "open": b.open_,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                },
            }
        return {"symbol": symbol, "subscribed": True, "latestBar": None}

    @mcp.tool()
    async def head_timestamp(
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        what_to_show: str = "TRADES",
    ) -> dict[str, Any]:
        """Get the earliest available data timestamp for a symbol."""
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        ts = await ib.reqHeadTimeStampAsync(
            contract, whatToShow=what_to_show, useRTH=True, formatDate=1
        )
        return {"symbol": symbol, "headTimestamp": str(ts) if ts else None}
