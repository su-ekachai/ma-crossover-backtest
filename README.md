# EMA-99 Backtesting System

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A local trading backtesting system for evaluating Moving Average (MA) based buy/sell strategies across multiple asset classes and timeframes.

> **Note**: This is a research/backtesting tool only. It does not connect to exchanges or execute live trades.

## Features

- **MA types**: EMA (Exponential) and SMA (Simple) — selectable per run
- **Confirmation candles**: Wait N consecutive candles above/below MA before triggering entry (reduces false signals)
- **Direction modes**: Long-only, short-only, or both (flip between long and short)
- **Position sizing**: All-in (100% equity), fixed dollar amount, or percentage of equity
- **Multi-timeframe**: Resample data from smaller timeframes (1m, 5m, 15m, 30m) to larger ones (1h, 4h, 1d)
- **Batch comparison**: Run multiple configurations in one command and compare results side-by-side
- **Parameter optimization**: Sweep MA period ranges to find optimal settings
- **Interactive charts**: Bokeh-powered HTML charts saved with each result
- **Web viewer**: Browse and compare results in a Flask web interface

---

## Installation

### Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (modern Python package manager)

### Setup

```bash
# Clone or navigate to the project
cd ema-99-buy-and-sell

# Install dependencies
uv sync

# Verify installation
uv run python main.py --help
```

---

## Data Format

The system expects OHLCV (Open, High, Low, Close, Volume) CSV files with a `datetime` column.

### CSV Format

```csv
datetime,Open,High,Low,Close,Volume
2024-01-01 00:00:00,42000.00,42500.00,41800.00,42300.00,1500.5
2024-01-01 01:00:00,42300.00,42800.00,42100.00,42600.00,1200.3
```

**Requirements:**
- Column names are **case-sensitive** and must match exactly
- `datetime` is parsed as a DatetimeIndex
- No NaN values in OHLCV columns
- Chronological order (sorted automatically if out of order)

### Supported Timeframes for Resampling

| Timeframe | Description |
|-----------|-------------|
| `1m`, `5m`, `15m`, `30m` | Minutes (source data) |
| `1h`, `2h`, `4h` | Hours |
| `1d` | Daily |
| `1w` | Weekly |

When you specify a `--timeframe` larger than your source data, the system automatically resamples. For example, resampling 5-minute data to 1-hour uses:
- **Open**: First bar's open in the period
- **High**: Highest high in the period
- **Low**: Lowest low in the period
- **Close**: Last bar's close in the period
- **Volume**: Sum of all volumes in the period

---

## Quick Start

### 1. Prepare Your Data

Place your OHLCV CSV file in the `data/` directory:

```bash
cp /path/to/your/BTCUSDT_1h.csv data/
```

### 2. Run a Backtest

```bash
uv run python main.py run --data data/BTCUSDT_1h.csv --ma-type EMA --period 99 --confirm 3 --direction both
```

### 3. View Results

Results are saved to `results/`. The output shows:

```
=== Backtest Results ===
MA: EMA(99)
Confirmation: 3 candles
Direction: both

Return [%]:     45.23
Sharpe Ratio:   1.82
Max Drawdown [%]: -12.4
Win Rate [%]:   58.3
# Trades:       47

Results saved to: results/20260417_143022_BTCUSDT_MAEMA99_1h/
```

---

## CLI Reference

### `run` — Single Backtest

Run a single backtest with the specified parameters.

```bash
uv run python main.py run --data <path> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--data` | **(required)** | Path to OHLCV CSV file |
| `--config` | — | YAML config file (overridden by CLI options below) |
| `--ma-type` | `EMA` | MA type: `EMA` or `SMA` |
| `--period` | `99` | MA period (e.g., 99 for EMA-99) |
| `--confirm` | `0` | Confirmation candles (0 = instant signal) |
| `--direction` | `both` | `long_only`, `short_only`, or `both` |
| `--sizing-mode` | `all_in` | `all_in`, `fixed`, or `percentage` |
| `--sizing-amount` | `1000.0` | Fixed dollar amount (when sizing-mode=fixed) |
| `--sizing-risk` | `0.02` | Risk percentage (when sizing-mode=percentage) |
| `--cash` | `10000.0` | Initial cash |
| `--commission` | `0.001` | Commission per trade (0.001 = 0.1%) |
| `--timeframe` | — | Target timeframe for resampling |

**Example with all options:**

```bash
uv run python main.py run \
    --data data/BTCUSDT_1h.csv \
    --ma-type EMA \
    --period 99 \
    --confirm 3 \
    --direction both \
    --sizing-mode percentage \
    --sizing-risk 0.02 \
    --cash 10000 \
    --commission 0.001 \
    --timeframe 1h
```

