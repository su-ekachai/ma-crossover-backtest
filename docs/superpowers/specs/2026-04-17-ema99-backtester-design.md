# EMA-99 Backtesting System — Design Spec

## Context

This project builds a local trading backtesting system to evaluate Moving Average (MA) based buy/sell strategies across multiple asset classes and timeframes. The goal is to measure strategy performance (PnL, ratios, drawdown) and test whether waiting for confirmation candles reduces false signals. Data will come from CSV files; a separate database project will handle data storage/sourcing later.

## Requirements

### Functional
- **MA types**: EMA (Exponential), SMA (Simple) — selectable per run
- **Period**: Configurable, default 99
- **Signal logic**: Buy when price is above the MA line, sell when below
- **Confirmation candles**: Wait N consecutive candles above/below MA before triggering entry (configurable, default 0 = instant signal)
- **Direction modes**: Long-only, short-only, or both (flip between long and short)
- **Position sizing**: All-in (100% equity), fixed dollar amount, or percentage of equity — configurable
- **Multi-timeframe**: Test the same strategy on different timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- **Batch comparison**: Run multiple configurations in one command and compare results side-by-side
- **Parameter optimization**: Sweep parameter ranges to find optimal settings
- **Performance metrics**: PnL, Return %, Sharpe Ratio, Max Drawdown, Win Rate, # Trades, Avg Trade, Best/Worst Trade (provided by Backtesting.py)
- **Commission/fees**: Configurable per backtest
- **Multi-asset**: Works with any asset (crypto, stocks, forex) as long as OHLCV data is provided

### Non-Functional
- Python 3.12
- `uv` for package management (no pip)
- `loguru` for logging
- `ruff` for linting
- `ty` for type checking
- Local development only — no deployment/cloud concerns

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.12 | Best ecosystem for trading/data |
| Backtesting engine | Backtesting.py | Simple API, built-in metrics/charts/optimizer |
| Package manager | uv | Fast, modern, user preference |
| Logging | Loguru | Zero-config structured logging |
| Linting | Ruff | Fast, comprehensive |
| Type checking | ty | User preference |
| Data handling | Pandas + NumPy | Industry standard |
| Indicators | pandas-ta | EMA/SMA calculations |
| Charts | Plotly (via Backtesting.py) | Interactive, built-in |
| Config | PyYAML | Human-readable config files |
| CLI | Click | Clean CLI interface with subcommands |
| Web viewer | Flask | Lightweight, serves saved results |

## Architecture

```
ema-99-buy-and-sell/
├── data/                          # Raw OHLCV CSV files (gitignored)
│   ├── BTCUSDT_1h.csv
│   ├── AAPL_1d.csv
│   └── ...
├── results/                       # Saved backtest results (gitignored)
│   ├── 2026-04-17_BTCUSDT_EMA99_1h/
│   │   ├── stats.json             # Performance metrics
│   │   ├── trades.csv             # Trade log
│   │   └── chart.html             # Interactive Plotly chart
│   └── ...
├── src/
│   ├── __init__.py
│   ├── strategies/
│   │   ├── __init__.py
│   │   └── ma_strategy.py         # MA strategy with confirmation logic
│   ├── indicators.py              # EMA, SMA helper functions
│   ├── data_loader.py             # CSV → DataFrame, validation, resampling
│   ├── runner.py                  # Batch runner, comparison logic
│   └── config.py                  # Config dataclass, YAML parsing
├── web/
│   ├── app.py                     # Flask app serving results
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html             # Results listing
│   │   └── detail.html            # Single result detail view
│   └── static/
│       └── style.css
├── main.py                        # CLI entry point (Click)
├── config.yaml                    # Default strategy config
├── pyproject.toml                 # Project config (uv, ruff, ty)
├── .gitignore
├── .python-version                # 3.12
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-17-ema99-backtester-design.md
```

## Data Format

### Input: OHLCV CSV

```csv
datetime,Open,High,Low,Close,Volume
2024-01-01 00:00:00,42000.00,42500.00,41800.00,42300.00,1500.5
2024-01-01 01:00:00,42300.00,42800.00,42100.00,42600.00,1200.3
```

- **Columns**: `datetime`, `Open`, `High`, `Low`, `Close`, `Volume`
- **datetime format**: `YYYY-MM-DD HH:MM:SS` (parsed as DatetimeIndex)
- **Column names**: Case-sensitive, must match exactly (Backtesting.py requirement)
- **One file per asset+timeframe** is simplest, but the loader can resample from smaller timeframes

### Supported timeframes for resampling
`1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d`, `1w`

## Component Details

### 1. Strategy (`src/strategies/ma_strategy.py`)

```python
class MAStrategy(Strategy):
    # Configurable parameters (class variables for optimization)
    ma_type = 'EMA'           # 'EMA' or 'SMA'
    ma_period = 99
    confirmation_candles = 0  # 0 = no confirmation
    direction = 'both'        # 'long_only', 'short_only', 'both'
    sizing_mode = 'all_in'    # 'all_in', 'fixed', 'percentage'
    sizing_fixed_amount = 1000.0   # used when sizing_mode='fixed'
    sizing_risk_pct = 0.02         # used when sizing_mode='percentage'
```

**Signal logic in `next()`:**
1. Compute whether close is above or below the MA
2. Track consecutive candles above/below (for confirmation)
3. When confirmation threshold is met:
   - **Above MA + confirmed**: Enter long (close short if direction=both)
   - **Below MA + confirmed**: Enter short or close long (depending on direction mode)

