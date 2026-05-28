<!-- SPDX-License-Identifier: Apache-2.0 -->

# Skill migrations

When a skill is renamed or split between framework versions, the reconciler needs to translate the old id in an adopter's existing lock into the new id (or ids) so `magpie plan` shows a clean substitution instead of "remove old, add new".

Each migration is a YAML file in this directory describing one transition. PR 5 lays down the loader stub; the first real migration entry lands when the framework actually renames a skill.

## File shape

```yaml
# 2026-04-01-split-pr-triage.yaml
schema-version: 1
applies-from: 1.0.0      # framework version where the rename took effect
old-id: pr-management-triage
type: split              # rename | split | merge | retire
into:
  - pr-management-triage          # the renamed survivor
  - pr-management-stale-sweep     # carved-out skill
notes: |
  Stale-PR detection was carved out into its own skill so adopters
  can disable it independently. Locks referring to the old single
  pr-management-triage at version <1.0.0 land both new skill ids on
  reconcile.
```

## How the reconciler uses migrations

When `magpie plan` reads an existing lock that mentions a skill no longer present in the registry, it consults this directory and presents the adopter with the substitution before generating the new lock. Adopter confirms; reconciler emits the new lock.

PR 5 introduces the loader stub; no migrations exist yet. Real migrations land alongside the framework changes that motivate them.
