-- Security Master Database Schema
--
-- Stores instrument metadata and market data using Databento's schema and terminology.
--
-- [:material-link-variant: View DataBento's Schemas and Data Formats Documentation](https://databento.com/docs/schemas-and-data-formats?historical=python&live=python&reference=python)
--
-- [:material-link-variant: View DataBento's Standards and Conventions Documentation](https://databento.com/docs/standards-and-conventions?historical=python&live=python&reference=python)
--
-- The security master database schema follows a normalized one-to-many relationship structure: each publisher
-- can have many instruments, and each instrument can have many records in each of the
-- market data tables.
--
-- Metadata Tables:
--
-- | Table | Databento Schema | Description |
-- |-------|------------------|-------------|
-- | `publishers` | - | Registry of data vendors and market data sources that provide instrument definitions and price data. Each publisher represents a distinct data feed with its own instrument identifiers. |
-- | `instruments` | `definition` | Comprehensive security master containing static reference data for all tradeable instruments including contract specifications, pricing parameters, expiration dates, and hierarchical relationships between derivatives and their underlyings. |
--
-- Market Data Tables:
--
-- | Table | Databento Schema | Description |
-- |-------|------------------|-------------|
-- | `ohlcv` | `ohlcv-1s`, `ohlcv-1m`, etc. | Aggregated Open-High-Low-Close-Volume bar/candlestick data at various time intervals (1-second, 1-minute, hourly, daily). Foundation for technical analysis and strategy backtesting. |
-- | `trades` | `trades` / `mbp-0` | Individual trade executions (prints) with price, size, and exchange-assigned trade conditions. Captures every matched order for tick-level analysis. |
-- | `quotes` | `mbp-1` | Top-of-book bid/ask quotes with the most recent trade information. Each record represents an order book event that changed the best bid or offer. |
-- | `bbo` | `bbo-1s`, `bbo-1m` | Periodically sampled best bid/offer snapshots at regular intervals. Provides compressed spread data without full tick granularity. |
-- | `mbo` | `mbo` | Full market-by-order data capturing every order book event including additions, modifications, cancellations, and executions with individual order IDs. |
-- | `mbp10` | `mbp-10` | 10-level market depth snapshots showing the top 10 price levels on both bid and ask sides. Balances depth visibility with storage efficiency. |
-- | `imbalance` | `imbalance` | Auction imbalance messages published during opening, closing, and intraday auctions showing paired and unpaired share quantities. |
-- | `statistics` | `statistics` | Exchange-published statistics including settlement prices, open interest, trading volume, and reference prices for mark-to-market calculations. |
-- | `status` | `status` | Trading status updates indicating instrument state changes such as trading halts, pre-open periods, auction states, and session boundaries. |


-- Data providers and market data vendors that supply instrument definitions and market data.
--
-- This table serves as the authoritative registry of all data sources in the system.
-- It is intentionally separated from the instruments table because the same trading
-- symbol (e.g., `ESH5` for the March 2025 E-mini S&P 500 future) may exist across
-- multiple vendors, each assigning their own unique `instrument_id`. This design
-- allows the system to track and reconcile data from multiple sources while
-- maintaining clear provenance for each instrument.
--
-- The `dataset` field uses Databento's dataset naming convention, which combines
-- the venue and feed identifier (e.g., `GLBX.MDP3` for CME Globex MDP 3.0 feed).
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `publisher_id` | INTEGER | PRIMARY KEY | Auto-incrementing unique identifier that serves as the primary key for this publisher record |
-- | `name` | TEXT | NOT NULL, UNIQUE | Human-readable name of the data provider or vendor (e.g., `Databento`, `Bloomberg`). Must be unique across all publishers |
-- | `dataset` | TEXT | NOT NULL | Databento dataset identifier that specifies the venue and feed combination (e.g., `GLBX.MDP3` for CME Globex Market Data Platform 3.0) |
-- | `venue` | TEXT | | ISO 10383 Market Identifier Code (MIC) for the trading venue (e.g., `XCME` for Chicago Mercantile Exchange). May be NULL if the publisher covers multiple venues |
CREATE TABLE publishers (
    publisher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    dataset TEXT NOT NULL,
    venue TEXT
);

-- Security and instrument metadata sourced from Databento's `InstrumentDefMsg`.
--
-- This table serves as the central repository for all tradeable instruments in the system.
-- It stores static reference data that defines each instrument's characteristics, including
-- contract specifications, pricing parameters, and temporal validity. The schema is designed
-- to accommodate a wide variety of instrument types including equities, futures, options,
-- spreads, and FX products.
--
-- Each instrument is uniquely identified within the system by `instrument_id`, but the same
-- logical instrument (e.g., ESH5) may appear multiple times if sourced from different
-- publishers. The unique constraint on (`publisher_id`, `raw_symbol`) ensures data integrity
-- while allowing multi-source reconciliation.
--
-- For derivatives, the `underlying_id` field creates a self-referential relationship that
-- links options and futures to their underlying instruments, enabling hierarchical queries
-- across the derivatives chain.
--
-- Instrument Class Codes (used in `instrument_class`):
--
-- | Code | Description |
-- |------|-------------|
-- | B | Bond |
-- | C | Call option |
-- | F | Future |
-- | K | Stock |
-- | M | Mixed spread |
-- | P | Put option |
-- | S | Future spread |
-- | T | Option spread |
-- | X | FX spot |
-- | Y | Commodity spot |
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | PRIMARY KEY | Auto-incrementing unique identifier that serves as the primary key for this instrument record within the security master |
-- | `publisher_id` | INTEGER | NOT NULL, FK | Foreign key reference to `publishers.publisher_id` identifying which data vendor provided this instrument definition |
-- | `raw_instrument_id` | INTEGER | | The native instrument identifier assigned by the publisher/exchange (e.g., Databento's internal ID). May be NULL if not provided |
-- | `raw_symbol` | TEXT | NOT NULL | The trading symbol exactly as provided by the publisher without any normalization (e.g., `ESH5` for March 2025 E-mini S&P 500) |
-- | `instrument_class` | TEXT | NOT NULL, DEFAULT 'K' | Single-character classification code indicating the instrument type. See the Instrument Class Codes table above for the complete mapping |
-- | `security_type` | TEXT | | Descriptive security type string used by the exchange (e.g., `FUT` for futures, `OPT` for options, `STK` for stocks, `MLEG` for multi-leg) |
-- | `asset` | TEXT | | The underlying asset or product code that this instrument is based on (e.g., `ES` for E-mini S&P 500, `CL` for Crude Oil, `AAPL` for Apple stock) |
-- | `cfi` | TEXT | | ISO 10962 Classification of Financial Instruments code providing standardized instrument categorization (e.g., `FXXXXX` for futures) |
-- | `exchange` | TEXT | | ISO 10383 Market Identifier Code (MIC) for the primary exchange where this instrument trades (e.g., `XCME` for CME, `XNYS` for NYSE) |
-- | `currency` | TEXT | DEFAULT 'USD' | ISO 4217 currency code for the currency in which the instrument is quoted and traded. Defaults to USD if not specified |
-- | `strike_price` | INTEGER | | For options: the strike price at which the option can be exercised. Stored as fixed-point integer with $10^9$ scale factor. NULL for non-option instruments |
-- | `strike_price_currency` | TEXT | | ISO 4217 currency code for the strike price, which may differ from the trading currency in quanto or cross-currency options |
-- | `expiration` | INTEGER | | The timestamp when the instrument expires and ceases trading, stored as nanoseconds since Unix epoch. NULL for perpetual instruments |
-- | `activation` | INTEGER | | The timestamp when the instrument becomes available for trading, stored as nanoseconds since Unix epoch. Useful for newly listed contracts |
-- | `maturity_year` | INTEGER | | The calendar year component embedded in the instrument symbol (e.g., 2025 for ESH5). Used for futures and options contract identification |
-- | `maturity_month` | INTEGER | | The calendar month component (1-12) embedded in the instrument symbol (e.g., 3 for March in ESH5). Used for contract roll calculations |
-- | `maturity_day` | INTEGER | | The calendar day component embedded in the instrument symbol, if applicable. NULL for monthly contracts, populated for weekly options |
-- | `contract_multiplier` | INTEGER | | The multiplier applied to the quoted price to determine the contract's notional value (e.g., 50 for ES futures means $50 per index point) |
-- | `unit_of_measure` | TEXT | | The unit in which the underlying commodity or asset is measured (e.g., `USD` for financial futures, `LBS` for cattle, `BBL` for oil) |
-- | `unit_of_measure_qty` | INTEGER | | The quantity of the unit of measure per contract, stored as fixed-point integer with $10^9$ scale factor (e.g., 1000 barrels for CL) |
-- | `underlying_id` | INTEGER | FK | Self-referential foreign key to `instruments.instrument_id` linking derivatives to their underlying instrument. NULL for non-derivatives |
-- | `underlying` | TEXT | | The symbol of the underlying instrument as a string. Provides a denormalized reference when the underlying may not exist in the database |
-- | `display_factor` | INTEGER | | Multiplier for converting internal prices to display prices, stored as fixed-point integer with $10^9$ scale factor. Used for price formatting |
-- | `high_limit_price` | INTEGER | | The maximum price at which the instrument can trade during the session (circuit breaker), stored as fixed-point integer with $10^9$ scale factor |
-- | `low_limit_price` | INTEGER | | The minimum price at which the instrument can trade during the session (circuit breaker), stored as fixed-point integer with $10^9$ scale factor |
-- | `min_price_increment` | INTEGER | | The minimum price movement (tick size) for the instrument, stored as fixed-point integer with $10^9$ scale factor (e.g., 0.25 for ES) |
-- | `security_group` | TEXT | | Exchange-defined grouping code that categorizes related instruments (e.g., `ES` group contains all E-mini S&P 500 contracts) |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when this instrument definition was received/captured by the data infrastructure, stored as nanoseconds since Unix epoch |
CREATE TABLE instruments (
    instrument_id INTEGER PRIMARY KEY,
    publisher_id INTEGER NOT NULL,
    raw_instrument_id INTEGER,
    raw_symbol TEXT NOT NULL,
    instrument_class TEXT NOT NULL DEFAULT 'K' CHECK(instrument_class IN ('B', 'C', 'F', 'K', 'M', 'P', 'S', 'T', 'X', 'Y')),
    security_type TEXT,
    asset TEXT,
    cfi TEXT,
    exchange TEXT,
    currency TEXT DEFAULT 'USD',
    strike_price INTEGER,
    strike_price_currency TEXT,
    expiration INTEGER,
    activation INTEGER,
    maturity_year INTEGER,
    maturity_month INTEGER CHECK(maturity_month IS NULL OR (maturity_month >= 1 AND maturity_month <= 12)),
    maturity_day INTEGER CHECK(maturity_day IS NULL OR (maturity_day >= 1 AND maturity_day <= 31)),
    contract_multiplier INTEGER,
    unit_of_measure TEXT,
    unit_of_measure_qty INTEGER,
    underlying_id INTEGER,
    underlying TEXT,
    display_factor INTEGER,
    high_limit_price INTEGER,
    low_limit_price INTEGER,
    min_price_increment INTEGER,
    security_group TEXT,
    ts_recv INTEGER NOT NULL,
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    FOREIGN KEY (underlying_id) REFERENCES instruments(instrument_id),
    UNIQUE(publisher_id, raw_symbol)
);

-- OHLCV (Open-High-Low-Close-Volume) bar/candlestick data sourced from Databento's `OhlcvMsg`.
--
-- This table stores aggregated price and volume data at various time intervals, providing
-- the foundation for technical analysis, charting, and strategy backtesting. Each row
-- represents a single bar/candle summarizing all trading activity within a specific time
-- period for a given instrument.
--
-- The table supports multiple bar durations through the `rtype` field, allowing storage of
-- 1-second, 1-minute, 1-hour, 1-day, and end-of-day bars in a single unified table. This
-- design enables efficient cross-timeframe analysis without requiring separate tables for
-- each granularity.
--
-- The composite primary key is ordered with `instrument_id` first to ensure that all bars
-- for the same instrument are physically clustered together on disk, optimizing sequential
-- reads for time-series queries and backtesting operations.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this bar belongs to. Part of the composite primary key |
-- | `rtype` | INTEGER | NOT NULL, PK | Databento record type code indicating the bar duration: 32=1-second, 33=1-minute, 34=1-hour, 35=1-day, 36=end-of-day. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp marking the beginning of the bar interval, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `open` | INTEGER | NOT NULL | The first traded price during the bar interval, stored as fixed-point integer with $10^9$ scale factor for nanosecond price precision |
-- | `high` | INTEGER | NOT NULL | The highest traded price during the bar interval, stored as fixed-point integer with $10^9$ scale factor |
-- | `low` | INTEGER | NOT NULL | The lowest traded price during the bar interval, stored as fixed-point integer with $10^9$ scale factor |
-- | `close` | INTEGER | NOT NULL | The last traded price during the bar interval, stored as fixed-point integer with $10^9$ scale factor |
-- | `volume` | INTEGER | NOT NULL | The total number of contracts or shares traded during the bar interval. Represents the sum of all trade sizes |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree,
-- eliminating the overhead of rowid indirection and reducing storage requirements for this
-- high-volume table.
CREATE TABLE ohlcv (
    instrument_id INTEGER NOT NULL,
    rtype INTEGER NOT NULL CHECK(rtype IN (32, 33, 34, 35, 36)),
    ts_event INTEGER NOT NULL,
    open INTEGER NOT NULL,
    high INTEGER NOT NULL,
    low INTEGER NOT NULL CHECK(low <= high),
    close INTEGER NOT NULL,
    volume INTEGER NOT NULL CHECK(volume >= 0),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, rtype, ts_event)
) WITHOUT ROWID;

-- Individual trade execution records sourced from Databento's `Mbp0Msg` (trades schema).
--
-- This table captures every individual trade that occurs on the exchange, providing the
-- highest granularity of execution data available. Each row represents a single match
-- between a buyer and seller, recording the exact price, quantity, and timing of the
-- transaction.
--
-- Trade data is essential for transaction cost analysis (TCA), market microstructure
-- research, VWAP/TWAP calculations, and high-frequency trading strategies. The `side`
-- field indicates which side of the order book was the aggressor (the party that crossed
-- the spread to execute immediately).
--
-- The composite primary key includes `sequence` in addition to timestamp because modern
-- exchanges can execute multiple trades within the same nanosecond, particularly during
-- periods of high volatility or when large orders are filled across multiple price levels.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument was traded. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the trade was executed by the exchange's matching engine, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the trade message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `price` | INTEGER | NOT NULL | The execution price of the trade, stored as fixed-point integer with $10^9$ scale factor for nanosecond price precision |
-- | `size` | INTEGER | NOT NULL | The number of contracts or shares that were traded in this execution |
-- | `action` | TEXT | NOT NULL | The event action type. For trades, this is always 'T' indicating a trade execution |
-- | `side` | TEXT | NOT NULL | Indicates which side was the aggressor (liquidity taker): 'A'=Ask (buyer lifted the offer), 'B'=Bid (seller hit the bid), 'N'=None/unknown |
-- | `flags` | INTEGER | NOT NULL | Bit field containing message flags including packet boundary indicators and data quality markers. See Databento documentation for bit definitions |
-- | `depth` | INTEGER | NOT NULL | The book depth level. For trades this is always 0 as trades occur at the top of book |
-- | `ts_in_delta` | INTEGER | NOT NULL | The latency between exchange transmission and capture receipt, calculated as `ts_recv - ts_exchange_send` in nanoseconds. Useful for latency analysis |
-- | `sequence` | INTEGER | NOT NULL, PK | The venue's message sequence number, used to detect gaps and ensure message ordering. Part of the composite primary key to disambiguate simultaneous trades |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree,
-- critical for this high-volume tick data table where storage efficiency is paramount.
CREATE TABLE trades (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    price INTEGER NOT NULL,
    size INTEGER NOT NULL CHECK(size > 0),
    action TEXT NOT NULL CHECK(action IN ('A', 'C', 'M', 'R', 'T', 'F', 'N')),
    side TEXT NOT NULL CHECK(side IN ('A', 'B', 'N')),
    flags INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    ts_in_delta INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event, sequence)
) WITHOUT ROWID;

-- Top-of-book quote updates with embedded trade information sourced from Databento's `Mbp1Msg` (mbp-1 schema).
--
-- This table captures every change to the best bid and offer (BBO) along with any associated
-- trade information. It provides a complete tick-by-tick view of the top of the order book,
-- enabling precise spread analysis, quote-to-trade ratio calculations, and market making
-- strategy development.
--
-- Unlike the `trades` table which only contains executions, this table records all order book
-- events at the top level including order additions, cancellations, and modifications. Each
-- row includes a snapshot of the current best bid and ask after the event, making it easy to
-- reconstruct the BBO at any point in time without maintaining order book state.
--
-- The `action` field distinguishes between different event types: new orders being added to
-- the book, existing orders being cancelled or modified, book clears (typically at session
-- boundaries), and trade executions.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this quote update belongs to. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the event occurred at the exchange's matching engine, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `price` | INTEGER | NOT NULL | The price associated with the order book event (the order being added/cancelled/modified, or the trade price), stored as fixed-point integer with $10^9$ scale factor |
-- | `size` | INTEGER | NOT NULL | The quantity associated with the order book event (the order size being added/cancelled/modified, or the trade size) |
-- | `action` | TEXT | NOT NULL | The type of order book event: 'A'=Add (new order), 'C'=Cancel, 'M'=Modify, 'R'=Clear (book reset), 'T'=Trade execution |
-- | `side` | TEXT | NOT NULL | The side of the order book affected: 'A'=Ask (sell side), 'B'=Bid (buy side), 'N'=None (for trades or unclear) |
-- | `flags` | INTEGER | NOT NULL | Bit field containing message flags including packet boundary indicators and data quality markers. See Databento documentation for bit definitions |
-- | `depth` | INTEGER | NOT NULL | The price level in the order book where this event occurred. For top-of-book data this is typically 0 (best price) |
-- | `ts_in_delta` | INTEGER | NOT NULL | The latency between exchange transmission and capture receipt, calculated as `ts_recv - ts_exchange_send` in nanoseconds |
-- | `sequence` | INTEGER | NOT NULL, PK | The venue's message sequence number for ordering and gap detection. Part of the composite primary key to disambiguate simultaneous events |
-- | `bid_px` | INTEGER | NOT NULL | The best bid price after this event, stored as fixed-point integer with $10^9$ scale factor. Represents the highest price buyers are willing to pay |
-- | `ask_px` | INTEGER | NOT NULL | The best ask price after this event, stored as fixed-point integer with $10^9$ scale factor. Represents the lowest price sellers are willing to accept |
-- | `bid_sz` | INTEGER | NOT NULL | The total quantity available at the best bid price after this event |
-- | `ask_sz` | INTEGER | NOT NULL | The total quantity available at the best ask price after this event |
-- | `bid_ct` | INTEGER | NOT NULL | The number of individual orders resting at the best bid price, useful for understanding order book fragmentation |
-- | `ask_ct` | INTEGER | NOT NULL | The number of individual orders resting at the best ask price, useful for understanding order book fragmentation |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree,
-- critical for this high-volume tick data table.
CREATE TABLE quotes (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    price INTEGER NOT NULL,
    size INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('A', 'C', 'M', 'R', 'T', 'F', 'N')),
    side TEXT NOT NULL CHECK(side IN ('A', 'B', 'N')),
    flags INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    ts_in_delta INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    bid_px INTEGER NOT NULL,
    ask_px INTEGER NOT NULL,
    bid_sz INTEGER NOT NULL CHECK(bid_sz >= 0),
    ask_sz INTEGER NOT NULL CHECK(ask_sz >= 0),
    bid_ct INTEGER NOT NULL,
    ask_ct INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event, sequence)
) WITHOUT ROWID;


