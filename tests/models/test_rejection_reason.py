from onesecondtrader.models import (
    OrderRejectionReason,
    ModificationRejectionReason,
    CancellationRejectionReason,
)


class TestOrderRejectionReason:
    def test_members(self):
        assert set(OrderRejectionReason.__members__) == {
            "UNKNOWN",
        }


class TestModificationRejectionReason:
    def test_members(self):
        assert set(ModificationRejectionReason.__members__) == {
            "UNKNOWN",
        }


class TestCancellationRejectionReason:
    def test_members(self):
        assert set(CancellationRejectionReason.__members__) == {
            "UNKNOWN",
        }
