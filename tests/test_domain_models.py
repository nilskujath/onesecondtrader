import pytest

from src.onesecondtrader.domain_models import (
    MarketData,
    PositionManagement,
    SystemManagement,
)


def test_marketdata_ohlcv_structure_and_access():
    o = MarketData.OHLCV(1, 2, 3, 4, 5)
    assert MarketData.OHLCV._fields == ("open", "high", "low", "close", "volume")
    assert (o.open, o.high, o.low, o.close, o.volume) == (1, 2, 3, 4, 5)
    o_kw = MarketData.OHLCV(open=1, high=2, low=3, close=4, volume=5)
    assert o == o_kw
    assert {o, o_kw} == {o}


def test_marketdata_recordtype_values_match_databento():
    assert MarketData.RecordType.OHLCV_1S.value == 32
    assert MarketData.RecordType.OHLCV_1M.value == 33
    assert MarketData.RecordType.OHLCV_1H.value == 34
    assert MarketData.RecordType.OHLCV_1D.value == 35


@pytest.mark.parametrize(
    "code,expected",
    [
        (32, "1-second bars"),
        (33, "1-minute bars"),
        (34, "1-hour bars"),
        (35, "daily bars"),
    ],
)
def test_marketdata_recordtype_to_string_known(code, expected):
    assert MarketData.RecordType.to_string(code) == expected


def test_marketdata_recordtype_to_string_unknown():
    assert MarketData.RecordType.to_string(99) == "unknown (99)"


def test_position_management_order_type_members_and_uniqueness():
    expected = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}
    members = PositionManagement.OrderType.__members__
    assert set(members.keys()) == expected
    values = [m.value for m in PositionManagement.OrderType]
    assert len(values) == len(set(values))
    assert all(isinstance(m, PositionManagement.OrderType) for m in members.values())


def test_position_management_order_state_members_and_uniqueness():
    expected = {
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
    assert set(members.keys()) == expected
    values = [m.value for m in PositionManagement.OrderState]
    assert len(values) == len(set(values))


def test_position_management_side_members_and_uniqueness():
    expected = {"BUY", "SELL"}
    members = PositionManagement.Side.__members__
    assert set(members.keys()) == expected
    values = [m.value for m in PositionManagement.Side]
    assert len(values) == len(set(values))


def test_position_management_time_in_force_members_and_uniqueness():
    expected = {"DAY", "FOK", "GTC", "GTD", "IOC"}
    members = PositionManagement.TimeInForce.__members__
    assert set(members.keys()) == expected
    values = [m.value for m in PositionManagement.TimeInForce]
    assert len(values) == len(set(values))


def test_position_management_cancel_reason_members_and_uniqueness():
    expected = {
        "CLIENT_REQUEST",
        "EXPIRED_TIME_IN_FORCE",
        "BROKER_REJECTED_AT_SUBMISSION",
        "BROKER_FORCED_CANCEL",
        "UNKNOWN",
    }
    members = PositionManagement.CancelReason.__members__
    assert set(members.keys()) == expected
    values = [m.value for m in PositionManagement.CancelReason]
    assert len(values) == len(set(values))


def test_system_management_stop_reason_members_and_uniqueness():
    expected = {"SYSTEM_SHUTDOWN", "COMPONENT_DISCONNECT"}
    members = SystemManagement.StopReason.__members__
    assert set(members.keys()) == expected
    values = [m.value for m in SystemManagement.StopReason]
    assert len(values) == len(set(values))