-- Subsampled best bid/offer (BBO) snapshots sourced from Databento's `BboMsg` (bbo-1s, bbo-1m schemas).
--
-- This table stores periodic snapshots of the best bid and offer at regular time intervals,
-- providing a compressed view of top-of-book data that is more storage-efficient than full
-- tick data while still capturing the essential spread dynamics.
--
-- Unlike the `quotes` table which records every individual order book event, this table
-- contains only one record per time interval (1-second or 1-minute), representing the state
-- of the BBO at the end of each interval. This makes it ideal for strategies that don't
-- require tick-by-tick granularity but still need accurate spread information.
--
-- Each snapshot also includes information about the last trade that occurred during the
-- interval (if any), providing a convenient way to correlate quote and trade data without
-- joining multiple tables.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this BBO snapshot belongs to. Part of the composite primary key |
-- | `rtype` | INTEGER | NOT NULL, PK | Databento record type code indicating the snapshot interval: 195=1-second snapshots, 196=1-minute snapshots. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp marking the end of the snapshot interval, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the snapshot message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `price` | INTEGER | NOT NULL | The price of the last trade during the interval, stored as fixed-point integer with $10^9$ scale factor. Set to UNDEF_PRICE if no trade occurred |
-- | `size` | INTEGER | NOT NULL | The size of the last trade during the interval. Set to 0 if no trade occurred during the interval |
-- | `side` | TEXT | NOT NULL | The aggressor side of the last trade during the interval: 'A'=Ask (buyer lifted offer), 'B'=Bid (seller hit bid), 'N'=None (no trade or unknown) |
-- | `flags` | INTEGER | NOT NULL | Bit field containing message flags including data quality markers. See Databento documentation for bit definitions |
-- | `sequence` | INTEGER | NOT NULL | The venue's message sequence number of the last update that affected this snapshot, useful for synchronization |
-- | `bid_px` | INTEGER | NOT NULL | The best bid price at the end of the interval, stored as fixed-point integer with $10^9$ scale factor |
-- | `ask_px` | INTEGER | NOT NULL | The best ask price at the end of the interval, stored as fixed-point integer with $10^9$ scale factor |
-- | `bid_sz` | INTEGER | NOT NULL | The total quantity available at the best bid price at the end of the interval |
-- | `ask_sz` | INTEGER | NOT NULL | The total quantity available at the best ask price at the end of the interval |
-- | `bid_ct` | INTEGER | NOT NULL | The number of individual orders resting at the best bid price at the end of the interval |
-- | `ask_ct` | INTEGER | NOT NULL | The number of individual orders resting at the best ask price at the end of the interval |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree
-- for efficient storage and retrieval of time-series data.
CREATE TABLE bbo (
    instrument_id INTEGER NOT NULL,
    rtype INTEGER NOT NULL CHECK(rtype IN (195, 196)),
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    price INTEGER NOT NULL,
    size INTEGER NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('A', 'B', 'N')),
    flags INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    bid_px INTEGER NOT NULL,
    ask_px INTEGER NOT NULL,
    bid_sz INTEGER NOT NULL CHECK(bid_sz >= 0),
    ask_sz INTEGER NOT NULL CHECK(ask_sz >= 0),
    bid_ct INTEGER NOT NULL,
    ask_ct INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, rtype, ts_event)
) WITHOUT ROWID;

