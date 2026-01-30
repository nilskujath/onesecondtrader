from onesecondtrader.models import BarField


class TestBarField:
    def test_members(self):
        assert set(BarField.__members__) == {
            "OPEN",
            "HIGH",
            "LOW",
            "CLOSE",
            "VOLUME",
        }
