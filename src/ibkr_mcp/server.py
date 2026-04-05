"""Interactive Brokers MCP Server — entry point.

Architecture:
    Claude Code ←→ MCP Server (stdio) ←→ ib_async ←→ TWS / IB Gateway (port 7497)

Equivalent to the TradingView MCP but for Interactive Brokers.
Instead of Chrome DevTools Protocol → TradingView Desktop,
this uses the IB API → TWS or IB Gateway.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "ibkr",
    version="1.0.0",
    instructions="""
Interactive Brokers MCP Server — AI-assisted trading, market data, and
portfolio management via TWS or IB Gateway.

## Getting Started
1. Launch TWS or IB Gateway and enable the API (Edit → Global Config → API → Settings)
2. Call `ib_connect` to establish a connection (default: 127.0.0.1:7497 paper trading)
3. Use `ib_health_check` to verify connectivity

## Tool Categories

### Connection (4 tools)
- `ib_connect` — Connect to TWS/Gateway (ports: 7496=live, 7497=paper, 4001/4002=gateway)
- `ib_disconnect` — Disconnect
- `ib_health_check` — Verify connection status
- `ib_status` — Connection state and account info

### Account (4 tools)
- `account_summary` — Net liquidation, buying power, cash balances
- `account_values` — All account key-value pairs
- `account_pnl` — Real-time account P&L
- `managed_accounts` — List all managed accounts

### Market Data (6 tools)
- `quote_get` — Real-time quote snapshot (bid/ask/last/volume)
- `data_get_ohlcv` — Historical OHLCV bars with summary mode
- `market_data_subscribe` — Stream live market data
- `market_data_unsubscribe` — Cancel streaming data
- `realtime_bars_subscribe` — 5-second real-time bars
- `head_timestamp` — Earliest available data date

### Contracts (5 tools)
- `contract_search` — Search by name/symbol pattern
- `contract_details` — Full details (trading hours, min tick, exchanges)
- `contract_qualify` — Fill in conId and missing fields
- `option_chain` — Expirations and strikes for an underlying
- `matching_symbols` — Quick symbol lookup

### Orders (13 tools)
- `order_place` — Place MKT/LMT/STP/STP_LMT/TRAIL orders
- `order_modify` — Modify open order (qty, price)
- `order_cancel` — Cancel single order
- `order_cancel_all` — Global cancel
- `open_orders` — List open orders
- `completed_orders` — Filled/cancelled orders
- `executions` — Today's fills
- `what_if_order` — Preview margin impact and commission
- `combo_order` — Multi-leg combo/spread orders (verticals, strangles, etc.)
- `oca_order` — One-Cancels-All linked order groups
- `conditional_order` — Orders with price/time/volume/margin conditions
- `algo_order` — Algorithmic orders (Adaptive, VWAP, TWAP, PctVol, etc.)
- `bracket_order` — Place bracket (entry + take-profit + stop-loss)

### Portfolio (3 tools)
- `positions` — All positions across accounts
- `portfolio_items` — Positions with market value and P&L
- `position_pnl` — Real-time P&L for a single position

### Market Depth (2 tools)
- `market_depth` — Level 2 order book snapshot
- `market_depth_exchanges` — List exchanges with L2 data

### Scanner & Research (5 tools)
- `scanner_run` — Market scanner (top gainers, most active, etc.)
- `scanner_parameters` — Available scan codes and filters
- `fundamental_data` — Company overview, financials, ratios
- `news_headlines` — Recent news by symbol or provider
- `news_article` — Full article text

### Advanced Data (3 tools)
- `histogram_data` — Price histogram
- `tick_by_tick_data` — Granular tick data (last, bid/ask, midpoint)
- `historical_ticks` — Historical tick-level data

### Options Analytics (4 tools)
- `option_greeks` — Delta, gamma, theta, vega, implied vol
- `calculate_implied_vol` — IV from option price (server-side)
- `calculate_option_price` — Theoretical price from volatility
- `option_exercise` — Exercise or lapse option positions

### Market Control (3 tools)
- `set_market_data_type` — Switch Live/Frozen/Delayed/Delayed-Frozen
- `historical_schedule` — Trading hours and sessions
- `market_rule` — Tick size rules by market rule ID

### Watchlist (1 tool)
- `watchlist_quotes` — Get quotes for all symbols in a list

### System (1 tool)
- `news_bulletins` — Exchange-wide system messages and halts

## Tips
- Always call `ib_connect` before other tools
- Use `contract_qualify` before placing orders for non-stock instruments
- Use `what_if_order` to preview margin impact before placing large orders
- Use `data_get_ohlcv` with summary=true to save context window space
- Market data requires appropriate IB subscriptions
""",
)

# ---------------------------------------------------------------------------
# Register all tool modules
# ---------------------------------------------------------------------------

from ibkr_mcp.tools import connection, account, market_data, contracts, orders, portfolio, scanner, advanced

connection.register(mcp)
account.register(mcp)
market_data.register(mcp)
contracts.register(mcp)
orders.register(mcp)
portfolio.register(mcp)
scanner.register(mcp)
advanced.register(mcp)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    print(
        "Interactive Brokers MCP Server v1.0.0\n"
        "Connect to TWS/Gateway on 127.0.0.1:7497 (paper) or 7496 (live)\n"
        "This is an unofficial tool — use at your own risk.",
        file=sys.stderr,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
