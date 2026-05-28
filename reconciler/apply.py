# SPDX-License-Identifier: Apache-2.0
"""Materialise a Resolution to disk.

PR 6 ships ``apply`` behind an ``--experimental`` flag. Apply is
two things:

1. **Lock write.** Serialise the Resolution into a YAML lock at
   the configured path. The lock conforms to
   ``reconciler/schemas/lock.schema.json``.
2. **Workspace materialisation (optional).** When the caller
   passes ``--symlink-target <dir>`` and a framework checkout
   path, apply creates a symlink per resolved skill from
   ``<symlink-target>/<skill-id>`` to
   ``<framework-root>/.claude/skills/<skill-id>``. Existing
   symlinks under ``<symlink-target>`` that point into the
   framework checkout are pruned when they no longer correspond
   to a resolved skill. Non-symlinks are left alone (we never
   delete adopter-authored files).

Apply is **idempotent**: re-running with the same intent
produces the same lock and the same set of symlinks.

Apply is **safe by default**: without ``--symlink-target`` only
the lock file is written.

Adopter-facing wiring (replacing the legacy family-based
takeover) lands in PR 9.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from .resolve import Resolution


@dataclass
class ApplyOutcome:
    lock_path: Path
    lock_written: bool                  # False on --dry-run
    symlinks_created: list[Path]
    symlinks_removed: list[Path]
    symlinks_unchanged: list[Path]
    templates_rendered: list[Path]
    checksum: str


def _stable_serialise(payload: dict) -> str:
    """Canonical YAML dump: sorted keys, no aliases, trailing newline."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML required to serialise lock")
    text = yaml.safe_dump(
        payload,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )
    if not text.endswith("\n"):
        text += "\n"
    return text


def _compute_checksum(payload_without_checksum: dict) -> str:
    serialised = _stable_serialise(payload_without_checksum)
    digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_lock_payload(
    resolution: Resolution,
    *,
    intent_relpath: str,
    framework_version: str,
    generated_at: str | None = None,
) -> dict:
    """Pure: turn a Resolution into the dict that hits disk."""
    payload: dict = {
        "schema-version": 1,
        "generated-from": intent_relpath,
        "generated-at": generated_at
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "framework-version": framework_version,
        "skills": {},
    }
    for sid in sorted(resolution.skills):
        skill = resolution.skills[sid]
        entry: dict = {
            "version": skill.version,
            "source": skill.source,
        }
        if skill.integrations_resolved:
            entry["integrations-resolved"] = list(skill.integrations_resolved)
        if skill.params:
            entry["params"] = dict(skill.params)
        payload["skills"][sid] = entry
    if resolution.exclusions:
        payload["exclusions"] = {
            sid: {"reason": excl.reason}
            for sid, excl in sorted(resolution.exclusions.items())
        }
    if resolution.warnings:
        payload["warnings"] = [
            {
                "code": w.code,
                "message": w.message,
                **({"skill": w.skill_id} if w.skill_id else {}),
            }
            for w in resolution.warnings
        ]

    payload["checksum"] = _compute_checksum(payload)
    return payload


def write_lock(payload: dict, lock_path: Path, *, dry_run: bool) -> bool:
    if dry_run:
        return False
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(_stable_serialise(payload), encoding="utf-8")
    return True


