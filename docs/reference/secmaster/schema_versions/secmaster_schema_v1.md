# Secmaster Schema V1

Security master database schema.

The schema is designed for Databento-native ingestion via DBN files, while remaining compatible with other sources.
Instrument identity is modeled per publisher namespace and supports either numeric upstream identifiers or symbols.
Contract specifications and other static reference metadata are intentionally out of scope for this schema and should be stored separately if ingested.

The schema is explicitly ingestion-safe in the sense that:

1) publishers are keyed by (vendor, dataset) rather than vendor alone, allowing multiple feeds per vendor;
2) symbology admits multiple mappings sharing the same start date by including the resolved instrument identifier
in the primary key, preventing accidental overwrites during bulk ingestion.

| Table         | Description |
|---------------|-------------|
| `publishers`  | Registry of vendor+dataset namespaces used for market data and instrument ingestion. |
| `instruments` | Registry of instruments observed from ingestion within a publisher namespace. |
| `ohlcv`       | Aggregated OHLCV bar data keyed by instrument, bar duration (`rtype`), and event timestamp (`ts_event`). |
| `symbology`   | Time-bounded mappings from publisher-native symbols to publisher-native instrument identifiers. |


## Publishers

Registry of all data sources used for market data and instrument ingestion.

Each row represents a distinct data product (feed) within a vendor namespace.
A publisher record is uniquely identified by the pair (`name`, `dataset`), not by `name` alone.
This allows a single vendor (e.g. Databento) to appear multiple times, once per concrete dataset/feed
(e.g. `GLBX.MDP3`, `XNAS.ITCH`).

A publisher establishes the provenance of instrument definitions and price data and provides the context
in which raw symbols and native instrument identifiers are interpreted.

| Field           | Type      | Constraints             | Description                                                                                                                                                                     |
|-----------------|-----------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `publisher_id`  | `INTEGER` | `PRIMARY KEY`           | Internal surrogate key uniquely identifying a publisher record within the system.                                                                                               |
| `name`          | `TEXT`    | `NOT NULL`              | Human-readable vendor identifier for the data source (e.g. `databento`, `yfinance`).                                                                                            |
| `dataset`       | `TEXT`    | `NOT NULL`              | Identifier of the concrete data product or feed through which data is sourced; uses Databento dataset names (e.g. `GLBX.MDP3`) for Databento ingestion and internal identifiers for other sources (e.g. `YFINANCE`). |
| `venue`         | `TEXT`    |                         | Optional ISO 10383 Market Identifier Code (MIC) describing the primary trading venue; may be NULL for aggregated or multi-venue sources.                                        |

**Table constraints**

* `UNIQUE(name, dataset)` ensures that each vendor+feed combination is represented at most once.

**Examples**

Databento CME Globex feed:

*  `name`    = `'databento'`
*  `dataset` = `'GLBX.MDP3'`
*  `venue`   = `XCME`

Databento NASDAQ TotalView feed:

*  `name`    = `'databento'`
*  `dataset` = `'XNAS.ITCH'`
*  `venue`   = `XNAS`

Yahoo Finance equity data:

*  `name`    = `'yfinance'`
*  `dataset` = `'YFINANCE'`
*  `venue`   = `NULL`



```sql
CREATE TABLE publishers (
    publisher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    dataset TEXT NOT NULL,
    venue TEXT,
    UNIQUE (name, dataset)
);
```

## Instruments

Registry of instruments observed through market data ingestion.

Each row represents an instrument identity within a publisher namespace.
Instruments may be identified by a publisher-native numeric identifier, a symbol identifier, or both.
Databento ingestion uses `source_instrument_id` as the primary identifier and may optionally store a symbol from symbology.
Symbol-first sources such as yfinance use `symbol` as the primary identifier and typically leave `source_instrument_id` to be `NULL`.

The table does not store contract specifications or other reference metadata.
Such metadata must be stored separately when available.

| Field                  | Type      | Constraints      | Description                                                                                                                                                  |
|------------------------|-----------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `instrument_id`        | `INTEGER` | `PRIMARY KEY`    | Internal surrogate key identifying an instrument record within the system.                                                                                   |
| `publisher_ref`        | `INTEGER` | `NOT NULL`, `FK` | Foreign key reference to `publishers.publisher_id`, defining the publisher namespace in which this instrument identity is valid.                             |
| `source_instrument_id` | `INTEGER` |                  | Publisher-native numeric instrument identifier as provided by the upstream data source (e.g. Databento instrument_id); may be `NULL` for symbol-only sources. |
| `symbol`               | `TEXT`    |                  | Publisher-native symbol string identifying the instrument (e.g. raw symbol, ticker); may be NULL when numeric identifiers are used.                          |
| `symbol_type`          | `TEXT`    |                  | Identifier describing the symbol scheme or resolution type used by the publisher (e.g. `raw_symbol`, `continuous`, `ticker`).                                |

Each instrument must be identifiable by at least one of `source_instrument_id` or `symbol`.
Uniqueness constraints ensure that instrument identities do not collide within a publisher namespace.
The table intentionally excludes contract specifications and other reference metadata, which must be stored separately when available.



```sql
CREATE TABLE instruments (
    instrument_id INTEGER PRIMARY KEY,
    publisher_ref INTEGER NOT NULL,
    source_instrument_id INTEGER,
    symbol TEXT,
	symbol_type TEXT,
    FOREIGN KEY (publisher_ref) REFERENCES publishers(publisher_id),
    CHECK (
        source_instrument_id IS NOT NULL
        OR symbol IS NOT NULL
    ),
	CHECK (symbol IS NULL OR symbol_type IS NOT NULL),
    UNIQUE (publisher_ref, source_instrument_id),
    UNIQUE (publisher_ref, symbol, symbol_type)
);
```

