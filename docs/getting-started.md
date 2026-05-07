# Getting Started

A step-by-step guide to running your first backtest with the EMA-99 Backtesting System.

---

## Prerequisites

- **Python 3.12 or newer** — check with `python --version`
- **uv** (Python package manager) — install from [astral.sh/uv](https://github.com/astral-sh/uv)

---

## Installation

```bash
# Clone or download the project
cd ema-99-buy-and-sell

# Install all dependencies
uv sync

# Verify it works
uv run python main.py --help
```

You should see the CLI help with commands: `run`, `compare`, `optimize`, `web`.

---

## Getting Data

The system needs OHLCV (Open, High, Low, Close, Volume) data in CSV format.

### CSV Format

Your file must have these exact column names (case-sensitive):

```csv
datetime,Open,High,Low,Close,Volume
2024-01-01 00:00:00,42000.00,42500.00,41800.00,42300.00,1500.5
2024-01-01 01:00:00,42300.00,42800.00,42100.00,42600.00,1200.3
```

### Where to Get Data

- **Binance**: Export from TradingView or use CCXT library to download
- **Yahoo Finance**: Use `yfinance` Python package
- **Any exchange**: Export OHLCV history as CSV

Place your CSV files in the `data/` directory:

```bash
cp ~/Downloads/BTCUSDT_1h.csv data/
```

---

## Running Your First Backtest

### 1. Quick Run (defaults: EMA-99, no confirmation, both directions)

```bash
uv run python main.py run --data data/BTCUSDT_1h.csv
```

### 2. Customized Run

```bash
uv run python main.py run \
    --data data/BTCUSDT_1h.csv \
    --ma-type EMA \
    --period 99 \
    --confirm 3 \
    --direction both \
    --cash 10000
```

### 3. What You'll See

```
=== Backtest Results ===
MA: EMA(99)
Confirmation: 3 candles
Direction: both

Return [%]: 45.23
Sharpe Ratio: 1.82
Max Drawdown [%]: -12.4
Win Rate [%]: 58.3
# Trades: 47

Results saved to: results/20260417_143022_BTCUSDT_MAEMA99_1h/
```

---

## Understanding Results

Each backtest saves three files:

| File | What It Contains |
|------|-----------------|
| `stats.json` | All performance metrics (machine-readable) |
| `trades.csv` | Every trade with entry/exit prices and P&L |
| `chart.html` | Interactive candlestick chart (open in browser) |

### Key Metrics

| Metric | What It Means | Good Value |
|--------|---------------|------------|
| **Return [%]** | Total profit/loss | Positive |
| **Sharpe Ratio** | Risk-adjusted return | > 1.5 |
| **Max Drawdown [%]** | Worst peak-to-trough drop | > -20% |
| **Win Rate [%]** | % of profitable trades | > 50% |
| **Profit Factor** | Gross profit / gross loss | > 1.5 |
| **SQN** | System Quality Number | > 2.0 is excellent |

---

## Comparing Strategies

Test multiple configurations at once:

```bash
uv run python main.py compare \
    --data data/BTCUSDT_1h.csv \
    --ma-types EMA,SMA \
    --periods 50,99,200 \
    --confirm-range 0,1,3
```

This runs all combinations (2 MA types x 3 periods x 3 confirmations = 18 backtests) and shows a comparison table.

---

## Finding Optimal Parameters

Let the optimizer sweep a range to find the best MA period:

```bash
uv run python main.py optimize \
    --data data/BTCUSDT_1h.csv \
    --period-range 20-200 \
    --maximize "Sharpe Ratio"
```

The optimizer tests every period from 20 to 200 and reports which one produced the best Sharpe Ratio.

**Warning**: Optimizing on the same data you test on can lead to overfitting. Consider splitting your data into train/test periods.

---

## Viewing Results in Browser

Launch the web interface:

```bash
uv run python main.py web
```

Open http://127.0.0.1:5000 in your browser to:
- Browse all saved backtest results
- View detailed stats and trade logs
- Compare multiple results side-by-side
- View interactive charts

---

## Common Workflows

### Testing a New Asset

```bash
# 1. Download data
cp ~/Downloads/ETHUSDT_4h.csv data/

# 2. Quick test with small period (faster)
uv run python main.py run --data data/ETHUSDT_4h.csv --period 20

# 3. Full optimization
uv run python main.py optimize --data data/ETHUSDT_4h.csv --period-range 20-200
```

### Finding the Best Confirmation Setting

```bash
uv run python main.py compare \
    --data data/BTCUSDT_1h.csv \
    --periods 99 \
    --confirm-range 0,1,2,3,5,8
```

### Multi-Timeframe Analysis

If you have 5-minute data, test across multiple timeframes:

```bash
uv run python main.py compare \
    --data data/BTCUSDT_5m.csv \
    --periods 99 \
    --timeframes 1h,4h,1d
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "period must be less than data length" | Dataset too short for chosen MA period | Use smaller period or more data |
| "NaN values found" | Missing data in CSV | Clean CSV or interpolate gaps |
| "Sharpe Ratio: nan" | Too few trades or zero volatility | Use more data or different parameters |
| No chart.html generated | Bokeh rendering issue | Check internet connection (CDN) |

---

## Next Steps

- Read the full [README](../README.md) for complete CLI reference
- Check `config.yaml` for all available settings
- Browse `docs/superpowers/specs/` for design documentation