-- Market-by-order (MBO) event data sourced from Databento's `MboMsg` (mbo schema).
--
-- This table contains the highest fidelity order book data available, tracking every
-- individual order throughout its lifecycle from submission to completion. Each row
-- represents a single event affecting a specific order, enabling complete reconstruction
-- of the order book state at any point in time.
--
-- MBO data is essential for advanced market microstructure analysis, order flow toxicity
-- measurement, and strategies that require understanding of individual order behavior
-- rather than just aggregate price levels. It allows identification of specific trading
-- patterns such as spoofing, layering, and iceberg order detection.
--
-- The composite primary key includes `order_id` because the same timestamp and sequence
-- number can contain events for multiple orders (e.g., when a single aggressive order
-- matches against multiple resting orders).
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this order event belongs to. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the order event occurred at the exchange's matching engine, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `order_id` | INTEGER | NOT NULL, PK | The unique order identifier assigned by the exchange, used to track the order across its entire lifecycle. Part of the composite primary key |
-- | `price` | INTEGER | NOT NULL | The limit price of the order, stored as fixed-point integer with $10^9$ scale factor. For market orders, this may be set to a sentinel value |
-- | `size` | INTEGER | NOT NULL | The quantity of the order. For modify events, this is the new size; for fill events, this is the filled quantity |
-- | `flags` | INTEGER | NOT NULL | Bit field containing message flags including packet boundary indicators and data quality markers. See Databento documentation for bit definitions |
-- | `channel_id` | INTEGER | NOT NULL | Databento's internal channel identifier used for data routing and synchronization across multiple feed handlers |
-- | `action` | TEXT | NOT NULL | The type of order event: 'A'=Add (new order), 'C'=Cancel, 'M'=Modify, 'R'=Clear (book reset), 'T'=Trade, 'F'=Fill (partial or complete) |
-- | `side` | TEXT | NOT NULL | The side of the order book: 'A'=Ask (sell order), 'B'=Bid (buy order), 'N'=None (for trades or unclear) |
-- | `ts_in_delta` | INTEGER | NOT NULL | The latency between exchange transmission and capture receipt, calculated as `ts_recv - ts_exchange_send` in nanoseconds |
-- | `sequence` | INTEGER | NOT NULL, PK | The venue's message sequence number for ordering and gap detection. Part of the composite primary key |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree,
-- critical for this extremely high-volume order book data table.
CREATE TABLE mbo (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    price INTEGER NOT NULL,
    size INTEGER NOT NULL,
    flags INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('A', 'C', 'M', 'R', 'T', 'F', 'N')),
    side TEXT NOT NULL CHECK(side IN ('A', 'B', 'N')),
    ts_in_delta INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event, sequence, order_id)
) WITHOUT ROWID;

