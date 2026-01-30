from onesecondtrader.models import OrderType


class TestOrderType:
    def test_members(self):
        assert set(OrderType.__members__) == {
            "LIMIT",
            "MARKET",
            "STOP",
            "STOP_LIMIT",
        }
