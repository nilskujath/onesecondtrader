-- Run Recorder Database Schema (runs.db)
--
-- A single database file storing all strategy runs. This schema captures the
-- complete lifecycle of each run including metadata, processed bars with
-- indicator values, order requests, broker responses, and fill executions.
--
-- The database uses WAL (Write-Ahead Logging) mode for concurrent read/write
-- access, allowing the dashboard to read while a strategy is actively writing.
--
-- All tables reference `run_id` to associate records with their parent run.
-- This enables efficient querying within a run and across multiple runs.
--
-- Tables:
--
-- | Table | Description |
-- |-------|-------------|
-- | `runs` | Run metadata including strategy name, symbols, status, and timestamps. |
-- | `bars` | Processed OHLCV bars with computed indicator values. |
-- | `order_requests` | Order requests from strategy to broker: submissions, modifications, cancellations. |
-- | `order_responses` | Broker responses: acceptances, rejections, expirations. |
-- | `fills` | Executed fills with price, quantity, commission, and exchange information. |


-- Run metadata capturing the configuration and status of strategy executions.
--
-- Each row represents a single strategy run. The table stores the initial
-- configuration used to start the run as well as runtime status that is updated
-- when the run completes or is interrupted.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `run_id` | TEXT | PRIMARY KEY | Unique identifier for this run, typically formatted as `YYYY-MM-DD_HH-MM-SS_StrategyName` |
-- | `strategy` | TEXT | NOT NULL | Name of the strategy class that was executed |
-- | `symbols` | TEXT | | JSON array of symbols traded during this run (e.g., `["AAPL", "MSFT"]`) |
-- | `bar_period` | TEXT | | Bar period used by the strategy (e.g., `SECOND`, `MINUTE`, `HOUR`, `DAY`) |
-- | `mode` | TEXT | NOT NULL | Execution mode: `backtest` for historical simulation or `live` for real-time trading |
-- | `status` | TEXT | NOT NULL | Current run status: `running`, `completed`, or `interrupted` |
-- | `created_at` | TEXT | NOT NULL | ISO 8601 timestamp when the run was started |
-- | `completed_at` | TEXT | | ISO 8601 timestamp when the run finished (NULL if still running or interrupted) |

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    strategy TEXT NOT NULL,
    symbols TEXT,
    bar_period TEXT,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);


-- Processed OHLCV bars with indicator values computed by the strategy.
--
-- Each row represents a single bar that was processed by the strategy. The bar
-- data comes from `BarProcessed` events which include both the raw OHLCV values
-- and any indicator values computed by the strategy's indicators.
--
-- Indicator values are stored as a JSON object where keys are indicator names
-- prefixed with their plot position (e.g., `{"00_SMA_20": 150.5, "01_RSI": 65.2}`).
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `id` | INTEGER | PRIMARY KEY | Auto-incrementing unique identifier for this bar record |
-- | `run_id` | TEXT | NOT NULL, FK | Reference to the parent run in the `runs` table |
-- | `ts_event` | TEXT | NOT NULL | ISO 8601 timestamp of the bar's closing time |
-- | `symbol` | TEXT | NOT NULL | Trading symbol (e.g., `AAPL`, `ESH5`) |
-- | `bar_period` | TEXT | NOT NULL | Bar aggregation period: `SECOND`, `MINUTE`, `HOUR`, or `DAY` |
-- | `open` | REAL | NOT NULL | Opening price of the bar |
-- | `high` | REAL | NOT NULL | Highest price during the bar |
-- | `low` | REAL | NOT NULL | Lowest price during the bar |
-- | `close` | REAL | NOT NULL | Closing price of the bar |
-- | `volume` | INTEGER | | Trading volume during the bar (NULL if not available) |
-- | `indicators` | TEXT | | JSON object of indicator name-value pairs computed for this bar |

CREATE TABLE IF NOT EXISTS bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    ts_event TEXT NOT NULL,
    symbol TEXT NOT NULL,
    bar_period TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER,
    indicators TEXT
);


-- Order requests sent from the strategy to the broker.
--
-- Each row represents a request event initiated by the strategy. This includes
-- new order submissions, modifications to existing orders, and cancellation
-- requests. These are the "outbound" events from the strategy's perspective.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `id` | INTEGER | PRIMARY KEY | Auto-incrementing unique identifier for this request record |
-- | `run_id` | TEXT | NOT NULL, FK | Reference to the parent run in the `runs` table |
-- | `ts_event` | TEXT | NOT NULL | ISO 8601 timestamp when the request was sent |
-- | `request_type` | TEXT | NOT NULL | Request type: `submission`, `modification`, or `cancellation` |
-- | `order_id` | TEXT | NOT NULL | System-assigned UUID for this order |
-- | `symbol` | TEXT | NOT NULL | Trading symbol |
-- | `order_type` | TEXT | | Order type: `MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT` (submission only) |
-- | `side` | TEXT | | Order side: `BUY` or `SELL` (submission only) |
-- | `quantity` | REAL | | Order quantity (submission and modification) |
-- | `limit_price` | REAL | | Limit price for LIMIT and STOP_LIMIT orders |
-- | `stop_price` | REAL | | Stop trigger price for STOP and STOP_LIMIT orders |
-- | `action` | TEXT | | Strategy action type: `ENTRY`, `EXIT`, `ADD`, `REDUCE`, `REVERSE` |
-- | `signal` | TEXT | | Strategy-defined signal label identifying which condition triggered the order |

