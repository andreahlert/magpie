<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Capability taxonomy](#capability-taxonomy)
  - [Files](#files)
  - [Lifecycle](#lifecycle)
  - [Why centralised](#why-centralised)
  - [Reference](#reference)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

<!-- SPDX-License-Identifier: Apache-2.0 -->

# Capability taxonomy

Canonical vocabulary that skill manifests and adopter `intent.yaml` files reference. Anything outside these files is invalid by definition: the validator rejects manifests or intent that name an unknown domain, audience, risk tier, or integration.

## Files

| File | Purpose |
|---|---|
| [`domains.yaml`](domains.yaml) | Top-level areas of maintainer work the framework covers. |
| [`audiences.yaml`](audiences.yaml) | Who the skill talks to or acts on behalf of. |
| [`risk-tiers.yaml`](risk-tiers.yaml) | Ordered automation levels. Skill cannot exceed adopter's declared max. |
| [`integrations.yaml`](integrations.yaml) | External systems a skill can require (GitHub, Jira, mail archives, etc.). |

## Lifecycle

- Taxonomy is **versioned with the framework release**, not with skills.
- Adding a new value: regular PR, requires manifest reviewer sign-off. Existing skills auto-pick up nothing; adopters can opt in by editing intent.
- Renaming a value: needs a migration entry under `reconciler/migrations/` so adopter locks reconcile cleanly.
- Removing a value: a major framework version bump, with a deprecation window of at least one minor release.

## Why centralised

The reconciler resolves an adopter's `intent.yaml` into a concrete skill set by intersecting capability tags. If two manifests use slightly different strings for the same concept ("github" vs "github-cloud"), resolution silently misses skills. Centralised vocabulary turns that into a CI failure instead of a quiet bug.

## Reference

Background and the model this taxonomy serves: [`docs/rfcs/RFC-MAG-0002-model-c-structural-impact.md`](../../docs/rfcs/RFC-MAG-0002-model-c-structural-impact.md).
