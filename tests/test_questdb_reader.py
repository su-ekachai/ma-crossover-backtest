"""Tests for QuestDB reader with mocked psycopg connection."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import QuestDBConfig
from src.questdb_reader import QuestDBSource


@pytest.fixture
def qdb_config() -> QuestDBConfig:
    return QuestDBConfig(host="localhost", port=8812, user="admin", password="quest")


@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    conn = MagicMock()
    conn.closed = False
    conn.cursor.return_value = mock_cursor
    return conn


class TestGetConnection:
    @patch("src.questdb_reader.psycopg.connect")
    def test_creates_connection(self, mock_connect, qdb_config):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_connect.return_value = mock_conn

        qdb = QuestDBSource(qdb_config)
        conn = qdb._get_connection()

        assert conn == mock_conn
        mock_connect.assert_called_once()

    @patch("src.questdb_reader.psycopg.connect")
    def test_reconnects_when_closed(self, mock_connect, qdb_config):
        mock_conn = MagicMock()
        mock_conn.closed = True
        mock_connect.return_value = mock_conn

        qdb = QuestDBSource(qdb_config)
        qdb._conn = mock_conn
        qdb._get_connection()

        mock_connect.assert_called_once()


class TestListSymbols:
    @patch("src.questdb_reader.psycopg.connect")
    def test_returns_dataframe(self, mock_connect, qdb_config, mock_cursor):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.description = [
            MagicMock(name="symbol"),
            MagicMock(name="exchange"),
            MagicMock(name="timeframe"),
            MagicMock(name="rows"),
            MagicMock(name="last_update"),
        ]
        for i, desc in enumerate(mock_cursor.description):
            desc.name = ["symbol", "exchange", "timeframe", "rows", "last_update"][i]

        mock_cursor.fetchall.return_value = [
            ("BTC/USDT", "binance", "1m", 1000, "2024-01-01"),
        ]

        qdb = QuestDBSource(qdb_config)
        result = qdb.list_symbols()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert "symbol" in result.columns


class TestLoadOhlcv:
    @patch("src.questdb_reader.psycopg.connect")
    def test_raw_query_returns_dataframe(self, mock_connect, qdb_config, mock_cursor):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.description = [
            MagicMock(name="timestamp"),
            MagicMock(name="open"),
            MagicMock(name="high"),
            MagicMock(name="low"),
            MagicMock(name="close"),
            MagicMock(name="volume"),
        ]
        for i, desc in enumerate(mock_cursor.description):
            desc.name = ["timestamp", "open", "high", "low", "close", "volume"][i]

        mock_cursor.fetchall.return_value = [
            ("2024-01-01 00:00:00", 100.0, 101.0, 99.0, 100.5, 1000.0),
            ("2024-01-01 01:00:00", 100.5, 102.0, 100.0, 101.0, 1200.0),
        ]

        qdb = QuestDBSource(qdb_config)
        df = qdb.load_ohlcv("BTC/USDT", "binance", "1h")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert df.index.name == "datetime"

    @patch("src.questdb_reader.psycopg.connect")
    def test_sample_by_query_path(self, mock_connect, qdb_config, mock_cursor):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.description = [
            MagicMock(name="timestamp"),
            MagicMock(name="open"),
            MagicMock(name="high"),
            MagicMock(name="low"),
            MagicMock(name="close"),
            MagicMock(name="volume"),
        ]
        for i, desc in enumerate(mock_cursor.description):
            desc.name = ["timestamp", "open", "high", "low", "close", "volume"][i]

        mock_cursor.fetchall.return_value = [
            ("2024-01-01 00:00:00", 100.0, 105.0, 98.0, 103.0, 5000.0),
        ]

        qdb = QuestDBSource(qdb_config)
        df = qdb.load_ohlcv("BTC/USDT", "binance", "1m", resample_to="1h")

        assert len(df) == 1
        executed_sql = mock_cursor.execute.call_args[0][0]
        assert "SAMPLE BY" in executed_sql

    @patch("src.questdb_reader.psycopg.connect")
    def test_empty_result_raises_value_error(self, mock_connect, qdb_config, mock_cursor):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.description = [MagicMock(name="timestamp")]
        mock_cursor.fetchall.return_value = []

        qdb = QuestDBSource(qdb_config)
        with pytest.raises(ValueError, match="No data found"):
            qdb.load_ohlcv("BTC/USDT", "binance", "1h")

    @patch("src.questdb_reader.psycopg.connect")
    def test_date_filters_included_in_query(self, mock_connect, qdb_config, mock_cursor):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.description = [
            MagicMock(name="timestamp"),
            MagicMock(name="open"),
            MagicMock(name="high"),
            MagicMock(name="low"),
            MagicMock(name="close"),
            MagicMock(name="volume"),
        ]
        for i, desc in enumerate(mock_cursor.description):
            desc.name = ["timestamp", "open", "high", "low", "close", "volume"][i]

        mock_cursor.fetchall.return_value = [
            ("2024-01-01 00:00:00", 100.0, 101.0, 99.0, 100.5, 1000.0),
        ]

        qdb = QuestDBSource(qdb_config)
        qdb.load_ohlcv(
            "BTC/USDT",
            "binance",
            "1h",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
        )

        executed_sql = mock_cursor.execute.call_args[0][0]
        assert "2024-01-01" in executed_sql
        assert "2024-01-31" in executed_sql


class TestValidateResample:
    def test_valid_upscale(self, qdb_config):
        qdb = QuestDBSource(qdb_config)
        qdb._validate_resample("1m", "1h")  # no exception

    def test_invalid_downscale_raises(self, qdb_config):
        qdb = QuestDBSource(qdb_config)
        with pytest.raises(ValueError, match="target timeframe must be larger"):
            qdb._validate_resample("1h", "1m")

    def test_unknown_target_raises(self, qdb_config):
        qdb = QuestDBSource(qdb_config)
        with pytest.raises(ValueError, match="Unknown target timeframe"):
            qdb._validate_resample("1m", "3h")

    def test_unknown_source_skips_validation(self, qdb_config):
        qdb = QuestDBSource(qdb_config)
        qdb._validate_resample("unknown", "1h")  # no exception, just warning


class TestClose:
    @patch("src.questdb_reader.psycopg.connect")
    def test_closes_open_connection(self, mock_connect, qdb_config):
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_connect.return_value = mock_conn

        qdb = QuestDBSource(qdb_config)
        qdb._get_connection()
        qdb.close()

        mock_conn.close.assert_called_once()
        assert qdb._conn is None

    def test_close_without_connection(self, qdb_config):
        qdb = QuestDBSource(qdb_config)
        qdb.close()  # no exception
