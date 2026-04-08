"""Temporal admissibility linter.

Checks whether a query or model's use of data sources is temporally
coherent given their declared contracts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cadence.contract import TemporalContract, TimeSemantics, UseClass


class Severity(Enum):
    ERROR = "error"  # incoherent — decision not supportable
    WARNING = "warning"  # suspect — may be acceptable with justification
    INFO = "info"  # notable but likely fine


@dataclass(frozen=True)
class Violation:
    """A temporal coherence violation."""

    rule: str
    severity: Severity
    message: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class QuerySpec:
    """A declared query or model that consumes data sources."""

    name: str
    sources: list[str]
    intended_use: UseClass | None = None
    claims_current: bool = False  # does the output present itself as "now"?


def load_query_spec(path: Path) -> QuerySpec:
    """Load a query spec from a JSON file."""
    data = json.loads(path.read_text())
    return _parse_query_spec(data)


def load_query_specs(path: Path) -> list[QuerySpec]:
    """Load all query specs from a directory."""
    specs = []
    for f in sorted(path.glob("*.query.json")):
        data = json.loads(f.read_text())
        if isinstance(data, list):
            specs.extend(_parse_query_spec(item) for item in data)
        else:
            specs.append(_parse_query_spec(data))
    return specs


def _parse_query_spec(data: dict[str, Any]) -> QuerySpec:
    use_raw = data.get("intended_use")
    use = UseClass(use_raw) if use_raw else None
    return QuerySpec(
        name=data["name"],
        sources=data["sources"],
        intended_use=use,
        claims_current=data.get("claims_current", False),
    )


def lint(
    query: QuerySpec,
    contracts: dict[str, TemporalContract],
) -> list[Violation]:
    """Check a query spec against its source contracts for temporal violations."""
    violations: list[Violation] = []

    resolved = []
    for src_name in query.sources:
        contract = contracts.get(src_name)
        if contract is None:
            violations.append(Violation(
                rule="missing-contract",
                severity=Severity.ERROR,
                message=f"Source '{src_name}' has no temporal contract",
                sources=(src_name,),
            ))
        else:
            resolved.append(contract)

    if len(resolved) < 2:
        # Single-source queries skip join checks
        pass
    else:
        violations.extend(_check_semantics_mismatch(resolved))
        violations.extend(_check_cadence_mismatch(resolved))
        violations.extend(_check_skew(resolved))

    for contract in resolved:
        violations.extend(_check_use_class(query, contract))

    if query.claims_current:
        violations.extend(_check_current_claim(resolved))

    return violations


def _check_semantics_mismatch(sources: list[TemporalContract]) -> list[Violation]:
    """Flag joins between sources with incompatible time semantics."""
    violations = []
    semantics = {s.time_semantics for s in sources}

    # unknown is always suspect
    unknown_sources = [s for s in sources if s.time_semantics == TimeSemantics.UNKNOWN]
    for src in unknown_sources:
        violations.append(Violation(
            rule="unknown-time-semantics",
            severity=Severity.WARNING,
            message=f"Source '{src.name}' has unknown time semantics — "
                    f"temporal alignment cannot be verified",
            sources=(src.name,),
        ))

    # mixing event time with ingest/processing time is the classic trap
    known = semantics - {TimeSemantics.UNKNOWN}
    if len(known) > 1:
        names = tuple(s.name for s in sources)
        labels = ", ".join(f"{s.name}={s.time_semantics.value}" for s in sources)
        violations.append(Violation(
            rule="semantics-mismatch",
            severity=Severity.ERROR,
            message=f"Sources joined with incompatible time semantics: {labels}",
            sources=names,
        ))

    return violations


def _check_cadence_mismatch(sources: list[TemporalContract]) -> list[Violation]:
    """Flag joins between sources with wildly different update cadences."""
    violations = []
    with_cadence = [(s, s.update_cadence_seconds) for s in sources
                    if s.update_cadence_seconds is not None]
    if len(with_cadence) < 2:
        return violations

    cadences = sorted(with_cadence, key=lambda x: x[1])
    fastest_src, fastest = cadences[0]
    slowest_src, slowest = cadences[-1]

    if fastest > 0 and slowest / fastest >= 10:
        violations.append(Violation(
            rule="cadence-mismatch",
            severity=Severity.WARNING,
            message=f"Sources have >=10x cadence mismatch: "
                    f"'{fastest_src.name}' every {fastest}s vs "
                    f"'{slowest_src.name}' every {slowest}s",
            sources=(fastest_src.name, slowest_src.name),
        ))

    return violations


def _check_skew(sources: list[TemporalContract]) -> list[Violation]:
    """Flag when sources have lag that exceeds declared skew tolerance."""
    violations = []
    for src in sources:
        if (src.max_skew_seconds is not None
                and src.expected_lag_seconds is not None
                and src.expected_lag_seconds > src.max_skew_seconds):
            violations.append(Violation(
                rule="lag-exceeds-skew",
                severity=Severity.ERROR,
                message=f"Source '{src.name}' expected lag ({src.expected_lag_seconds}s) "
                        f"exceeds its declared max skew ({src.max_skew_seconds}s)",
                sources=(src.name,),
            ))
    return violations


def _check_use_class(query: QuerySpec, contract: TemporalContract) -> list[Violation]:
    """Flag when a source is used for a purpose it wasn't declared safe for."""
    violations = []
    if query.intended_use is not None and contract.safe_for:
        if query.intended_use not in contract.safe_for:
            violations.append(Violation(
                rule="unsafe-use-class",
                severity=Severity.ERROR,
                message=f"Source '{contract.name}' is not declared safe for "
                        f"'{query.intended_use.value}' "
                        f"(safe for: {', '.join(u.value for u in contract.safe_for)})",
                sources=(contract.name,),
            ))
    return violations


def _check_current_claim(sources: list[TemporalContract]) -> list[Violation]:
    """Flag when a query claims 'current' but sources can't support it."""
    violations = []
    for src in sources:
        budget = src.staleness_budget()
        # If staleness budget > 5 minutes, "current" is a stretch
        if budget is not None and budget > 300:
            violations.append(Violation(
                rule="stale-current-claim",
                severity=Severity.WARNING,
                message=f"Query claims 'current' but source '{src.name}' has "
                        f"a staleness budget of {budget}s ({budget // 60}m)",
                sources=(src.name,),
            ))
        if src.time_semantics in (TimeSemantics.PROCESSING, TimeSemantics.UNKNOWN):
            violations.append(Violation(
                rule="non-event-current-claim",
                severity=Severity.WARNING,
                message=f"Query claims 'current' but source '{src.name}' uses "
                        f"'{src.time_semantics.value}' time — not event time",
                sources=(src.name,),
            ))
    return violations
