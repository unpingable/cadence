# CLAUDE.md — Instructions for Claude Code

## What This Is

cadence: Temporal admissibility checker for data analytics — a linter that validates whether evidence is temporally coherent enough to justify the decisions being made from it.

## What This Is Not

- Not a data observability platform or pipeline monitor (that's nq's domain)
- Not an authorization/governance system (that's standing/governor's domain)
- Not a query engine or data warehouse — it inspects, it doesn't execute

## Invariants

1. Every source must have a temporal contract before it can be checked
2. Admissibility checks are pure functions of contracts + query structure — no side effects
3. Receipts are append-only and machine-readable

## Quick Start

```bash
pip install -e ".[dev]"
python -m cadence lint examples/
pytest
```

## Project Structure

- `src/cadence/` — core library
  - `contract.py` — temporal contract schema and loading
  - `lint.py` — admissibility checker / temporal linter
  - `receipt.py` — decision receipt emitter
- `tests/` — pytest test suite
- `examples/` — example contracts and queries

## Vocabulary

| Term | Code identifier | Meaning |
|------|----------------|---------|
| present-tense claim | `claims_current` (QuerySpec field) | Output presents itself as "now" |
| staleness budget | `staleness_budget()` (TemporalContract method) | cadence + lag; total acceptable delay |
| correction window | `correction_window_seconds` | Backfill/restatement period |
| freshness SLA | `freshness_sla_seconds` | Max acceptable record age |
| decision receipt | `Receipt` (receipt.py) | Proof of temporal admissibility at eval time |
| proof artifact | decision receipt | Same thing — use "decision receipt" in code/docs |

## Rules

| Rule | Trigger |
|------|---------|
| `missing-contract` | Source referenced without a temporal contract |
| `semantics-mismatch` | Join across incompatible time semantics (e.g. event + ingest) |
| `cadence-mismatch` | Joined sources differ by >=10x in update cadence |
| `lag-exceeds-skew` | Expected lag exceeds declared max skew |
| `unknown-time-semantics` | Source in a join has undeclared time semantics |
| `unsafe-use-class` | Intended use not in source's safe-for set |
| `stale-current-claim` | Claims "current" but staleness budget > 5 min |
| `non-event-current-claim` | Claims "current" but source uses processing/unknown time |

## Conventions

- License: Apache-2.0
- Python >=3.10, type hints everywhere
- Testing: pytest
- Entry point: `python -m cadence`

## Don't

- Don't build pipeline execution or orchestration
- Don't implement data quality checks unrelated to temporal coherence
- Don't add vendor-specific integrations before the core is proven
