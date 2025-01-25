# Multi-Producer Multi-Consumer Systems and the Event Loop

To support multiple producers and consumers, we need an event loop that continuously monitors the queue for new events and dispatches them to the appropriate system components.
Adding a new component requires specifying which events it should receive within the event loop’s distribution logic. Recall that in our [second MWE](the-basics-of-event-driven-infrastructure.md), the consumer function itself acted as a rudimentary event loop, as there was only a single consumer handling all incoming events.

``` py title="Consumer function in second MWE with integrated, rudimentary event loop" linenums="1"
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
```

If we were to implement two distinct consumer functions, `consumer_1` and `consumer_2`, each handling a different type of event—`DummyEventMessage1` and `DummyEventMessage2`, respectively—we would need an **event loop** to dispatch events to the appropriate consumer. Instead of having a single producer generating both event types, we can extend the design by allowing `consumer_1`, after processing a `DummyEventMessage1`, to produce a `DummyEventMessage2` and enqueue it. This demonstrates that consumers can also function as producers, enabling a dynamic event-driven workflow where event consumption can trigger further event generation.

To achieve this, we first define the two distinct event messages, `DummyEventMessage1` and `DummyEventMessage2`, as `@dataclass` objects:

``` py title="Dataclass objects for the dummy event messages" linenums="1"
from dataclasses import dataclass

@dataclass
class DummyEventMessage1:
    message_id: int

@dataclass
class DummyEventMessage2:
    message_id: int
```

Next, we define the two consumer functions, `consumer_1` and `consumer_2`. At this stage, we use the `pass` statement as a placeholder, allowing us to integrate them into the system structure before implementing their actual functionality.

``` py title="Placeholder implementation of consumer functions" linenums="1"
def consumer_1():
    pass

def consumer_2():
    pass
```

With these function definitions in place, we can proceed to implement the event loop that will dispatch events to the appropriate consumer.

``` py title="Event loop function" linenums="1" 
import queue

event_message_queue = queue.Queue()

def event_loop():
    while True:
        event = event_message_queue.get()

        if event is None:  # Sentinel value to terminate the loop
            break

        if isinstance(event, DummyEventMessage1):
            consumer_1(event)
        elif isinstance(event, DummyEventMessage2):
            consumer_2(event)

```

Now, we need to modify the consumer functions so that `consumer_1` not only processes `DummyEventMessage1` but also produces a `DummyEventMessage2`, demonstrating that consumers can act as producers:

``` py title="Implemented consumer functions" linenums="1" 
import logging

def consumer_1(event):
    logging.info(f"Consumer 1 processed event: {event.message_id}")
    new_event = DummyEventMessage2(message_id=event.message_id + 99)
    event_message_queue.put(new_event)
    logging.info(f"Consumer 1 put event {new_event.message_id} in queue")


def consumer_2(event):
    logging.info(f"Consumer 2 processed event: {event.message_id} (produced by {event.source})")
```

To enhance readability in the output, we modify `consumer_1` to add `+100` to the `message_id` when creating `DummyEventMessage2` objects. This ensures a clear distinction between the two event types, making it easier to track their flow in the logs. Now we can put everything together. The only change in the producer function will be that `DummyEventMessage` from the second MWE will be changed to `DummyEventMessage1` for consistency with the new event message definitions.


``` py title="architectural-conception-MWE-3.py" linenums="1"
--8<-- "./docs/documentation-code-snippets/architectural-conception-MWE-3.py"
```

``` title="Console output architectural-conception-MWE-1.py" linenums="1"
2025-01-25 16:03:35 +0100 INFO [MainThread] MWE-1_logger - Starting MWE-1_logger
2025-01-25 16:03:35 +0100 INFO [Thread-1 (producer)] MWE-1_logger - Producer put event message 1 in queue | Queue Size: 1
2025-01-25 16:03:35 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 processed event: 1 | Queue Size before consuming: 0
2025-01-25 16:03:35 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 put event 101 in queue | Queue Size after producing: 1
2025-01-25 16:03:35 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 1 | Queue Size: 1
2025-01-25 16:03:35 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 2 processed event: 101 | Queue Size: 0
2025-01-25 16:03:35 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 101 | Queue Size: 0
2025-01-25 16:03:36 +0100 INFO [Thread-1 (producer)] MWE-1_logger - Producer put event message 2 in queue | Queue Size: 1
2025-01-25 16:03:36 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 processed event: 2 | Queue Size before consuming: 0
2025-01-25 16:03:36 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 put event 102 in queue | Queue Size after producing: 1
2025-01-25 16:03:36 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 2 | Queue Size: 1
2025-01-25 16:03:36 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 2 processed event: 102 | Queue Size: 0
2025-01-25 16:03:36 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 102 | Queue Size: 0
2025-01-25 16:03:37 +0100 INFO [Thread-1 (producer)] MWE-1_logger - Producer put event message 3 in queue | Queue Size: 1
2025-01-25 16:03:37 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 processed event: 3 | Queue Size before consuming: 0
2025-01-25 16:03:37 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 put event 103 in queue | Queue Size after producing: 1
2025-01-25 16:03:37 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 3 | Queue Size: 1
2025-01-25 16:03:37 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 2 processed event: 103 | Queue Size: 0
2025-01-25 16:03:37 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 103 | Queue Size: 0
2025-01-25 16:03:38 +0100 INFO [Thread-1 (producer)] MWE-1_logger - Producer put event message 4 in queue | Queue Size: 1
2025-01-25 16:03:38 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 processed event: 4 | Queue Size before consuming: 0
2025-01-25 16:03:38 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 put event 104 in queue | Queue Size after producing: 1
2025-01-25 16:03:38 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 4 | Queue Size: 1
2025-01-25 16:03:38 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 2 processed event: 104 | Queue Size: 0
2025-01-25 16:03:38 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 104 | Queue Size: 0
2025-01-25 16:03:39 +0100 INFO [Thread-1 (producer)] MWE-1_logger - Producer put event message 5 in queue | Queue Size: 1
2025-01-25 16:03:39 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 processed event: 5 | Queue Size before consuming: 0
2025-01-25 16:03:39 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 1 put event 105 in queue | Queue Size after producing: 1
2025-01-25 16:03:39 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 5 | Queue Size: 1
2025-01-25 16:03:39 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumer 2 processed event: 105 | Queue Size: 0
2025-01-25 16:03:39 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Event loop processed event: 105 | Queue Size: 0
2025-01-25 16:03:40 +0100 INFO [Thread-1 (producer)] MWE-1_logger - Producer put sentinel value 'None' in queue | Queue Size: 1
2025-01-25 16:03:40 +0100 INFO [Thread-2 (event_loop)] MWE-1_logger - Consumed sentinel value from queue; Terminating event loop | Queue Size: 0
2025-01-25 16:03:40 +0100 INFO [MainThread] MWE-1_logger - Producer and Consumer threads have finished execution.

Process finished with exit code 0
```

The log output reveals that while the system is multi-threaded, the event loop (`Thread-2`) handles both consumer functions sequentially, meaning there is no true parallelism in event processing. The producer (`Thread-1`) enqueues events one at a time**, and the event loop immediately dequeues and processes them, calling `consumer_1` first, then `consumer_2`. Since both consumers run within the event loop thread, if one consumer is slow, it blocks the entire event pipeline. The queue size alternates between 1 and 0, indicating that events are consumed as soon as they arrive. At the end, the producer enqueues a sentinel (`None`), which the event loop consumes, signaling termination.