## OHLCV

Stores aggregated OHLCV bars for instruments at multiple time resolutions.

| Field           | Type      | Constraints                                 | Description                                                                                                              |
|-----------------|-----------|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `instrument_id` | `INTEGER` | `NOT NULL`, `FK`                            | Foreign key reference to `instruments.instrument_id`, identifying the instrument to which this bar belongs.              |
| `rtype`         | `INTEGER` | `NOT NULL`, `CHECK IN (32, 33, 34, 35, 36)` | Record type code encoding the bar duration using Databento OHLCV conventions (e.g. `32`=1s, `33`=1m, `34`=1h, `35`=1d). |
| `ts_event`      | `INTEGER` | `NOT NULL`                                  | Event timestamp of the bar as provided by the upstream source, stored as nanoseconds since the UTC Unix epoch.           |
| `open`          | `INTEGER` | `NOT NULL`                                  | Opening price of the bar interval, stored as a fixed-point integer using the upstream price scaling convention.          |
| `high`          | `INTEGER` | `NOT NULL`                                  | Highest traded price during the bar interval, stored as a fixed-point integer.                                           |
| `low`           | `INTEGER` | `NOT NULL`, `CHECK(low <= high)`            | Lowest traded price during the bar interval, stored as a fixed-point integer.                                            |
| `close`         | `INTEGER` | `NOT NULL`                                  | Closing price of the bar interval, stored as a fixed-point integer.                                                      |
| `volume`        | `INTEGER` | `NOT NULL`, `CHECK(volume >= 0)`            | Total traded volume during the bar interval.                                                                             |

The composite primary key enforces uniqueness per instrument, bar duration, and event timestamp.
Integrity constraints ensure basic OHLC consistency and prevent invalid price relationships from being stored.
The table uses `WITHOUT ROWID` to store rows directly in the primary key B-tree for reduced storage overhead and faster lookups.



```sql
CREATE TABLE ohlcv (
    instrument_id INTEGER NOT NULL,
    rtype INTEGER NOT NULL CHECK(rtype IN (32, 33, 34, 35, 36)),
    ts_event INTEGER NOT NULL,
    open INTEGER NOT NULL,
    high INTEGER NOT NULL,
    low INTEGER NOT NULL,
    close INTEGER NOT NULL,
    volume INTEGER NOT NULL CHECK(volume >= 0),
    FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    PRIMARY KEY (instrument_id, rtype, ts_event),
    CHECK(low <= high),
    CHECK(open BETWEEN low AND high),
    CHECK(close BETWEEN low AND high)
) WITHOUT ROWID;
```

## Symbology

Stores time-bounded mappings from publisher-native symbols to publisher-native instrument identifiers.

The table captures symbol resolution rules as provided by upstream data sources and must be interpreted within the
namespace of a specific publisher.

The schema permits multiple mappings to share the same `start_date` for a given (`publisher_ref`, `symbol`, `symbol_type`)
by including `source_instrument_id` in the primary key. This prevents accidental overwrite when upstream symbology exports
contain same-day corrections, backfills, or parallel resolution segments.

| Field                  | Type      | Constraints      | Description                                                                                                                |
|------------------------|-----------|------------------|----------------------------------------------------------------------------------------------------------------------------|
| `publisher_ref`        | `INTEGER` | `NOT NULL`, `FK` | Foreign key reference to `publishers.publisher_id`, defining the publisher namespace in which the symbol mapping is valid. |
| `symbol`               | `TEXT`    | `NOT NULL`       | Publisher-native symbol string as provided by the upstream source (e.g. raw symbol, continuous symbol).                    |
| `symbol_type`          | `TEXT`    | `NOT NULL`       | Identifier describing the symbol scheme or resolution type used by the publisher (e.g. `raw_symbol`, `continuous`).        |
| `source_instrument_id` | `INTEGER` | `NOT NULL`       | Publisher-native numeric instrument identifier corresponding to the resolved symbol.                                       |
| `start_date`           | `TEXT`    | `NOT NULL`       | First calendar date (inclusive) on which this symbol-to-instrument mapping is valid, stored in YYYY-MM-DD format.          |
| `end_date`             | `TEXT`    | `NOT NULL`       | First calendar date (exclusive) after which this symbol-to-instrument mapping is no longer valid, stored in YYYY-MM-DD format. |

The primary key enforces uniqueness of mappings at the granularity of a resolved instrument.
Date bounds are interpreted as half-open intervals [start_date, end_date).



```sql
CREATE TABLE symbology (
    publisher_ref INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    source_instrument_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    FOREIGN KEY (publisher_ref) REFERENCES publishers(publisher_id),
    FOREIGN KEY (publisher_ref, source_instrument_id)
        REFERENCES instruments(publisher_ref, source_instrument_id),
    PRIMARY KEY (publisher_ref, symbol, symbol_type, start_date, source_instrument_id),
    CHECK (start_date <= end_date)
);
```

## Idx_symbology_symbol

```sql
CREATE INDEX idx_symbology_symbol ON symbology(symbol);
```

## Symbol_coverage

```sql
CREATE TABLE symbol_coverage (
    publisher_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    rtype INTEGER NOT NULL,
    min_ts INTEGER NOT NULL,
    max_ts INTEGER NOT NULL,
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    PRIMARY KEY (publisher_id, symbol, rtype)
);
```
