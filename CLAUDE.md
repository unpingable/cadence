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

## Conventions

- License: Apache-2.0
- Python >=3.10, type hints everywhere
- Testing: pytest
- Entry point: `python -m cadence`

## Don't

- Don't build pipeline execution or orchestration
- Don't implement data quality checks unrelated to temporal coherence
- Don't add vendor-specific integrations before the core is proven
