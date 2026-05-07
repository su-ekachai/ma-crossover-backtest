"""Tests for Plotly chart generation."""

import pandas as pd
import plotly.graph_objects as go

from src.charts import create_backtest_chart, create_optimization_heatmap


class TestCreateBacktestChart:
    def test_returns_figure_with_trades(
        self, sample_ohlcv_df: pd.DataFrame, sample_trades_df: pd.DataFrame
    ):
        ma_series = sample_ohlcv_df["Close"].rolling(5).mean()
        fig = create_backtest_chart(sample_ohlcv_df, ma_series, sample_trades_df, "EMA5")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 5  # candlestick + MA + buy + sell + volume

    def test_returns_figure_with_empty_trades(self, sample_ohlcv_df: pd.DataFrame):
        ma_series = sample_ohlcv_df["Close"].rolling(5).mean()
        empty_trades = pd.DataFrame()
        fig = create_backtest_chart(sample_ohlcv_df, ma_series, empty_trades, "EMA5")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # candlestick + MA + volume

    def test_trades_without_size_column(self, sample_ohlcv_df: pd.DataFrame):
        ma_series = sample_ohlcv_df["Close"].rolling(5).mean()
        trades = pd.DataFrame(
            {
                "EntryTime": ["2024-01-01 10:00:00"],
                "ExitTime": ["2024-01-01 18:00:00"],
                "EntryPrice": [100.0],
                "ExitPrice": [103.0],
            }
        )
        fig = create_backtest_chart(sample_ohlcv_df, ma_series, trades, "SMA10")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 5


class TestCreateOptimizationHeatmap:
    def test_returns_valid_figure(self):
        results_df = pd.DataFrame(
            {
                "ma_period": [10, 10, 20, 20],
                "confirmation": [0, 1, 0, 1],
                "Sharpe Ratio": [1.0, 1.5, 0.8, 2.0],
            }
        )
        fig = create_optimization_heatmap(results_df, "ma_period", "confirmation", "Sharpe Ratio")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # single heatmap trace

    def test_heatmap_axis_labels(self):
        results_df = pd.DataFrame(
            {
                "x_param": [1, 1, 2, 2],
                "y_param": [3, 4, 3, 4],
                "metric": [0.5, 0.6, 0.7, 0.8],
            }
        )
        fig = create_optimization_heatmap(results_df, "x_param", "y_param", "metric")
        assert fig.layout.xaxis.title.text == "x_param"
        assert fig.layout.yaxis.title.text == "y_param"
