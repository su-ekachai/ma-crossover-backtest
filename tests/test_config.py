"""Tests for configuration module."""

import tempfile

import pytest

from src.config import (
    BacktestConfig,
    Config,
    DataConfig,
    QuestDBConfig,
    SizingConfig,
    StrategyConfig,
)


class TestStrategyConfig:
    def test_valid_defaults(self):
        cfg = StrategyConfig()
        assert cfg.ma_type == "EMA"
        assert cfg.ma_period == 99
        assert cfg.confirmation_candles == 0
        assert cfg.direction == "both"

    @pytest.mark.parametrize(
        "field,value,match",
        [
            ("ma_type", "WMA", "ma_type"),
            ("direction", "up_only", "direction"),
            ("ma_period", 0, "ma_period"),
            ("ma_period", -5, "ma_period"),
            ("confirmation_candles", -1, "confirmation_candles"),
        ],
    )
    def test_invalid_values(self, field, value, match):
        with pytest.raises(ValueError, match=match):
            StrategyConfig(**{field: value})


class TestSizingConfig:
    def test_valid_defaults(self):
        cfg = SizingConfig()
        assert cfg.mode == "all_in"

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="mode"):
            SizingConfig(mode="yolo")

    def test_invalid_fixed_amount(self):
        with pytest.raises(ValueError, match="fixed_amount"):
            SizingConfig(fixed_amount=-100)

    def test_invalid_risk_percentage(self):
        with pytest.raises(ValueError, match="risk_percentage"):
            SizingConfig(risk_percentage=1.5)


class TestBacktestConfig:
    def test_invalid_cash(self):
        with pytest.raises(ValueError, match="initial_cash"):
            BacktestConfig(initial_cash=0)

    def test_invalid_commission(self):
        with pytest.raises(ValueError, match="commission"):
            BacktestConfig(commission=-0.1)


class TestDataConfig:
    def test_valid_timeframe(self):
        cfg = DataConfig(timeframe="4h")
        assert cfg.timeframe == "4h"

    def test_invalid_timeframe(self):
        with pytest.raises(ValueError, match="timeframe"):
            DataConfig(timeframe="3h")

    def test_empty_timeframe_allowed(self):
        cfg = DataConfig(timeframe="")
        assert cfg.timeframe == ""


class TestConfigYaml:
    def test_from_yaml_roundtrip(self):
        yaml_content = """
strategy:
  ma_type: SMA
  ma_period: 50
  confirmation_candles: 2
  direction: long_only
sizing:
  mode: fixed
  fixed_amount: 500
  risk_percentage: 0.05
backtest:
  initial_cash: 5000
  commission: 0.002
data:
  path: data/test.csv
  timeframe: 4h
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            cfg = Config.from_yaml(f.name)

        assert cfg.strategy.ma_type == "SMA"
        assert cfg.strategy.ma_period == 50
        assert cfg.strategy.confirmation_candles == 2
        assert cfg.strategy.direction == "long_only"
        assert cfg.sizing.mode == "fixed"
        assert cfg.sizing.fixed_amount == 500.0
        assert cfg.backtest.initial_cash == 5000.0
        assert cfg.data.timeframe == "4h"

    def test_from_yaml_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Config.from_yaml("/nonexistent/path.yaml")

    def test_to_dict(self):
        cfg = Config()
        d = cfg.to_dict()
        assert "strategy" in d
        assert "sizing" in d
        assert "backtest" in d
        assert "data" in d
        assert d["strategy"]["ma_type"] == "EMA"


class TestQuestDBConfig:
    def test_from_env_uses_environment_variables(self, monkeypatch):
        monkeypatch.setenv("QUESTDB_HOST", "db.example.com")
        monkeypatch.setenv("QUESTDB_PG_PORT", "9999")
        monkeypatch.setenv("QUESTDB_USER", "testuser")
        monkeypatch.setenv("QUESTDB_PASSWORD", "secret")

        cfg = QuestDBConfig.from_env()
        assert cfg.host == "db.example.com"
        assert cfg.port == 9999
        assert cfg.user == "testuser"
        assert cfg.password == "secret"

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("QUESTDB_HOST", raising=False)
        monkeypatch.delenv("QUESTDB_PG_PORT", raising=False)
        monkeypatch.delenv("QUESTDB_USER", raising=False)
        monkeypatch.delenv("QUESTDB_PASSWORD", raising=False)

        cfg = QuestDBConfig.from_env()
        assert cfg.host == "localhost"
        assert cfg.port == 8812
        assert cfg.user == "admin"
        assert cfg.password == "quest"
