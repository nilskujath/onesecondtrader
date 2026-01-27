# Package Structure Overview

The OneSecondTrader library is organized as a top-level Python package composed of four sub-packages ([`core`](../../api-reference/overview.md), [`connectors`](../../api-reference/overview.md), [`secmaster`](../../api-reference/overview.md), and [`dashboard`](../../api-reference/overview.md)), each encapsulating an architecturally distinct set of responsibilities.


## Core Package

The [`core`](../../api-reference/overview.md) package provides the skeleton of an event-driven trading system.
It does include the definition of a set of events which are used to communicate between the different system components, an event bus for routing events to the concerned components, as well as base classes for strategies, brokers, and indicators.
It does not include any datafeed component or any actual broker implementation, which are provided by the [`connectors`](../../api-reference/overview.md) package to isolate external dependencies from the system's core logic.

[:material-link-variant: View Core Package Documentation](core.md).

## Connectors Package

The [`connectors`](../../api-reference/overview.md) package provides actual implementations of brokers and datafeeds.
This includes both the (internally) simulated broker and datafeed as well as connectors to actual live brokers and datafeeds APIs.
This makes it possible for the core of the system to stay the same, while the options for connecting to actual live brokers and datafeeds can be expanded as needed.

[:material-link-variant: View Connectors Package Documentation](connectors.md).

## Securities Master Database Package

The [`secmaster`](../../api-reference/overview.md) package provides the skeleton for a securities master database as well as some utilities to actually ingest data from various sources into this database.
Simulated datafeeds (see `connectors` package) will use it as a source of market data.

[:material-link-variant: View Securities Master Database Package Documentation](secmaster.md).


## Dashboard Package

The [`dashboard`](../../api-reference/overview.md) package provides a web-based dashboard to view and control the runs of the trading system. A run refers to a single execution of the trading system, and is associated with a concrete instance of a strategy (or instances of multiple strategies), as well as the connected broker and datafeed. 
The backend of the dashboard is organized around a database that persistently records all run-related activity on a per-run basis.
The frontend is implemented as a web application that presents this information in a form suitable for both inspection  and operational decision-making.
Backtests differ from live runs only in temporal behavior. Backtests complete quickly, as historical data is replayed at maximum speed, whereas live runs naturally unfold in real time.

[:material-link-variant: View Dashboard Package Documentation](dashboard.md).
