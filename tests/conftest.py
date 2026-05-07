"""Shared test fixtures."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.config import BacktestConfig, Config, DataConfig, SizingConfig, StrategyConfig


@pytest.fixture
def sample_ohlcv_df() -> pd.DataFrame:
    """Generate a synthetic OHLCV DataFrame with clear trend changes."""
    dates = pd.date_range("2024-01-01", periods=100, freq="h")
    prices = []
    base = 100.0
    for i in range(100):
        if i < 30:
            base += 0.5
        elif i < 60:
            base -= 0.5
        else:
            base += 0.3
        prices.append(base)

    df = pd.DataFrame(
        {
            "Open": [p - 0.2 for p in prices],
            "High": [p + 1.0 for p in prices],
            "Low": [p - 1.0 for p in prices],
            "Close": prices,
            "Volume": [1000.0] * 100,
        },
        index=dates,
    )
    df.index.name = "datetime"
    return df


@pytest.fixture
def sample_csv_path(sample_ohlcv_df: pd.DataFrame) -> Path:
    """Write sample OHLCV data to a temp CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_ohlcv_df.to_csv(f)
        return Path(f.name)


@pytest.fixture
def default_config(sample_csv_path: Path) -> Config:
    """Create a default Config pointing to sample data."""
    return Config(
        strategy=StrategyConfig(ma_type="EMA", ma_period=5, confirmation_candles=0),
        sizing=SizingConfig(),
        backtest=BacktestConfig(initial_cash=10000.0),
        data=DataConfig(path=str(sample_csv_path)),
    )


@pytest.fixture
def sample_trades_df() -> pd.DataFrame:
    """Sample trades DataFrame matching backtesting.py output format."""
    return pd.DataFrame(
        {
            "EntryTime": ["2024-01-01 10:00:00", "2024-01-02 14:00:00"],
            "ExitTime": ["2024-01-01 18:00:00", "2024-01-03 09:00:00"],
            "EntryPrice": [100.0, 105.0],
            "ExitPrice": [103.0, 102.0],
            "Size": [1.0, -1.0],
            "PnL": [3.0, 3.0],
            "ReturnPct": [0.03, 0.03],
        }
    )


@pytest.fixture
def results_dir_with_data(tmp_path: Path) -> Path:
    """Create a fake results directory with a valid result folder."""
    results = tmp_path / "results"
    results.mkdir()

    folder = results / "20260507_BTCUSDT_MAEMA99_1h"
    folder.mkdir()

    stats = {
        "Return [%]": 12.5,
        "Sharpe Ratio": 1.2,
        "Max. Drawdown [%]": -5.0,
        "Win Rate [%]": 60.0,
        "# Trades": 10,
        "Avg. Trade [%]": 1.25,
        "Best Trade [%]": 5.0,
        "Worst Trade [%]": -2.0,
        "Profit Factor": 2.1,
    }
    with open(folder / "stats.json", "w") as f:
        json.dump(stats, f)

    trades_csv = "EntryTime,ExitTime,EntryPrice,ExitPrice,Size,PnL,ReturnPct\n"
    trades_csv += "2024-01-01 10:00:00,2024-01-01 18:00:00,100.0,103.0,1.0,3.0,0.03\n"
    (folder / "trades.csv").write_text(trades_csv)

    config = {
        "symbol": "BTC/USDT",
        "exchange": "binance",
        "timeframe": "1h",
        "source_timeframe": "1m",
        "ma_type": "EMA",
        "ma_period": 99,
    }
    with open(folder / "config.json", "w") as f:
        json.dump(config, f)

    return results