def _is_framework_symlink(path: Path, framework_root: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        target = path.resolve()
    except OSError:
        return False
    try:
        target.relative_to(framework_root.resolve())
    except ValueError:
        return False
    return True


def materialise_symlinks(
    resolution: Resolution,
    *,
    symlink_dir: Path,
    framework_root: Path,
    dry_run: bool,
) -> tuple[list[Path], list[Path], list[Path]]:
    """Reconcile the symlink directory with the resolution.

    Returns (created, removed, unchanged) as absolute paths.
    """
    framework_skills = (framework_root / ".claude" / "skills").resolve()
    if not framework_skills.is_dir():
        raise FileNotFoundError(
            f"framework skills directory missing: {framework_skills}"
        )

    desired: dict[str, Path] = {}
    for sid in resolution.skills:
        target = framework_skills / sid
        if not target.is_dir():
            raise FileNotFoundError(
                f"resolved skill '{sid}' has no directory at {target}"
            )
        desired[sid] = target

    symlink_dir = symlink_dir.resolve()
    created: list[Path] = []
    removed: list[Path] = []
    unchanged: list[Path] = []

    if not dry_run:
        symlink_dir.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Path] = {}
    if symlink_dir.is_dir():
        for entry in symlink_dir.iterdir():
            if _is_framework_symlink(entry, framework_root):
                existing[entry.name] = entry

    for sid in sorted(existing):
        if sid not in desired:
            if not dry_run:
                existing[sid].unlink()
            removed.append(existing[sid])

    for sid, target in sorted(desired.items()):
        link_path = symlink_dir / sid
        if sid in existing:
            current_target = existing[sid].resolve()
            if current_target == target.resolve():
                unchanged.append(link_path)
                continue
            if not dry_run:
                existing[sid].unlink()
                link_path.symlink_to(target)
            created.append(link_path)
            continue
        if not dry_run:
            if link_path.exists() and not link_path.is_symlink():
                raise FileExistsError(
                    f"{link_path} exists and is not a symlink; refusing to overwrite"
                )
            link_path.symlink_to(target)
        created.append(link_path)

    return created, removed, unchanged


def render_templates(
    resolution: Resolution,
    *,
    framework_root: Path,
    output_dir: Path,
    dry_run: bool,
) -> list[Path]:
    """Render every Jinja2 template declared by every resolved skill.

    Reads the framework manifest at
    ``framework_root/.claude/skills/<skill-id>/manifest.yaml`` to
    discover ``templates:``. For each template, renders with the
    effective params (the merged values already attached to the
    resolved skill) and writes to
    ``output_dir/<skill-id>/<basename without .j2>``.

    Returns the list of written paths (or what *would* be written
    on dry-run).
    """
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML required to render templates")
    try:
        from jinja2 import (
            Environment,
            FileSystemLoader,
            StrictUndefined,
            select_autoescape,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Jinja2 is required to render templates. Install with `pip install jinja2`."
        ) from exc

    written: list[Path] = []
    skills_root = framework_root / ".claude" / "skills"

    for sid in sorted(resolution.skills):
        skill_dir = skills_root / sid
        manifest_path = skill_dir / "manifest.yaml"
        if not manifest_path.is_file():
            continue
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        templates = manifest.get("templates") or []
        if not templates:
            continue

        env = Environment(
            loader=FileSystemLoader(str(skill_dir)),
            autoescape=select_autoescape(disabled_extensions=("j2",), default_for_string=False),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        params = resolution.skills[sid].params or {}
        skill_output = output_dir / sid
        if not dry_run:
            skill_output.mkdir(parents=True, exist_ok=True)

        for rel_template in templates:
            template = env.get_template(rel_template)
            rendered = template.render(**params)
            basename = Path(rel_template).name
            if basename.endswith(".j2"):
                basename = basename[:-3]
            target = skill_output / basename
            if not dry_run:
                target.write_text(rendered, encoding="utf-8")
            written.append(target)

    return written


def apply(
    resolution: Resolution,
    *,
    lock_path: Path,
    intent_relpath: str,
    framework_version: str,
    framework_root: Path | None = None,
    symlink_dir: Path | None = None,
    render_output_dir: Path | None = None,
    dry_run: bool = False,
    generated_at: str | None = None,
) -> ApplyOutcome:
    payload = build_lock_payload(
        resolution,
        intent_relpath=intent_relpath,
        framework_version=framework_version,
        generated_at=generated_at,
    )
    lock_written = write_lock(payload, lock_path, dry_run=dry_run)

    created: list[Path] = []
    removed: list[Path] = []
    unchanged: list[Path] = []
    if symlink_dir is not None and framework_root is not None:
        created, removed, unchanged = materialise_symlinks(
            resolution,
            symlink_dir=symlink_dir,
            framework_root=framework_root,
            dry_run=dry_run,
        )

    rendered: list[Path] = []
    if render_output_dir is not None and framework_root is not None:
        rendered = render_templates(
            resolution,
            framework_root=framework_root,
            output_dir=render_output_dir,
            dry_run=dry_run,
        )

    return ApplyOutcome(
        lock_path=lock_path,
        lock_written=lock_written,
        symlinks_created=created,
        symlinks_removed=removed,
        symlinks_unchanged=unchanged,
        templates_rendered=rendered,
        checksum=payload["checksum"],
    )
