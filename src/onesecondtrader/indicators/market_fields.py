from __future__ import annotations

import numpy as np

from onesecondtrader import events, indicators


class Open(indicators.IndicatorBase):
    """
    Open price indicator.

    This indicator exposes the open price of each incoming market bar as a scalar time series.
    Values are stored per symbol and can be accessed historically via the indicator interface.
    """

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Fixed identifier for the open price indicator.
        """
        return "OPEN"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Extract the open price from an incoming market bar.

        Parameters:
            incoming_bar:
                Market bar used as input.

        Returns:
            Open price of the bar.
        """
        return incoming_bar.open


class High(indicators.IndicatorBase):
    """
    High price indicator.

    This indicator exposes the high price of each incoming market bar as a scalar time series.
    Values are stored per symbol and can be accessed historically via the indicator interface.
    """

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Fixed identifier for the high price indicator.
        """
        return "HIGH"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Extract the high price from an incoming market bar.

        Parameters:
            incoming_bar:
                Market bar used as input.

        Returns:
            High price of the bar.
        """
        return incoming_bar.high


class Low(indicators.IndicatorBase):
    """
    Low price indicator.

    This indicator exposes the low price of each incoming market bar as a scalar time series.
    Values are stored per symbol and can be accessed historically via the indicator interface.
    """

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Fixed identifier for the low price indicator.
        """
        return "LOW"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Extract the low price from an incoming market bar.

        Parameters:
            incoming_bar:
                Market bar used as input.

        Returns:
            Low price of the bar.
        """
        return incoming_bar.low


class Close(indicators.IndicatorBase):
    """
    Close price indicator.

    This indicator exposes the close price of each incoming market bar as a scalar time series.
    Values are stored per symbol and can be accessed historically via the indicator interface.
    """

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Fixed identifier for the close price indicator.
        """
        return "CLOSE"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Extract the close price from an incoming market bar.

        Parameters:
            incoming_bar:
                Market bar used as input.

        Returns:
            Close price of the bar.
        """
        return incoming_bar.close


class Volume(indicators.IndicatorBase):
    """
    Volume indicator.

    This indicator exposes the traded volume of each incoming market bar as a scalar time series.
    Values are stored per symbol and can be accessed historically via the indicator interface.
    Missing volume values yield `numpy.nan`.
    """

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Fixed identifier for the volume indicator.
        """
        return "VOLUME"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Extract the volume from an incoming market bar.

        Parameters:
            incoming_bar:
                Market bar used as input.

        Returns:
            Volume of the bar, or `numpy.nan` if unavailable.
        """
        return float(incoming_bar.volume) if incoming_bar.volume is not None else np.nan
