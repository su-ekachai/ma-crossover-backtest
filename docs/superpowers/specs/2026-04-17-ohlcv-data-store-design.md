# OHLCV Data Store — Design Spec

## Context

A standalone project for downloading, storing, and serving OHLCV (Open, High, Low, Close, Volume) market data using PostgreSQL + TimescaleDB. This is the centralized data layer for all trading projects — the EMA-99 backtester and future projects will consume data from this store. It lives in its own repository.

## Requirements

### Functional
- **Download** OHLCV data from Binance (crypto) and Yahoo Finance (stocks/ETFs)
- **Store** data in PostgreSQL with TimescaleDB extension
- **Store 1m candles** as the canonical source; auto-generate larger timeframes via continuous aggregates
- **Support direct ingestion** of larger timeframes when 1m isn't available (e.g., historical daily stock data)
- **Export** data to CSV for use with other tools (e.g., the backtester)
- **Gap detection** — identify missing periods in downloaded data
- **CLI** for all operations (download, list, check gaps, export, db management)
- **Library API** — importable Python functions for other projects (`get_ohlcv()`)
- **Manual downloads only** — no auto-scheduler (can be added later)
- Forex support deferred to a future phase

### Non-Functional
- Python 3.12, uv, loguru, ruff, ty (same as backtester)
- Local development — PostgreSQL + TimescaleDB running locally (Docker or native)
- Clean separation: downloaders know nothing about the database, DB layer knows nothing about exchanges

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.12 | Consistent with backtester |
| Package manager | uv | Consistent with backtester |
| Database | PostgreSQL 16+ | Robust, widely supported, reusable |
| Time-series extension | TimescaleDB | Hypertables, continuous aggregates, compression — purpose-built for OHLCV |
| DB client | psycopg 3 | Modern, async-capable, lightweight (no ORM overhead) |
| Crypto data | ccxt | Unified API for 100+ exchanges; future-proof beyond just Binance |
| Stock data | yfinance | Simple, free, covers US/international stocks and ETFs |
| CLI | Click | Consistent with backtester |
| Logging | Loguru | Consistent with backtester |
| Config | PyYAML | Database connection + download settings |
| Linting | Ruff | Consistent with backtester |
| Type checking | ty | Consistent with backtester |

## Architecture

```
ohlcv-data-store/
├── src/
│   ├── __init__.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py        # Connection pool, context manager
│   │   ├── schema.py            # Table creation, hypertables, continuous aggregates
│   │   ├── repository.py        # Insert, query, gap detection
│   │   └── migrations/          # SQL migration files (versioned)
│   │       ├── 001_create_tables.sql
│   │       ├── 002_create_hypertable.sql
│   │       ├── 003_continuous_aggregates.sql
│   │       └── 004_compression_policy.sql
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract DataSource class
│   │   ├── binance.py           # Binance via ccxt
│   │   └── yahoo.py             # Yahoo Finance via yfinance
│   ├── services/
│   │   ├── __init__.py
│   │   ├── downloader.py        # Orchestrates: source → validate → store
│   │   └── exporter.py          # DB → CSV export
│   ├── config.py                # Config dataclass + YAML loader
│   └── api.py                   # Public library API (get_ohlcv, list_assets, etc.)
├── main.py                      # Click CLI entry point
├── config.yaml                  # Database connection + defaults
├── pyproject.toml
├── .python-version
├── .gitignore
├── tests/
│   └── ...
└── docker/
    └── docker-compose.yml       # PostgreSQL + TimescaleDB for local dev
```

## Database Schema

### Tables

```sql
-- Asset metadata
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,             -- e.g., 'BTCUSDT', 'AAPL'
    exchange TEXT NOT NULL,           -- e.g., 'binance', 'yahoo'
    asset_type TEXT NOT NULL,         -- 'crypto', 'stock', 'etf'
    base_currency TEXT,               -- e.g., 'BTC'
    quote_currency TEXT,              -- e.g., 'USDT'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, exchange)
);

-- OHLCV candle data (TimescaleDB hypertable)
CREATE TABLE ohlcv (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,          -- '1m', '5m', '1h', '1d', etc.
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL DEFAULT 0,
    UNIQUE(timestamp, symbol, exchange, timeframe)
);

-- Convert to hypertable
SELECT create_hypertable('ohlcv', 'timestamp');

-- Indexes for common query patterns
CREATE INDEX idx_ohlcv_symbol_tf_time
    ON ohlcv (symbol, exchange, timeframe, timestamp DESC);

-- Download tracking
CREATE TABLE download_log (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    rows_inserted INTEGER NOT NULL,
    downloaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Continuous Aggregates (auto-generated from 1m data)

```sql
-- Example: 1-hour aggregate from 1-minute data
CREATE MATERIALIZED VIEW ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS timestamp,
    symbol,
    exchange,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM ohlcv
