<!-- SPDX-License-Identifier: Apache-2.0 -->

# Override guide

The four override mechanisms, when to use each, and patterns to avoid.

## The mechanisms

| Override | Purpose | Effect on lock |
|---|---|---|
| `exclude` | Drop a specific skill the capability filter would have included. | Skill absent from lock; appears in `exclusions:` with reason `intent.overrides.exclude`. |
| `force-include` | Bring in a skill the capability filter dropped. | Skill present; warning if it violates `risk-tier-max` or has `status: off`. |
| `pin` | Use a specific version instead of registry's latest. | Skill version set to the pinned value; warning if pinned value differs from registry. |
| `params` | Per-key override of a skill's default parameters. | Effective params used when rendering templates and when the skill runs. |

## When to use each

### `exclude`

- A domain skill is on by default but your project's culture doesn't fit.
- A skill is too noisy at current maturity (campaign-mode skills the project runs on-demand).
- A skill duplicates an existing project process (you already have a stable triage flow).

Anti-pattern: `exclude`-ing skills you don't understand. Read the SKILL.md first.

### `force-include`

- You want a dev-side skill on a project where the audience axis would have filtered it.
- You're piloting a `status: experimental` skill that the registry would have included anyway (no effect — read the warning if any).
- You explicitly want auto-merge (`risk-tier=write-merge`). Today this is also gated by `status: off` at the framework level, so two warnings will fire; you are taking responsibility for both.

Anti-pattern: `force-include` as a workaround for misclassified integrations. If a skill is being excluded by `integrations`, the right fix is to add the missing integration to your `capabilities.integrations` list, not to bypass the filter.

### `pin`

- You're running a regression against a known-good version of a skill while the next release shakes out.
- Compliance: PMC reviews each version bump.
- Reproducing a historical incident.

Anti-pattern: pinning everything by default. The point of running on `main` is to pick up improvements; pinning by default freezes you out.

### `params`

- Project-specific URLs, project name, marker strings, mailbox labels.
- Locale and tone preferences.
- Anything declared in the skill's `params.schema.json`.

Anti-pattern: putting secrets in `params`. The intent file is committed.

## How many overrides is too many

If your `intent.overrides` block grows past 5 skill-level entries (across `exclude` + `force-include` + `pin`), reconsider whether your `capabilities` declaration matches your project's actual shape. Overrides are escape hatches for the 10% of cases that don't fit the four-axis cut; if they cover the 50%, the cut is wrong.

A future linter on `magpie plan` will surface this as a warning. For now it's a guideline.

## Reading the lock for override impact

After `apply`, every skill in the lock carries a `source:` field showing why it landed:

- `intent.domains` — capability filter accepted it.
- `intent.overrides.force-include` — you forced it in.
- `skill.requires` — pulled in transitively by a `requires` chain.

If a skill is `intent.overrides.force-include` but you don't remember why, read your own intent file and see what you wrote. The intent is the source of truth; the lock is just the resolution.
