"""CSV data loading, validation, and timeframe resampling."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

TIMEFRAME_RESAMPLERS = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "h",
    "2h": "2h",
    "4h": "4h",
    "1d": "D",
    "1w": "W",
}


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load an OHLCV CSV file with validation.

    Args:
        path: Path to the CSV file.

    Returns:
        A DataFrame with a DatetimeIndex and OHLCV columns.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing or data is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    df = pd.read_csv(path, parse_dates=["datetime"])
    df.set_index("datetime", inplace=True)

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns in {path.name}: {missing}. "
            f"Expected: datetime, Open, High, Low, Close, Volume"
        )

    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"NaN values found in OHLCV data in {path.name}")

    if not df.index.is_monotonic_increasing:
        df.sort_index(inplace=True)

    return df


def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample OHLCV DataFrame to a target timeframe.

    Args:
        df: A DataFrame with DatetimeIndex and OHLCV columns.
        timeframe: Target timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w).

    Returns:
        A resampled DataFrame with aggregated OHLCV data.

    Raises:
        ValueError: If the timeframe is not supported.
    """
    if timeframe not in TIMEFRAME_RESAMPLERS:
        raise ValueError(
            f"Unsupported timeframe: {timeframe}. Supported: {list(TIMEFRAME_RESAMPLERS.keys())}"
        )

    rule = TIMEFRAME_RESAMPLERS[timeframe]
    resampled = (
        df.resample(rule)
        .agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        .dropna()
    )

    return resampled
