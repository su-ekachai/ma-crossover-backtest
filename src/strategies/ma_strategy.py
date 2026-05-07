"""MA-based trading strategy for Backtesting.py."""

from __future__ import annotations

import pandas_ta as ta
from backtesting import Strategy


class MAStrategy(Strategy):
    """Moving Average strategy with configurable confirmation candles.

    Class variables are used so Backtesting.py's optimize() can modify them.
    """

    ma_type: str = "EMA"
    ma_period: int = 99
    confirmation_candles: int = 0
    direction: str = "both"
    sizing_mode: str = "all_in"
    sizing_fixed_amount: float = 1000.0
    sizing_risk_pct: float = 0.02

    def init(self) -> None:
        prices = self.data.Close.s
        if self.ma_type == "EMA":
            self._ma = self.I(
                lambda: ta.ema(prices, length=self.ma_period),
                name=f"EMA{self.ma_period}",
            )
        else:
            self._ma = self.I(
                lambda: ta.sma(prices, length=self.ma_period),
                name=f"SMA{self.ma_period}",
            )

        self._consecutive_above = 0
        self._consecutive_below = 0

    def next(self) -> None:
        close = self.data.Close[-1]
        ma = self._ma[-1]

        above = close > ma
        below = close < ma

        if above:
            self._consecutive_above += 1
            self._consecutive_below = 0
        elif below:
            self._consecutive_below += 1
            self._consecutive_above = 0

        confirmed_above = self._consecutive_above > self.confirmation_candles
        confirmed_below = self._consecutive_below > self.confirmation_candles

        if not self.position:
            if confirmed_above and self.direction in ("long_only", "both"):
                self.buy(size=self._calculate_size())
            elif confirmed_below and self.direction in ("short_only", "both"):
                self.sell(size=self._calculate_size())
        else:
            if (self.position.is_long and confirmed_below and self.direction == "both") or (
                self.position.is_short and confirmed_above and self.direction == "both"
            ):
                self.position.close()

    def _calculate_size(self) -> float:
        if self.sizing_mode == "all_in":
            return 1.0
        if self.sizing_mode == "fixed":
            return min(self.sizing_fixed_amount / self.data.Close[-1], 0.99)
        if self.sizing_mode == "percentage":
            equity = self._broker.equity
            return min((equity * self.sizing_risk_pct) / self.data.Close[-1], 0.99)
        return 1.0
