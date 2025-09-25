from onesecondtrader.brokers import base_broker


class SimulatedBroker(base_broker.BaseBroker):
    """
    Simple simulated broker used as a safe default.
    """

    def __init__(self, event_bus=None):
        super().__init__(event_bus)
