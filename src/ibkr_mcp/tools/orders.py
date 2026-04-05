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
