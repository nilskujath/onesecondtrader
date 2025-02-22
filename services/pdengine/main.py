import yaml
import logging
import time
import sys
import uuid
from enum import Enum
from logging.handlers import RotatingFileHandler
import os
import pandas as pd


session_id = str(uuid.uuid4())[:8]

logging.basicConfig(
    level=logging.DEBUG,
    format=f"%(asctime)s - %(levelname)s - %(threadName)s - [{session_id}] - %(message)s",
)

log_handler = RotatingFileHandler("pdengine.log", maxBytes=5_000_000, backupCount=3)
log_handler.setFormatter(
    logging.Formatter(
        f"%(asctime)s - %(levelname)s - %(threadName)s - [{session_id}] - %(message)s"
    )
)
logger = logging.getLogger(__name__)
logger.addHandler(log_handler)

logger.info(f"Starting new session: {session_id}")


class Mode(Enum):
    LIVE = "LIVE"
    REPLAY = "REPLAY"


class Pdengine:
    def __init__(self, config):
        self.config = config

        if "Mode" not in self.config:
            logger.error(
                f"Missing `Mode` key in `pdengine_config.yaml`. Expected one of: "
                f"{', '.join(m.value for m in Mode)}."
            )
            sys.exit(1)

        try:
            self.mode = Mode(self.config["Mode"])
        except ValueError:
            logger.error(
                f"Invalid mode: '{self.config['Mode']}'. Expected one of: "
                f"{', '.join(m.value for m in Mode)}."
            )
            sys.exit(1)

        logger.info(f"Pdengine initialized in {self.mode.value} mode.")

    def connect(self):
        try:
            if self.mode == Mode.LIVE:
                self._connect_live()
            elif self.mode == Mode.REPLAY:
                self._connect_backtest()
        except NotImplementedError as e:
            logger.error(e)
            sys.exit(1)

    def _connect_backtest(self):
        csv_file_path = self._validate_csv_path()
        logger.info(f"Opening CSV file: {csv_file_path}")

        with open(csv_file_path, "r") as csv_file:
            df = pd.read_csv(csv_file)
            first_row = df.iloc[0].to_dict()
            logger.info(f"First row of CSV: {first_row}")

    def _open_replay_csv(self):
        csv_file_path = self._validate_csv_path()
        logger.info(f"Opening CSV file: {csv_file_path}")
        return open(csv_file_path, "r")

    def _validate_csv_path(self):
        csv_directory = "/app/replay_dbcsv"

        if not os.path.exists(csv_directory):
            logger.error(f"Directory {csv_directory} does not exist.")
            sys.exit(1)

        csv_files = [f for f in os.listdir(csv_directory) if f.endswith(".csv")]

        if len(csv_files) == 0:
            logger.error("No CSV file found in the replay_dbcsv directory.")
            sys.exit(1)
        elif len(csv_files) > 1:
            logger.error("More than one CSV file found in the replay_dbcsv directory.")
            sys.exit(1)

        return os.path.join(csv_directory, csv_files[0])

    def _connect_live(self):
        raise NotImplementedError(
            "Method `_connect_live()` has not been implemented yet."
        )


def load_config():
    try:
        with open("pdengine_config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(
            f"Configuration file `pdengine_config.yaml` not found in pdengine directory."
        )
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        sys.exit(1)


def main():
    config = load_config()
    pdengine = Pdengine(config)
    pdengine.connect()


if __name__ == "__main__":
    main()
