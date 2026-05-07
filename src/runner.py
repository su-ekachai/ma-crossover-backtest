"""Backtest runner with single, comparison, and optimization modes."""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from backtesting import Backtest
from bokeh.embed import file_html
from bokeh.resources import CDN
from loguru import logger

from src.config import Config
from src.data_loader import load_csv, resample
from src.strategies.ma_strategy import MAStrategy


def run_single(config: Config, data: pd.DataFrame | None = None) -> dict[str, Any]:
    """Run a single backtest.

    Args:
        config: Configuration for the backtest run.
        data: Pre-loaded DataFrame to avoid re-reading CSV (used by run_comparison).

    Returns:
        A dictionary containing:
        - 'stats': the backtest statistics dictionary
        - 'results_dir': path to the saved results directory
        - 'trades': DataFrame of individual trades
    """
    if data is not None:
        df = data.copy()
    else:
        df = load_csv(config.data.path)
        if config.data.timeframe:
            df = resample(df, config.data.timeframe)

    bt = Backtest(
        df,
        MAStrategy,
        cash=config.backtest.initial_cash,
        commission=config.backtest.commission,
        finalize_trades=True,
    )

    _apply_config_to_strategy(config)

    stats = bt.run()
    stats_dict = _extract_stats(stats)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    asset = (
        config.data.symbol.replace("/", "") if config.data.symbol else Path(config.data.path).stem
    )
    results_dir = (
        Path("results") / f"{run_id}_{asset}_MA{config.strategy.ma_type}"
        f"{config.strategy.ma_period}_{config.data.timeframe}"
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    stats["_trades"].to_csv(results_dir / "trades.csv", index=False)

    with open(results_dir / "stats.json", "w") as f:
        json.dump(_make_serializable(stats_dict), f, indent=2, default=str)

    config_meta = {
        "symbol": config.data.symbol,
        "exchange": config.data.exchange,
        "timeframe": config.data.timeframe,
        "source_timeframe": config.data.source_timeframe or config.data.timeframe,
        "ma_type": config.strategy.ma_type,
        "ma_period": config.strategy.ma_period,
    }
    with open(results_dir / "config.json", "w") as f:
        json.dump(config_meta, f, indent=2)

    try:
        fig = bt.plot(open_browser=False)
        html = file_html(fig, CDN)
        with open(results_dir / "chart.html", "w") as f:
            f.write(html)
    except Exception as e:
        logger.warning(f"Chart generation failed: {e}")

    return {
        "stats": stats_dict,
        "results_dir": str(results_dir),
        "trades": stats["_trades"],
    }


def run_comparison(configs: list[Config]) -> pd.DataFrame:
    """Run multiple backtest configurations and compare results.

    Args:
        configs: List of Config objects, each representing a different run.

    Returns:
        A DataFrame with columns: Run, MA, Period, Confirm, Direction,
        Return %, Sharpe, MaxDD, Trades.
    """
    data_cache: dict[tuple[str, str], pd.DataFrame] = {}
    rows = []
    for i, config in enumerate(configs):
        cache_key = (config.data.path, config.data.timeframe)
        if cache_key not in data_cache:
            df = load_csv(config.data.path)
            if config.data.timeframe:
                df = resample(df, config.data.timeframe)
            data_cache[cache_key] = df
        result = run_single(config, data=data_cache[cache_key])
        stats = result["stats"]
        rows.append(
            {
                "Run": f"Run {i + 1}",
                "MA": f"{config.strategy.ma_type}{config.strategy.ma_period}",
                "Confirm": config.strategy.confirmation_candles,
                "Direction": config.strategy.direction,
                "Return [%]": stats.get("Return [%]", 0),
                "Sharpe": stats.get("Sharpe Ratio", 0),
                "MaxDD": stats.get("Max. Drawdown [%]", 0),
                "Trades": stats.get("# Trades", 0),
            }
        )
    return pd.DataFrame(rows)


def run_optimization(
    config: Config,
    param_name: str,
    param_range: range,
    maximize: str = "Sharpe Ratio",
) -> dict[str, Any]:
    """Run parameter optimization on a backtest.

    Args:
        config: Base configuration for the backtest.
        param_name: Name of the parameter to sweep (e.g., 'ma_period').
        param_range: Range of values to test.
        maximize: Metric to maximize (e.g., 'Sharpe Ratio').

    Returns:
        A dictionary containing optimized parameters, stats, and results directory.
    """
    df = load_csv(config.data.path)
    if config.data.timeframe:
        df = resample(df, config.data.timeframe)

    bt = Backtest(
        df,
        MAStrategy,
        cash=config.backtest.initial_cash,
        commission=config.backtest.commission,
        finalize_trades=True,
    )

    _apply_config_to_strategy(config)

    param_kwargs = {param_name: param_range}
    stats = bt.optimize(**param_kwargs, maximize=maximize, return_heatmap=False)

    stats_dict = _extract_stats(stats)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    asset = Path(config.data.path).stem
    results_dir = Path("results") / f"{run_id}_{asset}_optimized_{param_name}"
    results_dir.mkdir(parents=True, exist_ok=True)

    optimized_value = getattr(stats._strategy, param_name)
    stats["_trades"].to_csv(results_dir / "trades.csv", index=False)

    with open(results_dir / "stats.json", "w") as f:
        json.dump(_make_serializable(stats_dict), f, indent=2, default=str)

    try:
        fig = bt.plot(open_browser=False)
        html = file_html(fig, CDN)
        with open(results_dir / "chart.html", "w") as f:
            f.write(html)
    except Exception as e:
        logger.warning(f"Chart generation failed: {e}")

    return {
        "stats": stats_dict,
        "optimized_params": {param_name: optimized_value},
        "results_dir": str(results_dir),
    }


def _apply_config_to_strategy(config: Config) -> None:
    """Apply configuration values to the MAStrategy class."""
    MAStrategy.ma_type = config.strategy.ma_type
    MAStrategy.ma_period = config.strategy.ma_period
    MAStrategy.confirmation_candles = config.strategy.confirmation_candles
    MAStrategy.direction = config.strategy.direction
    MAStrategy.sizing_mode = config.sizing.mode
    MAStrategy.sizing_fixed_amount = config.sizing.fixed_amount
    MAStrategy.sizing_risk_pct = config.sizing.risk_percentage


def _extract_stats(stats: Any) -> dict[str, Any]:
    """Extract serializable stats from the backtest stats object."""
    keys_to_extract = [
        "Return [%]",
        "Sharpe Ratio",
        "Max. Drawdown [%]",
        "Win Rate [%]",
        "# Trades",
        "Avg. Trade [%]",
        "Best Trade [%]",
        "Worst Trade [%]",
        "Profit Factor",
        "Expectancy [%]",
        "SQN",
        "Kelly Criterion",
    ]
    result = {}
    for key in keys_to_extract:
        if key in stats:
            result[key] = stats[key]
    return result


def _make_serializable(obj: Any) -> Any:
    """Convert non-serializable objects to serializable forms."""
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict()
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if hasattr(obj, "__float__"):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    return obj
