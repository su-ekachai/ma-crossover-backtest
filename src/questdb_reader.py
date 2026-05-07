"""QuestDB read-only data source via PostgreSQL wire protocol."""

from datetime import datetime

import pandas as pd
import psycopg
from loguru import logger

from src.config import QuestDBConfig

TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "1d": 1440,
    "1w": 10080,
    "1M": 43200,
}

QUESTDB_SAMPLE_INTERVALS: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
    "1M": "1M",
}


class QuestDBSource:
    """Read-only access to OHLCV data stored in QuestDB."""

    def __init__(self, config: QuestDBConfig) -> None:
        self._config = config
        self._conn: psycopg.Connection | None = None

    def _get_connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                dbname="qdb",
                autocommit=True,
                connect_timeout=30,
            )
        return self._conn

    def list_symbols(self) -> pd.DataFrame:
        """List all available symbol/exchange/timeframe combinations.

        Returns:
            DataFrame with columns: symbol, exchange, timeframe, rows, last_update
        """
        conn = self._get_connection()
        query = """
            SELECT symbol, exchange, timeframe, count() as rows, max(timestamp) as last_update
            FROM ohlcv
            GROUP BY symbol, exchange, timeframe
            ORDER BY symbol
        """
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc.name for desc in cur.description]
            data = cur.fetchall()

        df = pd.DataFrame(data, columns=columns)
        logger.debug(f"Found {len(df)} symbol/exchange/timeframe combinations in QuestDB")
        return df

    def load_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
        resample_to: str | None = None,
    ) -> pd.DataFrame:
        """Load OHLCV data from QuestDB, optionally resampled via SAMPLE BY.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT").
            exchange: Exchange name (e.g., "binance").
            timeframe: Source timeframe stored in QuestDB (e.g., "1m").
            start: Optional start datetime filter.
            end: Optional end datetime filter.
            resample_to: Target timeframe for SAMPLE BY aggregation (e.g., "1h").
                If None or equal to timeframe, returns raw data.

        Returns:
            DataFrame with DatetimeIndex named 'datetime' and columns:
            Open, High, Low, Close, Volume (capitalized to match Backtesting.py format).

        Raises:
            ValueError: If no data found, invalid resample direction, or unknown timeframe.
        """
        use_sample_by = bool(resample_to and resample_to != timeframe)

        if use_sample_by:
            assert resample_to is not None
            self._validate_resample(timeframe, resample_to)

        conn = self._get_connection()
        conditions = [
            f"symbol = '{symbol}'",
            f"exchange = '{exchange}'",
            f"timeframe = '{timeframe}'",
        ]

        if start:
            conditions.append(f"timestamp >= '{start.isoformat()}'")
        if end:
            conditions.append(f"timestamp <= '{end.isoformat()}'")

        where_clause = " AND ".join(conditions)

        if use_sample_by:
            assert resample_to is not None
            interval = QUESTDB_SAMPLE_INTERVALS[resample_to]
            query = f"""
                SELECT
                    timestamp,
                    first(open) as open,
                    max(high) as high,
                    min(low) as low,
                    last(close) as close,
                    sum(volume) as volume
                FROM ohlcv
                WHERE {where_clause}
                SAMPLE BY {interval} ALIGN TO CALENDAR
            """
            logger.info(
                f"Loading {symbol} ({exchange}) resampled from {timeframe} to {resample_to}"
            )
        else:
            query = f"""
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE {where_clause}
                ORDER BY timestamp
            """

        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc.name for desc in cur.description]
            data = cur.fetchall()

        if not data:
            raise ValueError(f"No data found for {symbol} on {exchange} ({timeframe})")

        df = pd.DataFrame(data, columns=columns)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")
        df.index.name = "datetime"
        df.columns = ["Open", "High", "Low", "Close", "Volume"]

        target = resample_to if use_sample_by else timeframe
        logger.info(f"Loaded {len(df)} candles for {symbol} ({exchange}/{target}) from QuestDB")
        return df

    def _validate_resample(self, source: str, target: str) -> None:
        """Validate that target timeframe is larger than source."""
        supported = list(TIMEFRAME_MINUTES.keys())

        if source not in TIMEFRAME_MINUTES:
            logger.warning(
                f"Unknown source timeframe '{source}', skipping validation. Supported: {supported}"
            )
            return

        if target not in TIMEFRAME_MINUTES:
            raise ValueError(f"Unknown target timeframe '{target}'. Supported: {supported}")

        if TIMEFRAME_MINUTES[target] <= TIMEFRAME_MINUTES[source]:
            raise ValueError(
                f"Cannot resample {source} -> {target}: target timeframe must be larger than source"
            )

    def close(self) -> None:
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
