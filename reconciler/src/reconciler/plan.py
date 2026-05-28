# SPDX-License-Identifier: Apache-2.0
"""Compute and format a plan diff between current lock and resolution.

Pure. The CLI in ``reconciler.__main__`` loads the on-disk lock,
hands the parsed dict in, receives a string, and prints it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .resolve import Resolution


@dataclass
class PlanRow:
    action: str  # "add", "remove", "change", "keep"
    skill_id: str
    detail: str


def compute_plan(current_lock: dict | None, resolution: Resolution) -> list[PlanRow]:
    rows: list[PlanRow] = []
    current_skills: dict[str, dict] = {}
    if current_lock:
        current_skills = dict(current_lock.get("skills") or {})

    resolved_ids = set(resolution.skills.keys())
    current_ids = set(current_skills.keys())

    for sid in sorted(resolved_ids - current_ids):
        skill = resolution.skills[sid]
        rows.append(
            PlanRow(
                action="add",
                skill_id=sid,
                detail=f"{skill.version} ({skill.source})",
            )
        )

    for sid in sorted(current_ids - resolved_ids):
        reason = "no longer resolves"
        excl = resolution.exclusions.get(sid)
        if excl is not None:
            reason = excl.reason
        rows.append(
            PlanRow(
                action="remove",
                skill_id=sid,
                detail=reason,
            )
        )

    for sid in sorted(resolved_ids & current_ids):
        resolved = resolution.skills[sid]
        previous = current_skills[sid]
        prev_version = previous.get("version")
        if prev_version != resolved.version:
            rows.append(
                PlanRow(
                    action="change",
                    skill_id=sid,
                    detail=f"{prev_version} -> {resolved.version}",
                )
            )
            continue
        prev_params = previous.get("params") or {}
        if (resolved.params or {}) != prev_params:
            rows.append(
                PlanRow(
                    action="change",
                    skill_id=sid,
                    detail="params updated",
                )
            )
            continue
        rows.append(
            PlanRow(action="keep", skill_id=sid, detail=f"{resolved.version}")
        )

    return rows


_ACTION_GLYPH = {
    "add": "+",
    "remove": "-",
    "change": "~",
    "keep": " ",
}


def format_plan(
    rows: list[PlanRow], warnings: list, *, show_keeps: bool = False
) -> str:
    add_count = sum(1 for r in rows if r.action == "add")
    remove_count = sum(1 for r in rows if r.action == "remove")
    change_count = sum(1 for r in rows if r.action == "change")
    keep_count = sum(1 for r in rows if r.action == "keep")

    lines: list[str] = []
    lines.append(
        f"Plan: +{add_count} -{remove_count} ~{change_count} ={keep_count}"
    )
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in warnings:
            scope = f" [{warning.skill_id}]" if warning.skill_id else ""
            lines.append(f"  ! {warning.code}{scope}: {warning.message}")

    lines.append("")
    lines.append("Skills:")
    visible_rows = [r for r in rows if show_keeps or r.action != "keep"]
    if not visible_rows:
        lines.append("  (no changes)")
    else:
        width = max(len(r.skill_id) for r in visible_rows)
        for row in visible_rows:
            lines.append(
                f"  {_ACTION_GLYPH[row.action]} {row.skill_id:<{width}}  {row.detail}"
            )
    lines.append("")
    return "\n".join(lines)