-- 10-level market depth (MBP-10) snapshots sourced from Databento's `Mbp10Msg` (mbp-10 schema).
--
-- This table provides a complete view of the top 10 price levels on both the bid and ask
-- sides of the order book at each update. It offers a balance between the full granularity
-- of MBO data and the minimal footprint of top-of-book (MBP-1) data, capturing enough depth
-- to understand market liquidity structure without the storage overhead of full order book
-- reconstruction.
--
-- Each row contains both the triggering event (the order book change that caused this
-- snapshot) and the resulting state of all 10 levels. This denormalized design eliminates
-- the need for joins when analyzing depth data and ensures that each record is self-contained.
--
-- The depth data is essential for strategies that consider liquidity beyond the best price,
-- such as iceberg detection, depth-weighted fair value calculations, and execution algorithms
-- that need to estimate market impact across multiple price levels.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this depth snapshot belongs to. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the triggering event occurred at the exchange's matching engine, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `price` | INTEGER | NOT NULL | The price associated with the triggering order book event, stored as fixed-point integer with $10^9$ scale factor |
-- | `size` | INTEGER | NOT NULL | The quantity associated with the triggering order book event |
-- | `action` | TEXT | NOT NULL | The type of event that triggered this snapshot: 'A'=Add, 'C'=Cancel, 'M'=Modify, 'R'=Clear, 'T'=Trade |
-- | `side` | TEXT | NOT NULL | The side of the triggering event: 'A'=Ask, 'B'=Bid, 'N'=None |
-- | `flags` | INTEGER | NOT NULL | Bit field containing message flags including packet boundary indicators and data quality markers |
-- | `depth` | INTEGER | NOT NULL | The price level (0-9) where the triggering event occurred in the order book |
-- | `ts_in_delta` | INTEGER | NOT NULL | The latency between exchange transmission and capture receipt, calculated as `ts_recv - ts_exchange_send` in nanoseconds |
-- | `sequence` | INTEGER | NOT NULL, PK | The venue's message sequence number for ordering and gap detection. Part of the composite primary key |
-- | `bid_px_00` - `bid_px_09` | INTEGER | NOT NULL | Bid prices at levels 0 (best) through 9 (10th best), stored as fixed-point integers with $10^9$ scale factor |
-- | `ask_px_00` - `ask_px_09` | INTEGER | NOT NULL | Ask prices at levels 0 (best) through 9 (10th best), stored as fixed-point integers with $10^9$ scale factor |
-- | `bid_sz_00` - `bid_sz_09` | INTEGER | NOT NULL | Total quantities available at each bid price level (0-9) |
-- | `ask_sz_00` - `ask_sz_09` | INTEGER | NOT NULL | Total quantities available at each ask price level (0-9) |
-- | `bid_ct_00` - `bid_ct_09` | INTEGER | NOT NULL | Number of individual orders at each bid price level (0-9), useful for fragmentation analysis |
-- | `ask_ct_00` - `ask_ct_09` | INTEGER | NOT NULL | Number of individual orders at each ask price level (0-9), useful for fragmentation analysis |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree
-- for efficient storage of this high-volume depth data.
--
-- Design Note: Price levels are stored as separate columns (denormalized) rather than
-- in a separate table to avoid expensive joins and maintain query performance for time-series
-- analysis.
CREATE TABLE mbp10 (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    price INTEGER NOT NULL,
    size INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('A', 'C', 'M', 'R', 'T', 'F', 'N')),
    side TEXT NOT NULL CHECK(side IN ('A', 'B', 'N')),
    flags INTEGER NOT NULL,
    depth INTEGER NOT NULL CHECK(depth >= 0 AND depth <= 9),
    ts_in_delta INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    bid_px_00 INTEGER NOT NULL, bid_px_01 INTEGER NOT NULL, bid_px_02 INTEGER NOT NULL,
    bid_px_03 INTEGER NOT NULL, bid_px_04 INTEGER NOT NULL, bid_px_05 INTEGER NOT NULL,
    bid_px_06 INTEGER NOT NULL, bid_px_07 INTEGER NOT NULL, bid_px_08 INTEGER NOT NULL,
    bid_px_09 INTEGER NOT NULL,
    ask_px_00 INTEGER NOT NULL, ask_px_01 INTEGER NOT NULL, ask_px_02 INTEGER NOT NULL,
    ask_px_03 INTEGER NOT NULL, ask_px_04 INTEGER NOT NULL, ask_px_05 INTEGER NOT NULL,
    ask_px_06 INTEGER NOT NULL, ask_px_07 INTEGER NOT NULL, ask_px_08 INTEGER NOT NULL,
    ask_px_09 INTEGER NOT NULL,
    bid_sz_00 INTEGER NOT NULL, bid_sz_01 INTEGER NOT NULL, bid_sz_02 INTEGER NOT NULL,
    bid_sz_03 INTEGER NOT NULL, bid_sz_04 INTEGER NOT NULL, bid_sz_05 INTEGER NOT NULL,
    bid_sz_06 INTEGER NOT NULL, bid_sz_07 INTEGER NOT NULL, bid_sz_08 INTEGER NOT NULL,
    bid_sz_09 INTEGER NOT NULL,
    ask_sz_00 INTEGER NOT NULL, ask_sz_01 INTEGER NOT NULL, ask_sz_02 INTEGER NOT NULL,
    ask_sz_03 INTEGER NOT NULL, ask_sz_04 INTEGER NOT NULL, ask_sz_05 INTEGER NOT NULL,
    ask_sz_06 INTEGER NOT NULL, ask_sz_07 INTEGER NOT NULL, ask_sz_08 INTEGER NOT NULL,
    ask_sz_09 INTEGER NOT NULL,
    bid_ct_00 INTEGER NOT NULL, bid_ct_01 INTEGER NOT NULL, bid_ct_02 INTEGER NOT NULL,
    bid_ct_03 INTEGER NOT NULL, bid_ct_04 INTEGER NOT NULL, bid_ct_05 INTEGER NOT NULL,
    bid_ct_06 INTEGER NOT NULL, bid_ct_07 INTEGER NOT NULL, bid_ct_08 INTEGER NOT NULL,
    bid_ct_09 INTEGER NOT NULL,
    ask_ct_00 INTEGER NOT NULL, ask_ct_01 INTEGER NOT NULL, ask_ct_02 INTEGER NOT NULL,
    ask_ct_03 INTEGER NOT NULL, ask_ct_04 INTEGER NOT NULL, ask_ct_05 INTEGER NOT NULL,
    ask_ct_06 INTEGER NOT NULL, ask_ct_07 INTEGER NOT NULL, ask_ct_08 INTEGER NOT NULL,
    ask_ct_09 INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event, sequence)
) WITHOUT ROWID;

