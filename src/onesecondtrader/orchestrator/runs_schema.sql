-- Runs database schema.
--
-- The schema stores metadata about trading system runs and all events that occurred during each run.
-- Events are recorded by a runs_recorder subscriber listening to the event_bus.
-- Each event type has a dedicated table with typed columns for efficient querying and charting.
--
-- | Table                      | Description                                                    |
-- |----------------------------|----------------------------------------------------------------|
-- | `runs`                     | Registry of trading system runs with metadata.                 |
-- | `bars`                     | Market data bars (BarReceived events).                         |
-- | `bars_processed`           | Processed bars with indicator values (BarProcessed events).    |
-- | `order_submissions`        | Order submission requests.                                     |
-- | `order_cancellations`      | Order cancellation requests.                                   |
-- | `order_modifications`      | Order modification requests.                                   |
-- | `orders_accepted`          | Broker order acceptance responses.                             |
-- | `orders_rejected`          | Broker order rejection responses.                              |
-- | `cancellations_accepted`   | Broker cancellation acceptance responses.                      |
-- | `cancellations_rejected`   | Broker cancellation rejection responses.                       |
-- | `modifications_accepted`   | Broker modification acceptance responses.                      |
-- | `modifications_rejected`   | Broker modification rejection responses.                       |
-- | `fills`                    | Trade execution fill events.                                   |
-- | `expirations`              | Order expiration events.                                       |



-- Registry of trading system runs.
--
-- Each row represents a single execution of the trading system, whether a backtest or live session.
-- A run is uniquely identified by `run_id` which is a UUID assigned at run creation.
-- The `config` and `metadata` fields store JSON-encoded data for flexibility.
--
-- | Field      | Type      | Constraints                                              | Description                                                                              |
-- |------------|-----------|----------------------------------------------------------|------------------------------------------------------------------------------------------|
-- | `run_id`   | `TEXT`    | `PRIMARY KEY`                                            | Unique identifier for the run (UUID string).                                             |
-- | `name`     | `TEXT`    | `NOT NULL`                                               | Human-readable name or label for the run.                                                |
-- | `ts_start` | `INTEGER` | `NOT NULL`                                               | Start time of the run as nanoseconds since the UTC Unix epoch.                           |
-- | `ts_end`   | `INTEGER` |                                                          | End time of the run as nanoseconds since the UTC Unix epoch; NULL if still in progress.  |
-- | `status`   | `TEXT`    | `NOT NULL`, `CHECK IN ('running','completed','failed','cancelled')` | Current status of the run.                                                    |
-- | `config`   | `TEXT`    |                                                          | JSON-encoded configuration used for the run.                                             |
-- | `metadata` | `TEXT`    |                                                          | JSON-encoded additional metadata about the run.                                          |
--
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ts_start INTEGER NOT NULL,
    ts_end INTEGER,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
    config TEXT,
    metadata TEXT
);


