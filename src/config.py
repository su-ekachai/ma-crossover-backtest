"""Dataclass-based configuration with YAML parsing."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class StrategyConfig:
    """Strategy configuration parameters."""

    ma_type: str = "EMA"
    ma_period: int = 99
    confirmation_candles: int = 0
    direction: str = "both"

    VALID_MA_TYPES = ("EMA", "SMA")
    VALID_DIRECTIONS = ("long_only", "short_only", "both")

    def __post_init__(self) -> None:
        if self.ma_type not in self.VALID_MA_TYPES:
            raise ValueError(f"ma_type must be one of {self.VALID_MA_TYPES}, got {self.ma_type}")
        if self.direction not in self.VALID_DIRECTIONS:
            raise ValueError(
                f"direction must be one of {self.VALID_DIRECTIONS}, got {self.direction}"
            )
        if self.ma_period < 1:
            raise ValueError(f"ma_period must be >= 1, got {self.ma_period}")
        if self.confirmation_candles < 0:
            raise ValueError(f"confirmation_candles must be >= 0, got {self.confirmation_candles}")


@dataclass
class SizingConfig:
    """Position sizing configuration."""

    mode: str = "all_in"
    fixed_amount: float = 1000.0
    risk_percentage: float = 0.02

    VALID_MODES = ("all_in", "fixed", "percentage")

    def __post_init__(self) -> None:
        if self.mode not in self.VALID_MODES:
            raise ValueError(f"mode must be one of {self.VALID_MODES}, got {self.mode}")
        if self.fixed_amount <= 0:
            raise ValueError(f"fixed_amount must be > 0, got {self.fixed_amount}")
        if self.risk_percentage <= 0 or self.risk_percentage > 1:
            raise ValueError(f"risk_percentage must be between 0 and 1, got {self.risk_percentage}")


@dataclass
class BacktestConfig:
    """Backtesting engine configuration."""

    initial_cash: float = 10000.0
    commission: float = 0.001

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(f"initial_cash must be > 0, got {self.initial_cash}")
        if self.commission < 0 or self.commission > 1:
            raise ValueError(f"commission must be between 0 and 1, got {self.commission}")


@dataclass
class DataConfig:
    """Data source configuration."""

    path: str = ""
    timeframe: str = ""
    symbol: str = ""
    exchange: str = ""
    source_timeframe: str = ""

    VALID_TIMEFRAMES = ("1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1w")

    def __post_init__(self) -> None:
        if self.timeframe and self.timeframe not in self.VALID_TIMEFRAMES:
            raise ValueError(
                f"timeframe must be one of {self.VALID_TIMEFRAMES}, got {self.timeframe}"
            )


@dataclass
class QuestDBConfig:
    """QuestDB connection configuration (read-only via PG wire protocol)."""

    host: str = "localhost"
    port: int = 8812
    user: str = "admin"
    password: str = "quest"

    @classmethod
    def from_env(cls) -> "QuestDBConfig":
        """Load from environment variables, falling back to defaults."""
        return cls(
            host=os.environ.get("QUESTDB_HOST", "localhost"),
            port=int(os.environ.get("QUESTDB_PG_PORT", "8812")),
            user=os.environ.get("QUESTDB_USER", "admin"),
            password=os.environ.get("QUESTDB_PASSWORD", "quest"),
        )


@dataclass
class Config:
    """Top-level configuration for a backtest run."""

    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data: DataConfig = field(default_factory=DataConfig)
    questdb: QuestDBConfig = field(default_factory=QuestDBConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            A Config instance with loaded values.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        strategy_cfg = raw.get("strategy", {})
        sizing_cfg = raw.get("sizing", {})
        backtest_cfg = raw.get("backtest", {})
        data_cfg = raw.get("data", {})
        questdb_cfg = raw.get("questdb", {})

        return cls(
            strategy=StrategyConfig(
                ma_type=strategy_cfg.get("ma_type", "EMA"),
                ma_period=int(strategy_cfg.get("ma_period", 99)),
                confirmation_candles=int(strategy_cfg.get("confirmation_candles", 0)),
                direction=strategy_cfg.get("direction", "both"),
            ),
            sizing=SizingConfig(
                mode=sizing_cfg.get("mode", "all_in"),
                fixed_amount=float(sizing_cfg.get("fixed_amount", 1000.0)),
                risk_percentage=float(sizing_cfg.get("risk_percentage", 0.02)),
            ),
            backtest=BacktestConfig(
                initial_cash=float(backtest_cfg.get("initial_cash", 10000.0)),
                commission=float(backtest_cfg.get("commission", 0.001)),
            ),
            data=DataConfig(
                path=str(data_cfg.get("path", "")),
                timeframe=str(data_cfg.get("timeframe", "")),
                symbol=str(data_cfg.get("symbol", "")),
                exchange=str(data_cfg.get("exchange", "")),
            ),
            questdb=QuestDBConfig(
                host=questdb_cfg.get("host", os.environ.get("QUESTDB_HOST", "localhost")),
                port=int(questdb_cfg.get("port", os.environ.get("QUESTDB_PG_PORT", "8812"))),
                user=questdb_cfg.get("user", os.environ.get("QUESTDB_USER", "admin")),
                password=questdb_cfg.get("password", os.environ.get("QUESTDB_PASSWORD", "quest")),
            ),
        )

    def to_dict(self) -> dict:
        """Convert configuration to a dictionary for serialization."""
        return {
            "strategy": {
                "ma_type": self.strategy.ma_type,
                "ma_period": self.strategy.ma_period,
                "confirmation_candles": self.strategy.confirmation_candles,
                "direction": self.strategy.direction,
            },
            "sizing": {
                "mode": self.sizing.mode,
                "fixed_amount": self.sizing.fixed_amount,
                "risk_percentage": self.sizing.risk_percentage,
            },
            "backtest": {
                "initial_cash": self.backtest.initial_cash,
                "commission": self.backtest.commission,
            },
            "data": {
                "path": self.data.path,
                "timeframe": self.data.timeframe,
                "symbol": self.data.symbol,
                "exchange": self.data.exchange,
                "source_timeframe": self.data.source_timeframe,
            },
            "questdb": {
                "host": self.questdb.host,
                "port": self.questdb.port,
                "user": self.questdb.user,
                "password": self.questdb.password,
            },
        }
