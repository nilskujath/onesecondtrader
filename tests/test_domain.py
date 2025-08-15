"""
Test suite for domain.py module.

This module tests the domain models defined in the domain.py file.
Event classes are excluded from testing coverage.
"""

import pytest

from src.onesecondtrader.domain import (
    DomainModel,
    MarketData,
    PositionManagement,
    SystemManagement,
)


class TestDomainModelAliases:
    """Test that domain model aliases work correctly."""

    def test_aliases_point_to_correct_classes(self):
        """Test all aliases point to their respective DomainModel classes."""
        assert MarketData is DomainModel.MarketData
        assert PositionManagement is DomainModel.PositionManagement
        assert SystemManagement is DomainModel.SystemManagement


class TestMarketDataDomainModels:
    """Test MarketData domain models."""

    def test_ohlcv_basic_functionality(self):
        """Test OHLCV namedtuple basic functionality."""
        ohlcv = MarketData.OHLCV(12.34, 13.74, 11.26, 12.32, 56789)

        assert MarketData.OHLCV._fields == ("open", "high", "low", "close", "volume")
        assert ohlcv.open == 12.34
        assert ohlcv.high == 13.74
        assert ohlcv.low == 11.26
        assert ohlcv.close == 12.32
        assert ohlcv.volume == 56789

    def test_ohlcv_keyword_construction(self):
        """Test OHLCV construction with keyword arguments."""
        ohlcv_pos = MarketData.OHLCV(1.0, 2.0, 0.5, 1.5, 1000)
        ohlcv_kw = MarketData.OHLCV(open=1.0, high=2.0, low=0.5, close=1.5, volume=1000)
        assert ohlcv_pos == ohlcv_kw

    def test_record_type_enum_values(self):
        """Test RecordType enum values match Databento specification."""
        assert MarketData.RecordType.OHLCV_1S.value == 32
        assert MarketData.RecordType.OHLCV_1M.value == 33
        assert MarketData.RecordType.OHLCV_1H.value == 34
        assert MarketData.RecordType.OHLCV_1D.value == 35

    @pytest.mark.parametrize(
        "record_type,expected_string",
        [
            (32, "1-second bars"),
            (33, "1-minute bars"),
            (34, "1-hour bars"),
            (35, "daily bars"),
            (99, "unknown (99)"),
        ],
    )
    def test_record_type_to_string(self, record_type, expected_string):
        """Test to_string method for both known and unknown record types."""
        assert MarketData.RecordType.to_string(record_type) == expected_string


class TestPositionManagementDomainModels:
    """Test PositionManagement domain models."""

    def test_order_type_enum_members(self):
        """Test OrderType enum has expected members with unique values."""
        expected_members = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}
        members = PositionManagement.OrderType.__members__
        assert set(members.keys()) == expected_members

        # Test uniqueness of values
        values = [member.value for member in PositionManagement.OrderType]
        assert len(values) == len(set(values))

    def test_order_state_enum_members(self):
        """Test OrderState enum has expected members with unique values."""
        expected_members = {
            "NEW",
            "SUBMITTED",
            "ACTIVE",
            "PARTIALLY_FILLED",
            "FILLED",
            "CANCELLED",
            "CANCELLED_AT_PARTIAL_FILL",
            "REJECTED",
            "EXPIRED",
        }
        members = PositionManagement.OrderState.__members__
        assert set(members.keys()) == expected_members

        # Test uniqueness of values
        values = [member.value for member in PositionManagement.OrderState]
        assert len(values) == len(set(values))

    def test_side_enum_members(self):
        """Test Side enum has expected members with unique values."""
        expected_members = {"BUY", "SELL"}
        members = PositionManagement.Side.__members__
        assert set(members.keys()) == expected_members

        # Test uniqueness of values
        values = [member.value for member in PositionManagement.Side]
        assert len(values) == len(set(values))

    def test_time_in_force_enum_members(self):
        """Test TimeInForce enum has expected members with unique values."""
        expected_members = {"DAY", "FOK", "GTC", "GTD", "IOC"}
        members = PositionManagement.TimeInForce.__members__
        assert set(members.keys()) == expected_members

        # Test uniqueness of values
        values = [member.value for member in PositionManagement.TimeInForce]
        assert len(values) == len(set(values))

    def test_cancel_reason_enum_members(self):
        """Test CancelReason enum has expected members with unique values."""
        expected_members = {
            "CLIENT_REQUEST",
            "EXPIRED_TIME_IN_FORCE",
            "BROKER_REJECTED_AT_SUBMISSION",
            "BROKER_FORCED_CANCEL",
            "UNKNOWN",
        }
        members = PositionManagement.CancelReason.__members__
        assert set(members.keys()) == expected_members

        # Test uniqueness of values
        values = [member.value for member in PositionManagement.CancelReason]
        assert len(values) == len(set(values))


class TestSystemManagementDomainModels:
    """Test SystemManagement domain models."""

    def test_stop_reason_enum_members(self):
        """Test StopReason enum has expected members with unique values."""
        expected_members = {"SYSTEM_SHUTDOWN", "COMPONENT_DISCONNECT"}
        members = SystemManagement.StopReason.__members__
        assert set(members.keys()) == expected_members

        # Test uniqueness of values
        values = [member.value for member in SystemManagement.StopReason]
        assert len(values) == len(set(values))


class TestDocumentationExamples:
    """Test examples from docstrings work correctly."""

    def test_ohlcv_docstring_example(self):
        """Test the OHLCV example from the docstring."""
        bar = MarketData.OHLCV(12.34, 13.74, 11.26, 12.32, 56789)
        assert bar.open == 12.34
        assert bar.high == 13.74

    def test_record_type_docstring_examples(self):
        """Test the RecordType examples from the docstring."""
        assert MarketData.RecordType.OHLCV_1S.value == 32
        assert MarketData.RecordType.to_string(32) == "1-second bars"
        assert MarketData.RecordType.to_string(99) == "unknown (99)"
