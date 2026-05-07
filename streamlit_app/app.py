"""EMA-99 Backtester Dashboard — Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="EMA-99 Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Tighter metric cards */
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 600;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.7;
    }
    /* Sidebar section headers */
    .sidebar-header {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #94A3B8;
        margin-top: 1rem;
        margin-bottom: 0.25rem;
        font-weight: 600;
    }
    /* Plotly chart container */
    [data-testid="stPlotlyChart"] {
        border: 1px solid rgba(59, 130, 246, 0.15);
        border-radius: 8px;
    }
    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
    }
    /* Remove default padding from main block */
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/backtest.py", title="Backtest", icon="📊"),
    st.Page("pages/history.py", title="History", icon="📋"),
    st.Page("pages/optimize.py", title="Optimize", icon="🔬"),
]

nav = st.navigation(pages)
nav.run()
