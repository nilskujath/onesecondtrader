---
hide:
#  - navigation
#  - toc
---

# :material-file-document-multiple-outline: Read the **Docs**

## Introduction

At its core, the OneSecondTrader package enables users to implement a trading strategy and execute it by connecting two interchangeable components: a data feed and a broker.
Both components may operate either in simulated mode—using historical market data and a simulated execution layer—or in live or paper-trading mode via a live data feed and a real broker API.


A central design principle of the system is that backtesting and live trading follow the same execution flow from market data ingestion to order handling, while differing only in the concrete implementations of the data feed and broker.
As a result, transitioning a strategy from historical simulation to live deployment requires no changes to the strategy code itself.

This architectural decision ensures that any discrepancy between backtested and live performance can be attributed exclusively to the fidelity of the simulations. 
On the data side, this concerns how accurately the imitation of a live datafeed from historical records approximates real-time market behavior.
On the execution side, it concerns how well the simulated broker models real-world constraints such as slippage, partial fills, et cetera. 

By strictly isolating these sources of divergence, OneSecondTrader provides a controlled and transparent environment for strategy development, validation, and deployment, without the risk of structural mismatches between research and production.


## Package Structure

The OneSecondTrader library is organized as a top-level Python package composed of four sub-packages (`core`, `connectors`, `secmaster`, and `dashboard`), each encapsulating an architecturally distinct set of responsibilities.

* `core`: Provides the skeleton of an event-driven trading system.
It does include the definition of a set of events which are used to communicate between the different system components, an event bus for routing events to the concerned components, as well as base classes for strategies, brokers, and indicators.
It does not include any datafeed component or any actual broker implementation, which are provided by the `connectors` package to isolate external dependencies from the system's core logic.

* `connectors` Provides actual implementations of brokers and datafeeds.
This includes both the (internally) simulated broker and datafeed as well as connectors to actual live brokers and datafeeds APIs.
This makes it possible for the core of the system to stay the same, while the options for connecting to actual live brokers and datafeeds can be expanded as needed.

* `secmaster`: Povides the skeleton for a securities master database as well as some utilities to actually ingest data from various sources into this database.
Simulated datafeeds (see `connectors` package) will use it as a source of market data.

* `dashboard`: Provides a web-based dashboard to view and control the runs of the trading system. A run refers to a single execution of the trading system, and is associated with a concrete instance of a strategy (or instances of multiple strategies), as well as the connected broker and datafeed. 
The backend of the dashboard is organized around a database that persistently records all run-related activity on a per-run basis.
The frontend is implemented as a web application that presents this information in a form suitable for both inspection  and operational decision-making.
Backtests differ from live runs only in temporal behavior. Backtests complete quickly, as historical data is replayed at maximum speed, whereas live runs naturally unfold in real time.


### System Core (`core` package) { data-toc-label="Core Package" }

!!! warning "Under Construction"

    This part of the documentation is still under construction!
    If necessary, have a look at the API reference for now.


### Broker and Datafeed Connectors (`connectors` package) { data-toc-label="Connectors Package" }

!!! warning "Under Construction"

    This part of the documentation is still under construction!
    If necessary, have a look at the API reference for now.


### Securities Master Database (`secmaster` package) { data-toc-label="Secmaster Package" }

#### Introduction

The securities master database stores market data for use by the simulated datafeed when replaying historical data during backtesting.
It is implemented as an SQLite database and populated via utilities provided by the `secmaster` package.
SQLite is an embedded database engine that stores the entire database in a single file and requires no server or external configuration, making it well suited for market data storage due to its simplicity, portability, read performance, and reliability.

For background on SQL and database concepts used in this schema, see the [SQL Primer](../sql_primer.md).

#### Schema Design Decisions

- **Prices as integers**: Floating-point numbers can't represent all decimal values exactly, so prices are stored as integers using fixed-point arithmetic with a scale factor of $10^9$—guaranteeing exact representation and fast integer arithmetic.
- **Nanosecond timestamps**: Timestamps are stored as integers representing nanoseconds since the Unix epoch, preserving microsecond/nanosecond ordering information, avoiding conversion errors, and matching data vendor formats like Databento.
- **Primary key order**: The `ohlcv` primary key `(instrument_id, rtype, ts_event)` ensures all bars for the same instrument are contiguous on disk, enabling the common query pattern "bars for instrument X, timeframe Y, between time A and B" to become a fast sequential read.


### Dashboard (`dashboard` package) { data-toc-label="Dashboard Package" }

!!! warning "Under Construction"

    This part of the documentation is still under construction!
    If necessary, have a look at the API reference for now.
