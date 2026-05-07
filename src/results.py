"""Results directory scanner for saved backtest runs."""

import json
import re
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path("results")


def parse_result_folder(folder_name: str) -> dict | None:
    """Parse a result folder name to extract metadata.

    Folder names look like: 20260417_123456_BTCUSDT_MAEMA99_1h
    Returns dict with: id, date, asset, ma_type, ma_period, timeframe
    """
    pattern = r"^(\d{8})_(\w+)_MA(EMA|SMA)(\d+)(?:_(.*))?$"
    match = re.match(pattern, folder_name)
    if not match:
        return None

    date_str, asset, ma_type, ma_period, timeframe = match.groups()
    return {
        "id": folder_name,
        "date": date_str,
        "asset": asset,
        "ma_type": ma_type,
        "ma_period": int(ma_period),
        "timeframe": timeframe or "",
    }


def load_result_stats(result_id: str) -> dict:
    """Load stats.json for a given result ID."""
    stats_path = RESULTS_DIR / result_id / "stats.json"
    if not stats_path.exists():
        return {}
    with open(stats_path) as f:
        return json.load(f)


def load_trades(result_id: str) -> pd.DataFrame:
    """Load trades.csv for a given result ID."""
    trades_path = RESULTS_DIR / result_id / "trades.csv"
    if not trades_path.exists():
        return pd.DataFrame()
    return pd.read_csv(trades_path)


def load_result_config(result_id: str) -> dict:
    """Load config.json for a given result ID."""
    config_path = RESULTS_DIR / result_id / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return json.load(f)


def list_results() -> list[dict]:
    """List all result folders with their metadata and key stats."""
    if not RESULTS_DIR.exists():
        return []

    results = []
    for folder in sorted(RESULTS_DIR.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        parsed = parse_result_folder(folder.name)
        if parsed is None:
            continue

        stats = load_result_stats(folder.name)
        parsed["return_pct"] = stats.get("Return [%]")
        parsed["sharpe"] = stats.get("Sharpe Ratio")
        parsed["max_dd"] = stats.get("Max. Drawdown [%]")
        parsed["num_trades"] = stats.get("# Trades")
        parsed["win_rate"] = stats.get("Win Rate [%]")
        parsed["avg_trade"] = stats.get("Avg. Trade [%]")
        parsed["best_trade"] = stats.get("Best Trade [%]")
        parsed["worst_trade"] = stats.get("Worst Trade [%]")
        results.append(parsed)

    return results
