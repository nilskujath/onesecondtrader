# Explanation

## Models Package

The `models` package defines the fundamental domain concepts used throughout the trading system.

Concrete definitions and their semantics are documented in the API Reference.

[:material-link-variant: View Models Package API Reference](../reference/overview.md).


## Events Package

The `events` package defines the event message objects propagated through the system.

Concrete types of event message objects and their payloads are documented in the API Reference.

[:material-link-variant: View Events Package API Reference](../reference/overview.md).


## Indicators Package

The `indicators` package provides a library of common technical indicators and a base class for creating custom ones.
Indicators are intended to be used in the context of (multi-symbol) strategies and provide a thread-safe mechanism for storing and retrieving per-symbol indicator values computed from incoming market bars.

Concrete indicators and their computation logic, as well as the base class for creating custom indicators, are documented in the API Reference.

[:material-link-variant: View Indicators Package API Reference](../reference/overview.md).