### 2. Data Loader (`src/data_loader.py`)

- `load_csv(path: str) -> pd.DataFrame` — Load and validate CSV
- `resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame` — Resample OHLCV to target timeframe
- Validation: checks for required columns, no NaN in OHLC, chronological order, DatetimeIndex

### 3. Config (`src/config.py`)

Pydantic-free dataclass-based config:

```python
@dataclass
class StrategyConfig:
    ma_type: str = 'EMA'
    ma_period: int = 99
    confirmation_candles: int = 0
    direction: str = 'both'

@dataclass
class SizingConfig:
    mode: str = 'all_in'
    fixed_amount: float = 1000.0
    risk_percentage: float = 0.02

@dataclass
class BacktestConfig:
    initial_cash: float = 10000.0
    commission: float = 0.001

@dataclass
class Config:
    strategy: StrategyConfig
    sizing: SizingConfig
    backtest: BacktestConfig
    data_path: str = ''
    timeframe: str = ''
```

### 4. CLI (`main.py`)

Three subcommands:

```bash
# Run a single backtest
python main.py run --data data/BTCUSDT_1h.csv --config config.yaml

# Run with inline overrides
python main.py run --data data/BTCUSDT_1h.csv --ma-type SMA --period 99 --confirm 3 --direction long_only

# Batch comparison: sweep parameters
python main.py compare --data data/BTCUSDT_1h.csv \
    --ma-types EMA,SMA \
    --confirm-range 0,1,2,3,5 \
    --timeframes 1h,4h,1d

# Parameter optimization
python main.py optimize --data data/BTCUSDT_1h.csv \
    --maximize "Sharpe Ratio" \
    --confirm-range 0-5

# Launch web viewer
python main.py web --port 5000
```

### 5. Runner (`src/runner.py`)

- `run_single(config: Config) -> dict` — Run one backtest, return stats + save results
- `run_comparison(configs: list[Config]) -> pd.DataFrame` — Run multiple, return comparison table
- `run_optimization(config: Config, param_ranges: dict) -> dict` — Use `bt.optimize()`
- Each run saves to `results/` with timestamp, asset, and config in folder name

### 6. Web Viewer (`web/app.py`)

Simple Flask app:
- **`/`** — Lists all saved results in `results/` folder, sorted by date
- **`/result/<id>`** — Shows stats table, trade log, and embedded interactive chart (the HTML file generated by Backtesting.py's `bt.plot()`)
- **`/compare`** — Side-by-side comparison of selected results
- No database — reads directly from `results/` directory (JSON + HTML files)

## Config File (`config.yaml`)

```yaml
strategy:
  ma_type: EMA              # EMA or SMA
  ma_period: 99
  confirmation_candles: 0   # 0 = no confirmation
  direction: both           # long_only, short_only, both

sizing:
  mode: all_in              # all_in, fixed, percentage
  fixed_amount: 1000        # used when mode=fixed
  risk_percentage: 0.02     # used when mode=percentage

backtest:
  initial_cash: 10000
  commission: 0.001         # 0.1% per trade

data:
  path: data/BTCUSDT_1h.csv
  timeframe: 1h             # target timeframe (resample if source is smaller)
```

## Output

### Console output (single run)
```
=== Backtest Results ===
Asset:          BTCUSDT
Timeframe:      1h
MA Type:        EMA(99)
Confirmation:   3 candles
Direction:      both
Period:         2024-01-01 → 2024-12-31

Return [%]:     45.23
Sharpe Ratio:   1.82
Max Drawdown:   -12.4%
Win Rate [%]:   58.3
# Trades:       47
Avg Trade [%]:  0.96

Results saved to: results/2026-04-17_BTCUSDT_EMA99_1h_confirm3/
```

### Console output (comparison)
```
┌──────────┬───────┬─────────┬───────────┬──────────┬──────────┬──────────┐
│ Config   │ MA    │ Confirm │ Return %  │ Sharpe   │ Max DD   │ # Trades │
├──────────┼───────┼─────────┼───────────┼──────────┼──────────┼──────────┤
│ Run 1    │ EMA99 │ 0       │ 38.2%     │ 1.45     │ -15.3%   │ 62       │
│ Run 2    │ EMA99 │ 3       │ 45.2%     │ 1.82     │ -12.4%   │ 47       │
│ Run 3    │ SMA99 │ 0       │ 32.1%     │ 1.21     │ -18.7%   │ 58       │
│ Run 4    │ SMA99 │ 3       │ 41.5%     │ 1.68     │ -13.1%   │ 43       │
└──────────┴───────┴─────────┴───────────┴──────────┴──────────┴──────────┘
```

## Verification

1. **Unit tests**: Test indicator calculations (EMA/SMA match expected values), data loader validation, config parsing
2. **Integration test**: Run a backtest with known data and verify stats match expected values
3. **Manual verification**: Run against real BTCUSDT 1h data, check that buy/sell signals align with MA crossings on a chart
4. **Comparison test**: Run batch comparison and verify the comparison table renders correctly
5. **Web viewer**: Start Flask app, verify results load and charts display

## Future Considerations (out of scope)

- PostgreSQL + TimescaleDB data storage (separate project)
- Data downloader CLI (separate project, feeds CSV or DB)
- Additional strategies beyond MA-based
- Stop-loss / take-profit / trailing stop (can be added to strategy later)
- Live trading / paper trading
