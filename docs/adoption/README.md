<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Adopting Magpie (Model C)](#adopting-magpie-model-c)
  - [Three-step adoption](#three-step-adoption)
  - [Topics](#topics)
  - [Reference](#reference)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

<!-- SPDX-License-Identifier: Apache-2.0 -->

# Adopting Magpie (Model C)

Adoption under the **intent + lock** model. As of PR 9 this is the default flow. The legacy family-based `setup-steward` takeover remains available as a fallback during the transition window; documentation is being migrated.

## Three-step adoption

1. **Bootstrap the framework snapshot** into your repo. Same shell recipe as before. See [`../setup/install-recipes.md`](../setup/install-recipes.md).
2. **Author your intent.** Copy [`projects/_example-airflow/.apache-steward.intent.yaml`](../../projects/_example-airflow/.apache-steward.intent.yaml) to your repo root as `.apache-steward.intent.yaml`. Edit four blocks: `capabilities`, `overrides.exclude`, `overrides.pin`, `overrides.params`.
3. **Plan and apply.** Commands point `uv` at the reconciler's `pyproject.toml` + `uv.lock` inside the bootstrapped snapshot via `--project`. The lockfile pins reconciler deps (PyYAML included) so the serialised lock checksum is reproducible across machines.

```bash
# See what would happen
uv run --project .apache-steward/reconciler magpie-reconciler plan

# Materialise: write lock + symlinks + render templates
uv run --project .apache-steward/reconciler magpie-reconciler apply \
  --symlink-target .claude/skills \
  --render-templates-to .apache-steward-overrides/rendered
```

Commit:
- `.apache-steward.intent.yaml`
- `.apache-steward.lock`
- `.apache-steward-overrides/` (any rendered templates you want versioned)

Do not commit `.apache-steward/` (gitignored snapshot) or the symlinks under `.claude/skills/` (also gitignored).

## Topics

| Doc | Purpose |
|---|---|
| [intent-cookbook.md](intent-cookbook.md) | Sample intents by adopter shape (security-only, full PMC, dev-cycle focus). |
| [plan-apply-cycle.md](plan-apply-cycle.md) | How `plan` and `apply` work day-to-day: edit intent, plan, apply, commit. |
| [migration-when-skill-renames.md](migration-when-skill-renames.md) | What happens when a framework version renames or splits a skill. |
| [override-guide.md](override-guide.md) | When to use `exclude`, `force-include`, `pin`, `params`. Anti-patterns. |

## Reference

- [RFC-MAG-0001](../rfcs/RFC-MAG-0001-adoption-models.md) Adoption models discussion
- [RFC-MAG-0002](../rfcs/RFC-MAG-0002-model-c-structural-impact.md) Structural impact
- [`reconciler/README.md`](../../reconciler/README.md) Engine command reference
- [`projects/_example-airflow/`](../../projects/_example-airflow/) Canonical example
