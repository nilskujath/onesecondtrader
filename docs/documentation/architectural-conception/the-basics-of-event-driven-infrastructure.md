# The Basics of Event-driven Infrastructure

## Event-driven Infrastructure

In an event-driven infrastructure, the components of the system communicate via event messages and thus have the advantage of being loosely coupled. 
Loose coupling enables components of the system to evolve independently, thereby allowing developers to work in parallel on different components of the system without interfering with each other.

In general, an event represents a state change that is of significance to the system. Within the context of trading infrastructure, events may include the reception of a new OHLC (Open, High, Low, Close) bar, the generation of a buy signal by a trading strategy, or a broker's notification indicating that a specific order has been filled.

The occurrence of an event is conveyed within the system via an event message, which is placed into a queue. The system continuously monitors this queue for newly arriving events and subsequently dispatches them to the appropriate components.

In a trading environment, for instance, upon the receipt of new market data in the form of an OHLC bar, the system creates a `BarEventMessage` and puts it into the event queue. The system then dispatches this event message to the strategy component. The strategy component updates its indicator calculations and, if a trading signal is generated, places a `SignalEventMessage` into the queue. This message is then dispatched to an execution component, responsible for sending the corresponding order to the broker. Upon order fulfillment, the execution component generates a `FillEventMessage`, which it places into the queue, and so on. 

If a risk management layer were to be introduced, it could consume a `SignalEventMessage` and, upon approval based on predefined risk parameters, generate an `OrderEventMessage`. This addition would be straightforward to implement, as the new component could be integrated without requiring modifications to existing modules. The only necessary adjustment would be in the execution component, which would now process `OrderEventMessages` instead of `SignalEventMessages`.


## A First Minimal Working Example

To gain a deeper understanding of how **OneSecondTrader** implements an event-driven architecture, we will examine a series of Minimal Working Examples (MWEs) that progressively illustrate key implementation decisions. **These MWEs are designed to isolate and clarify the fundamental architectural decisions while intentionally abstracting away the complexities that real-world trading functionality would introduce.** 

