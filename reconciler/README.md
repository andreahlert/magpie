<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reconciler

The component that resolves an adopter's `intent.yaml` into a concrete `lock` and (eventually) materialises the adopter workspace.

This directory is built up across the PR sequence tracked in [issue #1](https://github.com/andreahlert/magpie/issues/1):

| PR | Drop |
|---|---|
| PR 1 (this PR) | `schemas/` (intent, lock, skill manifest) + `validate_taxonomy.py` |
| PR 5 | `resolve.py`, `plan.py`, CLI entry point in `plan` mode |
| PR 6 | `apply.py` behind `--experimental` |
| PR 7 | Jinja2 template rendering hooked into `apply` |

Each PR adds without breaking what came before.

## Layout

```
reconciler/
├── schemas/                    # JSON Schema for intent, lock, manifest
├── validate_taxonomy.py        # standalone taxonomy linter (PR 1)
├── resolve.py                  # intent + registry -> resolved skill set (PR 5)
├── plan.py                     # current lock vs resolved -> human diff (PR 5)
├── apply.py                    # write lock + materialise workspace (PR 6)
└── migrations/                 # skill rename / split registry (PR 5)
```

## Why a separate directory

The reconciler is the **only** place capability resolution lives. Keeping the engine, the schemas, the migration registry, and the validator together makes ownership obvious and the audit surface narrow. Other framework `tools/*` are integration adapters and orchestrators; the reconciler is the resolver.

## Running today

```bash
python reconciler/validate_taxonomy.py
```

Validates `agent/taxonomy/` for shape, uniqueness, and ordering rules. PR 4 wires this into CI.

## References

- [RFC-MAG-0001](../docs/rfcs/RFC-MAG-0001-adoption-models.md) Adoption models
- [RFC-MAG-0002](../docs/rfcs/RFC-MAG-0002-model-c-structural-impact.md) Model C structural impact
- [`agent/taxonomy/`](../agent/taxonomy/) Canonical vocabulary the schemas reference
