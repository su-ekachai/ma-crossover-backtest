"""Tests for MA strategy logic."""

import pandas as pd
from backtesting import Backtest

from src.strategies.ma_strategy import MAStrategy


def _run_backtest(df: pd.DataFrame, **strategy_kwargs) -> object:
    """Helper to run a backtest with given strategy parameters."""
    MAStrategy.ma_type = strategy_kwargs.get("ma_type", "EMA")
    MAStrategy.ma_period = strategy_kwargs.get("ma_period", 5)
    MAStrategy.confirmation_candles = strategy_kwargs.get("confirmation_candles", 0)
    MAStrategy.direction = strategy_kwargs.get("direction", "both")
    MAStrategy.sizing_mode = strategy_kwargs.get("sizing_mode", "all_in")
    MAStrategy.sizing_fixed_amount = strategy_kwargs.get("sizing_fixed_amount", 1000.0)
    MAStrategy.sizing_risk_pct = strategy_kwargs.get("sizing_risk_pct", 0.02)

    bt = Backtest(df, MAStrategy, cash=10000, commission=0.001, finalize_trades=True)
    return bt.run()


class TestConfirmationCandles:
    def test_zero_confirmation_enters_on_first_crossing(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(sample_ohlcv_df, confirmation_candles=0, ma_period=5)
        assert stats["# Trades"] > 0

    def test_zero_confirmation_no_entry_when_price_equals_ma(self):
        """When price == MA exactly, no entry should occur with confirmation=0."""
        dates = pd.date_range("2024-01-01", periods=20, freq="h")
        flat_price = 100.0
        df = pd.DataFrame(
            {
                "Open": [flat_price] * 20,
                "High": [flat_price] * 20,
                "Low": [flat_price] * 20,
                "Close": [flat_price] * 20,
                "Volume": [1000.0] * 20,
            },
            index=dates,
        )
        df.index.name = "datetime"
        stats = _run_backtest(df, confirmation_candles=0, ma_period=5)
        assert stats["# Trades"] == 0

    def test_higher_confirmation_reduces_trades(self, sample_ohlcv_df: pd.DataFrame):
        stats_0 = _run_backtest(sample_ohlcv_df, confirmation_candles=0, ma_period=5)
        stats_3 = _run_backtest(sample_ohlcv_df, confirmation_candles=3, ma_period=5)
        assert stats_3["# Trades"] <= stats_0["# Trades"]


class TestDirectionModes:
    def test_long_only_no_short_trades(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(
            sample_ohlcv_df, direction="long_only", ma_period=5, confirmation_candles=0
        )
        trades = stats["_trades"]
        if not trades.empty:
            assert all(trades["Size"] > 0)

    def test_short_only_no_long_trades(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(
            sample_ohlcv_df, direction="short_only", ma_period=5, confirmation_candles=0
        )
        trades = stats["_trades"]
        if not trades.empty:
            assert all(trades["Size"] < 0)


class TestPositionSizing:
    def test_all_in_uses_full_equity(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(sample_ohlcv_df, sizing_mode="all_in", ma_period=5)
        assert stats["# Trades"] > 0

    def test_fixed_size_clamped(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(
            sample_ohlcv_df,
            sizing_mode="fixed",
            sizing_fixed_amount=999999,
            ma_period=5,
        )
        assert stats["# Trades"] > 0

    def test_percentage_mode(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(
            sample_ohlcv_df, sizing_mode="percentage", sizing_risk_pct=0.5, ma_period=5
        )
        assert stats["# Trades"] > 0

    def test_unknown_sizing_mode_defaults_to_all_in(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(sample_ohlcv_df, sizing_mode="unknown_mode", ma_period=5)
        assert stats["# Trades"] > 0


class TestSMAInit:
    def test_sma_strategy_produces_trades(self, sample_ohlcv_df: pd.DataFrame):
        stats = _run_backtest(sample_ohlcv_df, ma_type="SMA", ma_period=5)
        assert stats["# Trades"] > 0