CREATE TABLE IF NOT EXISTS order_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    ts_event TEXT NOT NULL,
    request_type TEXT NOT NULL,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    order_type TEXT,
    side TEXT,
    quantity REAL,
    limit_price REAL,
    stop_price REAL,
    action TEXT,
    signal TEXT
);


-- Broker responses to order requests.
--
-- Each row represents a response event from the broker. This includes acceptances,
-- rejections, and expirations. These are the "inbound" events from the broker's
-- perspective. Fills are stored separately in the `fills` table.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `id` | INTEGER | PRIMARY KEY | Auto-incrementing unique identifier for this response record |
-- | `run_id` | TEXT | NOT NULL, FK | Reference to the parent run in the `runs` table |
-- | `ts_event` | TEXT | NOT NULL | ISO 8601 timestamp when the response was received |
-- | `ts_broker` | TEXT | NOT NULL | ISO 8601 timestamp when the broker processed the request |
-- | `response_type` | TEXT | NOT NULL | Response type: `submission_accepted`, `submission_rejected`, `modification_accepted`, `modification_rejected`, `cancellation_accepted`, `cancellation_rejected`, `expired` |
-- | `order_id` | TEXT | NOT NULL | System-assigned UUID of the associated order |
-- | `broker_order_id` | TEXT | | Broker-assigned order identifier (on acceptance) |
-- | `reason` | TEXT | | Rejection reason (on rejection) |

CREATE TABLE IF NOT EXISTS order_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    ts_event TEXT NOT NULL,
    ts_broker TEXT NOT NULL,
    response_type TEXT NOT NULL,
    order_id TEXT NOT NULL,
    broker_order_id TEXT,
    reason TEXT
);


-- Fill executions recording completed trades.
--
-- Each row represents a single fill event where an order was partially or fully
-- executed. An order may have multiple fills if it is executed in parts. Fills
-- are separated from other broker responses due to their distinct structure and
-- importance for P&L calculations.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `id` | INTEGER | PRIMARY KEY | Auto-incrementing unique identifier for this fill record |
-- | `run_id` | TEXT | NOT NULL, FK | Reference to the parent run in the `runs` table |
-- | `ts_event` | TEXT | NOT NULL | ISO 8601 timestamp when the fill event was received |
-- | `ts_broker` | TEXT | NOT NULL | ISO 8601 timestamp when the broker executed the fill |
-- | `fill_id` | TEXT | NOT NULL | System-assigned UUID for this specific fill |
-- | `order_id` | TEXT | NOT NULL | System-assigned UUID of the order that was filled |
-- | `broker_fill_id` | TEXT | | Broker-assigned fill identifier |
-- | `symbol` | TEXT | NOT NULL | Trading symbol that was filled |
-- | `side` | TEXT | NOT NULL | Fill side: `BUY` or `SELL` |
-- | `quantity` | REAL | NOT NULL | Number of units filled |
-- | `price` | REAL | NOT NULL | Execution price |
-- | `commission` | REAL | | Commission charged for this fill |
-- | `exchange` | TEXT | | Exchange or venue where the fill occurred |

CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    ts_event TEXT NOT NULL,
    ts_broker TEXT NOT NULL,
    fill_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    broker_fill_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    commission REAL,
    exchange TEXT
);


-- Indexes for efficient querying by run, timestamp, and order relationships.

CREATE INDEX IF NOT EXISTS idx_bars_run_id ON bars(run_id);
CREATE INDEX IF NOT EXISTS idx_bars_run_ts ON bars(run_id, ts_event);
CREATE INDEX IF NOT EXISTS idx_bars_run_symbol ON bars(run_id, symbol);
CREATE INDEX IF NOT EXISTS idx_order_requests_run_id ON order_requests(run_id);
CREATE INDEX IF NOT EXISTS idx_order_requests_run_ts ON order_requests(run_id, ts_event);
CREATE INDEX IF NOT EXISTS idx_order_requests_order_id ON order_requests(order_id);
CREATE INDEX IF NOT EXISTS idx_order_responses_run_id ON order_responses(run_id);
CREATE INDEX IF NOT EXISTS idx_order_responses_run_ts ON order_responses(run_id, ts_event);
CREATE INDEX IF NOT EXISTS idx_order_responses_order_id ON order_responses(order_id);
CREATE INDEX IF NOT EXISTS idx_fills_run_id ON fills(run_id);
CREATE INDEX IF NOT EXISTS idx_fills_run_ts ON fills(run_id, ts_event);
CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills(order_id);
