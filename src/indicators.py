"""EMA and SMA indicator calculations using pandas-ta."""

from pandas import Series


def calculate_ema(prices: Series, period: int) -> Series:
    """Calculate Exponential Moving Average.

    Args:
        prices: A pandas Series of price values.
        period: The EMA period (e.g., 99 for EMA-99).

    Returns:
        A pandas Series with the same index as input, containing EMA values.
    """
    import pandas_ta as ta

    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")

    result = ta.ema(prices, length=period)
    return result


def calculate_sma(prices: Series, period: int) -> Series:
    """Calculate Simple Moving Average.

    Args:
        prices: A pandas Series of price values.
        period: The SMA period.

    Returns:
        A pandas Series with the same index as input, containing SMA values.
    """
    import pandas_ta as ta

    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")

    result = ta.sma(prices, length=period)
    return result