WHERE timeframe = '1m'
GROUP BY time_bucket('1 hour', timestamp), symbol, exchange
WITH NO DATA;

-- Refresh policy: auto-refresh every 30 minutes, covering last 2 hours
SELECT add_continuous_aggregate_policy('ohlcv_1h',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '30 minutes',
    schedule_interval => INTERVAL '30 minutes'
);
```

Continuous aggregates created for: **5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w**

### Compression Policy

```sql
-- Enable compression on ohlcv table
ALTER TABLE ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, exchange, timeframe',
    timescaledb.compress_orderby = 'timestamp'
);

-- Auto-compress data older than 7 days
SELECT add_compression_policy('ohlcv', INTERVAL '7 days');
```

Expected compression ratio: **90-95%** for OHLCV data.

## Component Details

### 1. Data Sources (`src/sources/`)

Abstract base:
```python
class DataSource(ABC):
    @abstractmethod
    def download(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Returns DataFrame with columns: timestamp, open, high, low, close, volume"""
        ...

    @abstractmethod
    def list_symbols(self) -> list[str]:
        """Returns available symbols on this exchange"""
        ...

    @abstractmethod
    def get_earliest_timestamp(self, symbol: str, timeframe: str) -> datetime:
        """Returns the earliest available data point"""
        ...
```

**BinanceSource** (`src/sources/binance.py`):
- Uses `ccxt.binance()` to fetch OHLCV data
- Handles pagination (Binance returns max 1000 candles per request)
- Rate limiting built-in (ccxt handles this)
- Supports all Binance spot pairs

**YahooSource** (`src/sources/yahoo.py`):
- Uses `yfinance.download()` to fetch OHLCV data
- Note: Yahoo 1m data only available for last 30 days; 1d available historically
- Handles stock splits and adjusted close (use adjusted values)

### 2. Database Layer (`src/db/`)

**connection.py**:
- Connection pool via `psycopg_pool.ConnectionPool`
- Context manager for transactions
- Config from `config.yaml`

**repository.py**:
```python
class OHLCVRepository:
    def insert_candles(self, df: pd.DataFrame, symbol: str, exchange: str, timeframe: str) -> int:
        """Bulk insert with ON CONFLICT DO NOTHING (idempotent). Returns rows inserted."""

    def get_ohlcv(self, symbol: str, exchange: str, timeframe: str,
                  start: datetime, end: datetime) -> pd.DataFrame:
        """Query candles. Routing logic:
        - If timeframe == '1m': query ohlcv table directly
        - If timeframe in (5m,15m,30m,1h,2h,4h,1d,1w) AND 1m data exists: query continuous aggregate view
        - If timeframe was directly ingested (no 1m source): query ohlcv table with timeframe filter
        """

    def find_gaps(self, symbol: str, exchange: str, timeframe: str,
                  start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        """Returns list of (gap_start, gap_end) tuples where data is missing."""

    def get_date_range(self, symbol: str, exchange: str, timeframe: str) -> tuple[datetime, datetime]:
        """Returns (earliest, latest) timestamps for a symbol."""

    def list_assets(self) -> pd.DataFrame:
        """Returns all assets with their date ranges and row counts."""

    def get_db_stats(self) -> dict:
        """Returns total rows, compressed size, number of assets, etc."""
```

**schema.py**:
- `init_db()`: Run all migration SQL files in order
- `create_continuous_aggregates()`: Set up all timeframe aggregates
- `setup_compression()`: Enable compression policies

### 3. Downloader Service (`src/services/downloader.py`)

Orchestrates the download flow:
```python
class DownloadService:
    def download(self, symbol: str, exchange: str, timeframe: str,
                 start: datetime, end: datetime | None = None) -> int:
        """
        1. Resolve DataSource for exchange
        2. Determine date range (default: earliest available to now)
        3. Download in chunks (to handle large date ranges)
        4. Validate data (no future timestamps, OHLC sanity checks)
        5. Insert into database (idempotent)
        6. Log download to download_log table
        7. Return total rows inserted
        """

    def backfill(self, symbol: str, exchange: str) -> int:
        """Download all available history for a symbol at 1m timeframe."""

    def update(self, symbol: str, exchange: str) -> int:
        """Download new data since last known timestamp."""
```

### 4. Exporter (`src/services/exporter.py`)

```python
class ExportService:
    def to_csv(self, symbol: str, exchange: str, timeframe: str,
               start: datetime, end: datetime, output_path: str) -> str:
        """
        Query data from DB, format as OHLCV CSV compatible with the backtester.
        Output format:
            datetime,Open,High,Low,Close,Volume
        Returns the output file path.
        """
```

### 5. Public API (`src/api.py`)

The interface other projects import:
```python
def get_ohlcv(symbol: str, timeframe: str, start: str, end: str,
              exchange: str = 'binance') -> pd.DataFrame:
    """Get OHLCV data as a pandas DataFrame ready for backtesting."""

def list_assets(exchange: str | None = None) -> pd.DataFrame:
    """List all available assets in the database."""

def get_available_range(symbol: str, exchange: str = 'binance') -> tuple[datetime, datetime]:
    """Get the date range available for a symbol."""
```

### 6. CLI (`main.py`)

```bash
# Database management
ohlcv-store db init                     # Create tables, hypertables, aggregates
ohlcv-store db status                   # Show row counts, compression stats, date ranges

# Download data
ohlcv-store download BTCUSDT --exchange binance --timeframe 1m --start 2024-01-01
ohlcv-store download AAPL --exchange yahoo --timeframe 1d --start 2020-01-01
ohlcv-store download BTCUSDT --exchange binance --backfill   # Download all available history
ohlcv-store download BTCUSDT --exchange binance --update      # Fetch latest since last download

# List assets in database
ohlcv-store list                        # All assets with date ranges
ohlcv-store list --exchange binance     # Filter by exchange

# Check for data gaps
ohlcv-store check-gaps BTCUSDT --exchange binance --timeframe 1m

# Export to CSV (for backtester)
ohlcv-store export BTCUSDT --exchange binance --timeframe 1h \
    --start 2024-01-01 --end 2024-12-31 --output data/BTCUSDT_1h.csv
```

## Config File (`config.yaml`)

```yaml
database:
  host: localhost
  port: 5432
  name: ohlcv_store
  user: postgres
  password: postgres           # Use env var OHLCV_DB_PASSWORD in production

download:
  default_exchange: binance
  default_timeframe: 1m
  chunk_size: 1000             # Candles per API request
  rate_limit_pause: 0.5        # Seconds between requests

exchanges:
  binance:
    enabled: true
    # No API key needed for public OHLCV data
  yahoo:
    enabled: true
```

## Docker Setup (`docker/docker-compose.yml`)

```yaml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: ohlcv_store
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - timescaledb_data:/home/postgres/pgdata/data
    restart: unless-stopped

volumes:
  timescaledb_data:
```

Start with: `docker compose -f docker/docker-compose.yml up -d`

## Data Flow

```
Exchange APIs (Binance, Yahoo)
    │
    ▼
DataSource.download()          ← Fetches raw OHLCV, returns DataFrame
    │
    ▼
DownloadService.download()     ← Validates, chunks, orchestrates
    │
    ▼
OHLCVRepository.insert()      ← Bulk insert into ohlcv table (1m)
    │
    ▼
TimescaleDB continuous         ← Auto-generates 5m, 15m, 1h, 4h, 1d, 1w
aggregates (automatic)
    │
    ▼
OHLCVRepository.get_ohlcv()   ← Queries correct table/aggregate
    │
    ├──▶ api.get_ohlcv()       ← Other projects import this
    └──▶ ExportService.to_csv() ← CLI export for backtester
```

## Verification

1. **Docker**: `docker compose up -d` starts TimescaleDB, `psql` connects successfully
2. **DB init**: `ohlcv-store db init` creates all tables, hypertables, aggregates without errors
3. **Download**: `ohlcv-store download BTCUSDT --exchange binance --timeframe 1m --start 2024-12-01 --end 2024-12-02` downloads ~1440 rows
4. **Continuous aggregates**: Query `ohlcv_1h` after downloading 1m data — returns correct hourly candles
5. **Gap detection**: `ohlcv-store check-gaps` correctly identifies missing periods
6. **Export**: `ohlcv-store export` produces CSV compatible with the backtester's `data_loader.py`
7. **API**: `from ohlcv_data_store.api import get_ohlcv` works from another project
8. **Compression**: After inserting data and waiting for compression policy, `db status` shows compression ratio

## Future Considerations (out of scope)

- Forex data sources (OANDA, Alpha Vantage, etc.)
- Scheduled auto-downloads (APScheduler or cron)
- Real-time streaming (WebSocket feeds)
- Data quality alerts (anomaly detection)
- REST API server (for non-Python consumers)
- Multi-node TimescaleDB deployment
