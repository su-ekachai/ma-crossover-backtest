"""History page — view past backtest results with chart reconstruction."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.charts import create_backtest_chart
from src.config import QuestDBConfig
from src.indicators import calculate_ema, calculate_sma
from src.questdb_reader import QuestDBSource
from src.results import list_results, load_result_config, load_result_stats, load_trades

# --- Sidebar: Filters ---
results = list_results()

with st.sidebar:
    st.markdown('<p class="sidebar-header">Filters</p>', unsafe_allow_html=True)

    if not results:
        st.info("No saved results yet. Run a backtest first.")
        st.stop()

    all_assets = sorted({r["asset"] for r in results})
    all_ma_types = sorted({r["ma_type"] for r in results})

    filter_asset = st.multiselect("Asset", all_assets, default=all_assets)
    filter_ma = st.multiselect("MA Type", all_ma_types, default=all_ma_types)
    sort_by = st.selectbox("Sort by", ["Date (newest)", "Return %", "Sharpe", "Max DD", "Trades"])

filtered = [r for r in results if r["asset"] in filter_asset and r["ma_type"] in filter_ma]

if sort_by == "Return %":
    filtered.sort(key=lambda r: r.get("return_pct") or 0, reverse=True)
elif sort_by == "Sharpe":
    filtered.sort(key=lambda r: r.get("sharpe") or 0, reverse=True)
elif sort_by == "Max DD":
    filtered.sort(key=lambda r: r.get("max_dd") or 0)
elif sort_by == "Trades":
    filtered.sort(key=lambda r: r.get("num_trades") or 0, reverse=True)

# --- Main Area ---
st.title("History")
st.caption("View past backtest results and charts")

if not filtered:
    st.warning("No results match the current filters.")
    st.stop()

# --- Results Table ---
table_data = []
for r in filtered:
    table_data.append(
        {
            "Date": r["date"],
            "Asset": r["asset"],
            "MA": f"{r['ma_type']}{r['ma_period']}",
            "TF": r["timeframe"],
            "Return %": r.get("return_pct"),
            "Sharpe": r.get("sharpe"),
            "Max DD %": r.get("max_dd"),
            "Win %": r.get("win_rate"),
            "Trades": r.get("num_trades"),
        }
    )

table_df = pd.DataFrame(table_data)
st.dataframe(
    table_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Return %": st.column_config.NumberColumn(format="%.2f"),
        "Sharpe": st.column_config.NumberColumn(format="%.2f"),
        "Max DD %": st.column_config.NumberColumn(format="%.2f"),
        "Win %": st.column_config.NumberColumn(format="%.1f"),
        "Trades": st.column_config.NumberColumn(format="%d"),
    },
)

# --- Selection ---
st.divider()

result_labels = [
    f"{r['date']} — {r['asset']} {r['ma_type']}{r['ma_period']} ({r['timeframe']})"
    for r in filtered
]
selected_idx = st.selectbox(
    "Select a result to view details and chart",
    range(len(filtered)),
    format_func=lambda i: result_labels[i],
)

if selected_idx is not None:
    selected = filtered[selected_idx]
    selected_id = selected["id"]

    stats = load_result_stats(selected_id)
    trades = load_trades(selected_id)
    config = load_result_config(selected_id)

    # --- Metrics Row ---
    if stats:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        ret = stats.get("Return [%]", 0)
        m1.metric("Return", f"{ret:.2f}%")
        m2.metric("Sharpe", f"{stats.get('Sharpe Ratio', 0) or 0:.2f}")
        m3.metric("Max DD", f"{stats.get('Max. Drawdown [%]', 0):.2f}%")
        m4.metric("Win Rate", f"{stats.get('Win Rate [%]', 0):.1f}%")
        m5.metric("Trades", f"{int(stats.get('# Trades', 0))}")
        m6.metric("Profit Factor", f"{stats.get('Profit Factor', 0) or 0:.2f}")

    # --- Chart Reconstruction ---
    st.divider()

    chart_shown = False
    if config and config.get("symbol") and config.get("exchange") and not trades.empty:
        try:
            start = pd.to_datetime(trades["EntryTime"].min())
            end = pd.to_datetime(trades["ExitTime"].max())

            qdb = QuestDBSource(QuestDBConfig.from_env())
            source_tf = config.get("source_timeframe", config["timeframe"])
            target_tf = config["timeframe"]
            resample_to = target_tf if target_tf != source_tf else None

            df = qdb.load_ohlcv(
                config["symbol"],
                config["exchange"],
                source_tf,
                start=start.to_pydatetime(),
                end=end.to_pydatetime(),
                resample_to=resample_to,
            )
            qdb.close()

            ma_type = config["ma_type"]
            ma_period = config["ma_period"]
            ma_func = calculate_ema if ma_type == "EMA" else calculate_sma
            ma_series = ma_func(df["Close"], ma_period)
            ma_label = f"{ma_type}{ma_period}"

            fig = create_backtest_chart(df, ma_series, trades, ma_label)
            st.plotly_chart(fig, use_container_width=True)
            chart_shown = True
        except Exception as e:
            st.warning(f"Could not reconstruct chart: {e}")

    if not chart_shown:
        st.info(
            "Chart unavailable — run a new backtest with QuestDB data to enable chart reconstruction."
        )

    # --- Trade Log ---
    if not trades.empty:
        with st.expander(f"Trade Log ({len(trades)} trades)"):
            st.dataframe(trades, hide_index=True, use_container_width=True)

    # --- Compare Section ---
    st.divider()
    show_compare = st.checkbox("Compare with other results")

    if show_compare:
        compare_ids = st.multiselect(
            "Select 2-5 results to compare",
            [r["id"] for r in filtered],
            default=[selected_id],
            max_selections=5,
            format_func=lambda rid: next(
                (
                    f"{r['date']} — {r['asset']} {r['ma_type']}{r['ma_period']}"
                    for r in filtered
                    if r["id"] == rid
                ),
                rid,
            ),
        )

        if len(compare_ids) >= 2:
            compare_data = []
            for rid in compare_ids:
                s = load_result_stats(rid)
                parsed = next((r for r in filtered if r["id"] == rid), {})
                compare_data.append(
                    {
                        "Run": f"{parsed.get('asset', '')} {parsed.get('ma_type', '')}"
                        f"{parsed.get('ma_period', '')}",
                        "Return %": s.get("Return [%]"),
                        "Sharpe": s.get("Sharpe Ratio"),
                        "Max DD %": s.get("Max. Drawdown [%]"),
                        "Win %": s.get("Win Rate [%]"),
                        "Trades": s.get("# Trades"),
                        "Profit Factor": s.get("Profit Factor"),
                    }
                )

            compare_df = pd.DataFrame(compare_data)
            st.dataframe(compare_df, hide_index=True, use_container_width=True)
        elif compare_ids:
            st.info("Select at least 2 results to compare.")
