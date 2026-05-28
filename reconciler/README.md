<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Reconciler](#reconciler)
  - [Layout](#layout)
  - [Why a separate directory](#why-a-separate-directory)
  - [Running today](#running-today)
  - [Plan output](#plan-output)
  - [References](#references)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reconciler

The component that resolves an adopter's `intent.yaml` into a concrete `lock` and (eventually) materialises the adopter workspace.

This directory is built up across the PR sequence tracked in [issue #1](https://github.com/andreahlert/magpie/issues/1):

| PR | Drop |
|---|---|
| PR 1 | `schemas/` (intent, lock, skill manifest) + `validate_taxonomy.py` |
| PR 2 | First manifest + `validate_manifests.py` |
| PR 4 | `build_registry.py` + `registry/skills-index.json` + CI workflow |
| PR 5 | `resolve.py`, `plan.py`, `__main__.py` CLI in `plan` mode, tests |
| PR 6 | `apply.py` behind `--experimental` (lock write + optional symlink materialisation) |
| PR 7 | Jinja2 template rendering via `--render-templates-to`. Pilot: pr-management-triage |
| PR 9 (this PR) | Flip default. `--experimental` becomes no-op. New `docs/adoption/`. README + setup-steward updated. |

Each PR adds without breaking what came before.

## Layout

```text
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
# Validate the canonical taxonomy
uv run --with pyyaml python reconciler/validate_taxonomy.py

# Validate every skill manifest against schema + taxonomy
uv run --with pyyaml --with jsonschema python reconciler/validate_manifests.py

# Rebuild the registry from manifests (use --check in CI)
uv run --with pyyaml python reconciler/build_registry.py --stable-timestamp

# Generate a plan against an intent file
uv run --with pyyaml --with jsonschema python -m reconciler plan \
  --intent path/to/.apache-steward.intent.yaml \
  --lock path/to/.apache-steward.lock

# Apply: write the resolved lock (opt-in via --experimental
# during PR 6 rollout). Optional --symlink-target materialises
# one symlink per resolved skill into the framework checkout.
uv run --with pyyaml --with jsonschema python -m reconciler apply \
  --intent path/to/.apache-steward.intent.yaml \
  --lock   path/to/.apache-steward.lock \
  --experimental
# Add --dry-run to compute the result without writing.
# Add --symlink-target <adopter>/.claude/skills to also wire up symlinks.
# Add --render-templates-to <adopter>/.apache-steward-overrides/rendered
# to also render every resolved skill's Jinja2 templates with effective
# params (defaults + intent.overrides.params).

# Run the unit test suite
uv run --with pyyaml --with jsonschema --with pytest pytest reconciler/tests/ -v
```

CI runs all of the above on every PR that touches taxonomy, manifests, registry, or reconciler code.

## Plan output

`magpie plan` (today: `python -m reconciler plan`) outputs:

```text
Plan: +15 -0 ~0 =0

Warnings:                                  # only when present
  ! force-include-violates-risk-tier [auto-merge-lint]: ...

Skills:
  + security-issue-import          1.0.0 (intent.domains)
  + setup-isolated-setup-install   1.0.0 (skill.requires)
  ...
```

Glyphs: `+` add, `-` remove, `~` change, `=`/blank keep (hidden unless `--show-keeps`).

Exit codes:
- 0: no changes (lock matches resolution)
- 2: changes detected (CI gate signal)
- 1: error (invalid intent, missing file, schema failure)

## References

- [RFC-MAG-0001](../docs/rfcs/RFC-MAG-0001-adoption-models.md) Adoption models
- [RFC-MAG-0002](../docs/rfcs/RFC-MAG-0002-model-c-structural-impact.md) Model C structural impact
- [`agent/taxonomy/`](../agent/taxonomy/) Canonical vocabulary the schemas reference
