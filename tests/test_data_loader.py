"""Tests for data loader module."""

from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_csv, resample


class TestLoadCsv:
    def test_valid_csv(self, sample_csv_path: Path):
        df = load_csv(sample_csv_path)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert df.index.name == "datetime"
        assert len(df) == 100

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_csv("/nonexistent/file.csv")

    def test_missing_columns(self, tmp_path: Path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("datetime,Open,High\n2024-01-01,100,101\n")
        with pytest.raises(ValueError, match="Missing required columns"):
            load_csv(csv_path)

    def test_nan_values(self, tmp_path: Path):
        csv_path = tmp_path / "nan.csv"
        csv_path.write_text(
            "datetime,Open,High,Low,Close,Volume\n2024-01-01 00:00:00,100,101,99,,1000\n"
        )
        with pytest.raises(ValueError, match="NaN"):
            load_csv(csv_path)

    def test_unsorted_data_gets_sorted(self, tmp_path: Path):
        csv_path = tmp_path / "unsorted.csv"
        csv_path.write_text(
            "datetime,Open,High,Low,Close,Volume\n"
            "2024-01-02 00:00:00,102,103,101,102,1000\n"
            "2024-01-01 00:00:00,100,101,99,100,1000\n"
        )
        df = load_csv(csv_path)
        assert df.index[0] < df.index[1]


class TestResample:
    def test_valid_resample_to_4h(self, sample_ohlcv_df: pd.DataFrame):
        resampled = resample(sample_ohlcv_df, "4h")
        assert len(resampled) < len(sample_ohlcv_df)
        assert list(resampled.columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_invalid_timeframe(self, sample_ohlcv_df: pd.DataFrame):
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            resample(sample_ohlcv_df, "3h")

    def test_resample_aggregation(self, sample_ohlcv_df: pd.DataFrame):
        resampled = resample(sample_ohlcv_df, "4h")
        assert resampled["High"].max() <= sample_ohlcv_df["High"].max()
        assert resampled["Low"].min() >= sample_ohlcv_df["Low"].min()
