<!-- SPDX-License-Identifier: Apache-2.0 -->

# Registry

Build artefact aggregated from every skill manifest. Committed so that adopters and tooling read a single canonical file rather than walking `.claude/skills/*/manifest.yaml`.

## Files

| File | Purpose |
|---|---|
| [`skills-index.json`](skills-index.json) | Slim view of every skill manifest, keyed by skill id. Drives the reconciler (PR 5+). |

## How it's built

```bash
uv run --with pyyaml python reconciler/build_registry.py --stable-timestamp
```

`--stable-timestamp` fixes the `generated-at` field to `1970-01-01T00:00:00Z` so the checksum is reproducible across runs and machines.

## How CI enforces freshness

The `reconciler-ci` workflow runs `build_registry.py --check --stable-timestamp` and fails the PR when the on-disk registry diverges from what would be generated from the current manifests. Updating a manifest without regenerating the registry blocks the merge.

## Schema

The index file structure (no formal JSON Schema yet — minor shape, may move into `reconciler/schemas/` if it grows):

```jsonc
{
  "schema-version": 1,
  "framework-version": "0.0.0",
  "generated-at": "1970-01-01T00:00:00Z",   // stable in CI builds
  "taxonomy": {                              // sizes only, for sanity
    "domains.yaml": 7,
    "audiences.yaml": 5,
    "risk-tiers.yaml": 5,
    "integrations.yaml": 9
  },
  "skill-count": 29,
  "skills": {
    "<skill-id>": {
      "version": "1.0.0",
      "domains": ["security"],
      "audiences": ["security-pmc", "maintainer-inbound"],
      "risk-tier": "write-comment",
      "integrations": ["gmail", "github", "privacy-llm", "sandbox"],
      "requires": ["setup-isolated-setup-install"],
      "params": { ... },
      "status": "stable"
      // 'templates' and 'replaces' included when set
    },
    ...
  },
  "checksum": "sha256:..."                   // over the canonical-serialised content
}
```

## Why JSON, not YAML

Adopter tooling reads this. JSON parses with stdlib in every runtime; YAML needs a dependency. Manifests stay YAML because skill authors write them by hand and benefit from comments + multi-line strings; the registry is machine input.