-- Auction imbalance data sourced from Databento's `ImbalanceMsg` (imbalance schema).
--
-- This table captures order imbalance information disseminated by exchanges during auction
-- periods, including market open, market close, and intraday auctions (such as volatility
-- interruptions). Imbalance data is critical for strategies that participate in or trade
-- around auction events.
--
-- During an auction, the exchange periodically publishes indicative prices and the imbalance
-- between buy and sell interest. This information helps market participants decide whether
-- to add, modify, or cancel orders before the auction concludes. The `paired_qty` represents
-- orders that would execute at the reference price, while `total_imbalance_qty` shows the
-- excess on one side that would remain unfilled.
--
-- The hypothetical clearing prices (`cont_book_clr_price`, `auct_interest_clr_price`) provide
-- estimates of where the auction might clear under different matching scenarios, helping
-- traders anticipate the final auction price.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this imbalance data belongs to. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the imbalance message was generated by the exchange, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `ref_price` | INTEGER | NOT NULL | The reference price used for calculating the imbalance, typically the last traded price or a calculated indicative price, stored as fixed-point integer with $10^9$ scale factor |
-- | `auction_time` | INTEGER | NOT NULL | Reserved field for future use. May contain the scheduled auction time on some venues |
-- | `cont_book_clr_price` | INTEGER | NOT NULL | The hypothetical clearing price if both auction orders and continuous book orders were matched together, stored as fixed-point integer with $10^9$ scale factor |
-- | `auct_interest_clr_price` | INTEGER | NOT NULL | The hypothetical clearing price if only auction-specific orders were matched (excluding continuous book), stored as fixed-point integer with $10^9$ scale factor |
-- | `ssr_filling_price` | INTEGER | NOT NULL | Reserved field for short sale restriction filling price. May be used on venues with SSR rules |
-- | `ind_match_price` | INTEGER | NOT NULL | Reserved field for indicative match price. May contain venue-specific indicative pricing |
-- | `upper_collar` | INTEGER | NOT NULL | Reserved field for upper price collar. May contain the maximum allowed auction price on some venues |
-- | `lower_collar` | INTEGER | NOT NULL | Reserved field for lower price collar. May contain the minimum allowed auction price on some venues |
-- | `paired_qty` | INTEGER | NOT NULL | The quantity of shares/contracts that would be matched (paired) at the reference price if the auction were to execute now |
-- | `total_imbalance_qty` | INTEGER | NOT NULL | The total quantity that cannot be paired at the reference price, representing the excess on the imbalanced side |
-- | `market_imbalance_qty` | INTEGER | NOT NULL | Reserved field for market order imbalance. May contain the portion of imbalance from market orders on some venues |
-- | `unpaired_qty` | INTEGER | NOT NULL | Reserved field for unpaired quantity. May contain additional unpaired order information on some venues |
-- | `auction_type` | TEXT | NOT NULL | Venue-specific code indicating the type of auction (e.g., opening, closing, volatility, IPO). Interpretation varies by exchange |
-- | `side` | TEXT | NOT NULL | The side with excess quantity (the imbalanced side): 'A'=Ask (more sell interest), 'B'=Bid (more buy interest), 'N'=None (balanced) |
-- | `auction_status` | INTEGER | NOT NULL | Venue-specific status code indicating the current phase or state of the auction process |
-- | `freeze_status` | INTEGER | NOT NULL | Venue-specific code indicating whether the auction is frozen (no new orders accepted) or still accepting modifications |
-- | `num_extensions` | INTEGER | NOT NULL | The number of times the auction period has been extended, typically due to price volatility or significant order changes |
-- | `unpaired_side` | TEXT | NOT NULL | The side of any unpaired quantity. May differ from `side` on venues with complex auction mechanics |
-- | `significant_imbalance` | TEXT | NOT NULL | Venue-specific indicator flagging whether the imbalance is considered significant and may trigger special handling |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree
-- for efficient storage of auction event data.
CREATE TABLE imbalance (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    ref_price INTEGER NOT NULL,
    auction_time INTEGER NOT NULL,
    cont_book_clr_price INTEGER NOT NULL,
    auct_interest_clr_price INTEGER NOT NULL,
    ssr_filling_price INTEGER NOT NULL,
    ind_match_price INTEGER NOT NULL,
    upper_collar INTEGER NOT NULL,
    lower_collar INTEGER NOT NULL,
    paired_qty INTEGER NOT NULL,
    total_imbalance_qty INTEGER NOT NULL,
    market_imbalance_qty INTEGER NOT NULL,
    unpaired_qty INTEGER NOT NULL,
    auction_type TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('A', 'B', 'N')),
    auction_status INTEGER NOT NULL,
    freeze_status INTEGER NOT NULL,
    num_extensions INTEGER NOT NULL CHECK(num_extensions >= 0),
    unpaired_side TEXT NOT NULL CHECK(unpaired_side IN ('A', 'B', 'N')),
    significant_imbalance TEXT NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event)
) WITHOUT ROWID;

