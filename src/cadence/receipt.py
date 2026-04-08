"""Decision receipts for temporal admissibility.

A receipt documents the temporal state of evidence at the moment a
query/dashboard/report was evaluated, including violations and an
overall admissibility grade.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

from cadence.contract import TemporalContract
from cadence.lint import Violation, Severity


class AdmissibilityGrade(Enum):
    """Overall temporal admissibility of a result."""

    DECISION_GRADE = "decision_grade"  # coherent, safe for intended use
    ADVISORY = "advisory"  # usable with caveats
    INADMISSIBLE = "inadmissible"  # temporally incoherent — don't decide from this


@dataclass(frozen=True)
class SourceSnapshot:
    """Temporal state of a source at evaluation time."""

    name: str
    time_semantics: str
    update_cadence_seconds: int | None
    expected_lag_seconds: int | None
    staleness_budget_seconds: int | None


@dataclass(frozen=True)
class Receipt:
    """Proof of temporal admissibility at evaluation time."""

    query_name: str
    evaluated_at: str
    grade: AdmissibilityGrade
    sources: list[SourceSnapshot]
    violations: list[dict[str, str]]
    error_count: int
    warning_count: int

    def to_json(self) -> str:
        d = {
            "query_name": self.query_name,
            "evaluated_at": self.evaluated_at,
            "grade": self.grade.value,
            "sources": [
                {
                    "name": s.name,
                    "time_semantics": s.time_semantics,
                    "update_cadence_seconds": s.update_cadence_seconds,
                    "expected_lag_seconds": s.expected_lag_seconds,
                    "staleness_budget_seconds": s.staleness_budget_seconds,
                }
                for s in self.sources
            ],
            "violations": self.violations,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }
        return json.dumps(d, indent=2)


def emit_receipt(
    query_name: str,
    contracts: list[TemporalContract],
    violations: list[Violation],
) -> Receipt:
    """Build a receipt from lint results."""
    errors = sum(1 for v in violations if v.severity == Severity.ERROR)
    warnings = sum(1 for v in violations if v.severity == Severity.WARNING)

    if errors > 0:
        grade = AdmissibilityGrade.INADMISSIBLE
    elif warnings > 0:
        grade = AdmissibilityGrade.ADVISORY
    else:
        grade = AdmissibilityGrade.DECISION_GRADE

    sources = [
        SourceSnapshot(
            name=c.name,
            time_semantics=c.time_semantics.value,
            update_cadence_seconds=c.update_cadence_seconds,
            expected_lag_seconds=c.expected_lag_seconds,
            staleness_budget_seconds=c.staleness_budget(),
        )
        for c in contracts
    ]

    violation_dicts = [
        {
            "rule": v.rule,
            "severity": v.severity.value,
            "message": v.message,
            "sources": list(v.sources),
        }
        for v in violations
    ]

    return Receipt(
        query_name=query_name,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        grade=grade,
        sources=sources,
        violations=violation_dicts,
        error_count=errors,
        warning_count=warnings,
    )
