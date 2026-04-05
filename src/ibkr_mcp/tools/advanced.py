"""Advanced tools — market depth, tick data, bracket orders, histograms, watchlists."""

from __future__ import annotations

from typing import Any

from ib_async import LimitOrder, Order, TagValue
from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def register(mcp: FastMCP) -> None:
    # -----------------------------------------------------------------------
    # Market Depth (Level 2)
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def market_depth(
        symbol: str,
        num_rows: int = 10,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Get Level 2 order book (market depth) for a symbol.

        Returns top bid/ask rows. Requires Level 2 market data subscription.
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        ticker = ib.reqMktDepth(contract, numRows=num_rows)
        await ib.sleep(3)
        ib.cancelMktDepth(contract)

        bids = [
            {"price": d.price, "size": d.size, "marketMaker": d.marketMaker}
            for d in ticker.domBids
        ] if ticker.domBids else []
        asks = [
            {"price": d.price, "size": d.size, "marketMaker": d.marketMaker}
            for d in ticker.domAsks
        ] if ticker.domAsks else []

        return {"symbol": symbol, "bids": bids, "asks": asks}

    @mcp.tool()
    async def market_depth_exchanges() -> list[dict[str, Any]]:
        """List exchanges that provide Level 2 (market depth) data."""
        ib = await core.get_ib()
        exchanges = await ib.reqMktDepthExchangesAsync()
        return [
            {
                "exchange": e.exchange,
                "secType": e.secType,
                "listingExch": e.listingExch,
                "serviceDataType": e.serviceDataType,
            }
            for e in exchanges
        ]

    # -----------------------------------------------------------------------
    # Tick-by-tick & historical ticks
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def tick_by_tick_data(
        symbol: str,
        tick_type: str = "Last",
        num_ticks: int = 100,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Get real-time tick-by-tick data.

        tick_type: 'Last', 'AllLast', 'BidAsk', 'MidPoint'
        Collects ticks for ~5 seconds then returns.
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        ticker = ib.reqTickByTickData(contract, tick_type)
        await ib.sleep(5)
        ib.cancelTickByTickData(contract, tick_type)

        ticks = []
        if tick_type in ("Last", "AllLast"):
            for t in (ticker.tickByTicks or [])[:num_ticks]:
                ticks.append({
                    "time": str(t.time),
                    "price": t.price,
                    "size": t.size,
                })
        elif tick_type == "BidAsk":
            for t in (ticker.tickByTicks or [])[:num_ticks]:
                ticks.append({
                    "time": str(t.time),
                    "bidPrice": t.bidPrice,
                    "askPrice": t.askPrice,
                    "bidSize": t.bidSize,
                    "askSize": t.askSize,
                })
        return ticks

    @mcp.tool()
    async def historical_ticks(
        symbol: str,
        start_time: str = "",
        end_time: str = "",
        num_ticks: int = 1000,
        what_to_show: str = "TRADES",
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Get historical tick data.

        start_time/end_time: 'YYYYMMDD HH:MM:SS' format. Provide one, not both.
        what_to_show: TRADES, BID_ASK, MIDPOINT
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)

        if what_to_show == "TRADES":
            ticks = await ib.reqHistoricalTicksAsync(
                contract, start_time, end_time, num_ticks, "TRADES", useRth=True
            )
            return [
                {
                    "time": str(t.time),
                    "price": t.price,
                    "size": t.size,
                }
                for t in ticks[:num_ticks]
            ]
        else:
            ticks = await ib.reqHistoricalTicksAsync(
                contract, start_time, end_time, num_ticks, what_to_show, useRth=True
            )
            return [
                {
                    "time": str(t.time),
                    "priceBid": t.priceBid,
                    "priceAsk": t.priceAsk,
                    "sizeBid": t.sizeBid,
                    "sizeAsk": t.sizeAsk,
                }
                for t in ticks[:num_ticks]
            ]

    # -----------------------------------------------------------------------
    # Histogram
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def histogram_data(
        symbol: str,
        use_rth: bool = True,
        duration: str = "1 W",
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Get price histogram data showing price distribution over a period."""
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        data = await ib.reqHistogramDataAsync(contract, use_rth, duration)
        return [{"price": h.price, "count": h.count} for h in data]

    # -----------------------------------------------------------------------
    # Bracket Orders
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def bracket_order(
        symbol: str,
        action: str,
        quantity: float,
        limit_price: float,
        take_profit_price: float,
        stop_loss_price: float,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        tif: str = "GTC",
    ) -> dict[str, Any]:
        """Place a bracket order (entry + take-profit + stop-loss).

        Creates three linked orders:
        1. Parent: Limit entry order
        2. Take profit: Limit order at take_profit_price
        3. Stop loss: Stop order at stop_loss_price

        All three are OCA-linked — if one fills, the others adjust accordingly.
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)

        bracket = ib.bracketOrder(
            action.upper(), quantity, limit_price, take_profit_price, stop_loss_price
        )

        trades = []
        for order in bracket:
            order.tif = tif
            trade = ib.placeOrder(contract, order)
            trades.append(trade)

        await ib.sleep(1)

        return {
            "parent": {
                "orderId": trades[0].order.orderId,
                "status": trades[0].orderStatus.status,
                "action": action,
                "limitPrice": limit_price,
            },
            "takeProfit": {
                "orderId": trades[1].order.orderId,
                "status": trades[1].orderStatus.status,
                "limitPrice": take_profit_price,
            },
            "stopLoss": {
                "orderId": trades[2].order.orderId,
                "status": trades[2].orderStatus.status,
                "stopPrice": stop_loss_price,
            },
        }

    # -----------------------------------------------------------------------
    # Watchlist helpers
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def watchlist_quotes(
        symbols: list[str],
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Get snapshot quotes for a list of symbols at once.

        Useful for building a watchlist view.
        """
        ib = await core.get_ib()
        results = []
        contracts = []
        for sym in symbols:
            c = core.build_contract(sym, sec_type, exchange, currency)
            contracts.append(c)

        qualified = await ib.qualifyContractsAsync(*contracts)
        tickers = []
        for c in qualified:
            t = ib.reqMktData(c, snapshot=True)
            tickers.append((c, t))

        await ib.sleep(3)

        for c, t in tickers:
            ib.cancelMktData(c)
            results.append({
                "symbol": c.symbol,
                "bid": t.bid,
                "ask": t.ask,
                "last": t.last,
                "close": t.close,
                "volume": t.volume,
                "change": round(t.last - t.close, 4) if t.last and t.close else None,
            })

        return results

    # -----------------------------------------------------------------------
    # Options analytics
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def option_greeks(
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Get option greeks (delta, gamma, theta, vega, implied vol) for a specific option.

        Args:
            right: 'C' for call, 'P' for put
            expiry: 'YYYYMMDD' format
        """
        ib = await core.get_ib()
        contract = core.build_contract(
            symbol, "OPT", exchange, currency, expiry=expiry, strike=strike, right=right
        )
        contract = await core.qualify_contract(contract)
        ticker = ib.reqMktData(contract, snapshot=True)
        await ib.sleep(3)
        ib.cancelMktData(contract)

        greeks = ticker.modelGreeks or ticker.lastGreeks
        if greeks:
            return {
                "symbol": symbol,
                "expiry": expiry,
                "strike": strike,
                "right": right,
                "impliedVol": greeks.impliedVol,
                "delta": greeks.delta,
                "gamma": greeks.gamma,
                "theta": greeks.theta,
                "vega": greeks.vega,
                "optPrice": greeks.optPrice,
                "undPrice": greeks.undPrice,
            }
        return {
            "symbol": symbol,
            "expiry": expiry,
            "strike": strike,
            "right": right,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "greeks": "unavailable — market may be closed or no subscription",
        }

    @mcp.tool()
    async def calculate_implied_vol(
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        option_price: float,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Calculate implied volatility for a given option price.

        Uses IB's server-side calculation.
        """
        ib = await core.get_ib()
        contract = core.build_contract(
            symbol, "OPT", exchange, currency, expiry=expiry, strike=strike, right=right
        )
        contract = await core.qualify_contract(contract)
        ticker = ib.reqMktData(contract, snapshot=True)
        await ib.sleep(2)

        # Use the underlying price from the ticker
        und_price = ticker.modelGreeks.undPrice if ticker.modelGreeks else ticker.last

        iv = await ib.calculateImpliedVolatilityAsync(
            contract, option_price, und_price
        )
        ib.cancelMktData(contract)

        if iv:
            return {
                "symbol": symbol,
                "optionPrice": option_price,
                "impliedVol": iv.impliedVol,
                "delta": iv.delta,
                "gamma": iv.gamma,
                "vega": iv.vega,
                "theta": iv.theta,
            }
        return {"error": "Could not calculate implied volatility"}

    @mcp.tool()
    async def calculate_option_price(
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        volatility: float,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Calculate theoretical option price for a given volatility.

        Uses IB's server-side calculation.
        """
        ib = await core.get_ib()
        contract = core.build_contract(
            symbol, "OPT", exchange, currency, expiry=expiry, strike=strike, right=right
        )
        contract = await core.qualify_contract(contract)
        ticker = ib.reqMktData(contract, snapshot=True)
        await ib.sleep(2)

        und_price = ticker.modelGreeks.undPrice if ticker.modelGreeks else ticker.last

        result = await ib.calculateOptionPriceAsync(
            contract, volatility, und_price
        )
        ib.cancelMktData(contract)

        if result:
            return {
                "symbol": symbol,
                "volatility": volatility,
                "optPrice": result.optPrice,
                "delta": result.delta,
                "gamma": result.gamma,
                "vega": result.vega,
                "theta": result.theta,
            }
        return {"error": "Could not calculate option price"}

    # -----------------------------------------------------------------------
    # Option Exercise
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def option_exercise(
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        exercise_quantity: int,
        action: int = 1,
        account: str = "",
        override: int = 0,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Exercise or lapse an option position.

        Args:
            action: 1 = exercise, 2 = lapse
            exercise_quantity: Number of contracts to exercise/lapse
            override: Set to 1 to override system's precautionary checks
            account: Account ID (leave blank for default)
        """
        ib = await core.get_ib()
        contract = core.build_contract(
            symbol, "OPT", exchange, currency, expiry=expiry, strike=strike, right=right
        )
        contract = await core.qualify_contract(contract)
        acct = account or ib.managedAccounts()[0]
        ib.exerciseOptions(contract, action, exercise_quantity, acct, override)
        await ib.sleep(1)
        return {
            "symbol": symbol,
            "expiry": expiry,
            "strike": strike,
            "right": right,
            "action": "exercise" if action == 1 else "lapse",
            "quantity": exercise_quantity,
            "status": "submitted",
        }

    # -----------------------------------------------------------------------
    # Market Data Type Control
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def set_market_data_type(
        data_type: int = 1,
    ) -> dict[str, Any]:
        """Switch market data type for all subsequent requests.

        Args:
            data_type: 1=Live, 2=Frozen, 3=Delayed, 4=Delayed-Frozen

        Use Delayed (3) if you don't have live market data subscriptions.
        """
        ib = await core.get_ib()
        ib.reqMarketDataType(data_type)
        type_names = {1: "Live", 2: "Frozen", 3: "Delayed", 4: "Delayed-Frozen"}
        return {
            "marketDataType": data_type,
            "name": type_names.get(data_type, "Unknown"),
        }

    # -----------------------------------------------------------------------
    # Historical Schedule (Trading Hours)
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def historical_schedule(
        symbol: str,
        num_days: int = 5,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Get trading hours/sessions schedule for a contract.

        Returns the trading sessions for the last N days including
        start/end times and timezone.
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)
        schedule = await ib.reqHistoricalScheduleAsync(
            contract, numDays=num_days, endDateTime="", useRTH=True
        )
        if not schedule:
            return {"symbol": symbol, "sessions": []}

        return {
            "symbol": symbol,
            "startDateTime": schedule.startDateTime,
            "endDateTime": schedule.endDateTime,
            "timeZone": schedule.timeZone,
            "sessions": [
                {
                    "startDateTime": s.startDateTime,
                    "endDateTime": s.endDateTime,
                    "refDate": s.refDate,
                }
                for s in (schedule.sessions or [])
            ],
        }

    # -----------------------------------------------------------------------
    # Market Rules (Tick Size)
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def market_rule(
        market_rule_id: int,
    ) -> list[dict[str, Any]]:
        """Get tick size rules (price increments) for a market rule ID.

        Market rule IDs can be found in contract_details results.
        Returns a list of price increments: below a certain low edge, the min tick is X.
        """
        ib = await core.get_ib()
        increments = await ib.reqMarketRuleAsync(market_rule_id)
        return [
            {"lowEdge": inc.lowEdge, "increment": inc.increment}
            for inc in increments
        ]

    # -----------------------------------------------------------------------
    # News Bulletins (Exchange-Wide)
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def news_bulletins(subscribe: bool = True) -> list[dict[str, Any]]:
        """Subscribe to or get exchange-wide news bulletins.

        These are system-wide messages from exchanges (halts, warnings, etc.).
        """
        ib = await core.get_ib()
        if subscribe:
            ib.reqNewsBulletins(allMessages=True)
            await ib.sleep(2)
        bulletins = ib.newsBulletins()
        if not subscribe:
            ib.cancelNewsBulletins()
        return [
            {
                "msgId": b.msgId,
                "msgType": b.msgType,
                "message": b.message,
                "origExchange": b.origExchange,
            }
            for b in bulletins
        ]