-- Venue statistics and reference data sourced from Databento's `StatMsg` (statistics schema).
--
-- This table serves as a flexible container for various statistical values disseminated by
-- exchanges and data vendors. It captures a wide range of reference data including settlement
-- prices, open interest, trading volumes, price limits, and other venue-specific metrics that
-- don't fit into the standard market data tables.
--
-- The schema uses a generic structure where the `stat_type` field identifies what kind of
-- statistic is being recorded, and either `price` or `quantity` contains the actual value
-- depending on whether the statistic is price-based or quantity-based. This design allows
-- the table to accommodate new statistic types without schema changes.
--
-- Common use cases include tracking daily settlement prices for futures (critical for
-- mark-to-market calculations), monitoring open interest changes, and capturing exchange-
-- published reference prices used for margin calculations.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this statistic belongs to. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the statistic was generated or became effective, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `ts_ref` | INTEGER | NOT NULL | The reference timestamp that the statistic applies to (e.g., the trading date for a settlement price), stored as nanoseconds since Unix epoch |
-- | `price` | INTEGER | NOT NULL | The value for price-based statistics (e.g., settlement price, high/low limits), stored as fixed-point integer with $10^9$ scale factor. Set to UNDEF_PRICE for non-price statistics |
-- | `quantity` | INTEGER | NOT NULL | The value for quantity-based statistics (e.g., open interest, volume), stored as an integer. Set to UNDEF_STAT_QUANTITY for price-based statistics |
-- | `sequence` | INTEGER | NOT NULL, PK | The venue's message sequence number for ordering. Part of the composite primary key to handle multiple statistics at the same timestamp |
-- | `ts_in_delta` | INTEGER | NOT NULL | The latency between exchange transmission and capture receipt, calculated as `ts_recv - ts_exchange_send` in nanoseconds |
-- | `stat_type` | INTEGER | NOT NULL, PK | Databento's StatType enum value identifying the type of statistic (e.g., settlement, open interest, volume). Part of the composite primary key |
-- | `channel_id` | INTEGER | NOT NULL | Databento's internal channel identifier used for data routing and synchronization |
-- | `update_action` | INTEGER | NOT NULL | Indicates whether this is a new statistic (1=Added) or a correction/deletion of a previous value (2=Deleted) |
-- | `stat_flags` | INTEGER | NOT NULL | Additional venue-specific flags that provide context for certain statistic types (e.g., preliminary vs. final settlement) |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree
-- for efficient storage and retrieval of statistical data.
CREATE TABLE statistics (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    ts_ref INTEGER NOT NULL,
    price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    ts_in_delta INTEGER NOT NULL,
    stat_type INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    update_action INTEGER NOT NULL CHECK(update_action IN (1, 2)),
    stat_flags INTEGER NOT NULL,
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event, stat_type, sequence)
) WITHOUT ROWID;

