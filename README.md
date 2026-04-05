# Interactive Brokers MCP Server

AI-assisted trading, market data, and portfolio management for Interactive Brokers via the Model Context Protocol (MCP).

Inspired by [tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — this is the Interactive Brokers equivalent.

```
Claude Code ←→ MCP Server (stdio) ←→ ib_async ←→ TWS / IB Gateway
```

## Features — 41 Tools

| Category | Tools | Description |
|----------|-------|-------------|
| **Connection** | 4 | Connect/disconnect, health check, status |
| **Account** | 4 | Summary, balances, P&L, managed accounts |
| **Market Data** | 6 | Quotes, OHLCV bars, streaming, real-time bars, head timestamp |
| **Contracts** | 5 | Search, details, qualify, option chains, symbol lookup |
| **Orders** | 9 | Place/modify/cancel, bracket orders, what-if preview, executions |
| **Portfolio** | 3 | Positions, portfolio items, per-position P&L |
| **Market Depth** | 2 | Level 2 order book, available exchanges |
| **Scanner & Research** | 5 | Market scanner, fundamental data, news headlines & articles |
| **Advanced Data** | 3 | Histograms, tick-by-tick, historical ticks |
| **Options** | 3 | Greeks, implied vol calculation, option price calculation |
| **Watchlist** | 1 | Batch quotes for multiple symbols |

## Quick Start

### Prerequisites

- **Python 3.10+**
- **TWS** (Trader Workstation) or **IB Gateway** running with API enabled
- An Interactive Brokers account (paper or live)

### Install

```bash
git clone https://github.com/dsshean/ibkr_mcp.git
cd ibkr_mcp
pip install -e .
```

### Configure TWS / IB Gateway

1. Open TWS → Edit → Global Configuration → API → Settings
2. **Enable ActiveX and Socket Clients** ✓
3. Set **Socket port**: `7497` (paper) or `7496` (live)
4. **Allow connections from localhost only** ✓ (recommended)
5. Uncheck **Read-Only API** if you want to place orders

### Add to Claude Code

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "ibkr": {
      "command": "ibkr-mcp",
      "type": "stdio"
    }
  }
}
```

Or if running from source:

```json
{
  "mcpServers": {
    "ibkr": {
      "command": "python",
      "args": ["-m", "ibkr_mcp.server"],
      "type": "stdio"
    }
  }
}
```

### Verify

```
> ib_connect
> ib_health_check
```

## Tool Reference

### Connection

| Tool | Description |
|------|-------------|
| `ib_connect` | Connect to TWS/Gateway (host, port, client_id, readonly) |
| `ib_disconnect` | Disconnect from TWS/Gateway |
| `ib_health_check` | Check connection status |
| `ib_status` | Connection state, accounts, server version |

### Account

| Tool | Description |
|------|-------------|
| `account_summary` | Net liquidation, buying power, cash, margins |
| `account_values` | All account key-value pairs |
| `account_pnl` | Real-time daily/unrealized/realized P&L |
| `managed_accounts` | List all managed accounts |

### Market Data

| Tool | Description |
|------|-------------|
| `quote_get` | Snapshot: bid, ask, last, volume, OHLC |
| `data_get_ohlcv` | Historical bars with optional summary mode |
| `market_data_subscribe` | Start streaming market data |
| `market_data_unsubscribe` | Stop streaming |
| `realtime_bars_subscribe` | 5-second real-time bars |
| `head_timestamp` | Earliest available data date |

### Contracts

| Tool | Description |
|------|-------------|
| `contract_search` | Search by name/pattern (e.g. "crude oil") |
| `contract_details` | Trading hours, min tick, valid exchanges |
| `contract_qualify` | Fill in conId and missing fields |
| `option_chain` | Get expirations and strikes |
| `matching_symbols` | Quick symbol lookup |

### Orders

| Tool | Description |
|------|-------------|
| `order_place` | Place MKT/LMT/STP/STP_LMT/TRAIL orders |
| `order_modify` | Modify open order price/quantity |
| `order_cancel` | Cancel single order |
| `order_cancel_all` | Global cancel all orders |
| `open_orders` | List all open orders |
| `completed_orders` | Filled/cancelled orders |
| `executions` | Today's fills with commissions |
| `what_if_order` | Preview margin impact & commission |
| `bracket_order` | Entry + take-profit + stop-loss (OCA linked) |

### Portfolio

| Tool | Description |
|------|-------------|
| `positions` | All positions across accounts |
| `portfolio_items` | Positions with market value and P&L |
| `position_pnl` | Real-time P&L for a single position |

### Market Depth

| Tool | Description |
|------|-------------|
| `market_depth` | Level 2 order book snapshot |
| `market_depth_exchanges` | Exchanges with L2 data |

### Scanner & Research

| Tool | Description |
|------|-------------|
| `scanner_run` | TOP_PERC_GAIN, MOST_ACTIVE, etc. |
| `scanner_parameters` | All available scan codes (XML) |
| `fundamental_data` | Company overview, financials, ratios |
| `news_headlines` | Recent news by symbol or provider |
| `news_article` | Full article text |

### Advanced Data

| Tool | Description |
|------|-------------|
| `histogram_data` | Price distribution histogram |
| `tick_by_tick_data` | Real-time tick data (Last/BidAsk/MidPoint) |
| `historical_ticks` | Historical tick-level data |

### Options Analytics

| Tool | Description |
|------|-------------|
| `option_greeks` | Delta, gamma, theta, vega, implied vol |
| `calculate_implied_vol` | IV from option price (server-side) |
| `calculate_option_price` | Theoretical price from volatility |

### Watchlist

| Tool | Description |
|------|-------------|
| `watchlist_quotes` | Batch quotes for a list of symbols |

## Context Optimization

Like the TradingView MCP, tools are designed to minimize context usage:

- **OHLCV summary mode**: Returns stats + last 5 bars instead of full history (default)
- **Option chain**: Strikes capped at 50 per chain
- **Fundamental data**: Truncated to 15KB
- **Scanner parameters**: Truncated XML
- **News articles**: Capped at 10KB

## Architecture

```
┌─────────────┐     stdio      ┌──────────────┐    TCP/IP     ┌──────────────┐
│ Claude Code  │ ◄────────────► │  ibkr_mcp    │ ◄───────────► │  TWS / IB    │
│ (AI Agent)   │     MCP        │  (Python)    │   IB API      │  Gateway     │
└─────────────┘                 └──────────────┘    :7497       └──────────────┘
```

- **Transport**: MCP over stdio
- **IB Connection**: ib_async (async Python wrapper for IB API)
- **Dependencies**: `mcp[cli]`, `ib_async` (only 2 deps)

## Port Reference

| Application | Live | Paper |
|-------------|------|-------|
| TWS | 7496 | 7497 |
| IB Gateway | 4001 | 4002 |

## Safety

- **Local only** — connects to TWS/Gateway on localhost
- **No external data transmission** — all processing on your machine
- **What-if orders** — preview margin/commission before placing
- **Read-only mode** — connect with `readonly=True` to disable order placement
- **Paper trading** — default port 7497 is paper trading

## Comparison with TradingView MCP

| Feature | TradingView MCP | IBKR MCP |
|---------|----------------|----------|
| Connection | CDP → Electron app | IB API → TWS/Gateway |
| Language | Node.js | Python |
| Tools | 78 (chart-focused) | 41 (trading-focused) |
| Chart analysis | ✓ Full chart control | ✗ No charting |
| Pine Script | ✓ Full development | ✗ N/A |
| Order placement | ✗ Replay mode only | ✓ Full order management |
| Real market orders | ✗ | ✓ |
| Options analytics | ✗ | ✓ Greeks, IV, pricing |
| Level 2 data | ✗ | ✓ Market depth |
| Fundamental data | ✗ | ✓ |
| Scanners | ✗ | ✓ Market scanners |

## License

MIT
