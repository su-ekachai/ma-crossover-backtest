# EMA-99 Backtesting System — Implementation Plan

## Context

Based on the design spec at `docs/superpowers/specs/2026-04-17-ema99-backtester-design.md`, this plan outlines the implementation of a local trading backtesting system using EMA/SMA strategies with Backtesting.py.

**Key technology decisions confirmed via Backtesting.py documentation research:**
- Strategy parameters via **class variables** (compatible with `bt.optimize()`)
- Position sizing via `size=` parameter on `buy()`/`sell()` (0-1 = fraction of equity, >=1 = units)
- Confirmation candle tracking via **instance variables** that persist across `next()` calls
- Stop-loss/take-profit via `sl=` and `tp=` parameters on orders

---

## Phase 1: Project Scaffolding

**Goal:** Create the project skeleton with all directories, configuration files, and dependencies.

### Files to create:

| File | Description |
|------|-------------|
| `pyproject.toml` | Project config: uv, ruff, ty, all runtime deps |
| `.gitignore` | Gitignore: data/, results/, __pycache__, .python-version |
| `.python-version` | Contains: `3.12` |
| `config.yaml` | Default strategy config |
| `src/__init__.py` | Empty init |
| `src/strategies/__init__.py` | Empty init |
| `src/strategies/ma_strategy.py` | **TODO: define MAStrategy stub for now (depends on indicators)** |
| `src/indicators.py` | **TODO: stub (depends on nothing)** |
| `src/data_loader.py` | **TODO: stub (depends on nothing)** |
| `src/config.py` | **TODO: stub (depends on nothing)** |
| `src/runner.py` | **TODO: stub (depends on nothing)** |
| `main.py` | **TODO: stub (depends on nothing)** |
| `web/app.py` | **TODO: stub** |
| `web/templates/base.html` | **TODO** |
| `web/templates/index.html` | **TODO** |
| `web/templates/detail.html` | **TODO** |
| `web/static/style.css` | **TODO** |
| `data/.gitkeep` | Placeholder for gitignored data directory |
| `results/.gitkeep` | Placeholder for gitignored results directory |
| `tests/__init__.py` | Empty init |

### Dependencies to include in `pyproject.toml`:

```
[project]
requires-python = ">=3.12"
dependencies = [
    "backtesting.py>=0.3.0",
    "pandas>=2.0.0",
    "pandas-ta>=0.3.0",
    "pyyaml>=6.0",
    "click>=8.0",
    "flask>=3.0",
    "loguru>=0.7",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.1.0",
    "ty>=0.1.0",
    "pytest>=7.0",
    "pytest-cov>=4.0",
]
```

### CLI subcommands (from design spec):
```bash
python main.py run --data data/BTCUSDT_1h.csv --config config.yaml
python main.py compare --data data/BTCUSDT_1h.csv --ma-types EMA,SMA --confirm-range 0,1,2,3,5 --timeframes 1h,4h,1d
python main.py optimize --data data/BTCUSDT_1h.csv --maximize "Sharpe Ratio" --confirm-range 0-5
python main.py web --port 5000
```

---

## Phase 2: Core Modules

### 2.1 Indicators (`src/indicators.py`)

**Purpose:** Pure EMA/SMA calculation functions using pandas-ta.

```python
import pandas as pd
import pandas_ta as ta

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return ta.ema(prices, length=period)

def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return ta.sma(prices, length=period)
```

**Tests needed:**
- Verify EMA/SMA output length matches input
- Verify known values (e.g., period=5 on [1,2,3,4,5] should give expected result)
- Edge case: period > length of data

---

### 2.2 Config (`src/config.py`)

**Purpose:** Dataclass-based config with YAML parsing (NO pydantic).

```python
from dataclasses import dataclass, field
from typing import Optional
import yaml

@dataclass
class StrategyConfig:
    ma_type: str = 'EMA'           # 'EMA' or 'SMA'
    ma_period: int = 99
    confirmation_candles: int = 0  # 0 = no confirmation
    direction: str = 'both'        # 'long_only', 'short_only', 'both'

@dataclass
class SizingConfig:
    mode: str = 'all_in'           # 'all_in', 'fixed', 'percentage'
    fixed_amount: float = 1000.0
    risk_percentage: float = 0.02

@dataclass
class BacktestConfig:
    initial_cash: float = 10000.0
    commission: float = 0.001     # 0.1% per trade

@dataclass
class Config:
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data_path: str = ''
    timeframe: str = ''

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        """Load config from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        # Map YAML structure to dataclass fields
        ...

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        ...
```

**Tests needed:**
- Load config from YAML file
- Override config with CLI args (test with_kwargs)
- Validate enum fields (ma_type in ['EMA', 'SMA'], direction in ['long_only', 'short_only', 'both'])

---

### 2.3 Data Loader (`src/data_loader.py`)

**Purpose:** Load CSV files into DataFrames, validate schema, resample timeframes.

