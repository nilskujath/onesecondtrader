-- Security Master Database Schema
--
-- Stores instrument metadata and OHLCV market data. Prices are stored as
-- fixed-point integers (scale factor $10^9$) to avoid floating-point errors.
-- Timestamps are nanoseconds since Unix epoch.

-- Data providers. Separated from instruments because the same symbol (e.g.,
-- `ESH5`) may exist across multiple vendors with different `instrument_id`s.
CREATE TABLE publishers (
    publisher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    dataset TEXT NOT NULL,
    venue TEXT
);

-- Security/instrument metadata. The UNIQUE constraint on (`publisher_id`, `raw_symbol`)
-- allows the same symbol from different vendors while preventing duplicates.
CREATE TABLE instruments (
    instrument_id INTEGER PRIMARY KEY,
    publisher_id INTEGER NOT NULL,
    raw_symbol TEXT NOT NULL,
    instrument_class TEXT NOT NULL DEFAULT 'K',
    exchange TEXT,
    currency TEXT DEFAULT 'USD',
    min_price_increment INTEGER,
    ts_recv INTEGER NOT NULL,
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    UNIQUE(publisher_id, raw_symbol)
);

-- OHLCV bar data. The primary key order (`instrument_id`, `rtype`, `ts_event`) ensures
-- bars for the same instrument/timeframe are contiguous on disk, making range
-- queries fast. `WITHOUT ROWID` stores data directly in the primary key B-tree,
-- eliminating the indirection of a separate rowid lookup.
CREATE TABLE ohlcv (
    instrument_id INTEGER NOT NULL,
    rtype INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    open INTEGER NOT NULL,
    high INTEGER NOT NULL,
    low INTEGER NOT NULL,
    close INTEGER NOT NULL,
    volume INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, rtype, ts_event)
) WITHOUT ROWID;