-- Trading status updates sourced from Databento's `StatusMsg` (status schema).
--
-- This table tracks changes to the trading state of instruments, including market opens,
-- closes, trading halts, and regulatory restrictions. Status information is critical for
-- trading systems to know when they can submit orders and when trading is suspended.
--
-- Trading halts can occur for various reasons including scheduled market closures, circuit
-- breakers triggered by price volatility, pending news announcements, or regulatory actions.
-- The `reason` field provides context for why the status changed, while `action` describes
-- what type of change occurred.
--
-- The boolean flags (`is_trading`, `is_quoting`, `is_short_sell_restricted`) provide a
-- quick way to check the current trading permissions without needing to interpret the
-- venue-specific action and reason codes.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `instrument_id` | INTEGER | NOT NULL, FK, PK | Foreign key reference to `instruments.instrument_id` identifying which instrument this status update applies to. Part of the composite primary key |
-- | `ts_event` | INTEGER | NOT NULL, PK | The timestamp when the status change occurred or became effective, stored as nanoseconds since Unix epoch. Part of the composite primary key |
-- | `ts_recv` | INTEGER | NOT NULL | The timestamp when the message was received by Databento's capture infrastructure, stored as nanoseconds since Unix epoch |
-- | `action` | INTEGER | NOT NULL | Venue-specific code indicating the type of status change (e.g., halt, resume, open, close). Interpretation varies by exchange |
-- | `reason` | INTEGER | NOT NULL | Venue-specific code explaining why the status changed (e.g., scheduled close, volatility halt, news pending). Interpretation varies by exchange |
-- | `trading_event` | INTEGER | NOT NULL | Venue-specific code describing the effect on trading activity (e.g., no change, trading suspended, trading resumed) |
-- | `is_trading` | TEXT | NOT NULL | TriState flag indicating whether continuous trading is currently active: 'Y'=trading allowed, 'N'=trading suspended, '~'=unknown/not applicable |
-- | `is_quoting` | TEXT | NOT NULL | TriState flag indicating whether market makers can submit quotes: 'Y'=quoting allowed, 'N'=quoting suspended, '~'=unknown. May differ from `is_trading` during pre-open |
-- | `is_short_sell_restricted` | TEXT | NOT NULL | TriState flag indicating whether short selling restrictions are in effect (e.g., SEC Rule 201 uptick rule): 'Y'=restricted, 'N'=unrestricted, '~'=unknown |
--
-- Optimization: Uses `WITHOUT ROWID` to store data directly in the primary key B-tree
-- for efficient storage of status event data.
CREATE TABLE status (
    instrument_id INTEGER NOT NULL,
    ts_event INTEGER NOT NULL,
    ts_recv INTEGER NOT NULL,
    action INTEGER NOT NULL,
    reason INTEGER NOT NULL,
    trading_event INTEGER NOT NULL,
    is_trading TEXT NOT NULL CHECK(is_trading IN ('Y', 'N', '~')),
    is_quoting TEXT NOT NULL CHECK(is_quoting IN ('Y', 'N', '~')),
    is_short_sell_restricted TEXT NOT NULL CHECK(is_short_sell_restricted IN ('Y', 'N', '~')),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, ts_event)
) WITHOUT ROWID;

