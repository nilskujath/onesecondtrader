from onesecondtrader.models import BarPeriod


class TestBarPeriod:
    def test_members(self):
        assert set(BarPeriod.__members__) == {
            "SECOND",
            "MINUTE",
            "HOUR",
            "DAY",
        }
