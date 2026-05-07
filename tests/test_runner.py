"""Tests for backtest runner module."""

import os
from pathlib import Path

import pandas as pd

from src.config import Config, DataConfig, StrategyConfig
from src.runner import _make_serializable, run_comparison, run_optimization, run_single


class TestRunSingle:
    def test_produces_output_files(self, default_config: Config, monkeypatch):
        monkeypatch.chdir(Path(default_config.data.path).parent.parent)
        os.makedirs("results", exist_ok=True)

        result = run_single(default_config)

        assert "stats" in result
        assert "results_dir" in result
        assert "trades" in result

        results_dir = Path(result["results_dir"])
        assert (results_dir / "stats.json").exists()
        assert (results_dir / "trades.csv").exists()
        assert (results_dir / "config.json").exists()

    def test_stats_contain_expected_keys(self, default_config: Config, monkeypatch):
        monkeypatch.chdir(Path(default_config.data.path).parent.parent)
        os.makedirs("results", exist_ok=True)

        result = run_single(default_config)
        stats = result["stats"]

        expected_keys = ["Return [%]", "Sharpe Ratio", "# Trades"]
        for key in expected_keys:
            assert key in stats

    def test_with_preloaded_data(self, default_config: Config, sample_ohlcv_df, monkeypatch):
        monkeypatch.chdir(Path(default_config.data.path).parent.parent)
        os.makedirs("results", exist_ok=True)

        result = run_single(default_config, data=sample_ohlcv_df)
        assert result["stats"]["# Trades"] >= 0

    def test_with_timeframe_resampling(self, default_config: Config, monkeypatch):
        monkeypatch.chdir(Path(default_config.data.path).parent.parent)
        os.makedirs("results", exist_ok=True)

        default_config.data.timeframe = "4h"
        result = run_single(default_config)
        assert "stats" in result


class TestRunComparison:
    def test_returns_dataframe_with_expected_columns(self, default_config: Config, monkeypatch):
        monkeypatch.chdir(Path(default_config.data.path).parent.parent)
        os.makedirs("results", exist_ok=True)

        config2 = Config(
            strategy=StrategyConfig(ma_type="SMA", ma_period=10, confirmation_candles=0),
            sizing=default_config.sizing,
            backtest=default_config.backtest,
            data=DataConfig(path=default_config.data.path),
        )

        results_df = run_comparison([default_config, config2])
        assert isinstance(results_df, pd.DataFrame)
        assert len(results_df) == 2
        assert "Return [%]" in results_df.columns
        assert "Sharpe" in results_df.columns


class TestRunOptimization:
    def test_returns_optimized_params(self, default_config: Config, monkeypatch):
        monkeypatch.chdir(Path(default_config.data.path).parent.parent)
        os.makedirs("results", exist_ok=True)

        result = run_optimization(
            default_config,
            param_name="ma_period",
            param_range=range(3, 8),
            maximize="Return [%]",
        )

        assert "stats" in result
        assert "optimized_params" in result
        assert "results_dir" in result
        assert "ma_period" in result["optimized_params"]
        assert result["optimized_params"]["ma_period"] in range(3, 8)


class TestMakeSerializable:
    def test_nan_to_none(self):
        assert _make_serializable(float("nan")) is None

    def test_inf_to_none(self):
        assert _make_serializable(float("inf")) is None

    def test_normal_float_unchanged(self):
        assert _make_serializable(3.14) == 3.14

    def test_nested_dict(self):
        result = _make_serializable({"a": float("nan"), "b": 1.0})
        assert result == {"a": None, "b": 1.0}

    def test_list_handling(self):
        result = _make_serializable([1.0, float("nan"), 2.0])
        assert result == [1.0, None, 2.0]

    def test_tuple_handling(self):
        result = _make_serializable((1.0, float("inf")))
        assert result == [1.0, None]

    def test_pandas_series(self):
        s = pd.Series([1.0, 2.0], index=["a", "b"])
        result = _make_serializable(s)
        assert result == {"a": 1.0, "b": 2.0}

    def test_object_with_dunder_float(self):
        class FakeNum:
            def __float__(self):
                return 42.0

        assert _make_serializable(FakeNum()) == 42.0

    def test_object_with_dunder_float_nan(self):
        class FakeNaN:
            def __float__(self):
                return float("nan")

        assert _make_serializable(FakeNaN()) is None
