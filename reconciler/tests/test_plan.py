# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from reconciler.plan import compute_plan, format_plan
from reconciler.resolve import resolve


def test_plan_against_empty_lock_lists_every_skill_as_add(
    taxonomy, registry, base_intent
):
    res = resolve(base_intent, registry, taxonomy)
    rows = compute_plan(None, res)
    actions = {row.action for row in rows}
    assert actions == {"add"}
    assert len(rows) == len(res.skills)


def test_plan_against_current_lock_with_no_change(
    taxonomy, registry, base_intent
):
    res = resolve(base_intent, registry, taxonomy)
    current_lock = {
        "skills": {
            sid: {"version": skill.version, "params": skill.params}
            for sid, skill in res.skills.items()
        }
    }
    rows = compute_plan(current_lock, res)
    assert all(row.action == "keep" for row in rows)


def test_plan_version_change_is_detected(taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    current_lock = {
        "skills": {
            "security-issue-import": {"version": "0.9.0"},
        }
    }
    rows = compute_plan(current_lock, res)
    change_rows = [r for r in rows if r.action == "change"]
    assert any(r.skill_id == "security-issue-import" for r in change_rows)


def test_plan_removed_skill_carries_reason(taxonomy, registry, base_intent):
    base_intent["overrides"] = {"exclude": ["pr-management-triage"]}
    res = resolve(base_intent, registry, taxonomy)
    current_lock = {
        "skills": {"pr-management-triage": {"version": "0.1.0"}}
    }
    rows = compute_plan(current_lock, res)
    removed = [r for r in rows if r.action == "remove"]
    assert removed
    assert any(
        r.skill_id == "pr-management-triage"
        and "intent.overrides.exclude" in r.detail
        for r in removed
    )


def test_format_plan_summary_counts(taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    rows = compute_plan(None, res)
    output = format_plan(rows, res.warnings)
    assert "Plan:" in output
    assert "+" in output
    assert "Skills:" in output
