"""Plotly chart generation for backtest visualization."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_backtest_chart(
    df: pd.DataFrame,
    ma_series: pd.Series,
    trades: pd.DataFrame,
    ma_label: str = "EMA99",
) -> go.Figure:
    """Create an interactive candlestick chart with MA overlay and trade markers.

    Args:
        df: OHLCV DataFrame with DatetimeIndex and columns Open, High, Low, Close, Volume.
        ma_series: MA values with same index as df.
        trades: Trades DataFrame with EntryTime, ExitTime, EntryPrice, ExitPrice columns.
        ma_label: Label for the MA line in the legend.

    Returns:
        A Plotly Figure object.
    """
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.8, 0.2],
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=ma_series.index,
            y=ma_series.values,
            mode="lines",
            name=ma_label,
            line={"color": "#ff9800", "width": 1.5},
        ),
        row=1,
        col=1,
    )

    if not trades.empty and "EntryTime" in trades.columns:
        entries = trades[trades["Size"] > 0] if "Size" in trades.columns else trades
        exits = trades.copy()

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(entries["EntryTime"]),
                y=entries["EntryPrice"],
                mode="markers",
                name="Buy",
                marker={"symbol": "triangle-up", "color": "#26a69a", "size": 10},
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(exits["ExitTime"]),
                y=exits["ExitPrice"],
                mode="markers",
                name="Sell",
                marker={"symbol": "triangle-down", "color": "#ef5350", "size": 10},
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker_color="rgba(100, 100, 100, 0.3)",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=600,
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        template="plotly_dark",
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def create_optimization_heatmap(
    results_df: pd.DataFrame,
    x_param: str,
    y_param: str,
    metric: str,
) -> go.Figure:
    """Create a heatmap for parameter optimization results.

    Args:
        results_df: DataFrame with parameter columns and a metric column.
        x_param: Column name for x-axis parameter.
        y_param: Column name for y-axis parameter.
        metric: Column name for the color metric.

    Returns:
        A Plotly Figure object.
    """
    pivot = results_df.pivot_table(index=y_param, columns=x_param, values=metric)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(x) for x in pivot.columns],
            y=[str(y) for y in pivot.index],
            colorscale="RdYlGn",
            colorbar={"title": metric},
        )
    )

    fig.update_layout(
        xaxis_title=x_param,
        yaxis_title=y_param,
        height=500,
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        template="plotly_dark",
    )

    return fig
