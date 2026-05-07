"""Optimize page — parameter sweeps with heatmap visualization."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.charts import create_optimization_heatmap
from src.config import Config, QuestDBConfig
from src.data_loader import resample
from src.questdb_reader import TIMEFRAME_MINUTES, QuestDBSource
from src.runner import run_single

# --- Sidebar: Data Source ---
with st.sidebar:
    st.markdown('<p class="sidebar-header">Data Source</p>', unsafe_allow_html=True)
    source = st.radio(
        "Source",
        ["QuestDB", "CSV Upload"],
        horizontal=True,
        label_visibility="collapsed",
        key="opt_source",
    )

    df: pd.DataFrame | None = None
    asset_name = ""
    timeframe = ""

    if source == "QuestDB":
        try:
            qdb = QuestDBSource(QuestDBConfig.from_env())
            symbols_df = qdb.list_symbols()
            qdb.close()
        except Exception as e:
            st.error(f"Cannot connect to QuestDB: {e}")
            st.stop()

        if symbols_df.empty:
            st.warning("No data in QuestDB.")
            st.stop()

        symbol = st.selectbox("Symbol", symbols_df["symbol"].unique(), key="opt_symbol")
        exchanges = symbols_df[symbols_df["symbol"] == symbol]["exchange"].unique()
        exchange = st.selectbox("Exchange", exchanges, key="opt_exchange")

        source_timeframes = symbols_df[
            (symbols_df["symbol"] == symbol) & (symbols_df["exchange"] == exchange)
        ]["timeframe"].unique()
        source_timeframe = st.selectbox("Source TF", source_timeframes, key="opt_src_tf")

        source_minutes = TIMEFRAME_MINUTES.get(source_timeframe, 0)
        available_targets = [tf for tf, mins in TIMEFRAME_MINUTES.items() if mins >= source_minutes]
        target_timeframe = st.selectbox("Backtest TF", available_targets, key="opt_tgt_tf")

        timeframe = target_timeframe
        asset_name = symbol.replace("/", "")
        resample_to = target_timeframe if target_timeframe != source_timeframe else None

        if st.button("Load Data", use_container_width=True, key="opt_load"):
            with st.spinner("Loading..."):
                qdb = QuestDBSource(QuestDBConfig.from_env())
                df = qdb.load_ohlcv(symbol, exchange, source_timeframe, resample_to=resample_to)
                qdb.close()
                st.session_state["opt_data"] = df
                st.session_state["opt_asset"] = asset_name
                st.session_state["opt_timeframe"] = timeframe

    else:
        uploaded = st.file_uploader("OHLCV CSV", type=["csv"], key="opt_csv")
        timeframe = st.selectbox(
            "Resample To",
            ["", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1w"],
            key="opt_resample",
        )
        if uploaded:
            df = pd.read_csv(uploaded, parse_dates=["datetime"], index_col="datetime")
            df = df.sort_index()
            asset_name = Path(uploaded.name).stem
            if timeframe:
                df = resample(df, timeframe)
            st.session_state["opt_data"] = df
            st.session_state["opt_asset"] = asset_name
            st.session_state["opt_timeframe"] = timeframe

    if "opt_data" in st.session_state:
        df = st.session_state["opt_data"]
        asset_name = st.session_state.get("opt_asset", "")
        timeframe = st.session_state.get("opt_timeframe", "")

    # --- Sidebar: Sweep Config ---
    st.markdown('<p class="sidebar-header">Sweep Parameters</p>', unsafe_allow_html=True)
    ma_type = st.selectbox("MA Type", ["EMA", "SMA"], key="opt_ma")
    direction = st.selectbox("Direction", ["both", "long_only", "short_only"], key="opt_dir")

    c1, c2 = st.columns(2)
    with c1:
        period_min = st.number_input("Period Min", min_value=2, value=20, key="opt_pmin")
        confirm_min = st.number_input("Confirm Min", min_value=0, value=0, key="opt_cmin")
    with c2:
        period_max = st.number_input("Period Max", min_value=3, value=200, key="opt_pmax")
        confirm_max = st.number_input("Confirm Max", min_value=0, value=5, key="opt_cmax")

    period_step = st.number_input("Period Step", min_value=1, value=10, key="opt_pstep")
    maximize = st.selectbox(
        "Maximize",
        ["Return [%]", "Sharpe Ratio", "Win Rate [%]", "Profit Factor", "SQN"],
        key="opt_metric",
    )

    st.divider()

    run_disabled = "opt_data" not in st.session_state
    if st.button(
        "Run Optimization", type="primary", use_container_width=True, disabled=run_disabled
    ):
        data = st.session_state.get("opt_data")
        if data is None:
            st.error("Load data first.")
            st.stop()

        periods = list(range(period_min, period_max + 1, period_step))
        confirmations = list(range(confirm_min, confirm_max + 1))
        total_runs = len(periods) * len(confirmations)

        sweep_results = []
        progress = st.progress(0, text=f"0/{total_runs}")
        completed = 0

        for period in periods:
            for confirm in confirmations:
                config = Config()
                config.strategy.ma_type = ma_type
                config.strategy.ma_period = period
                config.strategy.confirmation_candles = confirm
                config.strategy.direction = direction
                config.backtest.initial_cash = 10000.0
                config.backtest.commission = 0.001
                config.data.timeframe = timeframe
                config.data.symbol = asset_name
                config.data.path = asset_name or "optimize"

                try:
                    result = run_single(config, data=data)
                    stats = result["stats"]
                    sweep_results.append(
                        {
                            "ma_period": period,
                            "confirmation": confirm,
                            "Return [%]": stats.get("Return [%]", 0),
                            "Sharpe Ratio": stats.get("Sharpe Ratio") or 0,
                            "Max. Drawdown [%]": stats.get("Max. Drawdown [%]", 0),
                            "Win Rate [%]": stats.get("Win Rate [%]", 0),
                            "# Trades": stats.get("# Trades", 0),
                            "Profit Factor": stats.get("Profit Factor") or 0,
                            "SQN": stats.get("SQN") or 0,
                        }
                    )
                except Exception as e:
                    st.warning(f"Failed: period={period}, confirm={confirm}: {e}")

                completed += 1
                progress.progress(completed / total_runs, text=f"{completed}/{total_runs}")

        progress.empty()
        st.session_state["opt_results"] = sweep_results

# --- Main Area ---
st.title("Optimize")

if "opt_data" in st.session_state and "opt_results" not in st.session_state:
    data = st.session_state["opt_data"]
    st.info(f"{len(data)} candles loaded. Configure sweep parameters and run.")

if "opt_results" not in st.session_state:
    if "opt_data" not in st.session_state:
        st.markdown(
            """
            <div style="text-align: center; padding: 4rem 2rem; opacity: 0.6;">
                <p style="font-size: 1.2rem;">Configure data source and sweep parameters in the sidebar</p>
                <p>Load data, then click <strong>Run Optimization</strong></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()

# --- Display Results ---
sweep_results = st.session_state["opt_results"]
results_df = pd.DataFrame(sweep_results)

if results_df.empty:
    st.error("All runs failed.")
    st.stop()

# Best result highlight
best_idx = results_df[maximize].idxmax()
best = results_df.iloc[best_idx]

m1, m2, m3 = st.columns(3)
m1.metric("Best Period", int(best["ma_period"]))
m2.metric("Best Confirmation", int(best["confirmation"]))
m3.metric(maximize, f"{best[maximize]:.3f}")

st.divider()

# Heatmap
if len(results_df["ma_period"].unique()) > 1 and len(results_df["confirmation"].unique()) > 1:
    fig = create_optimization_heatmap(results_df, "ma_period", "confirmation", maximize)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Need variation in both period and confirmation for heatmap.")

# Full results table
with st.expander("All Results"):
    st.dataframe(
        results_df.sort_values(maximize, ascending=False),
        hide_index=True,
        use_container_width=True,
    )