The implementation of event messages as `@dataclasses` serves to enforce structure and type safety, while at the same time reducing boilerplate code and enhancing readability.
For our first MWE, we will implement a `DummyEventMessage` with a single field, `message_id`, which is simply an integer (and unrelated to any trading functionality.

```python linenums="1"
from dataclasses import dataclass

@dataclass
class DummyEventMessage:
    message_id: int

```

We use `queue.Queue` as our preferred implementation of an event message queue to ensure thread-safe, FIFO-based event message handling, enabling decoupled communication between system components.

```python linenums="1"
import queue

event_message_queue = queue.Queue()

```

The first MWE will illustrate the queue operation mechanisms by implementing a producer function that enqueues events and a consumer function that retrieves from the queue and processes them.


``` py title="architectural-conception-MWE-1.py" linenums="1"
--8<-- "./docs/documentation-code-snippets/architectural-conception-MWE-1.py"
```

``` title="Console output architectural-conception-MWE-1.py" linenums="1"
Producer put event message 1 in queue | Queue Size: 1
Producer put event message 2 in queue | Queue Size: 2
Producer put event message 3 in queue | Queue Size: 3
Producer put event message 4 in queue | Queue Size: 4
Producer put event message 5 in queue | Queue Size: 5
Producer put sentinel value 'None' in queue | Queue Size: 6'
Consumed event message 1 from queue | Queue Size: 5
Consumed event message 2 from queue | Queue Size: 4
Consumed event message 3 from queue | Queue Size: 3
Consumed event message 4 from queue | Queue Size: 2
Consumed event message 5 from queue | Queue Size: 1
Consumed sentinel value from queue; Terminating event consumption | Queue Size: 0

Process finished with exit code 0
```

The `producer` function generates `DummyEventMessage` instances with incrementing `message_id` values, enqueues them into `event_message_queue`, and prints the queue size after each insertion. It sleeps for one second between iterations to simulate some kind of real-time event generation. After producing five events, it places a `None` sentinel value in the queue to signal termination to the consumer.

The `consumer` function continuously retrieves events from `event_message_queue`. If the retrieved event is `None`, it prints a termination message and exits the loop. Otherwise, it prints the `message_id` of the consumed event along with the current queue size, ensuring all events are processed sequentially.

In `main`, `producer` is called before `consumer`, meaning the `consumer` function will only execute after `producer` has fully completed. This is evident in the output: first, `producer` fills the queue with `DummyEventMessage` objects until its loop completes and enqueues the sentinel value `None`. Only then does `consumer` begin retrieving the messages in the order they were enqueued.

Of course, this is not the desired behavior in our trading architecture. Ideally, the consumer should be able to process events as soon as they are enqueued by the producer, rather than waiting for the producer to finish completely. To achieve this, we need to implement threading, allowing both the producer and consumer to run concurrently.


## Concurrent Processing of Events

We use Python’s `threading` module for concurrent execution, as it efficiently handles I/O-bound tasks. Additionally, some NumPy and Pandas operations can release the Global Interpreter Lock (GIL), enabling true parallel execution in specific cases. In multithreaded Python, true parallel execution is generally not possible due to the GIL. However, certain C-implemented operations in NumPy and Pandas can release the GIL, allowing multiple threads to run in parallel rather than just concurrently. Because these operations can leverage multiple CPU cores within a single process, using the `multiprocessing` module is often unnecessary for performance gains in such cases.  

To enhance log clarity in a multi-threaded environment, we will replace all `print()` statements with structured logging using Python's `logging` module. The logging configuration will be loaded from the external YAML file `logger-config-MWW-1.yaml`.

``` yaml title="logger-config-MWE-2.yaml"
--8<-- "./docs/documentation-code-snippets/logger-config-MWE-1.yaml"
```

Using `print()` in multi-threaded applications can lead to interleaved output when multiple threads write to the console simultaneously, making debugging difficult. The `logging` module mitigates this issue by handling log messages in a thread-safe manner, ensuring that messages remain intact and properly formatted. It also provides structured logging levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`), enabling effective filtering of messages based on severity. Additionally, logging supports timestamps, thread names, and output redirection to files or other storage, improving debugging and monitoring workflows. Apart from the code necessary to set up logging, the code that introduces threading is highlighted in blue


``` py title="architectural-conception-MWE-2.py" linenums="1" hl_lines="6 64 65 67 68 70 71"
--8<-- "./docs/documentation-code-snippets/architectural-conception-MWE-2.py"
```

``` title="Console output architectural-conception-MWE-2.py" linenums="1"
2025-01-24 18:34:25 +0100 INFO [MainThread] MWE-3_logger - Starting MWE-3_logger
2025-01-24 18:34:25 +0100 INFO [Thread-1 (producer)] MWE-3_logger - Producer put event message 1 in queue | Queue Size: 1
2025-01-24 18:34:25 +0100 INFO [Thread-2 (consumer)] MWE-3_logger - Consumed event message 1 from queue | Queue Size: 0
2025-01-24 18:34:26 +0100 INFO [Thread-1 (producer)] MWE-3_logger - Producer put event message 2 in queue | Queue Size: 1
2025-01-24 18:34:26 +0100 INFO [Thread-2 (consumer)] MWE-3_logger - Consumed event message 2 from queue | Queue Size: 0
2025-01-24 18:34:27 +0100 INFO [Thread-1 (producer)] MWE-3_logger - Producer put event message 3 in queue | Queue Size: 1
2025-01-24 18:34:27 +0100 INFO [Thread-2 (consumer)] MWE-3_logger - Consumed event message 3 from queue | Queue Size: 0
2025-01-24 18:34:28 +0100 INFO [Thread-1 (producer)] MWE-3_logger - Producer put event message 4 in queue | Queue Size: 1
2025-01-24 18:34:28 +0100 INFO [Thread-2 (consumer)] MWE-3_logger - Consumed event message 4 from queue | Queue Size: 0
2025-01-24 18:34:29 +0100 INFO [Thread-1 (producer)] MWE-3_logger - Producer put event message 5 in queue | Queue Size: 1
2025-01-24 18:34:29 +0100 INFO [Thread-2 (consumer)] MWE-3_logger - Consumed event message 5 from queue | Queue Size: 0
2025-01-24 18:34:30 +0100 INFO [Thread-1 (producer)] MWE-3_logger - Producer put sentinel value 'None' in queue | Queue Size: 1
2025-01-24 18:34:30 +0100 INFO [Thread-2 (consumer)] MWE-3_logger - Consumed sentinel value from queue; Terminating event consumption | Queue Size: 0
2025-01-24 18:34:30 +0100 INFO [MainThread] MWE-3_logger - Producer and Consumer thread has finished execution.

Process finished with exit code 0

```

In this MWE, threading enables the producer and consumer to run concurrently, ensuring that events are processed as soon as they are enqueued. The `threading.Thread` class is used to create separate threads for `producer` and `consumer`, which are then started with `.start()`. The `.join()` method ensures the main thread waits for both to complete before exiting. This allows real-time event handling, where the consumer retrieves and processes messages immediately as they arrive in the queue, rather than waiting for the producer to finish, as is evident from the output.