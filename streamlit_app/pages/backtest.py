"""Backtest page — configure in sidebar, view results in main area."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.charts import create_backtest_chart
from src.config import Config, QuestDBConfig
from src.data_loader import resample
from src.indicators import calculate_ema, calculate_sma
from src.questdb_reader import TIMEFRAME_MINUTES, QuestDBSource
from src.runner import run_single

# --- Sidebar: Data Source ---
with st.sidebar:
    st.markdown('<p class="sidebar-header">Data Source</p>', unsafe_allow_html=True)
    source = st.radio(
        "Source", ["QuestDB", "CSV Upload"], horizontal=True, label_visibility="collapsed"
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

        symbol = st.selectbox("Symbol", symbols_df["symbol"].unique())
        exchanges = symbols_df[symbols_df["symbol"] == symbol]["exchange"].unique()
        exchange = st.selectbox("Exchange", exchanges)

        source_timeframes = symbols_df[
            (symbols_df["symbol"] == symbol) & (symbols_df["exchange"] == exchange)
        ]["timeframe"].unique()
        source_timeframe = st.selectbox("Source Timeframe", source_timeframes)

        source_minutes = TIMEFRAME_MINUTES.get(source_timeframe, 0)
        available_targets = [tf for tf, mins in TIMEFRAME_MINUTES.items() if mins >= source_minutes]
        target_timeframe = st.selectbox("Backtest Timeframe", available_targets)

        timeframe = target_timeframe
        asset_name = symbol.replace("/", "")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Start", value=None)
        with c2:
            end_date = st.date_input("End", value=None)

        resample_to = target_timeframe if target_timeframe != source_timeframe else None

        if st.button("Load Data", use_container_width=True):
            with st.spinner("Loading..."):
                qdb = QuestDBSource(QuestDBConfig.from_env())
                start = pd.Timestamp(start_date).to_pydatetime() if start_date else None
                end = pd.Timestamp(end_date).to_pydatetime() if end_date else None
                df = qdb.load_ohlcv(
                    symbol,
                    exchange,
                    source_timeframe,
                    start=start,
                    end=end,
                    resample_to=resample_to,
                )
                qdb.close()
                st.session_state["loaded_data"] = df
                st.session_state["asset_name"] = asset_name
                st.session_state["timeframe"] = timeframe
                st.session_state["exchange"] = exchange
                st.session_state["source_timeframe"] = source_timeframe

    else:
        uploaded = st.file_uploader("OHLCV CSV", type=["csv"])
        timeframe = st.selectbox(
            "Resample To",
            ["", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1w"],
        )
        if uploaded:
            df = pd.read_csv(uploaded, parse_dates=["datetime"], index_col="datetime")
            df = df.sort_index()
            asset_name = Path(uploaded.name).stem
            if timeframe:
                df = resample(df, timeframe)
            st.session_state["loaded_data"] = df
            st.session_state["asset_name"] = asset_name
            st.session_state["timeframe"] = timeframe

    if "loaded_data" in st.session_state:
        df = st.session_state["loaded_data"]
        asset_name = st.session_state.get("asset_name", "")
        timeframe = st.session_state.get("timeframe", "")

    # --- Sidebar: Strategy ---
    st.markdown('<p class="sidebar-header">Strategy</p>', unsafe_allow_html=True)
    ma_type = st.selectbox("MA Type", ["EMA", "SMA"])
    ma_period = st.number_input("Period", min_value=1, value=99)
    confirmation = st.number_input("Confirmation Candles", min_value=0, value=0)
    direction = st.selectbox("Direction", ["both", "long_only", "short_only"])

    # --- Sidebar: Backtest Settings ---
    st.markdown('<p class="sidebar-header">Backtest Settings</p>', unsafe_allow_html=True)
    sizing_mode = st.selectbox("Sizing", ["all_in", "fixed", "percentage"])
    initial_cash = st.number_input("Cash", min_value=100.0, value=10000.0, step=1000.0)
    commission = st.number_input(
        "Commission", min_value=0.0, max_value=1.0, value=0.001, step=0.0001, format="%.4f"
    )

    st.divider()

    run_disabled = df is None and "loaded_data" not in st.session_state
    if st.button("Run Backtest", type="primary", use_container_width=True, disabled=run_disabled):
        data = st.session_state.get("loaded_data")
        if data is None:
            st.error("Load data first.")
            st.stop()

        config = Config()
        config.strategy.ma_type = ma_type
        config.strategy.ma_period = ma_period
        config.strategy.confirmation_candles = confirmation
        config.strategy.direction = direction
        config.sizing.mode = sizing_mode
        config.backtest.initial_cash = initial_cash
        config.backtest.commission = commission
        config.data.timeframe = timeframe
        config.data.symbol = asset_name
        config.data.exchange = st.session_state.get("exchange", "")
        config.data.source_timeframe = st.session_state.get("source_timeframe", timeframe)
        config.data.path = asset_name or "uploaded"

        with st.spinner("Running backtest..."):
            result = run_single(config, data=data)

        st.session_state["last_result"] = result
        st.session_state["last_config"] = config

# --- Main Area ---
st.title("Backtest")

if "loaded_data" in st.session_state and "last_result" not in st.session_state:
    data = st.session_state["loaded_data"]
    st.info(f"{len(data)} candles loaded ({data.index[0].date()} to {data.index[-1].date()})")

if "last_result" not in st.session_state:
    if "loaded_data" not in st.session_state:
        st.markdown(
            """
            <div style="text-align: center; padding: 4rem 2rem; opacity: 0.6;">
                <p style="font-size: 1.2rem;">Configure data source and strategy in the sidebar</p>
                <p>Load data, then click <strong>Run Backtest</strong></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.stop()

# --- Display Results ---
result = st.session_state["last_result"]
config = st.session_state["last_config"]
stats = result["stats"]
trades = result["trades"]

st.caption(f"Results saved to `{result['results_dir']}`")

# Metrics row
m1, m2, m3, m4, m5, m6 = st.columns(6)
ret = stats.get("Return [%]", 0)
m1.metric("Return", f"{ret:.2f}%", delta=f"{ret:+.2f}%")
m2.metric("Sharpe", f"{stats.get('Sharpe Ratio', 0) or 0:.2f}")
m3.metric("Max DD", f"{stats.get('Max. Drawdown [%]', 0):.2f}%")
m4.metric("Win Rate", f"{stats.get('Win Rate [%]', 0):.1f}%")
m5.metric("Trades", f"{int(stats.get('# Trades', 0))}")
m6.metric("Profit Factor", f"{stats.get('Profit Factor', 0) or 0:.2f}")

st.divider()

# Chart
data = st.session_state.get("loaded_data")
if data is not None:
    ma_func = calculate_ema if config.strategy.ma_type == "EMA" else calculate_sma
    ma_series = ma_func(data["Close"], config.strategy.ma_period)
    ma_label = f"{config.strategy.ma_type}{config.strategy.ma_period}"
    fig = create_backtest_chart(data, ma_series, trades, ma_label)
    st.plotly_chart(fig, use_container_width=True)

# Bottom section: full stats and trade log
col_stats, col_trades = st.columns([1, 2])

with col_stats:
    st.markdown("**All Metrics**")
    stats_df = pd.DataFrame([{"Metric": k, "Value": v} for k, v in stats.items()])
    st.dataframe(stats_df, hide_index=True, use_container_width=True, height=300)

with col_trades:
    st.markdown(f"**Trade Log** ({len(trades)} trades)")
    if not trades.empty:
        st.dataframe(trades, hide_index=True, use_container_width=True, height=300)
    else:
        st.info("No trades executed.")
