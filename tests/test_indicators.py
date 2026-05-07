"""Tests for EMA/SMA indicator calculations."""

import pandas as pd
import pytest

from src.indicators import calculate_ema, calculate_sma


@pytest.mark.parametrize("calc_func", [calculate_ema, calculate_sma])
class TestMACalculations:
    def test_valid_calculation_returns_series(self, calc_func, sample_ohlcv_df: pd.DataFrame):
        result = calc_func(sample_ohlcv_df["Close"], period=10)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_df)

    def test_output_has_nan_for_warmup_period(self, calc_func, sample_ohlcv_df: pd.DataFrame):
        result = calc_func(sample_ohlcv_df["Close"], period=10)
        assert result.iloc[:9].isna().all()
        assert result.iloc[9:].notna().all()

    @pytest.mark.parametrize("invalid_period", [0, -1, -100])
    def test_invalid_period_raises_value_error(self, calc_func, invalid_period):
        prices = pd.Series([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="period must be >= 1"):
            calc_func(prices, period=invalid_period)

    def test_period_longer_than_series_returns_none(self, calc_func):
        prices = pd.Series([1.0, 2.0, 3.0])
        result = calc_func(prices, period=50)
        assert result is None


class TestEMASpecific:
    def test_ema_weights_recent_prices_more(self, sample_ohlcv_df: pd.DataFrame):
        prices = sample_ohlcv_df["Close"]
        ema = calculate_ema(prices, period=10)
        sma = calculate_sma(prices, period=10)
        assert not ema.equals(sma)
