# AGENTS.md — Working in this repo

This file is a **travel guide**, not a law.
If anything here conflicts with the user's explicit instructions, the user wins.

> Instruction files shape behavior; the user determines direction.

---

## Quick start

```bash
pip install -e ".[dev]"
python -m cadence lint examples/
pytest
```

## Tests

```bash
pytest
```

Always run tests before proposing commits. Never claim tests pass without running them.

---

## Safety and irreversibility

### Do not do these without explicit user confirmation
- Push to remote, create/close PRs or issues
- Delete or rewrite git history
- Modify dependency files in ways that change the lock file

### Preferred workflow
- Make changes in small, reviewable steps
- Run tests locally before proposing commits
- For any operation that affects external state, require explicit user confirmation

---

## Repository layout

```
src/cadence/          Core library
  contract.py         Temporal contract schema
  lint.py             Admissibility checker
  receipt.py          Decision receipt emitter
tests/                pytest suite
examples/             Example contracts and queries
```

---

## Coding conventions

- Python >=3.10, type hints on all public APIs
- Testing: pytest
- No external dependencies in core (stdlib only)

---

## Invariants

1. Sources without temporal contracts cannot be checked — fail closed
2. Admissibility checks are stateless pure functions
3. Receipts are machine-readable and never silently omit violations

---

## What this is not

- Not a pipeline monitor or data observability tool
- Not an authorization system
- Not a query engine or warehouse integration

---

## When you're unsure

Ask for clarification rather than guessing, especially around:
- What constitutes a temporal coherence violation vs. an acceptable tradeoff
- Whether a new check belongs in the linter or is out of scope
- Anything that changes the contract schema

---

## Agent-specific instruction files

| Agent | File | Role |
|-------|------|------|
| Claude Code | `CLAUDE.md` | Full operational context, build details, conventions |
| Codex | `AGENTS.md` (this file) | Operating context + defaults |
| Any future agent | `AGENTS.md` (this file) | Start here |
