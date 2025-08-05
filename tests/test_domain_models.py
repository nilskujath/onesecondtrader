"""
Test suite for domain models.

This module verifies the correctness and structure of the domain models
used in the trading infrastructure. These tests confirm the integrity of
enums, structural groupings, and auxiliary utilities such as human-readable
conversion methods.

Coverage:
- MarketData: OHLCV structure and RecordType enum
- PositionManagement: OrderType, OrderState, Side, TimeInForce
- Grouped namespace structure and accessibility
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from onesecondtrader.domain_models import MarketData, PositionManagement


class TestMarketData:
    def test_ohlcv_namedtuple(self):
        ohlcv = MarketData.OHLCV(100.0, 101.0, 99.0, 100.5, 1000)

        assert ohlcv.open == 100.0
        assert ohlcv.high == 101.0
        assert ohlcv.low == 99.0
        assert ohlcv.close == 100.5
        assert ohlcv.volume == 1000

    def test_record_type_enum_values(self):
        assert MarketData.RecordType.OHLCV_1S.value == 32
        assert MarketData.RecordType.OHLCV_1M.value == 33
        assert MarketData.RecordType.OHLCV_1H.value == 34
        assert MarketData.RecordType.OHLCV_1D.value == 35

    def test_record_type_to_string(self):
        assert MarketData.RecordType.to_string(32) == "1-second bars"
        assert MarketData.RecordType.to_string(33) == "1-minute bars"
        assert MarketData.RecordType.to_string(34) == "1-hour bars"
        assert MarketData.RecordType.to_string(35) == "daily bars"
        assert MarketData.RecordType.to_string(999) == "unknown (999)"


class TestPositionManagement:
    def test_order_type_enum(self):
        order_types = [
            PositionManagement.OrderType.MARKET,
            PositionManagement.OrderType.LIMIT,
            PositionManagement.OrderType.STOP,
            PositionManagement.OrderType.STOP_LIMIT,
        ]
        assert len(set(order_types)) == len(order_types)

    def test_order_state_enum(self):
        order_states = [
            PositionManagement.OrderState.NEW,
            PositionManagement.OrderState.SUBMITTED,
            PositionManagement.OrderState.ACTIVE,
            PositionManagement.OrderState.PARTIALLY_FILLED,
            PositionManagement.OrderState.FILLED,
            PositionManagement.OrderState.CANCELLED,
            PositionManagement.OrderState.CANCELLED_AT_PARTIAL_FILL,
            PositionManagement.OrderState.REJECTED,
            PositionManagement.OrderState.EXPIRED,
        ]
        assert len(set(order_states)) == len(order_states)

    def test_side_enum(self):
        sides = [PositionManagement.Side.BUY, PositionManagement.Side.SELL]
        assert PositionManagement.Side.BUY != PositionManagement.Side.SELL
        assert len(set(sides)) == 2

    def test_time_in_force_enum(self):
        tif_values = [
            PositionManagement.TimeInForce.DAY,
            PositionManagement.TimeInForce.FOK,
            PositionManagement.TimeInForce.GTC,
            PositionManagement.TimeInForce.GTD,
            PositionManagement.TimeInForce.IOC,
        ]
        assert len(set(tif_values)) == len(tif_values)


class TestGroupedStructure:
    def test_grouped_imports(self):
        from onesecondtrader.domain_models import MarketData, PositionManagement

        assert hasattr(MarketData, "OHLCV")
        assert hasattr(MarketData, "RecordType")
        assert hasattr(PositionManagement, "OrderType")
        assert hasattr(PositionManagement, "OrderState")
        assert hasattr(PositionManagement, "Side")
        assert hasattr(PositionManagement, "TimeInForce")

    def test_grouped_usage_patterns(self):
        ohlcv = MarketData.OHLCV(100, 101, 99, 100.5, 1000)
        assert ohlcv.close == 100.5

        assert MarketData.RecordType.OHLCV_1M.value == 33
        assert PositionManagement.Side.BUY != PositionManagement.Side.SELL
        assert PositionManagement.TimeInForce.DAY != PositionManagement.TimeInForce.GTC
