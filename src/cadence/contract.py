"""Temporal contracts for data sources.

A temporal contract declares what kind of time a data source produces,
what promises it makes about freshness and cadence, and what classes
of use it is safe for.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TimeSemantics(Enum):
    """What kind of time does this source's timestamp represent?"""

    EVENT = "event"  # when the thing actually happened
    INGEST = "ingest"  # when the system received the record
    PROCESSING = "processing"  # when a pipeline processed the record
    PUBLISH = "publish"  # when the result was made available
    UNKNOWN = "unknown"  # not declared — treated as suspect


class UseClass(Enum):
    """What decisions is this source safe for?"""

    MONITORING = "monitoring"  # real-time operational awareness
    REPORTING = "reporting"  # periodic business reporting
    ALLOCATION = "allocation"  # resource allocation decisions
    ESCALATION = "escalation"  # incident response / paging
    AUDIT = "audit"  # compliance / post-hoc review
    EXPLORATORY = "exploratory"  # ad-hoc analysis, no decisions


@dataclass(frozen=True)
class TemporalContract:
    """Declares the temporal properties of a data source.

    Fields:
        name: Human-readable identifier for the data source.
        time_semantics: What kind of timestamp this source produces
            (event, ingest, processing, publish, unknown).
        update_cadence_seconds: How often the source produces a new
            snapshot, in seconds. Used to compute staleness budget.
        expected_lag_seconds: Expected delay between when data is
            generated and when it becomes queryable. Used to compute
            staleness budget.
        correction_window_seconds: Duration during which the source may
            backfill or restate previously-published values.
        freshness_sla_seconds: Maximum acceptable age of the most recent
            record before the source is considered stale.
        max_skew_seconds: Acceptable clock drift between this source and
            others in a join. If expected lag exceeds this value, the
            lag-exceeds-skew rule fires.
        safe_for: Set of UseClass values declaring which decision
            contexts this source's temporal properties support.
    """

    name: str
    time_semantics: TimeSemantics
    update_cadence_seconds: int | None = None
    expected_lag_seconds: int | None = None
    correction_window_seconds: int | None = None
    freshness_sla_seconds: int | None = None
    max_skew_seconds: int | None = None
    safe_for: frozenset[UseClass] = field(default_factory=frozenset)

    def staleness_budget(self) -> int | None:
        """Total acceptable delay: cadence + lag + SLA headroom."""
        parts = [self.update_cadence_seconds, self.expected_lag_seconds]
        known = [p for p in parts if p is not None]
        if not known:
            return None
        return sum(known)


def load_contract(path: Path) -> TemporalContract:
    """Load a temporal contract from a JSON file."""
    data = json.loads(path.read_text())
    return _parse_contract(data)


def load_contracts(path: Path) -> list[TemporalContract]:
    """Load all contracts from a directory of JSON files."""
    contracts = []
    for f in sorted(path.glob("*.json")):
        data = json.loads(f.read_text())
        if isinstance(data, list):
            contracts.extend(_parse_contract(item) for item in data)
        else:
            contracts.append(_parse_contract(data))
    return contracts


def _parse_contract(data: dict[str, Any]) -> TemporalContract:
    safe_for_raw = data.get("safe_for", [])
    safe_for = frozenset(UseClass(u) for u in safe_for_raw)

    semantics_raw = data.get("time_semantics", "unknown")
    semantics = TimeSemantics(semantics_raw)

    return TemporalContract(
        name=data["name"],
        time_semantics=semantics,
        update_cadence_seconds=data.get("update_cadence_seconds"),
        expected_lag_seconds=data.get("expected_lag_seconds"),
        correction_window_seconds=data.get("correction_window_seconds"),
        freshness_sla_seconds=data.get("freshness_sla_seconds"),
        max_skew_seconds=data.get("max_skew_seconds"),
        safe_for=safe_for,
    )
