"""Order tools — place, modify, cancel, and query orders."""

from __future__ import annotations

from typing import Any

from ib_async import (
    LimitOrder,
    MarketOrder,
    StopOrder,
    StopLimitOrder,
    TrailingStopOrder,
    Order,
    Contract,
    ComboLeg,
    TagValue,
)
from mcp.server.fastmcp import FastMCP

from ibkr_mcp import core


def _trade_to_dict(trade) -> dict[str, Any]:
    return {
        "orderId": trade.order.orderId,
        "symbol": trade.contract.symbol,
        "secType": trade.contract.secType,
        "action": trade.order.action,
        "orderType": trade.order.orderType,
        "totalQuantity": float(trade.order.totalQuantity),
        "lmtPrice": trade.order.lmtPrice,
        "auxPrice": trade.order.auxPrice,
        "status": trade.orderStatus.status,
        "filled": float(trade.orderStatus.filled),
        "remaining": float(trade.orderStatus.remaining),
        "avgFillPrice": trade.orderStatus.avgFillPrice,
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def order_place(
        symbol: str,
        action: str,
        quantity: float,
        order_type: str = "MKT",
        limit_price: float = 0.0,
        stop_price: float = 0.0,
        trailing_percent: float = 0.0,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        tif: str = "DAY",
        outside_rth: bool = False,
    ) -> dict[str, Any]:
        """Place an order.

        Args:
            action: BUY or SELL
            order_type: MKT, LMT, STP, STP_LMT, TRAIL
            limit_price: Required for LMT and STP_LMT orders
            stop_price: Required for STP and STP_LMT orders
            trailing_percent: For TRAIL orders
            tif: Time in force — DAY, GTC, IOC, GTD
            outside_rth: Allow execution outside regular trading hours
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)

        ot = order_type.upper()
        if ot == "MKT":
            order = MarketOrder(action.upper(), quantity)
        elif ot == "LMT":
            order = LimitOrder(action.upper(), quantity, limit_price)
        elif ot == "STP":
            order = StopOrder(action.upper(), quantity, stop_price)
        elif ot == "STP_LMT":
            order = StopLimitOrder(action.upper(), quantity, limit_price, stop_price)
        elif ot == "TRAIL":
            order = TrailingStopOrder(action.upper(), quantity, trailingPercent=trailing_percent)
        else:
            order = Order()
            order.action = action.upper()
            order.totalQuantity = quantity
            order.orderType = ot

        order.tif = tif
        order.outsideRth = outside_rth

        trade = ib.placeOrder(contract, order)
        await ib.sleep(1)
        return _trade_to_dict(trade)

    @mcp.tool()
    async def order_modify(
        order_id: int,
        quantity: float | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> dict[str, Any]:
        """Modify an existing open order by order ID."""
        ib = await core.get_ib()
        trades = ib.openTrades()
        target = None
        for t in trades:
            if t.order.orderId == order_id:
                target = t
                break
        if not target:
            return {"error": f"Order {order_id} not found in open orders"}

        if quantity is not None:
            target.order.totalQuantity = quantity
        if limit_price is not None:
            target.order.lmtPrice = limit_price
        if stop_price is not None:
            target.order.auxPrice = stop_price

        trade = ib.placeOrder(target.contract, target.order)
        await ib.sleep(1)
        return _trade_to_dict(trade)

    @mcp.tool()
    async def order_cancel(order_id: int) -> dict[str, Any]:
        """Cancel an open order by order ID."""
        ib = await core.get_ib()
        trades = ib.openTrades()
        for t in trades:
            if t.order.orderId == order_id:
                ib.cancelOrder(t.order)
                await ib.sleep(1)
                return {"orderId": order_id, "status": "cancel_requested"}
        return {"error": f"Order {order_id} not found in open orders"}

    @mcp.tool()
    async def order_cancel_all() -> dict[str, Any]:
        """Cancel ALL open orders (global cancel)."""
        ib = await core.get_ib()
        ib.reqGlobalCancel()
        await ib.sleep(1)
        return {"status": "global_cancel_requested"}

    @mcp.tool()
    async def open_orders() -> list[dict[str, Any]]:
        """List all currently open orders."""
        ib = await core.get_ib()
        trades = ib.openTrades()
        return [_trade_to_dict(t) for t in trades]

    @mcp.tool()
    async def completed_orders(api_only: bool = True) -> list[dict[str, Any]]:
        """List completed (filled/cancelled) orders from the current session."""
        ib = await core.get_ib()
        trades = await ib.reqCompletedOrdersAsync(apiOnly=api_only)
        return [
            {
                "orderId": t.order.orderId,
                "symbol": t.contract.symbol,
                "action": t.order.action,
                "orderType": t.order.orderType,
                "totalQuantity": float(t.order.totalQuantity),
                "status": t.orderStatus.status,
                "filled": float(t.orderStatus.filled),
                "avgFillPrice": t.orderStatus.avgFillPrice,
            }
            for t in trades
        ]

    @mcp.tool()
    async def executions(
        symbol: str = "",
        sec_type: str = "",
        exchange: str = "",
        side: str = "",
    ) -> list[dict[str, Any]]:
        """Get today's executions (fills), optionally filtered."""
        ib = await core.get_ib()
        from ib_async import ExecutionFilter

        filt = ExecutionFilter()
        if symbol:
            filt.symbol = symbol
        if sec_type:
            filt.secType = sec_type
        if exchange:
            filt.exchange = exchange
        if side:
            filt.side = side

        fills = await ib.reqExecutionsAsync(filt)
        return [
            {
                "execId": f.execution.execId,
                "symbol": f.contract.symbol,
                "side": f.execution.side,
                "shares": float(f.execution.shares),
                "price": f.execution.price,
                "time": str(f.execution.time),
                "orderId": f.execution.orderId,
                "commission": f.commissionReport.commission if f.commissionReport else None,
            }
            for f in fills
        ]

    @mcp.tool()
    async def what_if_order(
        symbol: str,
        action: str,
        quantity: float,
        order_type: str = "MKT",
        limit_price: float = 0.0,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Preview an order without placing it — shows margin impact, commission estimate."""
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)

        ot = order_type.upper()
        if ot == "LMT":
            order = LimitOrder(action.upper(), quantity, limit_price)
        else:
            order = MarketOrder(action.upper(), quantity)

        order.whatIf = True
        trade = ib.placeOrder(contract, order)
        await ib.sleep(2)
        st = trade.orderStatus
        return {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "initMarginBefore": st.initMarginBefore,
            "initMarginChange": st.initMarginChange,
            "initMarginAfter": st.initMarginAfter,
            "maintMarginBefore": st.maintMarginBefore,
            "maintMarginChange": st.maintMarginChange,
            "maintMarginAfter": st.maintMarginAfter,
            "commission": st.commission,
            "minCommission": st.minCommission,
            "maxCommission": st.maxCommission,
        }

    # -------------------------------------------------------------------
    # Combo / Spread Orders
    # -------------------------------------------------------------------

    @mcp.tool()
    async def combo_order(
        symbol: str,
        legs: list[dict],
        action: str,
        quantity: float,
        order_type: str = "MKT",
        limit_price: float = 0.0,
        exchange: str = "SMART",
        currency: str = "USD",
        tif: str = "DAY",
    ) -> dict[str, Any]:
        """Place a combo/spread order (multi-leg).

        Args:
            symbol: Underlying symbol (e.g. 'AAPL')
            legs: List of leg dicts, each with:
                - con_id (int): Contract ID for the leg (use contract_qualify to get this)
                - ratio (int): Number of contracts for this leg
                - action (str): 'BUY' or 'SELL' for this leg
                - exchange (str, optional): Exchange for this leg (default 'SMART')
            action: Overall combo action — BUY or SELL
            order_type: MKT, LMT, etc.
            limit_price: Net debit/credit for LMT orders (positive=debit, negative=credit)

        Example legs for a vertical spread:
            [{"con_id": 123, "ratio": 1, "action": "BUY"},
             {"con_id": 456, "ratio": 1, "action": "SELL"}]
        """
        ib = await core.get_ib()

        bag = Contract()
        bag.symbol = symbol
        bag.secType = "BAG"
        bag.exchange = exchange
        bag.currency = currency
        bag.comboLegs = []

        for leg in legs:
            combo_leg = ComboLeg()
            combo_leg.conId = leg["con_id"]
            combo_leg.ratio = leg.get("ratio", 1)
            combo_leg.action = leg["action"].upper()
            combo_leg.exchange = leg.get("exchange", "SMART")
            bag.comboLegs.append(combo_leg)

        ot = order_type.upper()
        if ot == "LMT":
            order = LimitOrder(action.upper(), quantity, limit_price)
        else:
            order = MarketOrder(action.upper(), quantity)
        order.tif = tif

        trade = ib.placeOrder(bag, order)
        await ib.sleep(1)
        return {
            "orderId": trade.order.orderId,
            "symbol": symbol,
            "action": action,
            "legs": len(legs),
            "orderType": ot,
            "status": trade.orderStatus.status,
        }

    # -------------------------------------------------------------------
    # OCA (One-Cancels-All) Group
    # -------------------------------------------------------------------

    @mcp.tool()
    async def oca_order(
        orders_spec: list[dict],
        oca_group: str = "",
        oca_type: int = 1,
    ) -> list[dict[str, Any]]:
        """Place multiple orders linked in an OCA (One-Cancels-All) group.

        When one order fills, the others are cancelled.

        Args:
            orders_spec: List of order dicts, each with:
                - symbol (str), action (str), quantity (float)
                - order_type (str): MKT, LMT, STP
                - limit_price (float, optional), stop_price (float, optional)
                - sec_type (str, optional), exchange (str, optional), currency (str, optional)
            oca_group: Name for the OCA group (auto-generated if blank)
            oca_type: 1=Cancel remaining on fill, 2=Reduce remaining on partial fill,
                      3=Reduce remaining on fill with overfill protection
        """
        ib = await core.get_ib()

        if not oca_group:
            import time
            oca_group = f"OCA_{int(time.time())}"

        trades = []
        for spec in orders_spec:
            sym = spec["symbol"]
            sec = spec.get("sec_type", "STK")
            exch = spec.get("exchange", "SMART")
            curr = spec.get("currency", "USD")
            contract = core.build_contract(sym, sec, exch, curr)
            contract = await core.qualify_contract(contract)

            ot = spec.get("order_type", "MKT").upper()
            act = spec["action"].upper()
            qty = spec["quantity"]

            if ot == "LMT":
                order = LimitOrder(act, qty, spec.get("limit_price", 0))
            elif ot == "STP":
                order = StopOrder(act, qty, spec.get("stop_price", 0))
            else:
                order = MarketOrder(act, qty)

            order.ocaGroup = oca_group
            order.ocaType = oca_type

            trade = ib.placeOrder(contract, order)
            trades.append(trade)

        await ib.sleep(1)
        return [
            {
                "orderId": t.order.orderId,
                "symbol": t.contract.symbol,
                "action": t.order.action,
                "orderType": t.order.orderType,
                "ocaGroup": oca_group,
                "status": t.orderStatus.status,
            }
            for t in trades
        ]

    # -------------------------------------------------------------------
    # Conditional Orders
    # -------------------------------------------------------------------

    @mcp.tool()
    async def conditional_order(
        symbol: str,
        action: str,
        quantity: float,
        order_type: str = "MKT",
        limit_price: float = 0.0,
        condition_type: str = "Price",
        condition_trigger_symbol: str = "",
        condition_trigger_exchange: str = "SMART",
        condition_is_more: bool = True,
        condition_value: float = 0.0,
        condition_con_id: int = 0,
        cancel_on_condition: bool = False,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        tif: str = "GTC",
    ) -> dict[str, Any]:
        """Place an order with a condition that must be met before it activates.

        Args:
            condition_type: 'Price', 'Time', 'Volume', 'PercentChange', 'Margin'
            condition_trigger_symbol: Symbol that triggers the condition (for Price/Volume/PercentChange)
            condition_is_more: True if condition triggers when value goes ABOVE condition_value
            condition_value: Trigger value — price, volume, percent change, or margin %
            condition_con_id: Contract ID for trigger symbol (0 = auto-resolve from trigger_symbol)
            cancel_on_condition: If True, cancel order when condition is met (instead of activating)

        Examples:
            - Buy AAPL when SPY drops below 400:
              condition_type='Price', condition_trigger_symbol='SPY',
              condition_is_more=False, condition_value=400
            - Buy after specific time:
              condition_type='Time', condition_value=20260101_120000 (as float)
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)

        ot = order_type.upper()
        if ot == "LMT":
            order = LimitOrder(action.upper(), quantity, limit_price)
        else:
            order = MarketOrder(action.upper(), quantity)
        order.tif = tif
        order.conditionsCancelOrder = cancel_on_condition
        order.conditionsIgnoreRth = True

        ct = condition_type.lower()
        if ct == "price":
            from ib_async.order import PriceCondition
            # Resolve trigger conId if not provided
            trigger_con_id = condition_con_id
            if not trigger_con_id and condition_trigger_symbol:
                trigger_contract = core.build_contract(
                    condition_trigger_symbol, "STK", condition_trigger_exchange, currency
                )
                trigger_contract = await core.qualify_contract(trigger_contract)
                trigger_con_id = trigger_contract.conId

            cond = PriceCondition(
                isMore=condition_is_more,
                price=condition_value,
                conId=trigger_con_id,
                exch=condition_trigger_exchange,
                triggerMethod=0,  # default
            )
            order.conditions = [cond]

        elif ct == "time":
            from ib_async.order import TimeCondition
            cond = TimeCondition(
                isMore=condition_is_more,
                time=str(int(condition_value)),
            )
            order.conditions = [cond]

        elif ct == "volume":
            from ib_async.order import VolumeCondition
            trigger_con_id = condition_con_id
            if not trigger_con_id and condition_trigger_symbol:
                trigger_contract = core.build_contract(
                    condition_trigger_symbol, "STK", condition_trigger_exchange, currency
                )
                trigger_contract = await core.qualify_contract(trigger_contract)
                trigger_con_id = trigger_contract.conId

            cond = VolumeCondition(
                isMore=condition_is_more,
                volume=int(condition_value),
                conId=trigger_con_id,
                exch=condition_trigger_exchange,
            )
            order.conditions = [cond]

        elif ct == "percentchange":
            from ib_async.order import PercentChangeCondition
            trigger_con_id = condition_con_id
            if not trigger_con_id and condition_trigger_symbol:
                trigger_contract = core.build_contract(
                    condition_trigger_symbol, "STK", condition_trigger_exchange, currency
                )
                trigger_contract = await core.qualify_contract(trigger_contract)
                trigger_con_id = trigger_contract.conId

            cond = PercentChangeCondition(
                isMore=condition_is_more,
                changePercent=condition_value,
                conId=trigger_con_id,
                exch=condition_trigger_exchange,
            )
            order.conditions = [cond]

        elif ct == "margin":
            from ib_async.order import MarginCondition
            cond = MarginCondition(
                isMore=condition_is_more,
                percent=int(condition_value),
            )
            order.conditions = [cond]

        trade = ib.placeOrder(contract, order)
        await ib.sleep(1)
        return {
            "orderId": trade.order.orderId,
            "symbol": symbol,
            "action": action,
            "conditionType": condition_type,
            "conditionValue": condition_value,
            "status": trade.orderStatus.status,
        }

    # -------------------------------------------------------------------
    # Algorithmic Orders
    # -------------------------------------------------------------------

    @mcp.tool()
    async def algo_order(
        symbol: str,
        action: str,
        quantity: float,
        algo_strategy: str,
        order_type: str = "MKT",
        limit_price: float = 0.0,
        algo_params: list[dict] | None = None,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        tif: str = "DAY",
    ) -> dict[str, Any]:
        """Place an algorithmic order using IB's algo strategies.

        Args:
            algo_strategy: Algorithm name — 'Adaptive', 'Vwap', 'Twap', 'ArrivalPx',
                          'DarkIce', 'PctVol', 'Accumulate/Distribute', 'ClosePx'
            algo_params: List of {tag, value} dicts for algo parameters.

        Common algo_params by strategy:
            Adaptive: [{"tag": "adaptivePriority", "value": "Normal"}]
                      (values: Urgent, Normal, Patient)
            Vwap:     [{"tag": "maxPctVol", "value": "0.1"},
                       {"tag": "startTime", "value": "09:30:00 US/Eastern"},
                       {"tag": "endTime", "value": "16:00:00 US/Eastern"}]
            PctVol:   [{"tag": "pctVol", "value": "0.05"},
                       {"tag": "startTime", "value": "09:30:00 US/Eastern"},
                       {"tag": "endTime", "value": "16:00:00 US/Eastern"}]
            Twap:     [{"tag": "strategyType", "value": "Marketable"}]
        """
        ib = await core.get_ib()
        contract = core.build_contract(symbol, sec_type, exchange, currency)
        contract = await core.qualify_contract(contract)

        ot = order_type.upper()
        if ot == "LMT":
            order = LimitOrder(action.upper(), quantity, limit_price)
        else:
            order = MarketOrder(action.upper(), quantity)
        order.tif = tif
        order.algoStrategy = algo_strategy

        if algo_params:
            order.algoParams = [
                TagValue(p["tag"], p["value"]) for p in algo_params
            ]

        trade = ib.placeOrder(contract, order)
        await ib.sleep(1)
        return {
            "orderId": trade.order.orderId,
            "symbol": symbol,
            "action": action,
            "algoStrategy": algo_strategy,
            "status": trade.orderStatus.status,
        }
