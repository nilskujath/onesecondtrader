from onesecondtrader.engines.abstract_base_class_engines import ABCEngine
from onesecondtrader.datafeeds.replay_from_csv import ReplayFromCSV


class BarCSVToDummyBroker(ABCEngine):

    def connect_datafeed(self, path_to_csv_file):
        self._datafeed = ReplayFromCSV(path_to_csv_file)
        self._datafeed.connect()
