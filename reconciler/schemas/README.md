<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reconciler schemas

JSON Schema (Draft 2020-12) for the three machine-readable files that drive the Model C adoption flow.

| Schema | Lives where | Authored by | Validated when |
|---|---|---|---|
| [`skill-manifest.schema.json`](skill-manifest.schema.json) | `skills/<n>/manifest.yaml` in this repo | Skill author | CI on every PR, registry build |
| [`intent.schema.json`](intent.schema.json) | `.apache-steward.intent.yaml` in adopter repo | Adopter PMC | Before every `magpie plan` |
| [`lock.schema.json`](lock.schema.json) | `.apache-steward.lock` in adopter repo | Reconciler | Before adopter tooling reads it |

## Versioning

Each schema carries `schema-version`. The reconciler must support at least the current major version and the previous one (N and N-1). Schemas are bumped only when a breaking change lands.

## Why JSON Schema for YAML files

YAML and JSON share the same data model. JSON Schema gives:

- Standard tooling (`check-jsonschema`, IDE integration via `yaml.schemas` in `.vscode/settings.json`, the `ajv` validator).
- Self-documenting field descriptions reachable from editor tooltips.
- Cross-language: the reconciler is Python today, future runtime helpers may be elsewhere.

## How to validate locally

```bash
uvx check-jsonschema --schemafile reconciler/schemas/skill-manifest.schema.json skills/security-issue-import/manifest.yaml
```

CI runs the same check across every manifest and every example intent/lock under `projects/`.
