"""Flask web app for viewing backtest results."""

import json
import re
from pathlib import Path

import pandas as pd
from flask import Flask, abort, render_template, request

app = Flask(__name__)

RESULTS_DIR = Path("results")


def _validate_result_path(result_id: str) -> Path:
    """Resolve result path and verify it's within RESULTS_DIR."""
    target = (RESULTS_DIR / result_id).resolve()
    if not str(target).startswith(str(RESULTS_DIR.resolve())):
        abort(404)
    return target


def parse_result_folder(folder_name: str) -> dict | None:
    """Parse a result folder name to extract metadata.

    Folder names look like: 20260417_BTCUSDT_MAEMA99_1h
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
    result_dir = _validate_result_path(result_id)
    stats_path = result_dir / "stats.json"
    if not stats_path.exists():
        return {}
    with open(stats_path) as f:
        return json.load(f)


def load_trades(result_id: str) -> pd.DataFrame:
    """Load trades.csv for a given result ID as HTML."""
    result_dir = _validate_result_path(result_id)
    trades_path = result_dir / "trades.csv"
    if not trades_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(trades_path)
    return df


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
        parsed["return_pct"] = stats.get("Return [%]", "N/A")
        parsed["sharpe"] = stats.get("Sharpe Ratio", "N/A")
        parsed["max_dd"] = stats.get("Max. Drawdown [%]", "N/A")
        parsed["num_trades"] = stats.get("# Trades", "N/A")
        parsed["win_rate"] = stats.get("Win Rate [%]", "N/A")
        parsed["avg_trade"] = stats.get("Avg. Trade [%]", "N/A")
        parsed["best_trade"] = stats.get("Best Trade [%]", "N/A")
        parsed["worst_trade"] = stats.get("Worst Trade [%]", "N/A")
        results.append(parsed)

    return results


@app.route("/")
def index() -> str:
    """List all saved backtest results."""
    results = list_results()
    return render_template("index.html", results=results)


@app.route("/result/<result_id>")
def result(result_id: str) -> str:
    """Show detail view for a single result."""
    parsed = parse_result_folder(result_id)
    if parsed is None:
        abort(404)

    stats = load_result_stats(result_id)
    trades = load_trades(result_id)
    trades_html = (
        trades.to_html(classes="trades-table", border=0, index=False) if not trades.empty else ""
    )

    chart_path = RESULTS_DIR / result_id / "chart.html"
    has_chart = chart_path.exists()

    return render_template(
        "detail.html",
        result={
            **parsed,
            "name": result_id,
            "return_pct": stats.get("Return [%]", "N/A"),
            "sharpe": stats.get("Sharpe Ratio", "N/A"),
            "max_dd": stats.get("Max. Drawdown [%]", "N/A"),
            "num_trades": stats.get("# Trades", "N/A"),
            "win_rate": stats.get("Win Rate [%]", "N/A"),
            "avg_trade": stats.get("Avg. Trade [%]", "N/A"),
            "best_trade": stats.get("Best Trade [%]", "N/A"),
            "worst_trade": stats.get("Worst Trade [%]", "N/A"),
            "profit_factor": stats.get("Profit Factor", "N/A"),
            "expectancy": stats.get("Expectancy [%]", "N/A"),
            "sqn": stats.get("SQN", "N/A"),
            "kelly": stats.get("Kelly Criterion", "N/A"),
            "trades_html": trades_html,
            "has_chart": has_chart,
        },
    )


@app.route("/compare")
def compare() -> str:
    """Compare selected results side-by-side."""
    selected = request.args.getlist("results")
    if not selected:
        return render_template("compare.html", results=list_results(), selected=[])

    comparison_data = []
    for result_id in selected:
        parsed = parse_result_folder(result_id)
        if parsed is None:
            continue
        stats = load_result_stats(result_id)
        comparison_data.append(
            {
                **parsed,
                "return_pct": stats.get("Return [%]", "N/A"),
                "sharpe": stats.get("Sharpe Ratio", "N/A"),
                "max_dd": stats.get("Max. Drawdown [%]", "N/A"),
                "num_trades": stats.get("# Trades", "N/A"),
                "win_rate": stats.get("Win Rate [%]", "N/A"),
            }
        )

    return render_template(
        "compare.html",
        results=list_results(),
        selected=comparison_data,
        selected_ids=[r["id"] for r in comparison_data],
    )
