<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Drift audit: PRs 1–9 (issue #1)](#drift-audit-prs-19-issue-1)
  - [Severity legend](#severity-legend)
  - [P0 — broken on main](#p0--broken-on-main)
    - [1. `skill-validator` pytest now fails on main](#1-skill-validator-pytest-now-fails-on-main)
    - [2. Lychee broken links](#2-lychee-broken-links)
    - [3. Pre-commit (prek) failed on every PR](#3-pre-commit-prek-failed-on-every-pr)
  - [P1 — documented but does not work](#p1--documented-but-does-not-work)
    - [4. `python -m reconciler` from adopter cwd](#4-python--m-reconciler-from-adopter-cwd)
    - [5. setup-steward description/body mismatch](#5-setup-steward-descriptionbody-mismatch)
    - [6. pr-management-triage template renders into a directory the skill does not read](#6-pr-management-triage-template-renders-into-a-directory-the-skill-does-not-read)
  - [P2 — semantic changes beyond reorganization](#p2--semantic-changes-beyond-reorganization)
    - [7. setup-steward manifest version bump](#7-setup-steward-manifest-version-bump)
    - [8. pr-management-triage manifest extended](#8-pr-management-triage-manifest-extended)
    - [9. `.gitignore` behavioral change](#9-gitignore-behavioral-change)
    - [10. License header style inconsistency](#10-license-header-style-inconsistency)
  - [P2 — process drift](#p2--process-drift)
    - [11. CI failures merged without investigation](#11-ci-failures-merged-without-investigation)
    - [12. Example lock determinism untested](#12-example-lock-determinism-untested)
  - [Summary](#summary)
  - [Honest answer](#honest-answer)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

<!-- SPDX-License-Identifier: Apache-2.0 -->

# Drift audit: PRs 1–9 (issue #1)

Honest review against the question "foi só reorganização de arquivos?". Short answer: **não**. There are real semantic changes, broken commands in adopter docs, and CI failures merged through.

A subsequent cleanup PR (the one carrying this document, alongside the fixes) closes all P0 and most P1 items. The remaining debt is P2 and intentional; it is enumerated below for the record.

This document is intentionally critical. The work shipped; this is the followup punch list.

## Severity legend

- **P0** — broken-on-main today. Should be fixed in a follow-up PR before anyone else acts on this work.
- **P1** — documented behavior does not work as written. Will mislead any new adopter.
- **P2** — silent debt. Future work depends on cleaning up.

## P0 — broken on main

### 1. `skill-validator` pytest now fails on main

```
.claude/skills/setup-steward/SKILL.md:1:
description + when_to_use is 1758 chars; Claude Code truncates past 1536
(description=1428, when_to_use=330)
```

PR 9 extended `setup-steward` SKILL.md description to advertise Model C. The combined frontmatter now exceeds the 1536-character truncation limit Claude Code enforces.

- Test that fails: `tools/skill-validator/tests/test_validator.py::TestRunValidation::test_real_repo_passes`.
- Passed on PRs 2–9. Failed on PR 10. Merged anyway because fork has no branch protection.
- Reproduce locally: `uv run --directory tools/skill-validator --group dev pytest tests/test_validator.py -k test_real_repo_passes`.
- Fix: shrink the description back under the limit. Move the Model C announcement out of the frontmatter and into the SKILL.md body or a separate `model-c-onboarding.md`.

### 2. Lychee broken links

Lychee failed on every one of the 9 PRs. The broken references on main:

- `agent/taxonomy/README.md:29` links to `docs/rfcs/model-c-structural-impact.md`. The actual file is `docs/rfcs/RFC-MAG-0002-model-c-structural-impact.md`. Wrote the README with the planned filename, renamed the file, never updated the link.
- `docs/setup/README.md` TOC entry `#typical-lifecycle` is stale. PR 9 renamed the heading to `## Legacy lifecycle` (id `#legacy-lifecycle`) and added a new `## Model C lifecycle` above it. doctoc was never re-run.

### 3. Pre-commit (prek) failed on every PR

```
markdownlint........Failed (exit code 1)
  reconciler/README.md:36 MD040/fenced-code-language
  ...more across the new docs/adoption/, docs/rfcs/, reconciler/ files
Add TOC for Markdown and RST files........Failed
```

Two classes of failure:
- MD040: fenced code blocks need a language tag. Most of my new docs have `\`\`\`` blocks without a language (e.g. shell output, raw lock excerpts).
- doctoc: every markdown file in this repo expects an auto-generated TOC. My new docs do not have the TOC marker block.

The hook would have surfaced these locally if I had run it. I did not.

## P1 — documented but does not work

### 4. `python -m reconciler` from adopter cwd

`README.md` and `docs/adoption/*` document the adopter flow as:

```bash
cd <adopter-root>
uv run --with pyyaml --with jsonschema --with jinja2 \
  python -m reconciler plan
```

Reproduced empirically: this fails with `No module named reconciler` because the reconciler package lives at `<adopter>/.apache-steward/reconciler/` (gitignored snapshot) and Python does not look there by default.

Working invocations would be one of:

```bash
# From the framework checkout root
cd .apache-steward
uv run ... python -m reconciler plan --intent ../.apache-steward.intent.yaml --lock ../.apache-steward.lock
# Or set PYTHONPATH
PYTHONPATH=.apache-steward uv run ... python -m reconciler plan
# Or ship a `magpie` console-script entrypoint that knows the snapshot location
```

Until one of these is added (and the docs updated), every Model C adopter following the README hits the wall at step 3.

### 5. setup-steward description/body mismatch

`setup-steward/SKILL.md` frontmatter description was changed to lead with Model C. The body of the same file (untouched) still walks the agent through the legacy family-based takeover.

Agents read the description to decide *when* to fire and rely on the body for *what* to do. Today they pick the skill expecting Model C and execute the legacy flow.

Cleanest fix: revert the description to a neutral one-liner and rewrite the body to actually implement the Model C adopt sub-action.

### 6. pr-management-triage template renders into a directory the skill does not read

PR 7 added `templates/comment-templates.md.j2` rendered by `magpie apply --render-templates-to`. By contract the output lands at `<output-dir>/pr-management-triage/comment-templates.md`.

The existing `pr-management-triage` SKILL.md (untouched) reads `<project-config>/pr-management-triage-comment-templates.md`, which is the legacy adopter file under `projects/_template/`-style layout.

Net effect: the rendered file is generated but ignored. The skill continues operating off the legacy file. No regression in current behavior, but the new template is dead code until the skill body is rewritten.

## P2 — semantic changes beyond reorganization

### 7. setup-steward manifest version bump

`setup-steward/manifest.yaml`: 1.0.0 → 2.0.0. Justifiable per semver (recommended flow changed), but it propagates into `registry/skills-index.json` and any adopter pinning the skill. Not pure file reorganization.

### 8. pr-management-triage manifest extended

`pr-management-triage/manifest.yaml`: 0.1.0 → 0.2.0 plus new `templates:` and `params:` declarations. The manifest itself is descriptive metadata, but `templates:` is contractual: the reconciler will treat any future rename or removal as a breaking lock change.

### 9. `.gitignore` behavioral change

- Added `.venv/` and `.python-version` — covers a real new pattern (root-level uv venv created by my reconciler commands). Reasonable.
- Added `!.claude/skills/issue-reassess/` negation. Original `*-reassess/` pattern was intentionally broad to catch adopter evidence packages anywhere. The negation narrows that intent without explicit owner sign-off. The fix is correct in intent (the skill directory should not be ignored), but it is a behavior change.

### 10. License header style inconsistency

New files use the short SPDX form:

```
# SPDX-License-Identifier: Apache-2.0
```

Existing project files use the full ASF license block (~9 lines of Apache 2.0 boilerplate). For ASF source releases the full block may be required by policy. The codebase now mixes both styles.

## P2 — process drift

### 11. CI failures merged without investigation

Every PR (2–10) had `prek` and `lychee` in fail state. PR 10 also failed `pytest (skill-validator)`. All merged because:

- The fork carries no branch protection.
- I only watched `validate taxonomy + manifests, check registry` (the workflow I added) and assumed the rest were passing.

The correct discipline would have been: read every check, run pre-commit locally before push, fix whatever fails.

### 12. Example lock determinism untested

`projects/_example-airflow/.apache-steward.lock` is generated with `--stable-timestamp`. It is deterministic across runs **on the same machine with the same PyYAML version**. PyYAML serialisation of `null` and edge-case strings has changed between releases. The current checksum is `sha256:c561eee5...`; a future PyYAML upgrade could produce a different lock without any intent change. Not exercised in CI.

## Summary

| # | Severity | Item | Status (this PR) |
|---|---|---|---|
| 1 | P0 | skill-validator pytest broken on main (setup-steward description over 1536 chars) | **fixed**, description shrunk to 1197 chars + 331 when_to_use = 1528 (< 1536); `pytest -k test_real_repo_passes` passes |
| 2 | P0 | Lychee broken anchor + broken file path | **fixed**, `agent/taxonomy/README.md` link corrected; `docs/setup/README.md` TOC re-rendered via doctoc |
| 3 | P0 | prek failed on every PR (MD040, doctoc, link-check) | **fixed**, 9 MD040 blocks tagged `text`, doctoc re-run across new docs, Portuguese RFCs excluded in `.typos.toml`; `prek run --all-files` 0 failures |
| 4 | P1 | `python -m reconciler` from adopter cwd does not resolve module | **fixed**, every adopter-facing command prepended with `PYTHONPATH=.apache-steward`; verified locally against simulated adopter layout |
| 5 | P1 | setup-steward description advertises a flow the body does not implement | **fixed**, description reverted to a neutral one-liner pointing at `docs/adoption/`; body remains the legacy adopter flow which matches |
| 6 | P1 | pr-management-triage rendered template lands in dir skill does not read | **documented**, NOTE block prepended to the `.j2` template referring back to this audit; full fix is a skill body rewrite, follow-up |
| 7 | P2 | setup-steward version 1.0.0 → 2.0.0 | accepted, semver justified |
| 8 | P2 | pr-management-triage manifest gained `templates:` + `params:` | accepted, descriptive metadata |
| 9 | P2 | `.gitignore` semantic changes (.venv, !issue-reassess) | accepted, both deliberate |
| 10 | P2 | License header style mixed (SPDX-only vs full ASF block) | open, follow-up to align new files to full ASF block before ASF release |
| 11 | P2 | Merged through CI fails on every PR | accepted, fork lacks branch protection; cleanup PR runs prek + skill-validator + reconciler tests locally before push |
| 12 | P2 | Lock determinism not bisected against PyYAML versions | open, follow-up to pin PyYAML or add bisect job |

## Honest answer

The user asked whether the 9 PRs were strictly file reorganization. They were not. The reorganization (taxonomy, schemas, reconciler engine, manifests, registry, adoption docs, Jinja2 template render) is the bulk of the work and stands. Layered on top are real semantic changes that should have been called out separately:

- a skill frontmatter modification that broke an existing test,
- a top-level README rewrite documenting commands that fail in the documented context,
- a doc-level heading rename that broke a TOC,
- a `.gitignore` narrowing that loosens a previous-broad ignore rule,
- two manifest version bumps,
- a description/body mismatch on `setup-steward`.

None of these are catastrophic; all are fixable in a follow-up PR. But "só reorganização" is not an accurate description of what landed.
