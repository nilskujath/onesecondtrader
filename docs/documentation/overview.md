---
hide:
#  - navigation
#  - toc
---

# :material-file-document-multiple-outline: Read the **Docs**

At its core, the OneSecondTrader package enables users to implement a trading strategy and execute it by connecting two interchangeable components: a data feed and a broker.
Both components may operate either in simulated mode—using historical market data and a simulated execution layer—or in live or paper-trading mode via a live data feed and a real broker API.


A central design principle of the system is that backtesting and live trading follow the same execution flow from market data ingestion to order handling, while differing only in the concrete implementations of the data feed and broker.
As a result, transitioning a strategy from historical simulation to live deployment requires no changes to the strategy code itself.

This architectural decision ensures that any discrepancy between backtested and live performance can be attributed exclusively to the fidelity of the simulations. 
On the data side, this concerns how accurately the imitation of a live datafeed from historical records approximates real-time market behavior.
On the execution side, it concerns how well the simulated broker models real-world constraints such as slippage, partial fills, et cetera. 

By strictly isolating these sources of divergence, OneSecondTrader provides a controlled and transparent environment for strategy development, validation, and deployment, without the risk of structural mismatches between research and production.

The OneSecondTrader library is organized as a top-level Python package composed of four sub-packages (`core`, `connectors`, `secmaster`, and `dashboard`), each encapsulating an architecturally distinct set of responsibilities.
To get started, have a look at the [package structure overview](./structure/overview.md). 
