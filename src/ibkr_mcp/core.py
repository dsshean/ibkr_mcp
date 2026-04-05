"""Core IB connection manager — singleton wrapper around ib_async.IB."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from ib_async import IB, Contract, Stock, Option, Future, Forex, Index, CFD, Bond

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton connection
# ---------------------------------------------------------------------------

_ib: IB | None = None
_lock = asyncio.Lock()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7497  # TWS paper trading; 7496=live, 4001/4002=gateway
DEFAULT_CLIENT_ID = 1


async def get_ib() -> IB:
    """Return the shared IB instance, connecting if needed."""
    global _ib
    async with _lock:
        if _ib is None or not _ib.isConnected():
            _ib = IB()
            await _ib.connectAsync(
                host=DEFAULT_HOST,
                port=DEFAULT_PORT,
                clientId=DEFAULT_CLIENT_ID,
                readonly=False,
            )
            logger.info("Connected to IB on %s:%s", DEFAULT_HOST, DEFAULT_PORT)
        return _ib


async def connect(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    client_id: int = DEFAULT_CLIENT_ID,
    readonly: bool = False,
) -> dict[str, Any]:
    """Connect (or reconnect) to TWS / IB Gateway."""
    global _ib
    async with _lock:
        if _ib and _ib.isConnected():
            _ib.disconnect()
        _ib = IB()
        await _ib.connectAsync(
            host=host, port=port, clientId=client_id, readonly=readonly
        )
        logger.info("Connected to IB on %s:%s (client %s)", host, port, client_id)
        return {
            "connected": True,
            "host": host,
            "port": port,
            "clientId": client_id,
            "accounts": _ib.managedAccounts(),
        }


async def disconnect() -> dict[str, Any]:
    """Disconnect from TWS / IB Gateway."""
    global _ib
    async with _lock:
        if _ib and _ib.isConnected():
            _ib.disconnect()
            return {"disconnected": True}
        return {"disconnected": False, "reason": "not connected"}


async def health_check() -> dict[str, Any]:
    """Return connection health and basic account info."""
    global _ib
    if _ib is None or not _ib.isConnected():
        return {"connected": False, "hint": "Call ib_connect first"}
    return {
        "connected": True,
        "accounts": _ib.managedAccounts(),
        "serverVersion": _ib.client.serverVersion() if _ib.client else None,
    }


# ---------------------------------------------------------------------------
# Contract helpers
# ---------------------------------------------------------------------------

def build_contract(
    symbol: str,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    expiry: str = "",
    strike: float = 0.0,
    right: str = "",
    multiplier: str = "",
    local_symbol: str = "",
    con_id: int = 0,
) -> Contract:
    """Build an ib_async Contract from parameters."""
    sec = sec_type.upper()
    if sec == "STK":
        c = Stock(symbol, exchange, currency)
    elif sec == "OPT":
        c = Option(symbol, expiry, strike, right, exchange, currency=currency)
    elif sec == "FUT":
        c = Future(symbol, expiry, exchange, currency=currency)
        if multiplier:
            c.multiplier = multiplier
    elif sec == "CASH":
        c = Forex(symbol + currency if len(symbol) == 3 else symbol)
    elif sec == "IND":
        c = Index(symbol, exchange, currency)
    elif sec == "CFD":
        c = CFD(symbol, exchange, currency)
    elif sec == "BOND":
        c = Bond()
        c.symbol = symbol
        c.exchange = exchange
        c.currency = currency
    else:
        c = Contract()
        c.symbol = symbol
        c.secType = sec
        c.exchange = exchange
        c.currency = currency

    if local_symbol:
        c.localSymbol = local_symbol
    if con_id:
        c.conId = con_id
    return c


async def qualify_contract(contract: Contract) -> Contract:
    """Qualify a contract through IB to fill in missing details."""
    ib = await get_ib()
    qualified = await ib.qualifyContractsAsync(contract)
    if qualified:
        return qualified[0]
    raise ValueError(f"Could not qualify contract: {contract}")