```python
import pandas as pd
from pathlib import Path

REQUIRED_COLUMNS = ['datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
TIMEFRAME_RESAMPLERS = {
    '1m': '1T', '5m': '5T', '15m': '15T', '30m': '30T',
    '1h': '1H', '2h': '2H', '4h': '4H', '1d': '1D', '1w': '1W'
}

def load_csv(path: str) -> pd.DataFrame:
    """Load OHLCV CSV with validation."""
    df = pd.read_csv(path, parse_dates=['datetime'])
    df.set_index('datetime', inplace=True)

    # Validate columns exist
    missing = set(REQUIRED_COLUMNS[1:]) - set(df.columns)  # exclude 'datetime' from check
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Validate no NaN in OHLCV
    if df[['Open', 'High', 'Low', 'Close', 'Volume']].isna().any().any():
        raise ValueError("NaN values found in OHLCV data")

    # Validate chronological order
    if not df.index.is_monotonic_increasing:
        df.sort_index(inplace=True)

    return df

def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample OHLCV to target timeframe."""
    rule = TIMEFRAME_RESAMPLERS.get(timeframe)
    if not rule:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    resampled = df.resample(rule).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    return resampled
```

**Tests needed:**
- Load valid CSV
- Fail on missing columns
- Fail on NaN values
- Resample 1h → 4h correctly (OHLC aggregation, volume sum)
- Resample from smaller TF than target (e.g., 1m → 1h)

---

### 2.4 MA Strategy (`src/strategies/ma_strategy.py`)

**Purpose:** Backtesting.py Strategy with configurable MA type, period, confirmation candles, direction, position sizing.

```python
from backtesting import Strategy
from backtesting.lib import crossover
import pandas_ta as ta

class MAStrategy(Strategy):
    ma_type = 'EMA'
    ma_period = 99
    confirmation_candles = 0
    direction = 'both'       # 'long_only', 'short_only', 'both'
    sizing_mode = 'all_in'   # 'all_in', 'fixed', 'percentage'
    sizing_fixed_amount = 1000.0
    sizing_risk_pct = 0.02

    def init(self):
        prices = self.data.Close
        if self.ma_type == 'EMA':
            self.ma = self.I(lambda: ta.ema(prices, length=self.ma_period))
        else:
            self.ma = self.I(lambda: ta.sma(prices, length=self.ma_period))

        # Track consecutive candles above/below MA
        self._consecutive_above = 0
        self._consecutive_below = 0

    def next(self):
        close = self.data.Close[-1]
        ma = self.ma[-1]

        above = close > ma
        below = close < ma

        if above:
            self._consecutive_above += 1
            self._consecutive_below = 0
        elif below:
            self._consecutive_below += 1
            self._consecutive_above = 0

        confirmed_above = self._consecutive_above >= self.confirmation_candles
        confirmed_below = self._consecutive_below >= self.confirmation_candles

        if not self.position:
            # Entry logic
            if confirmed_above and self.direction in ('long_only', 'both'):
                size = self._calculate_size()
                self.buy(size=size)
            elif confirmed_below and self.direction in ('short_only', 'both'):
                size = self._calculate_size()
                self.sell(size=size)
        else:
            # Exit logic (close opposite position when direction=both)
            if self.position.is_long and confirmed_below and self.direction == 'both':
                self.position.close()
            elif self.position.is_short and confirmed_above and self.direction == 'both':
                self.position.close()

    def _calculate_size(self):
        if self.sizing_mode == 'all_in':
            return 1.0  # 100% of equity
        elif self.sizing_mode == 'fixed':
            return self.sizing_fixed_amount / self.data.Close[-1]
        elif self.sizing_mode == 'percentage':
            equity = self._broker.equity
            return (equity * self.sizing_risk_pct) / self.data.Close[-1]
        return 1.0
```

**Tests needed:**
- Strategy initializes with class variables
- EMA/SMA calculation produces expected shape
- Confirmation candle logic works (test with synthetic data)
- Direction modes work correctly (long_only, short_only, both)
- Position sizing modes work

---

### 2.5 Runner (`src/runner.py`)

**Purpose:** Orchestrate backtest runs, save results, support comparison and optimization.

```python
from pathlib import Path
import json
from datetime import datetime
from typing import Optional

def run_single(config: Config) -> dict:
    """Run single backtest, return stats, save results to results/."""
    from backtesting import Backtest
    from src.strategies.ma_strategy import MAStrategy

    df = load_csv(config.data_path)
    if config.timeframe:
        df = resample(df, config.timeframe)

    bt = Backtest(df, MAStrategy,
                  cash=config.backtest.initial_cash,
                  commission=config.backtest.commission)

    # Map config to strategy params
    MAStrategy.ma_type = config.strategy.ma_type
    MAStrategy.ma_period = config.strategy.ma_period
    MAStrategy.confirmation_candles = config.strategy.confirmation_candles
    MAStrategy.direction = config.strategy.direction
    MAStrategy.sizing_mode = config.sizing.mode
    MAStrategy.sizing_fixed_amount = config.sizing.fixed_amount
    MAStrategy.sizing_risk_pct = config.sizing.risk_percentage

    stats = bt.run()
    stats_dict = {k: v for k, v in stats.items() if not callable(v)}

    # Save results
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    asset = Path(config.data_path).stem
    results_dir = Path('results') / f"{run_id}_{asset}_MA{config.strategy.ma_type}{config.strategy.ma_period}_{config.timeframe}"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / 'stats.json', 'w') as f:
        json.dump(stats_dict, f, indent=2, default=str)

    stats._trades.to_csv(results_dir / 'trades.csv', index=False)

    if hasattr(stats, '_strategy'):
        fig = bt.plot()
        fig.write_html(str(results_dir / 'chart.html'))

    return {'stats': stats_dict, 'results_dir': str(results_dir)}
```