-- Stores market data bars received during a run.
--
-- Each row represents a BarReceived event captured from the event bus.
-- Bars are time-aggregated OHLCV data from a market data source or resampling process.
--
-- | Field         | Type      | Constraints      | Description                                                                              |
-- |---------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`          | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the bar record.                                      |
-- | `run_id`      | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this bar belongs to.         |
-- | `ts_event_ns` | `INTEGER` | `NOT NULL`       | Time at which the bar was observed by the system, as nanoseconds since UTC Unix epoch.   |
-- | `ts_created_ns`| `INTEGER`| `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `symbol`      | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
-- | `bar_period`  | `TEXT`    | `NOT NULL`       | Time interval represented by the bar (e.g. 'SECOND', 'MINUTE', 'HOUR', 'DAY').           |
-- | `open`        | `REAL`    | `NOT NULL`       | Opening price of the bar period.                                                         |
-- | `high`        | `REAL`    | `NOT NULL`       | Highest traded price during the bar period.                                              |
-- | `low`         | `REAL`    | `NOT NULL`       | Lowest traded price during the bar period.                                               |
-- | `close`       | `REAL`    | `NOT NULL`       | Closing price of the bar period.                                                         |
-- | `volume`      | `INTEGER` |                  | Traded volume during the bar period; may be NULL if not available.                       |
--
CREATE TABLE bars (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    bar_period TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_bars_run_symbol_ts ON bars(run_id, symbol, ts_event_ns);


-- Stores processed market data bars with computed indicator values.
--
-- Each row represents a BarProcessed event captured from the event bus.
-- This extends BarReceived by attaching indicator values derived from the bar data.
--
-- | Field         | Type      | Constraints      | Description                                                                              |
-- |---------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`          | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the bar record.                                      |
-- | `run_id`      | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this bar belongs to.         |
-- | `ts_event_ns` | `INTEGER` | `NOT NULL`       | Time at which the bar was observed by the system, as nanoseconds since UTC Unix epoch.   |
-- | `ts_created_ns`| `INTEGER`| `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `symbol`      | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
-- | `bar_period`  | `TEXT`    | `NOT NULL`       | Time interval represented by the bar (e.g. 'SECOND', 'MINUTE', 'HOUR', 'DAY').           |
-- | `open`        | `REAL`    | `NOT NULL`       | Opening price of the bar period.                                                         |
-- | `high`        | `REAL`    | `NOT NULL`       | Highest traded price during the bar period.                                              |
-- | `low`         | `REAL`    | `NOT NULL`       | Lowest traded price during the bar period.                                               |
-- | `close`       | `REAL`    | `NOT NULL`       | Closing price of the bar period.                                                         |
-- | `volume`      | `INTEGER` |                  | Traded volume during the bar period; may be NULL if not available.                       |
-- | `indicators`  | `TEXT`    | `NOT NULL`       | JSON-encoded mapping of indicator names to computed values.                              |
--
CREATE TABLE bars_processed (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    bar_period TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER,
    indicators TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_bars_processed_run_symbol_ts ON bars_processed(run_id, symbol, ts_event_ns);


-- Stores order submission requests issued by strategies.
--
-- Each row represents an OrderSubmissionRequest event captured from the event bus.
-- This records the intent to submit a new order to the broker.
--
-- | Field            | Type      | Constraints      | Description                                                                              |
-- |------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`             | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`         | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`    | `INTEGER` | `NOT NULL`       | Time at which the request was issued, as nanoseconds since UTC Unix epoch.               |
-- | `ts_created_ns`  | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `system_order_id`| `TEXT`    | `NOT NULL`       | System-assigned unique identifier for the order (UUID string).                           |
-- | `symbol`         | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
-- | `order_type`     | `TEXT`    | `NOT NULL`       | Execution constraint of the order (e.g. 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT').        |
-- | `side`           | `TEXT`    | `NOT NULL`       | Direction of the trade (e.g. 'BUY', 'SELL').                                             |
-- | `quantity`       | `REAL`    | `NOT NULL`       | Requested order quantity.                                                                |
-- | `limit_price`    | `REAL`    |                  | Limit price, if applicable to the order type.                                            |
-- | `stop_price`     | `REAL`    |                  | Stop price, if applicable to the order type.                                             |
-- | `action`         | `TEXT`    |                  | Intent of the order from the strategy's perspective (e.g. 'ENTRY', 'EXIT').              |
-- | `signal`         | `TEXT`    |                  | Optional signal name or identifier that triggered this order.                            |
--
CREATE TABLE order_submissions (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    system_order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    order_type TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    limit_price REAL,
    stop_price REAL,
    action TEXT,
    signal TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_order_submissions_run_ts ON order_submissions(run_id, ts_event_ns);
CREATE INDEX idx_order_submissions_order_id ON order_submissions(system_order_id);


-- Stores order cancellation requests issued by strategies.
--
-- Each row represents an OrderCancellationRequest event captured from the event bus.
-- This records the intent to cancel an existing order.
--
-- | Field            | Type      | Constraints      | Description                                                                              |
-- |------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`             | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`         | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`    | `INTEGER` | `NOT NULL`       | Time at which the request was issued, as nanoseconds since UTC Unix epoch.               |
-- | `ts_created_ns`  | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `system_order_id`| `TEXT`    | `NOT NULL`       | System-assigned identifier of the order to be cancelled (UUID string).                   |
-- | `symbol`         | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
--
CREATE TABLE order_cancellations (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    system_order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_order_cancellations_run_ts ON order_cancellations(run_id, ts_event_ns);
CREATE INDEX idx_order_cancellations_order_id ON order_cancellations(system_order_id);


-- Stores order modification requests issued by strategies.
--
-- Each row represents an OrderModificationRequest event captured from the event bus.
-- This records the intent to modify an existing order's parameters.
--
-- | Field            | Type      | Constraints      | Description                                                                              |
-- |------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`             | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`         | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`    | `INTEGER` | `NOT NULL`       | Time at which the request was issued, as nanoseconds since UTC Unix epoch.               |
-- | `ts_created_ns`  | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `system_order_id`| `TEXT`    | `NOT NULL`       | System-assigned identifier of the order to be modified (UUID string).                    |
-- | `symbol`         | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
-- | `quantity`       | `REAL`    |                  | Updated order quantity, if modified.                                                     |
-- | `limit_price`    | `REAL`    |                  | Updated limit price, if modified.                                                        |
-- | `stop_price`     | `REAL`    |                  | Updated stop price, if modified.                                                         |
--
CREATE TABLE order_modifications (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    system_order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL,
    limit_price REAL,
    stop_price REAL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_order_modifications_run_ts ON order_modifications(run_id, ts_event_ns);
CREATE INDEX idx_order_modifications_order_id ON order_modifications(system_order_id);


-- Stores broker order acceptance responses.
--
-- Each row represents an OrderAccepted event captured from the event bus.
-- This indicates that an order has been accepted by the broker and is active at the execution venue.
--
-- | Field               | Type      | Constraints      | Description                                                                              |
-- |---------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the acceptance was observed by the system, as nanoseconds since UTC epoch. |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the acceptance, as nanoseconds since UTC Unix epoch.     |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the accepted order (UUID string).                          |
-- | `broker_order_id`   | `TEXT`    |                  | Broker-assigned identifier of the accepted order, if reported.                           |
--
CREATE TABLE orders_accepted (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_orders_accepted_run_ts ON orders_accepted(run_id, ts_event_ns);
CREATE INDEX idx_orders_accepted_order_id ON orders_accepted(associated_order_id);


-- Stores broker order rejection responses.
--
-- Each row represents an OrderRejected event captured from the event bus.
-- This indicates that an order has been rejected by the broker.
--
-- | Field               | Type      | Constraints      | Description                                                                              |
-- |---------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the rejection was observed by the system, as nanoseconds since UTC epoch.  |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the rejection, as nanoseconds since UTC Unix epoch.      |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the rejected order (UUID string).                          |
-- | `rejection_reason`  | `TEXT`    | `NOT NULL`       | Canonical classification of the rejection cause (e.g. 'INSUFFICIENT_FUNDS').             |
-- | `rejection_message` | `TEXT`    | `NOT NULL`       | Human-readable explanation provided by the broker.                                       |
--
CREATE TABLE orders_rejected (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    rejection_message TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_orders_rejected_run_ts ON orders_rejected(run_id, ts_event_ns);
CREATE INDEX idx_orders_rejected_order_id ON orders_rejected(associated_order_id);


-- Stores broker cancellation acceptance responses.
--
-- Each row represents a CancellationAccepted event captured from the event bus.
-- This indicates that an order cancellation has been acknowledged and the order is no longer active.
--
-- | Field               | Type      | Constraints      | Description                                                                                |
-- |---------------------|-----------|------------------|--------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                            |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.         |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the cancellation was observed by the system, as nanoseconds since UTC epoch. |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.           |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the cancellation, as nanoseconds since UTC Unix epoch.     |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the cancelled order (UUID string).                           |
-- | `broker_order_id`   | `TEXT`    |                  | Broker-assigned identifier of the cancelled order, if reported.                            |
--
CREATE TABLE cancellations_accepted (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_cancellations_accepted_run_ts ON cancellations_accepted(run_id, ts_event_ns);
CREATE INDEX idx_cancellations_accepted_order_id ON cancellations_accepted(associated_order_id);


-- Stores broker cancellation rejection responses.
--
-- Each row represents a CancellationRejected event captured from the event bus.
-- This indicates that an order cancellation request has been rejected by the broker.
--
-- | Field               | Type      | Constraints      | Description                                                                              |
-- |---------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the rejection was observed by the system, as nanoseconds since UTC epoch.  |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the rejection, as nanoseconds since UTC Unix epoch.      |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the order associated with the rejected cancellation.       |
-- | `rejection_reason`  | `TEXT`    | `NOT NULL`       | Canonical classification of the cancellation rejection cause.                            |
-- | `rejection_message` | `TEXT`    | `NOT NULL`       | Human-readable explanation provided by the broker.                                       |
--
CREATE TABLE cancellations_rejected (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    rejection_message TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_cancellations_rejected_run_ts ON cancellations_rejected(run_id, ts_event_ns);
CREATE INDEX idx_cancellations_rejected_order_id ON cancellations_rejected(associated_order_id);


-- Stores broker modification acceptance responses.
--
-- Each row represents a ModificationAccepted event captured from the event bus.
-- This indicates that an order modification has been acknowledged and the updated parameters are active.
--
-- | Field               | Type      | Constraints      | Description                                                                                  |
-- |---------------------|-----------|------------------|----------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                              |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.           |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the acceptance was observed by the system, as nanoseconds since UTC epoch.     |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.             |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the modification acceptance, as nanoseconds since UTC epoch. |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the modified order (UUID string).                              |
-- | `broker_order_id`   | `TEXT`    |                  | Broker-assigned identifier of the order after modification, if reported.                     |
--
CREATE TABLE modifications_accepted (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_modifications_accepted_run_ts ON modifications_accepted(run_id, ts_event_ns);
CREATE INDEX idx_modifications_accepted_order_id ON modifications_accepted(associated_order_id);


-- Stores broker modification rejection responses.
--
-- Each row represents a ModificationRejected event captured from the event bus.
-- This indicates that an order modification request has been rejected by the broker.
--
-- | Field               | Type      | Constraints      | Description                                                                              |
-- |---------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the rejection was observed by the system, as nanoseconds since UTC epoch.  |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the rejection, as nanoseconds since UTC Unix epoch.      |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the order associated with the rejected modification.       |
-- | `rejection_reason`  | `TEXT`    | `NOT NULL`       | Canonical classification of the modification rejection cause.                            |
-- | `rejection_message` | `TEXT`    | `NOT NULL`       | Human-readable explanation provided by the broker.                                       |
--
CREATE TABLE modifications_rejected (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    rejection_message TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_modifications_rejected_run_ts ON modifications_rejected(run_id, ts_event_ns);
CREATE INDEX idx_modifications_rejected_order_id ON modifications_rejected(associated_order_id);


-- Stores trade execution fill events.
--
-- Each row represents a FillEvent captured from the event bus.
-- A fill records the execution of a quantity of an order at a specific price.
-- Multiple fills may be associated with the same order in the case of partial execution.
--
-- | Field               | Type      | Constraints      | Description                                                                              |
-- |---------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the fill was observed by the system, as nanoseconds since UTC epoch.       |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the fill, as nanoseconds since UTC Unix epoch.           |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the order associated with the fill (UUID string).          |
-- | `broker_order_id`   | `TEXT`    |                  | Broker-assigned identifier of the order, if available.                                   |
-- | `symbol`            | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
-- | `fill_id`           | `TEXT`    | `NOT NULL`       | System-assigned unique identifier of the fill event (UUID string).                       |
-- | `broker_fill_id`    | `TEXT`    |                  | Broker-assigned identifier of the execution record, if available.                        |
-- | `side`              | `TEXT`    | `NOT NULL`       | Trade direction of the executed quantity (e.g. 'BUY', 'SELL').                           |
-- | `quantity_filled`   | `REAL`    | `NOT NULL`       | Quantity executed in this fill.                                                          |
-- | `fill_price`        | `REAL`    | `NOT NULL`       | Execution price of the fill.                                                             |
-- | `commission`        | `REAL`    | `NOT NULL`       | Commission or fee associated with the fill.                                              |
-- | `exchange`          | `TEXT`    | `NOT NULL`       | Identifier of the execution venue.                                                       |
--
CREATE TABLE fills (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    symbol TEXT NOT NULL,
    fill_id TEXT NOT NULL,
    broker_fill_id TEXT,
    side TEXT NOT NULL,
    quantity_filled REAL NOT NULL,
    fill_price REAL NOT NULL,
    commission REAL NOT NULL,
    exchange TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_fills_run_ts ON fills(run_id, ts_event_ns);
CREATE INDEX idx_fills_run_symbol_ts ON fills(run_id, symbol, ts_event_ns);
CREATE INDEX idx_fills_order_id ON fills(associated_order_id);


-- Stores order expiration events.
--
-- Each row represents an OrderExpired event captured from the event bus.
-- This indicates that an order is no longer active due to expiration according to broker or venue rules
-- (e.g. time-in-force constraints).
--
-- | Field               | Type      | Constraints      | Description                                                                              |
-- |---------------------|-----------|------------------|------------------------------------------------------------------------------------------|
-- | `id`                | `INTEGER` | `PRIMARY KEY`    | Auto-incrementing surrogate key for the record.                                          |
-- | `run_id`            | `TEXT`    | `NOT NULL`, `FK` | Foreign key reference to `runs.run_id`, identifying the run this event belongs to.       |
-- | `ts_event_ns`       | `INTEGER` | `NOT NULL`       | Time at which the expiration was observed by the system, as nanoseconds since UTC epoch. |
-- | `ts_created_ns`     | `INTEGER` | `NOT NULL`       | Time at which the event object was created, as nanoseconds since UTC Unix epoch.         |
-- | `ts_broker_ns`      | `INTEGER` | `NOT NULL`       | Time reported by the broker for the expiration, as nanoseconds since UTC Unix epoch.     |
-- | `associated_order_id`| `TEXT`   | `NOT NULL`       | System-assigned identifier of the expired order (UUID string).                           |
-- | `broker_order_id`   | `TEXT`    |                  | Broker-assigned identifier of the expired order, if reported.                            |
-- | `symbol`            | `TEXT`    | `NOT NULL`       | Identifier of the traded instrument.                                                     |
--
CREATE TABLE expirations (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    ts_event_ns INTEGER NOT NULL,
    ts_created_ns INTEGER NOT NULL,
    ts_broker_ns INTEGER NOT NULL,
    associated_order_id TEXT NOT NULL,
    broker_order_id TEXT,
    symbol TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_expirations_run_ts ON expirations(run_id, ts_event_ns);
CREATE INDEX idx_expirations_order_id ON expirations(associated_order_id);


PRAGMA user_version = 1;
