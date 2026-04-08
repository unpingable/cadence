# cadence

Temporal admissibility checker for data analytics. Chain-of-custody for dashboard facts.

## What it does

- Declares **temporal contracts** for data sources (cadence, lag, event-time semantics, freshness SLA)
- **Lints** queries, models, and dashboards for temporal coherence violations (incompatible joins, unsafe cadences, misleading present-tense claims)
- Emits **decision receipts** documenting source as-of times, lag at render, coherence grade, and admissibility for the intended use

## What this is not

- Not a pipeline monitor — nq handles operational health
- Not an authorization layer — standing/governor handles entitlements
- Not a data warehouse or query engine

## Invariants

The question this system answers:

> Is this evidence temporally coherent enough to justify this decision, at this moment, for this use?

1. Every data source has an explicit temporal contract
2. Admissibility is evaluated at query/render time against declared contracts
3. Receipts are the proof artifact — no silent assumptions

## Quick start

```bash
pip install -e ".[dev]"
python -m cadence lint examples/
pytest
```

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌─────────┐
│  Temporal    │────▶│  Linter  │────▶│ Receipt │
│  Contracts  │     │          │     │         │
└─────────────┘     └──────────┘     └─────────┘
  source decls       coherence        proof of
  cadence, lag,      checks at        temporal
  semantics          query time       admissibility
```

## License

Licensed under Apache-2.0.