-- Ticker symbol to instrument ID mappings over time sourced from Databento's symbology.json.
--
-- This table maps human-readable ticker symbols (e.g., "AAPL", "MSFT") to the numeric
-- instrument IDs used in market data records. The mapping is time-bounded because
-- instrument IDs can change over time due to:
--
-- - Publisher remapping: Some venues reassign numeric IDs periodically (even daily)
-- - Delistings and relistings: When a symbol is delisted and later relisted, it may
--   receive a new instrument ID
-- - Corporate actions: Mergers, spin-offs, and ticker changes can result in new IDs
--
-- Each row represents a single mapping that is valid for a specific date range. To look
-- up the symbol for a given instrument_id at a specific point in time, query with:
--
--     SELECT symbol FROM symbology
--     WHERE instrument_id = ? AND date(?, 'unixepoch') BETWEEN start_date AND end_date
--
-- Note: The instrument_id in this table corresponds to the raw_instrument_id in the
-- instruments table (the publisher's native ID), not the auto-generated instrument_id
-- primary key.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `symbol` | TEXT | NOT NULL, PK | The ticker symbol as provided by the publisher (e.g., "AAPL", "ESH5"). Part of the composite primary key |
-- | `instrument_id` | INTEGER | NOT NULL, PK | The numeric instrument ID assigned by the publisher. Part of the composite primary key |
-- | `start_date` | TEXT | NOT NULL, PK | The first date (inclusive) when this mapping is valid, in YYYY-MM-DD format. Part of the composite primary key |
-- | `end_date` | TEXT | NOT NULL | The last date (inclusive) when this mapping is valid, in YYYY-MM-DD format |
CREATE TABLE symbology (
    symbol TEXT NOT NULL,
    instrument_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    PRIMARY KEY (symbol, instrument_id, start_date)
);

-- Precomputed database metadata for fast dashboard queries.
--
-- This table stores aggregate statistics about the database contents that would
-- otherwise require expensive COUNT(*) queries on large tables. Stats are updated
-- after each data ingestion operation.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `key` | TEXT | PRIMARY KEY | The name of the statistic (e.g., 'symbol_count', 'ohlcv_record_count') |
-- | `value` | TEXT | NOT NULL | The value of the statistic, stored as text for flexibility |
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Precomputed per-symbol coverage statistics for fast search queries.
--
-- This table stores aggregate statistics for each symbol/rtype combination,
-- eliminating the need for expensive JOIN and GROUP BY queries on the large
-- ohlcv table during symbol search. Stats are updated after each data ingestion.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `symbol` | TEXT | NOT NULL, PK | The ticker symbol |
-- | `rtype` | INTEGER | NOT NULL, PK | The bar duration type (32=1s, 33=1m, 34=1h, 35=1d) |
-- | `min_ts` | INTEGER | NOT NULL | The earliest timestamp for this symbol/rtype |
-- | `max_ts` | INTEGER | NOT NULL | The latest timestamp for this symbol/rtype |
-- | `record_count` | INTEGER | NOT NULL | Total number of records for this symbol/rtype |
CREATE TABLE symbol_coverage (
    symbol TEXT NOT NULL,
    rtype INTEGER NOT NULL,
    min_ts INTEGER NOT NULL,
    max_ts INTEGER NOT NULL,
    record_count INTEGER NOT NULL,
    PRIMARY KEY (symbol, rtype)
);

-- User-defined symbol presets for quick selection in the dashboard.
--
-- | Field | Type | Constraints | Description |
-- |-------|------|-------------|-------------|
-- | `name` | TEXT | PRIMARY KEY | Unique name for the preset (e.g., 'Tech Stocks', 'My Watchlist') |
-- | `symbols` | TEXT | NOT NULL | JSON array of symbol strings (e.g., '["AAPL", "GOOGL", "MSFT"]') |
CREATE TABLE symbol_presets (
    name TEXT PRIMARY KEY,
    symbols TEXT NOT NULL
);
