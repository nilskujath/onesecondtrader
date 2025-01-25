from dataclasses import dataclass
import logging.config
import logging.handlers
import pathlib
import queue
import threading
from time import sleep
import yaml


logger = logging.getLogger("MWE-1_logger")


def setup_logging():
    config_file = pathlib.Path("logger-config-MWE-1.yaml")
    with open(config_file) as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)


event_message_queue = queue.Queue()


@dataclass
class DummyEventMessage:
    message_id: int


def producer():
    for i in range(1, 6):
        event = DummyEventMessage(message_id=i)
        event_message_queue.put(event)
        logger.info(
            f"Producer put event message {event.message_id} in queue | "
            f"Queue Size: {event_message_queue.qsize()}"
        )
        sleep(1)
    event_message_queue.put(None)
    logger.info(
        f"Producer put sentinel value 'None' in queue | Queue Size: "
        f"{event_message_queue.qsize()}"
    )


def consumer():
    while True:
        event = event_message_queue.get()
        if event is None:
            logger.info(
                f"Consumed sentinel value from queue; Terminating event consumption "
                f"| Queue Size: {event_message_queue.qsize()}"
            )
            break
        logger.info(
            f"Consumed event message {event.message_id} from queue | Queue Size: "
            f"{event_message_queue.qsize()}"
        )


def main():
    setup_logging()
    logger.info("Starting MWE-1_logger")

    producer_thread = threading.Thread(target=producer)
    consumer_thread = threading.Thread(target=consumer)

    producer_thread.start()
    consumer_thread.start()

    producer_thread.join()
    consumer_thread.join()

    logger.info("Producer and Consumer thread have finished execution.")


if __name__ == "__main__":
    main()
