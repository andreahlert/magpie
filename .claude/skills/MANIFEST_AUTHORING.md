<!-- SPDX-License-Identifier: Apache-2.0 -->

# Authoring a skill manifest

Every skill carries a machine-readable `manifest.yaml` next to its `SKILL.md`. The reconciler (PR 5+) reads manifests to resolve an adopter's `intent.yaml` into a concrete skill set. See [RFC-MAG-0002](../../docs/rfcs/RFC-MAG-0002-model-c-structural-impact.md).

This document is the authoring guide. The contract is the JSON Schema at [`reconciler/schemas/skill-manifest.schema.json`](../../reconciler/schemas/skill-manifest.schema.json).

## Reference pilot

[`security-issue-import/`](security-issue-import/) is the reference. Open `manifest.yaml`, `params.schema.json`, and `params.defaults.yaml` side by side when authoring a new manifest.

## Required fields

| Field | Type | Rule |
|---|---|---|
| `schema-version` | integer | Always `1` for now. |
| `id` | string | Matches the directory name. Lowercase kebab-case. |
| `version` | string | Semver. Bumped independently of the framework. |
| `domains` | list of string | One or more taxonomy `domain` ids. |
| `audiences` | list of string | One or more taxonomy `audience` ids. |
| `risk-tier` | string | Single taxonomy `risk-tier` id, the highest tier the skill ever reaches. |
| `status` | string | `proposed`, `experimental`, `stable`, `deprecated`, or `off`. |

## Optional fields

| Field | Type | Use when |
|---|---|---|
| `integrations` | list of string | The skill talks to external systems. List every one. |
| `requires` | list of string | The skill depends on another skill being enabled. |
| `templates` | list of string | The skill renders templates into the adopter workspace (lands in PR 7). |
| `params.schema` | string | The skill accepts adopter-tunable parameters. |
| `params.defaults` | string | Required if `params.schema` is set. Safe default values. |
| `replaces` | list of string | The skill supersedes one or more old skills (rename or split). |

## Choosing the `risk-tier`

Pick the highest tier the skill ever reaches, not its most common action:

- **read-only** never writes anywhere.
- **suggest-only** prepares an artefact a human pastes or submits. No GitHub/Jira/mail write.
- **write-comment** writes comments, labels, or issue updates. Not a code change. Reversible.
- **draft-pr** opens a PR. Human reviews and merges.
- **write-merge** auto-merges. Restricted to objectively boring categories (MISSION sequencing).

When in doubt, pick the higher tier. Adopters configure `risk-tier-max`; over-classifying is safer than under-classifying.

## Choosing `audiences`

The audience is **who the skill addresses or acts on behalf of**, not who triggers it. A skill a maintainer runs *to draft a reply to a contributor* has audience `contributor-facing`, not `maintainer-inbound`. List every audience the skill actually touches.

## Choosing `integrations`

List **only the integrations the skill actually requires to run**. A skill that *can* use Jira if available but works without it should not list `jira`. Optional integrations are a future schema extension.

`sandbox` and `privacy-llm` are mandatory whenever the skill touches pre-disclosure security content. Skills that operate only on public data omit them.

## Validating

```bash
uv run --with pyyaml --with jsonschema python reconciler/validate_manifests.py
```

Walks every manifest in the tree, checks the schema, checks every taxonomy reference, checks that `params.schema` / `params.defaults` paths resolve, and warns on dangling `requires` / `replaces` ids.

PR 4 wires this into CI so a malformed manifest blocks the PR.

## When a skill is renamed or split

Add a migration entry under `reconciler/migrations/` (PR 5+) mapping the old id to the new one. List the old id in the new manifest's `replaces`. Adopter locks reconcile cleanly: `magpie plan` shows the substitution before applying.
