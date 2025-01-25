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
class DummyEventMessage1:
    message_id: int


@dataclass
class DummyEventMessage2:
    message_id: int


def event_loop():
    while True:
        event = event_message_queue.get()

        if event is None:  # Sentinel value to terminate the loop
            logger.info(
                f"Consumed sentinel value from queue; Terminating event loop | Queue Size: {event_message_queue.qsize()}"
            )
            break

        if isinstance(event, DummyEventMessage1):
            consumer_1(event)
        elif isinstance(event, DummyEventMessage2):
            consumer_2(event)

        # Log queue size after processing each event
        logger.info(
            f"Event loop processed event: {event.message_id} | Queue Size: {event_message_queue.qsize()}"
        )


def producer():
    for i in range(1, 6):
        event = DummyEventMessage1(message_id=i)
        event_message_queue.put(event)
        logger.info(
            f"Producer put event message {event.message_id} in queue | Queue Size: {event_message_queue.qsize()}"
        )
        sleep(1)

    event_message_queue.put(None)  # Sentinel value
    logger.info(
        f"Producer put sentinel value 'None' in queue | Queue Size: {event_message_queue.qsize()}"
    )


def consumer_1(event):
    logger.info(
        f"Consumer 1 processed event: {event.message_id} | Queue Size before consuming: {event_message_queue.qsize()}"
    )
    new_event = DummyEventMessage2(message_id=event.message_id + 100)
    event_message_queue.put(new_event)
    logger.info(
        f"Consumer 1 put event {new_event.message_id} in queue | Queue Size after producing: {event_message_queue.qsize()}"
    )


def consumer_2(event):
    logger.info(
        f"Consumer 2 processed event: {event.message_id} | Queue Size: {event_message_queue.qsize()}"
    )


def main():
    setup_logging()
    logger.info("Starting MWE-1_logger")

    producer_thread = threading.Thread(target=producer)
    event_loop_thread = threading.Thread(target=event_loop)

    producer_thread.start()
    event_loop_thread.start()

    producer_thread.join()
    event_loop_thread.join()

    logger.info("Producer and Consumer threads have finished execution.")


if __name__ == "__main__":
    main()
