from __future__ import annotations

import enum


class OrderRejectionReason(enum.Enum):
    """
    Enumeration of canonical order rejection reasons.

    This enumeration defines the system-level classification of order rejection causes.
    It provides a stable, broker-agnostic taxonomy for programmatic handling of rejected orders.

    | Value     | Semantics                                                                 |
    |-----------|---------------------------------------------------------------------------|
    | `UNKNOWN` | The rejection reason could not be classified into a known category.       |
    """

    UNKNOWN = enum.auto()


class ModificationRejectionReason(enum.Enum):
    """
    Enumeration of canonical order modification rejection reasons.

    This enumeration defines the system-level classification of reasons for which an order modification request may be rejected by a broker.
    It provides a stable, broker-agnostic taxonomy intended for programmatic handling and observability of modification rejections.

    | Value     | Semantics                                                                        |
    |-----------|----------------------------------------------------------------------------------|
    | `UNKNOWN` | The modification rejection reason could not be classified into a known category. |
    """

    UNKNOWN = enum.auto()


class CancellationRejectionReason(enum.Enum):
    """
    Enumeration of canonical order cancellation rejection reasons.

    This enumeration defines the system-level classification of reasons for which an order cancellation request may be rejected by a broker.
    It provides a stable, broker-agnostic taxonomy intended for programmatic handling and observability of cancellation rejections.

    | Value     | Semantics                                                                        |
    |-----------|----------------------------------------------------------------------------------|
    | `UNKNOWN` | The cancellation rejection reason could not be classified into a known category. |
    """

    UNKNOWN = enum.auto()