**Comparison function:** Run multiple configs, return a pandas DataFrame with key metrics:
- Config label, MA type, period, confirmation, Return %, Sharpe, Max Drawdown, # Trades

**Optimization function:** Use `bt.optimize()` with parameter ranges.

**Tests needed:**
- Single run produces stats.json and trades.csv
- Comparison produces DataFrame with all expected columns
- Results directory naming includes timestamp, asset, MA type

---

## Phase 3: CLI (`main.py`)

### Click subcommands:

```python
@click.group()
def cli():
    """EMA-99 Backtesting System CLI."""
    pass

@cli.command()
@click.option('--data', required=True, help='Path to OHLCV CSV file')
@click.option('--config', help='YAML config file')
@click.option('--ma-type', default='EMA', type=click.Choice(['EMA', 'SMA']))
@click.option('--period', default=99, type=int)
@click.option('--confirm', 'confirmation_candles', default=0, type=int)
@click.option('--direction', default='both', type=click.Choice(['long_only', 'short_only', 'both']))
def run(data, config, ma_type, period, confirmation_candles, direction):
    """Run a single backtest."""
    ...

@cli.command()
@click.option('--data', required=True)
@click.option('--ma-types', default='EMA,SMA')
@click.option('--confirm-range', default='0,1,2,3,5')
@click.option('--timeframes', default='1h,4h,1d')
def compare(data, ma_types, confirm_range, timeframes):
    """Run batch comparison."""
    ...

@cli.command()
@click.option('--data', required=True)
@click.option('--maximize', default='Sharpe Ratio')
@click.option('--confirm-range', default='0-5')
def optimize(data, maximize, confirm_range):
    """Parameter optimization."""
    ...

@cli.command()
@click.option('--port', default=5000)
def web(port):
    """Launch web viewer."""
    ...
```

---

## Phase 4: Web Viewer

### Routes:

| Route | Description |
|-------|-------------|
| `/` | Lists all results folders, sorted by date |
| `/result/<result_id>` | Shows stats, trade log, embedded chart HTML |
| `/compare` | Side-by-side comparison of selected results |

### Implementation:
- `web/app.py`: Flask app reading from `results/` directory
- Templates: Jinja2 templates inheriting from `base.html`
- Charts: Embed `chart.html` files via iframe (generated by Backtesting.py's `bt.plot()`)

---

## Phase 5: Testing

### Unit tests:
1. `tests/test_indicators.py` - EMA/SMA calculations
2. `tests/test_data_loader.py` - CSV loading, validation, resampling
3. `tests/test_config.py` - YAML parsing, field validation

### Integration tests:
4. `tests/test_strategy.py` - MAStrategy with synthetic OHLCV data
5. `tests/test_runner.py` - Full backtest run, verify output files

### Test data:
Create a minimal synthetic CSV in `tests/data/` for reproducible testing.

---

## Implementation Order Summary

| Step | File | Dependencies |
|------|------|-------------|
| 1 | Scaffolding (pyproject.toml, dirs) | None |
| 2 | `src/indicators.py` | pandas-ta |
| 3 | `src/config.py` | dataclasses, yaml |
| 4 | `src/data_loader.py` | pandas |
| 5 | `src/strategies/ma_strategy.py` | indicators, backtesting.py |
| 6 | `src/runner.py` | config, data_loader, strategy |
| 7 | `main.py` | runner, config, click |
| 8 | `config.yaml` | None |
| 9 | `web/app.py` + templates | flask |
| 10 | Tests | All of above |

---

## Verification Plan

After each phase:

1. **Phase 1**: Run `uv sync`, verify no import errors
2. **Phase 2**: Run pytest on each module as it's completed
3. **Phase 3**: Test CLI commands with synthetic data
4. **Phase 4**: Start Flask app, verify pages load
5. **Final**: Run full integration test with real-ish data

---

## Risk Areas

1. **Backtesting.py EMA/SMA integration**: Need to verify `self.I()` wrapper works correctly with pandas-ta functions
2. **Confirmation candle state**: Instance variables persist across `next()` calls - need to ensure re-initialization is correct when running multiple backtests
3. **Resampling volume**: Must use `sum` not `last` for volume aggregation
4. **CLI config override**: Merging YAML config with CLI argument overrides needs careful handling
5. **Results directory naming**: Must be unique to avoid collisions in batch mode