---

### `compare` — Batch Comparison

Run multiple configurations and compare results side-by-side.

```bash
uv run python main.py compare --data <path> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--data` | **(required)** | Path to OHLCV CSV file |
| `--ma-types` | `EMA,SMA` | Comma-separated MA types |
| `--periods` | `99` | Comma-separated periods |
| `--confirm-range` | `0,1,2,3,5` | Comma-separated confirmation values |
| `--timeframes` | `1h,4h,1d` | Comma-separated timeframes |
| `--direction` | `both` | `long_only`, `short_only`, or `both` |
| `--cash` | `10000.0` | Initial cash |
| `--commission` | `0.001` | Commission per trade |

**Example:**

```bash
uv run python main.py compare \
    --data data/BTCUSDT_1h.csv \
    --ma-types EMA,SMA \
    --periods 50,99,200 \
    --confirm-range 0,1,3 \
    --timeframes 1h,4h
```

**Output:**

```
  Run    MA      Confirm Direction  Return [%]  Sharpe  MaxDD   Trades
Run 1  EMA50         0      both        38.2%    1.45  -15.3%      62
Run 2  EMA99         1      both        45.2%    1.82  -12.4%      47
Run 3  SMA99         0      both        32.1%    1.21  -18.7%      58
Run 4  SMA200        3      both        41.5%    1.68  -13.1%      43
```

---

### `optimize` — Parameter Optimization

Sweep a range of MA periods to find the optimal setting.

```bash
uv run python main.py optimize --data <path> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--data` | **(required)** | Path to OHLCV CSV file |
| `--maximize` | `Sharpe Ratio` | Metric to maximize |
| `--confirm-range` | `0-5` | Confirmation range (start-end) |
| `--period-range` | `50-200` | MA period range (start-end) |
| `--direction` | `both` | `long_only`, `short_only`, or `both` |
| `--cash` | `10000.0` | Initial cash |
| `--commission` | `0.001` | Commission per trade |
| `--timeframe` | — | Target timeframe for resampling |

**Example:**

```bash
uv run python main.py optimize \
    --data data/BTCUSDT_1h.csv \
    --maximize "Sharpe Ratio" \
    --period-range 20-200 \
    --direction both
```

**Output:**

```
Optimized ma_period: 99
Return [%]:     45.23
Sharpe Ratio:   1.82
Max Drawdown [%]: -12.4
# Trades:       47

Results saved to: results/20260417_BTCUSDT_optimized_ma_period/
```

---

### `web` — Web Viewer

Launch a Flask web interface for browsing results.

```bash
uv run python main.py web --port 5000 --host 127.0.0.1
```

Then open `http://127.0.0.1:5000` in your browser.

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `5000` | Port for Flask app |
| `--host` | `127.0.0.1` | Host for Flask app |

**Routes:**
- `/` — Lists all saved results
- `/result/<id>` — Detail view with metrics, chart, and trade log
- `/compare` — Side-by-side comparison of selected results

---

## Configuration File

Instead of CLI options, you can use a YAML config file:

```yaml
strategy:
  ma_type: EMA              # EMA or SMA
  ma_period: 99
  confirmation_candles: 0   # 0 = no confirmation
  direction: both           # long_only, short_only, both

sizing:
  mode: all_in              # all_in, fixed, percentage
  fixed_amount: 1000         # used when mode=fixed
  risk_percentage: 0.02       # used when mode=percentage

backtest:
  initial_cash: 10000
  commission: 0.001         # 0.1% per trade

data:
  path: data/BTCUSDT_1h.csv
  timeframe: 1h             # target timeframe (resample if source is smaller)
```

Then run:

```bash
uv run python main.py run --config config.yaml
```

**Note:** CLI options override config file values.

---

## Understanding Results

### Output Directory Structure

Each backtest saves results to a timestamped directory:

```
results/
  20260417_143022_BTCUSDT_MAEMA99_1h/
    stats.json      # Performance metrics
    trades.csv      # Trade log
    chart.html      # Interactive chart
```

### Metrics Explained

| Metric | Description |
|--------|-------------|
| **Return [%]** | Total return percentage |
| **Sharpe Ratio** | Risk-adjusted return (higher is better) |
| **Max. Drawdown [%]** | Largest peak-to-trough decline |
| **Win Rate [%]** | Percentage of profitable trades |
| **# Trades** | Total number of trades |
| **Avg. Trade [%]** | Average return per trade |
| **Best Trade [%]** | Largest single trade gain |
| **Worst Trade [%]** | Largest single trade loss |
| **Profit Factor** | Gross profit / gross loss (>1 is profitable) |
| **Expectancy [%]** | Average expected return per trade |
| **SQN** | System Quality Number (>1.5 is good, >2 is excellent) |
| **Kelly Criterion** | Optimal position sizing fraction (lower is more conservative) |

