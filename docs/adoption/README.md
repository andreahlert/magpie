<!-- SPDX-License-Identifier: Apache-2.0 -->

# Adopting Magpie (Model C)

Adoption under the **intent + lock** model. As of PR 9 this is the default flow. The legacy family-based `setup-steward` takeover remains available as a fallback during the transition window; documentation is being migrated.

## Three-step adoption

1. **Bootstrap the framework snapshot** into your repo. Same shell recipe as before. See [`../setup/install-recipes.md`](../setup/install-recipes.md).
2. **Author your intent.** Copy [`projects/_example-airflow/.apache-steward.intent.yaml`](../../projects/_example-airflow/.apache-steward.intent.yaml) to your repo root as `.apache-steward.intent.yaml`. Edit four blocks: `capabilities`, `overrides.exclude`, `overrides.pin`, `overrides.params`.
3. **Plan and apply.**

```bash
# See what would happen
uv run --with pyyaml --with jsonschema --with jinja2 \
  python -m reconciler plan

# Materialise: write lock + symlinks + render templates
uv run --with pyyaml --with jsonschema --with jinja2 \
  python -m reconciler apply \
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
