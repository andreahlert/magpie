<!-- SPDX-License-Identifier: Apache-2.0 -->

# Migration: what happens when a framework version renames a skill

The framework occasionally renames or splits a skill across versions. Without coordination, that would leave every adopter's lock referencing a phantom id. The migration system removes the surprise: rename information is shipped alongside the skill change as a YAML migration entry under [`reconciler/migrations/`](../../reconciler/migrations/) (see the README in that directory for the file shape).

## Today

No migrations exist. The system is wired (PR 5 introduced the loader stub and directory) but no actual rename has been required yet. This document explains what happens when one does.

## When a skill renames

A migration entry looks like this (illustrative):

```yaml
# reconciler/migrations/2026-04-01-rename-pr-management-triage.yaml
schema-version: 1
applies-from: 1.0.0
old-id: pr-management-triage
type: rename
into:
  - pr-management-triage-v2
notes: |
  Renamed during the v1.0 cut to disambiguate from the
  pr-management-stale-sweep skill carved out alongside.
```

### What you see

On the next `magpie plan` against a refreshed framework snapshot:

```
Plan: +1 -1 ~0 =0

Migrations applied:
  pr-management-triage -> pr-management-triage-v2

Skills:
  - pr-management-triage      renamed (see migration entry)
  + pr-management-triage-v2   1.0.0 (intent.domains)
```

The remove + add pair is the same skill, renamed. No action needed beyond `magpie apply` to write the new lock.

### If the skill is referenced in your `overrides`

If your intent had `overrides.exclude: [pr-management-triage]` or `overrides.pin.pr-management-triage`, the migration applies the old id is automatically translated when reading the override, and `magpie plan` prints a deprecation warning suggesting you update the intent to the new id.

You do not need to edit immediately. Locks remain valid for at least one minor framework release after the rename lands.

## When a skill splits

`type: split` carves one old skill into two or more new ones. The migration entry lists every new id in `into:`. Plan shows the old skill removed and each new skill added; the adopter decides which of the new ones to keep by editing intent (typically: keep them all if the split was transparent, exclude the ones they don't need if the split was a feature carve-out).

## When a skill merges

`type: merge` is the inverse. Two old skills become one new one. Plan shows two removes and one add.

## When a skill retires

`type: retire` means the skill is gone, no replacement. Plan shows the remove with reason `migration.retire`, and the adopter's lock loses that skill on next apply. If anything depended on it via `requires`, that warning fires.

## Why this matters for project autonomy

The migration registry is the framework's contract with adopters: **renaming is not a breaking change for an adopter who tracks the framework's `main`**. The framework's bookkeeping absorbs the rename; the adopter's `magpie plan` shows the translation; `magpie apply` updates the lock. No grep-and-replace in adopter configs.

## How adopter PRs look across a rename

The PR that updates the framework snapshot in the adopter repo and runs `magpie apply` will show:

- snapshot bump (gitignored content; just a `.apache-steward.local.lock` change),
- lock diff with the rename substitution,
- (optionally) intent diff if the adopter chose to update id references in `overrides`.

Reviewer reads the migration entry in the framework's commit log, confirms the rename matches what the lock did, and approves.
