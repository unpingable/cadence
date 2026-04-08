"""Tests for temporal contract loading and parsing."""

import json
from pathlib import Path

from cadence.contract import (
    TemporalContract,
    TimeSemantics,
    UseClass,
    load_contract,
    load_contracts,
)


def test_parse_minimal(tmp_path: Path):
    p = tmp_path / "src.json"
    p.write_text(json.dumps({"name": "events", "time_semantics": "event"}))
    c = load_contract(p)
    assert c.name == "events"
    assert c.time_semantics == TimeSemantics.EVENT
    assert c.update_cadence_seconds is None
    assert c.safe_for == frozenset()


def test_parse_full(tmp_path: Path):
    data = {
        "name": "clicks",
        "time_semantics": "event",
        "update_cadence_seconds": 60,
        "expected_lag_seconds": 10,
        "correction_window_seconds": 3600,
        "freshness_sla_seconds": 120,
        "max_skew_seconds": 30,
        "safe_for": ["monitoring", "reporting"],
    }
    p = tmp_path / "src.json"
    p.write_text(json.dumps(data))
    c = load_contract(p)
    assert c.update_cadence_seconds == 60
    assert c.expected_lag_seconds == 10
    assert c.max_skew_seconds == 30
    assert UseClass.MONITORING in c.safe_for
    assert UseClass.REPORTING in c.safe_for


def test_staleness_budget():
    c = TemporalContract(
        name="t",
        time_semantics=TimeSemantics.EVENT,
        update_cadence_seconds=60,
        expected_lag_seconds=30,
    )
    assert c.staleness_budget() == 90


def test_staleness_budget_none():
    c = TemporalContract(name="t", time_semantics=TimeSemantics.EVENT)
    assert c.staleness_budget() is None


def test_load_contracts_array(tmp_path: Path):
    data = [
        {"name": "a", "time_semantics": "event"},
        {"name": "b", "time_semantics": "ingest"},
    ]
    (tmp_path / "sources.json").write_text(json.dumps(data))
    contracts = load_contracts(tmp_path)
    assert len(contracts) == 2
    assert contracts[0].name == "a"
    assert contracts[1].name == "b"


def test_unknown_semantics(tmp_path: Path):
    p = tmp_path / "mystery.json"
    p.write_text(json.dumps({"name": "mystery"}))
    c = load_contract(p)
    assert c.time_semantics == TimeSemantics.UNKNOWN
