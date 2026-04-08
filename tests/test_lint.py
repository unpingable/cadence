"""Tests for the temporal admissibility linter."""

from cadence.contract import TemporalContract, TimeSemantics, UseClass
from cadence.lint import lint, QuerySpec, Severity


def _contract(name: str, **kwargs) -> TemporalContract:
    defaults = {"time_semantics": TimeSemantics.EVENT}
    defaults.update(kwargs)
    return TemporalContract(name=name, **defaults)


def test_missing_contract():
    q = QuerySpec(name="q", sources=["nonexistent"])
    violations = lint(q, {})
    assert len(violations) == 1
    assert violations[0].rule == "missing-contract"
    assert violations[0].severity == Severity.ERROR


def test_semantics_mismatch():
    contracts = {
        "a": _contract("a", time_semantics=TimeSemantics.EVENT),
        "b": _contract("b", time_semantics=TimeSemantics.INGEST),
    }
    q = QuerySpec(name="q", sources=["a", "b"])
    violations = lint(q, contracts)
    rules = {v.rule for v in violations}
    assert "semantics-mismatch" in rules


def test_semantics_match_no_violation():
    contracts = {
        "a": _contract("a", time_semantics=TimeSemantics.EVENT),
        "b": _contract("b", time_semantics=TimeSemantics.EVENT),
    }
    q = QuerySpec(name="q", sources=["a", "b"])
    violations = lint(q, contracts)
    assert not any(v.rule == "semantics-mismatch" for v in violations)


def test_cadence_mismatch():
    contracts = {
        "fast": _contract("fast", update_cadence_seconds=60),
        "slow": _contract("slow", update_cadence_seconds=86400),
    }
    q = QuerySpec(name="q", sources=["fast", "slow"])
    violations = lint(q, contracts)
    rules = {v.rule for v in violations}
    assert "cadence-mismatch" in rules


def test_cadence_similar_no_violation():
    contracts = {
        "a": _contract("a", update_cadence_seconds=60),
        "b": _contract("b", update_cadence_seconds=120),
    }
    q = QuerySpec(name="q", sources=["a", "b"])
    violations = lint(q, contracts)
    assert not any(v.rule == "cadence-mismatch" for v in violations)


def test_lag_exceeds_skew():
    contracts = {
        "bad": _contract("bad", expected_lag_seconds=100, max_skew_seconds=30),
        "ok": _contract("ok", expected_lag_seconds=5, max_skew_seconds=30),
    }
    q = QuerySpec(name="q", sources=["bad", "ok"])
    violations = lint(q, contracts)
    lag_violations = [v for v in violations if v.rule == "lag-exceeds-skew"]
    assert len(lag_violations) == 1
    assert "bad" in lag_violations[0].sources


def test_unsafe_use_class():
    contracts = {
        "src": _contract("src", safe_for=frozenset({UseClass.REPORTING})),
    }
    q = QuerySpec(name="q", sources=["src"], intended_use=UseClass.ESCALATION)
    violations = lint(q, contracts)
    assert any(v.rule == "unsafe-use-class" for v in violations)


def test_safe_use_class():
    contracts = {
        "src": _contract("src", safe_for=frozenset({UseClass.REPORTING})),
    }
    q = QuerySpec(name="q", sources=["src"], intended_use=UseClass.REPORTING)
    violations = lint(q, contracts)
    assert not any(v.rule == "unsafe-use-class" for v in violations)


def test_stale_current_claim():
    contracts = {
        "daily": _contract(
            "daily",
            update_cadence_seconds=86400,
            expected_lag_seconds=7200,
        ),
    }
    q = QuerySpec(name="q", sources=["daily"], claims_current=True)
    violations = lint(q, contracts)
    assert any(v.rule == "stale-current-claim" for v in violations)


def test_current_claim_with_fast_source():
    contracts = {
        "fast": _contract("fast", update_cadence_seconds=5, expected_lag_seconds=2),
    }
    q = QuerySpec(name="q", sources=["fast"], claims_current=True)
    violations = lint(q, contracts)
    assert not any(v.rule == "stale-current-claim" for v in violations)


def test_unknown_semantics_warning():
    contracts = {
        "a": _contract("a", time_semantics=TimeSemantics.EVENT),
        "b": _contract("b", time_semantics=TimeSemantics.UNKNOWN),
    }
    q = QuerySpec(name="q", sources=["a", "b"])
    violations = lint(q, contracts)
    assert any(v.rule == "unknown-time-semantics" for v in violations)


def test_clean_query_no_violations():
    contracts = {
        "src": _contract(
            "src",
            update_cadence_seconds=60,
            expected_lag_seconds=10,
            safe_for=frozenset({UseClass.REPORTING}),
        ),
    }
    q = QuerySpec(name="q", sources=["src"], intended_use=UseClass.REPORTING)
    violations = lint(q, contracts)
    assert violations == []