---

## Strategy Logic

### How It Works

The MA strategy buys when price crosses above the Moving Average and sells when it crosses below. The "confirmation candles" feature requires price to stay on the same side of the MA for N consecutive bars before triggering entry.

### Confirmation Candles

| Value | Behavior |
|-------|----------|
| `0` | Instant entry on first close above/below MA |
| `1` | Wait 1 bar after crossing, then enter on next bar |
| `2` | Wait 2 consecutive bars above/below MA |
| `N` | Wait N consecutive bars |

This reduces false signals in volatile markets by requiring sustained pressure before entering.

### Direction Modes

| Mode | Long Entries | Short Entries |
|------|-------------|---------------|
| `long_only` | Yes | No |
| `short_only` | No | Yes |
| `both` | Yes | Yes (and flips between them) |

### Position Sizing

| Mode | Description |
|------|-------------|
| `all_in` | 100% of equity per trade |
| `fixed` | Fixed dollar amount per trade (e.g., $1000) |
| `percentage` | Risk-based sizing (e.g., 2% of equity per trade) |

---

## Troubleshooting

### "period must be less than data length"

Your MA period is too large for the dataset. For example, a 99-period MA requires at least 99 bars of data. Use a smaller period or more data.

```
# This requires at least 99 bars
uv run python main.py run --data data/BTCUSDT_1h.csv --period 99

# Try a smaller period for small datasets
uv run python main.py run --data data/TEST_1h.csv --period 5
```

### "NaN values found in OHLCV data"

Your CSV has missing values. Clean the data or interpolate before running backtests.

### "Sharpe Ratio: nan"

Sharpe Ratio is NaN when there's insufficient data or zero volatility. This usually occurs with very short datasets or when all price movements are identical.

### "Invalid frequency" when using `--timeframe`

Ensure the timeframe is one of: `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d`, `1w`.

Also ensure your source data timeframe is **smaller** than the target timeframe (you can resample 1m → 1h, but not 1h → 1m).

### No chart.html generated

Chart generation can fail silently if Bokeh encounters rendering issues. Check that:
- The backtest produced at least some trades
- The data has sufficient length for the MA period

### Web viewer shows "Unknown result"

The web viewer parses result folder names using the pattern:
```
YYYYMMDD_ASSET_MA<TYPE><PERIOD>_<TIMEFRAME>/
```
For example: `20260417_BTCUSDT_MAEMA99_1h/`

If your folder doesn't match this pattern exactly, it won't be recognized.

---

## Project Structure

```
ema-99-buy-and-sell/
├── main.py                  # CLI entry point (Click)
├── config.yaml              # Default strategy config
├── pyproject.toml           # Project config (uv, dependencies)
├── src/
│   ├── indicators.py        # EMA/SMA helper functions
│   ├── config.py            # Config dataclasses + YAML parsing
│   ├── data_loader.py      # CSV loading, validation, resampling
│   ├── runner.py           # Backtest runner (single, compare, optimize)
│   └── strategies/
│       └── ma_strategy.py  # MAStrategy (Backtesting.py)
├── web/
│   ├── app.py              # Flask web app
│   ├── templates/          # HTML templates
│   └── static/style.css    # Styles
├── data/                    # OHLCV CSV files (gitignored)
├── results/                 # Saved backtest results (gitignored)
└── tests/                  # Test files
```

---

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Linting

```bash
uv run ruff check src/ main.py
```

### Code Formatting

```bash
uv run ruff format src/ main.py
```

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Backtesting engine | Backtesting.py | Simple API, built-in metrics/charts/optimizer |
| Indicators | pandas-ta | EMA/SMA calculations |
| Data handling | Pandas + NumPy | Industry standard |
| Package manager | uv | Fast, modern |
| Logging | Loguru | Zero-config structured logging |
| Linting | Ruff | Fast, comprehensive |
| CLI | Click | Clean CLI interface |
| Web viewer | Flask | Lightweight, serves saved results |
| Charts | Bokeh (via Backtesting.py) | Interactive, saved as HTML |

---

## Limitations

- **Backtesting only** — no live trading or exchange connectivity
- **No slippage/spread modeling** — orders execute at close price with flat commission
- **Single-threaded optimization** — large parameter sweeps may be slow
- **No partial fills** — all-or-nothing order execution
- **Single indicator** — only one MA per strategy (no multi-indicator combinations)
- **No walk-forward testing** — optimization uses the full dataset (overfitting risk)
- **No stop-loss/take-profit** — exits only on MA crossover
