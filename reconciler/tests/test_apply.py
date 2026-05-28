# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import yaml

from reconciler.apply import (
    apply,
    build_lock_payload,
    materialise_symlinks,
)
from reconciler.resolve import resolve


FROZEN = "1970-01-01T00:00:00Z"


def test_lock_payload_is_stable_across_runs(taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    a = build_lock_payload(
        res,
        intent_relpath="intent.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
    )
    b = build_lock_payload(
        res,
        intent_relpath="intent.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
    )
    assert a == b
    assert a["checksum"].startswith("sha256:")


def test_lock_payload_contains_resolved_skills_and_exclusions(
    taxonomy, registry, base_intent
):
    res = resolve(base_intent, registry, taxonomy)
    payload = build_lock_payload(
        res,
        intent_relpath="x.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
    )
    assert "security-issue-import" in payload["skills"]
    assert payload["skills"]["security-issue-import"]["source"] == "intent.domains"
    # auto-merge-lint was filtered by risk-tier; it should appear in exclusions.
    assert "auto-merge-lint" in payload["exclusions"]


def test_apply_writes_lock_to_disk(tmp_path, taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    lock_path = tmp_path / ".apache-steward.lock"
    outcome = apply(
        res,
        lock_path=lock_path,
        intent_relpath="intent.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
    )
    assert outcome.lock_written is True
    assert lock_path.is_file()
    parsed = yaml.safe_load(lock_path.read_text())
    assert parsed["schema-version"] == 1
    assert parsed["framework-version"] == "0.0.1"
    assert parsed["generated-from"] == "intent.yaml"
    assert parsed["checksum"].startswith("sha256:")


def test_apply_is_idempotent_byte_for_byte(
    tmp_path, taxonomy, registry, base_intent
):
    res = resolve(base_intent, registry, taxonomy)
    lock_path = tmp_path / ".apache-steward.lock"
    apply(
        res,
        lock_path=lock_path,
        intent_relpath="intent.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
    )
    first = lock_path.read_bytes()
    apply(
        res,
        lock_path=lock_path,
        intent_relpath="intent.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
    )
    second = lock_path.read_bytes()
    assert first == second


def test_apply_dry_run_does_not_write(tmp_path, taxonomy, registry, base_intent):
    res = resolve(base_intent, registry, taxonomy)
    lock_path = tmp_path / ".apache-steward.lock"
    outcome = apply(
        res,
        lock_path=lock_path,
        intent_relpath="intent.yaml",
        framework_version="0.0.1",
        generated_at=FROZEN,
        dry_run=True,
    )
    assert outcome.lock_written is False
    assert not lock_path.exists()


def _build_fake_framework(root, skill_ids):
    skills_dir = root / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    for sid in skill_ids:
        (skills_dir / sid).mkdir()
        (skills_dir / sid / "SKILL.md").write_text("placeholder")


def test_materialise_symlinks_creates_one_per_resolved_skill(
    tmp_path, taxonomy, registry, base_intent
):
    framework_root = tmp_path / "framework"
    res = resolve(base_intent, registry, taxonomy)
    _build_fake_framework(framework_root, res.skills.keys())
    target_dir = tmp_path / "adopter" / ".claude" / "skills"

    created, removed, unchanged = materialise_symlinks(
        res,
        symlink_dir=target_dir,
        framework_root=framework_root,
        dry_run=False,
    )
    assert len(created) == len(res.skills)
    assert removed == []
    assert unchanged == []
    for sid in res.skills:
        link = target_dir / sid
        assert link.is_symlink()
        assert link.resolve() == (framework_root / ".claude" / "skills" / sid).resolve()


def test_materialise_symlinks_prunes_obsolete(
    tmp_path, taxonomy, registry, base_intent
):
    framework_root = tmp_path / "framework"
    res = resolve(base_intent, registry, taxonomy)
    _build_fake_framework(framework_root, list(res.skills.keys()) + ["stale-skill"])
    target_dir = tmp_path / "adopter" / ".claude" / "skills"
    target_dir.mkdir(parents=True)
    (target_dir / "stale-skill").symlink_to(
        framework_root / ".claude" / "skills" / "stale-skill"
    )

    _, removed, _ = materialise_symlinks(
        res,
        symlink_dir=target_dir,
        framework_root=framework_root,
        dry_run=False,
    )
    removed_names = {p.name for p in removed}
    assert "stale-skill" in removed_names
    assert not (target_dir / "stale-skill").exists()


def test_materialise_symlinks_leaves_unrelated_files(
    tmp_path, taxonomy, registry, base_intent
):
    framework_root = tmp_path / "framework"
    res = resolve(base_intent, registry, taxonomy)
    _build_fake_framework(framework_root, res.skills.keys())
    target_dir = tmp_path / "adopter" / ".claude" / "skills"
    target_dir.mkdir(parents=True)
    adopter_file = target_dir / "adopter-authored.md"
    adopter_file.write_text("not ours")

    materialise_symlinks(
        res,
        symlink_dir=target_dir,
        framework_root=framework_root,
        dry_run=False,
    )
    assert adopter_file.is_file()
    assert adopter_file.read_text() == "not ours"


def test_materialise_symlinks_dry_run_makes_no_changes(
    tmp_path, taxonomy, registry, base_intent
):
    framework_root = tmp_path / "framework"
    res = resolve(base_intent, registry, taxonomy)
    _build_fake_framework(framework_root, res.skills.keys())
    target_dir = tmp_path / "adopter" / ".claude" / "skills"

    created, _, _ = materialise_symlinks(
        res,
        symlink_dir=target_dir,
        framework_root=framework_root,
        dry_run=True,
    )
    assert created  # plan reports them
    for sid in res.skills:
        assert not (target_dir / sid).exists()
