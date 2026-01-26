# SQL Primer

SQL (Structured Query Language) is the language used to interact with databases.
This page covers the SQL concepts needed to understand the schema of the securities master database.

## Tables

A table is a collection of related data organized into rows and columns.
A table is created by using the `CREATE TABLE` statement:

```sql
CREATE TABLE publishers (
    publisher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    dataset TEXT NOT NULL,
    venue TEXT
);
```

This creates a table called `publishers` with four columns.
Every column has a data type that specifies what kind of values it can hold.
`NULL` is a special value meaning "no data" or "unknown".
`NOT NULL` is a constraint that specifies that a column must not contain NULL values.

## Primary Keys

A primary key is a column (or combination of columns) that uniquely identifies each row in a table. No two rows can have the same primary key value, and the primary key cannot be NULL.

```sql
publisher_id INTEGER PRIMARY KEY
```

When a column is declared as `INTEGER PRIMARY KEY` in SQLite, it becomes an auto-incrementing identifier—if no value is specified during insertion, SQLite automatically assigns the next available number. Primary keys guarantee each row can be individually identified, and SQLite automatically creates an efficient lookup structure for primary key columns.

## Foreign Keys

A foreign key is a column that references the primary key of another table, creating a relationship between the tables.

```sql
CREATE TABLE instruments (
    instrument_id INTEGER PRIMARY KEY,
    publisher_id INTEGER NOT NULL,
    ...
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id)
);
```

This declaration means the `publisher_id` column in the `instruments` table must contain a value that exists in the `publisher_id` column of the `publishers` table. Foreign keys enforce referential integrity—preventing the creation of an instrument that references a non-existent publisher, or the deletion of a publisher that still has instruments associated with it.

## Constraints

Constraints are rules that limit what data can be stored in a column. `NOT NULL` means the column must have a value. `UNIQUE` means no two rows can have the same value in this column. `DEFAULT` specifies a fallback value if none is provided during insertion. Constraints can also span multiple columns:

```sql
UNIQUE(publisher_id, raw_symbol)
```

This means the *combination* of publisher_id and raw_symbol must be unique. The same symbol (like 'ESH5') can appear multiple times in the table, as long as each occurrence is from a different publisher.

## Indexes

An index is a data structure that speeds up searches on specific columns—like the index at the back of a book that allows jumping directly to a topic instead of reading every page.

```sql
CREATE INDEX idx_instruments_symbol ON instruments(raw_symbol);
```

This creates an index named `idx_instruments_symbol` on the `raw_symbol` column of the `instruments` table. When searching for instruments by symbol, the database can find them quickly without scanning every row.

## Normalization

The schema uses separate `publishers` and `instruments` tables rather than storing publisher names directly in each instrument row. This design principle is called normalization. Without it, publisher information would be duplicated in every row, wasting storage, creating update anomalies (changing a dataset name requires updating every row), and risking inconsistency from typos. With normalization, publisher information is stored once, and each instrument stores only a reference (the publisher_id) to the publisher.

## One-to-Many Relationships

The relationship between publishers and instruments is called one-to-many: one publisher can have many instruments, but each instrument belongs to exactly one publisher. This is implemented through the foreign key: `instruments.publisher_id` references `publishers.publisher_id`. Similarly, the relationship between instruments and OHLCV bars is one-to-many: one instrument can have millions of bars, but each bar belongs to exactly one instrument.

```
publishers (1) ──────< instruments (many) ──────< ohlcv (many)
```

## Composite Primary Keys

Sometimes a single column isn't enough to uniquely identify a row. The `ohlcv` table uses a composite primary key—a primary key made up of multiple columns:

```sql
PRIMARY KEY (instrument_id, rtype, ts_event)
```

This means the *combination* of these three values must be unique—multiple bars for the same instrument with different timestamps, multiple bars at the same timestamp for different instruments, and multiple bar types for the same instrument and time are all allowed, but two rows with the same instrument_id, rtype, AND ts_event would be a duplicate bar.

## B-trees

A B-tree (balanced tree) is the data structure that databases use to organize data for fast lookups. It works like searching a phone book—instead of reading every name from page 1, the search opens to the middle, determines which half contains the target, and repeats until the entry is found. Each step eliminates half the remaining possibilities. A B-tree organizes data into a tree structure with a root node at the top, branch nodes that guide the search, and leaf nodes containing the actual data. Finding one row among a billion takes the same number of steps as finding one among a thousand.

## How Indexes Work

When a table is created with a primary key, SQLite automatically creates a B-tree index for that key. Additional indexes created with `CREATE INDEX` are additional B-trees. Each index stores the indexed column value(s) and a pointer to the full row. When searching by an indexed column, the database searches the index B-tree (fast—logarithmic time) and follows the pointer to retrieve the full row. Without an index, the database must perform a full table scan—reading every row to find matches.

## The Leftmost Prefix Rule

For composite indexes (indexes on multiple columns), the index can only be used efficiently if the query filters on a leftmost prefix of the indexed columns. The `ohlcv` table has a primary key of `(instrument_id, rtype, ts_event)`, creating a B-tree sorted first by instrument_id, then by rtype within each instrument, then by ts_event within each rtype. Queries filtering on `instrument_id` alone, or `instrument_id AND rtype`, or all three columns can use this index efficiently. However, queries filtering only on `ts_event` or only on `rtype` cannot use the primary key index because they skip the leftmost column(s)—the B-tree is sorted by instrument_id first. This is why the schema includes a separate index on `ts_event`:

```sql
CREATE INDEX idx_ohlcv_ts ON ohlcv(ts_event);
```

This creates a second B-tree sorted by timestamp, enabling fast time-based queries across all instruments.

## WITHOUT ROWID Tables

In a normal SQLite table, data is stored in a B-tree organized by an internal rowid (a hidden auto-incrementing integer). If a primary key is defined, SQLite creates a *second* B-tree for that key, which stores the primary key values and their corresponding rowids. Looking up a row by primary key requires searching the primary key B-tree to find the rowid, then searching the rowid B-tree to find the actual data. This double lookup is fine for most tables, but for a table with billions of rows accessed primarily by its composite key (like `ohlcv`), it's wasteful.

The `WITHOUT ROWID` optimization changes this:

```sql
CREATE TABLE ohlcv (
    ...
    PRIMARY KEY (instrument_id, rtype, ts_event)
) WITHOUT ROWID;
```

Now the table data is stored directly in the primary key B-tree. There's no separate rowid B-tree, no double lookup—resulting in ~50% storage reduction (primary key values aren't stored twice), faster lookups (one B-tree search instead of two), and better locality (data for the same instrument is physically adjacent on disk). The tradeoff is that WITHOUT ROWID tables can't use some SQLite optimizations that depend on rowids, but for time-series data accessed by composite key, this is the right choice.

## Index Tradeoffs

Indexes aren't free—each index consumes storage, slows down writes (every INSERT must update all indexes), and requires maintenance to stay in sync with data. The schema includes only two additional indexes beyond the primary keys: `idx_ohlcv_ts` on `ohlcv(ts_event)` to enable time-range queries across instruments, and `idx_instruments_symbol` on `instruments(raw_symbol)` to enable symbol lookups. Each was added because the query pattern it supports is common enough to justify the overhead.
