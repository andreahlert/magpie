# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from reconciler.resolve import resolve


def test_capability_filter_includes_matching_skills(taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    ids = set(res.skills.keys())
    assert "security-issue-import" in ids
    assert "security-cve-allocate" in ids
    assert "pr-management-triage" in ids


def test_setup_install_pulled_in_via_requires(taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    assert "setup-isolated-setup-install" in res.skills
    assert res.skills["setup-isolated-setup-install"].source == "skill.requires"


def test_auto_merge_filtered_out_when_risk_max_below_write_merge(
    taxonomy, registry, base_intent
):
    res = resolve(base_intent, registry, taxonomy)
    assert "auto-merge-lint" not in res.skills
    assert res.exclusions["auto-merge-lint"].reason == "intent.capabilities.risk-tier-max"


def test_missing_integration_excludes_skill(taxonomy, registry, base_intent):
    base_intent["capabilities"]["integrations"] = ["github"]
    res = resolve(base_intent, registry, taxonomy)
    assert "security-issue-import" not in res.skills
    assert (
        res.exclusions["security-issue-import"].reason
        == "intent.capabilities.integrations"
    )


def test_exclude_override_drops_skill(taxonomy, registry, base_intent):
    base_intent["overrides"] = {"exclude": ["pr-management-triage"]}
    res = resolve(base_intent, registry, taxonomy)
    assert "pr-management-triage" not in res.skills
    assert res.exclusions["pr-management-triage"].reason == "intent.overrides.exclude"


def test_force_include_against_risk_tier_warns(taxonomy, registry, base_intent):
    base_intent["overrides"] = {"force-include": ["auto-merge-lint"]}
    res = resolve(base_intent, registry, taxonomy)
    assert "auto-merge-lint" in res.skills
    codes = {w.code for w in res.warnings}
    assert "force-include-violates-risk-tier" in codes
    assert "force-include-off" in codes


def test_pin_overrides_registry_version(taxonomy, registry, base_intent):
    base_intent["overrides"] = {"pin": {"security-issue-import": "0.9.0"}}
    res = resolve(base_intent, registry, taxonomy)
    assert res.skills["security-issue-import"].version == "0.9.0"
    codes = {w.code for w in res.warnings}
    assert "pinned-version-mismatch" in codes


def test_force_include_unknown_skill_warns(taxonomy, registry, base_intent):
    base_intent["overrides"] = {"force-include": ["does-not-exist"]}
    res = resolve(base_intent, registry, taxonomy)
    codes = {w.code for w in res.warnings}
    assert "unknown-force-include" in codes
    assert "does-not-exist" not in res.skills


def test_params_merge_defaults_with_intent_overrides(
    taxonomy, registry, base_intent
):
    defaults = {"security-issue-import": {"default-window-days": 14, "locale": "en"}}
    base_intent["overrides"] = {
        "params": {"security-issue-import": {"locale": "pt-BR"}}
    }
    res = resolve(base_intent, registry, taxonomy, defaults)
    params = res.skills["security-issue-import"].params
    assert params == {"default-window-days": 14, "locale": "pt-BR"}


def test_narrow_intent_excludes_unrelated_domain(taxonomy, registry, base_intent):
    base_intent["capabilities"]["domains"] = ["security", "framework-meta"]
    res = resolve(base_intent, registry, taxonomy)
    assert "pr-management-triage" not in res.skills
    assert res.exclusions["pr-management-triage"].reason == "intent.capabilities.domains"


def test_excluded_skill_does_not_appear_as_exclusion_when_force_included(
    taxonomy, registry, base_intent
):
    base_intent["overrides"] = {
        "exclude": ["pr-management-triage"],
        "force-include": ["pr-management-triage"],
    }
    res = resolve(base_intent, registry, taxonomy)
    # force-include after exclude wins. The skill is enabled and not listed as an exclusion.
    assert "pr-management-triage" in res.skills
    assert "pr-management-triage" not in res.exclusions
