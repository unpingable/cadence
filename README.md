# cadence

Temporal admissibility checker for data analytics. Chain-of-custody for dashboard facts.

## What it does

- Declares **temporal contracts** for data sources (cadence, lag, event-time semantics, freshness SLA)
- **Lints** queries, models, and dashboards for temporal coherence violations (incompatible joins, unsafe cadences, misleading present-tense claims (`claims_current`))
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
3. Decision receipts are the proof artifact — no silent assumptions

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

## Glossary

- **Temporal contract** — A declaration of a data source's temporal properties: what kind of time it produces, how often it updates, how much lag to expect, and what decisions it is safe for.
- **Time semantics** — The meaning of a source's timestamp: event (when it happened), ingest (when the system received it), processing (when a pipeline transformed it), publish (when it became available), or unknown.
- **Use class** — The category of decision a source is declared safe for: monitoring, reporting, allocation, escalation, audit, or exploratory.
- **Staleness budget** — Total acceptable delay before data is considered stale. Computed as `update_cadence_seconds + expected_lag_seconds`.
- **Correction window** — The period during which a source may backfill or restate previously-published data.
- **Freshness SLA** — Maximum acceptable age of the newest record in a source before it breaches its service-level agreement.
- **Present-tense claim** (`claims_current`) — A query or dashboard that presents its output as reflecting "now." Triggers additional checks because sources with large staleness budgets or non-event-time semantics cannot truthfully support such claims.
- **Decision receipt** — A machine-readable record documenting the temporal state of all sources at evaluation time, the violations found, and the resulting admissibility grade.

## Violation rules

| Rule | Severity | Fires when |
|------|----------|------------|
| `missing-contract` | error | A query references a source with no temporal contract |
| `semantics-mismatch` | error | A join combines sources with incompatible time semantics (e.g., event + ingest) |
| `cadence-mismatch` | warning | Joined sources have a >=10x difference in update cadence |
| `lag-exceeds-skew` | error | A source's expected lag exceeds its declared max skew tolerance |
| `unknown-time-semantics` | warning | A source in a join has undeclared time semantics |
| `unsafe-use-class` | error | A query's intended use is not in the source's declared safe-for set |
| `stale-current-claim` | warning | A query claims "current" but a source's staleness budget exceeds 5 minutes |
| `non-event-current-claim` | warning | A query claims "current" but a source uses processing or unknown time semantics |

## Admissibility grades

| Grade | Meaning |
|-------|---------|
| `DECISION_GRADE` | No violations. Evidence is temporally coherent and safe for its intended use. |
| `ADVISORY` | Warnings only. Usable with caveats — the consumer should understand the temporal limitations. |
| `INADMISSIBLE` | One or more errors. Evidence is temporally incoherent — do not make decisions from it. |

Grade is determined by the worst violation severity: any error means INADMISSIBLE, warnings-only means ADVISORY, clean means DECISION_GRADE.

## License

Licensed under Apache-2.0.
