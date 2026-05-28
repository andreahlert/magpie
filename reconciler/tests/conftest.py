# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for reconciler tests.

The reconciler is pure (no I/O). Tests construct minimal in-memory
taxonomy and registry dicts so they exercise the resolution rules
without touching the real ``agent/taxonomy/`` or
``registry/skills-index.json`` files.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def taxonomy() -> dict:
    return {
        "risk-tiers": {
            "schema-version": 1,
            "tiers": [
                {"id": "read-only", "order": 0},
                {"id": "suggest-only", "order": 1},
                {"id": "write-comment", "order": 2},
                {"id": "draft-pr", "order": 3},
                {"id": "write-merge", "order": 4},
            ],
        },
        "domains": {
            "schema-version": 1,
            "domains": [
                {"id": "security"},
                {"id": "pr-queue"},
                {"id": "issue-queue"},
                {"id": "contributor-lifecycle"},
                {"id": "dev-cycle"},
                {"id": "framework-meta"},
            ],
        },
        "audiences": {
            "schema-version": 1,
            "audiences": [
                {"id": "maintainer-inbound"},
                {"id": "security-pmc"},
                {"id": "contributor-facing"},
                {"id": "framework-operator"},
                {"id": "dev-self"},
            ],
        },
        "integrations": {
            "schema-version": 1,
            "integrations": [
                {"id": "github"},
                {"id": "gmail"},
                {"id": "vulnogram"},
                {"id": "sandbox"},
                {"id": "privacy-llm"},
            ],
        },
    }


@pytest.fixture
def registry() -> dict:
    """Tiny registry exercising every classification path."""
    return {
        "schema-version": 1,
        "skills": {
            "security-issue-import": {
                "version": "1.0.0",
                "domains": ["security"],
                "audiences": ["security-pmc"],
                "risk-tier": "write-comment",
                "integrations": ["gmail", "github", "privacy-llm", "sandbox"],
                "requires": ["setup-isolated-setup-install"],
                "status": "stable",
            },
            "security-cve-allocate": {
                "version": "1.0.0",
                "domains": ["security"],
                "audiences": ["security-pmc"],
                "risk-tier": "write-comment",
                "integrations": ["github", "vulnogram", "privacy-llm", "sandbox"],
                "requires": ["security-issue-import"],
                "status": "stable",
            },
            "setup-isolated-setup-install": {
                "version": "1.0.0",
                "domains": ["framework-meta"],
                "audiences": ["framework-operator"],
                "risk-tier": "read-only",
                "integrations": ["sandbox"],
                "status": "stable",
            },
            "pr-management-triage": {
                "version": "0.1.0",
                "domains": ["pr-queue"],
                "audiences": ["maintainer-inbound"],
                "risk-tier": "write-comment",
                "integrations": ["github"],
                "status": "experimental",
            },
            "auto-merge-lint": {
                "version": "0.1.0",
                "domains": ["pr-queue"],
                "audiences": ["maintainer-inbound"],
                "risk-tier": "write-merge",
                "integrations": ["github"],
                "status": "off",
            },
        },
    }


@pytest.fixture
def base_intent() -> dict:
    """Minimal intent covering security + pr-queue at draft-pr max.

    framework-meta is intentionally absent so that
    setup-isolated-setup-install enters the resolution only via the
    `requires` closure from a security skill.
    """
    return {
        "schema-version": 1,
        "framework": {"install": {"method": "git-branch", "ref": "main"}},
        "capabilities": {
            "domains": ["security", "pr-queue"],
            "audiences": ["security-pmc", "maintainer-inbound"],
            "risk-tier-max": "draft-pr",
            "integrations": [
                "gmail",
                "github",
                "vulnogram",
                "privacy-llm",
                "sandbox",
            ],
        },
    }
