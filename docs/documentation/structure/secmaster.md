# Securities Master Database Package Documentation

The [`secmaster`](../../api-reference/overview.md) package provides schema file [`schema.sql`](../../api-reference/secmaster/schema.md) for the securities master database as well as a module [`utils.py`](../../api-reference/secmaster/utils.md) that provides utility functions to create and populate the database.

The securities master database is intended to be used as a source of market data for the simulated datafeed when replaying historical data during backtesting. 
It is implemented as an SQLite database.
SQLite is an embedded database engine that stores the entire database in a single file and requires no server or external configuration.

As part of this documentation page, we will provide an explanation of the schema itself and an overview of the utility functions provided to create and populate the database.


## Schema Overview

For a complete overview and explanation of the schema used by the securities master database, please refer to the API reference documentation.

[:material-link-variant: View Securities Master Database Schema Documentation](../../api-reference/secmaster/schema.md).

## Utility Functions
