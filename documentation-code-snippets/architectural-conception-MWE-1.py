from dataclasses import dataclass
import queue
from time import sleep


event_message_queue = queue.Queue()


@dataclass
class DummyEventMessage:
    message_id: int


def producer():
    for i in range(1, 6):
        event = DummyEventMessage(message_id=i)
        event_message_queue.put(event)
        print(
            f"Producer put event message {event.message_id} in queue | "
            f"Queue Size: {event_message_queue.qsize()}"
        )
        sleep(1)
    event_message_queue.put(None)
    print(
        f"Producer put sentinel value 'None' in queue | Queue Size: "
        f"{event_message_queue.qsize()}"
    )


def consumer():
    while True:
        event = event_message_queue.get()
        if event is None:
            print(
                f"Consumed sentinel value from queue; Terminating event consumption "
                f"| Queue Size: {event_message_queue.qsize()}"
            )
            break
        print(
            f"Consumed event message {event.message_id} from queue | Queue Size: "
            f"{event_message_queue.qsize()}"
        )


def main():
    producer()
    consumer()


if __name__ == "__main__":
    main()
