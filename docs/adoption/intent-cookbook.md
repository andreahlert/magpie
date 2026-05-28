<!-- SPDX-License-Identifier: Apache-2.0 -->

# Intent cookbook

Sample `.apache-steward.intent.yaml` files by adopter shape. Copy the closest match, edit values, run `magpie plan` to see what it resolves to.

## A. Security-only adopter

Small project, no PR queue automation yet, just wants to handle inbound security reports under PMC review.

```yaml
schema-version: 1

framework:
  install: { method: git-branch, ref: main }

capabilities:
  domains: [security, framework-meta]
  audiences: [security-pmc, framework-operator]
  risk-tier-max: write-comment
  integrations: [github, gmail, vulnogram, privacy-llm, sandbox]

overrides:
  params:
    security-issue-import:
      security-list-mailbox: "label:security@yourproject.org"
      tracker-repo: "yourproject-s/yourproject-s"
```

What lands: every `domain: security` skill at or below `write-comment` + framework-meta. No PR queue skills, no issue triage. About 9 skills.

## B. Full PMC adopter (security + PR + issue + mentoring)

Established project with active PR queue, issue triage, mentorship goals, security flow.

```yaml
schema-version: 1

framework:
  install: { method: git-branch, ref: main }

capabilities:
  domains:
    - security
    - pr-queue
    - issue-queue
    - contributor-lifecycle
    - framework-meta
  audiences:
    - security-pmc
    - maintainer-inbound
    - contributor-facing
    - framework-operator
  risk-tier-max: draft-pr
  integrations: [github, gmail, ponymail, vulnogram, privacy-llm, sandbox]

overrides:
  params:
    pr-management-triage:
      project_display_name: "Your Project"
      quality_criteria_url: "https://yourproject.org/contributing#pr-quality"
      # ...remaining required params...
    security-issue-import:
      security-list-mailbox: "label:security-list"
      tracker-repo: "yourproject-s/yourproject-s"
```

Closest match to [`projects/_example-airflow/`](../../projects/_example-airflow/).

## C. Dev-cycle focus

Project mostly wants pre-flight self-review and agent-drafted patches for committers, less interested in inbound queue management.

```yaml
schema-version: 1

framework:
  install: { method: git-branch, ref: main }

capabilities:
  domains: [dev-cycle, framework-meta]
  audiences: [dev-self, framework-operator]
  risk-tier-max: draft-pr
  integrations: [github, sandbox]
```

What lands: write-skill, issue-reproducer (for local repro), framework-meta skills. Very narrow set.

## D. Non-ASF adopter

Closed-source corporate repo, no public mailing list, GitHub-only.

```yaml
schema-version: 1

framework:
  install: { method: git-tag, ref: v0.4.0 }   # pinned per ASF distribution norms not applicable

capabilities:
  domains: [pr-queue, issue-queue, contributor-lifecycle]
  audiences: [maintainer-inbound, contributor-facing]
  risk-tier-max: draft-pr
  integrations: [github]

overrides:
  exclude:
    # Project does not use a private security list flow; security
    # reports come through GitHub Security Advisories instead.
    # Security domain itself is unselected above.
```

## How to read these

Every cookbook entry produces a different resolved skill set. Use `magpie plan` after copying to confirm the resulting set matches expectations before `magpie apply`.

If a skill you expected to land is missing, check the exclusion reasons in the plan output:

```
Plan: +9 -0 ~0 =0
...
```

Exclusions live in the lock file under the `exclusions:` block once you apply, each with the rule that filtered the skill out. Tighten or loosen the matching axis to bring it in.
