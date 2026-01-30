from onesecondtrader.models import TradeSide


class TestTradeSide:
    def test_members(self):
        assert set(TradeSide.__members__) == {
            "BUY",
            "SELL",
        }
