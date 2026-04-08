"""Tests for decision receipt emission."""

import json

from cadence.contract import TemporalContract, TimeSemantics
from cadence.lint import Violation, Severity
from cadence.receipt import emit_receipt, AdmissibilityGrade


def test_decision_grade_no_violations():
    contracts = [
        TemporalContract(name="clean", time_semantics=TimeSemantics.EVENT,
                         update_cadence_seconds=60, expected_lag_seconds=10),
    ]
    receipt = emit_receipt("q", contracts, [])
    assert receipt.grade == AdmissibilityGrade.DECISION_GRADE
    assert receipt.error_count == 0
    assert receipt.warning_count == 0


def test_advisory_with_warnings():
    contracts = [
        TemporalContract(name="src", time_semantics=TimeSemantics.EVENT),
    ]
    violations = [
        Violation(rule="test", severity=Severity.WARNING,
                  message="heads up", sources=("src",)),
    ]
    receipt = emit_receipt("q", contracts, violations)
    assert receipt.grade == AdmissibilityGrade.ADVISORY
    assert receipt.warning_count == 1


def test_inadmissible_with_errors():
    contracts = [
        TemporalContract(name="src", time_semantics=TimeSemantics.EVENT),
    ]
    violations = [
        Violation(rule="test", severity=Severity.ERROR,
                  message="bad", sources=("src",)),
    ]
    receipt = emit_receipt("q", contracts, violations)
    assert receipt.grade == AdmissibilityGrade.INADMISSIBLE
    assert receipt.error_count == 1


def test_receipt_json_roundtrip():
    contracts = [
        TemporalContract(name="src", time_semantics=TimeSemantics.EVENT,
                         update_cadence_seconds=60, expected_lag_seconds=10),
    ]
    receipt = emit_receipt("test_query", contracts, [])
    parsed = json.loads(receipt.to_json())
    assert parsed["query_name"] == "test_query"
    assert parsed["grade"] == "decision_grade"
    assert len(parsed["sources"]) == 1
    assert parsed["sources"][0]["staleness_budget_seconds"] == 70


def test_receipt_source_snapshot():
    contracts = [
        TemporalContract(name="s", time_semantics=TimeSemantics.INGEST,
                         update_cadence_seconds=3600, expected_lag_seconds=600),
    ]
    receipt = emit_receipt("q", contracts, [])
    assert receipt.sources[0].time_semantics == "ingest"
    assert receipt.sources[0].staleness_budget_seconds == 4200
