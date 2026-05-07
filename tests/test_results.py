"""Tests for results directory scanner."""

from pathlib import Path

import pandas as pd
import pytest

from src.results import (
    list_results,
    load_result_config,
    load_result_stats,
    load_trades,
    parse_result_folder,
)


class TestParseResultFolder:
    @pytest.mark.parametrize(
        "folder,expected",
        [
            (
                "20260507_BTCUSDT_MAEMA99_1h",
                {
                    "date": "20260507",
                    "asset": "BTCUSDT",
                    "ma_type": "EMA",
                    "ma_period": 99,
                    "timeframe": "1h",
                },
            ),
            (
                "20260101_ETHUSDT_MASMA200_4h",
                {
                    "date": "20260101",
                    "asset": "ETHUSDT",
                    "ma_type": "SMA",
                    "ma_period": 200,
                    "timeframe": "4h",
                },
            ),
            (
                "20260507_BTCUSDT_MAEMA5",
                {
                    "date": "20260507",
                    "asset": "BTCUSDT",
                    "ma_type": "EMA",
                    "ma_period": 5,
                    "timeframe": "",
                },
            ),
        ],
    )
    def test_valid_formats(self, folder: str, expected: dict):
        result = parse_result_folder(folder)
        assert result is not None
        assert result["id"] == folder
        for key, val in expected.items():
            assert result[key] == val

    @pytest.mark.parametrize(
        "folder",
        ["", "invalid", "../etc/passwd", "abc_xyz_MAabc_1h", "no_match_here"],
    )
    def test_invalid_formats_return_none(self, folder: str):
        assert parse_result_folder(folder) is None


class TestLoadResultStats:
    def test_existing_stats(self, results_dir_with_data: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", results_dir_with_data)
        stats = load_result_stats("20260507_BTCUSDT_MAEMA99_1h")
        assert stats["Return [%]"] == 12.5
        assert stats["# Trades"] == 10

    def test_missing_stats_returns_empty_dict(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", tmp_path)
        assert load_result_stats("nonexistent") == {}


class TestLoadTrades:
    def test_existing_trades(self, results_dir_with_data: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", results_dir_with_data)
        trades = load_trades("20260507_BTCUSDT_MAEMA99_1h")
        assert isinstance(trades, pd.DataFrame)
        assert len(trades) == 1
        assert "EntryPrice" in trades.columns

    def test_missing_trades_returns_empty_dataframe(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", tmp_path)
        trades = load_trades("nonexistent")
        assert isinstance(trades, pd.DataFrame)
        assert trades.empty


class TestLoadResultConfig:
    def test_existing_config(self, results_dir_with_data: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", results_dir_with_data)
        config = load_result_config("20260507_BTCUSDT_MAEMA99_1h")
        assert config["symbol"] == "BTC/USDT"
        assert config["ma_period"] == 99

    def test_missing_config_returns_empty_dict(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", tmp_path)
        assert load_result_config("nonexistent") == {}


class TestListResults:
    def test_returns_results_with_stats(self, results_dir_with_data: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", results_dir_with_data)
        results = list_results()
        assert len(results) == 1
        assert results[0]["asset"] == "BTCUSDT"
        assert results[0]["return_pct"] == 12.5

    def test_empty_directory(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", tmp_path)
        assert list_results() == []

    def test_nonexistent_directory(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", tmp_path / "nope")
        assert list_results() == []

    def test_skips_invalid_folders(self, results_dir_with_data: Path, monkeypatch):
        monkeypatch.setattr("src.results.RESULTS_DIR", results_dir_with_data)
        (results_dir_with_data / "not_a_valid_folder").mkdir()
        (results_dir_with_data / "random_file.txt").write_text("hi")
        results = list_results()
        assert len(results) == 1
