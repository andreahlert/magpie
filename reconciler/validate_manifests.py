# SPDX-License-Identifier: Apache-2.0
"""Validate every ``manifest.yaml`` under ``.claude/skills/``.

Checks:
  1. Manifest matches ``reconciler/schemas/skill-manifest.schema.json``.
  2. Every ``domains[*]``, ``audiences[*]``, ``risk-tier``, and
     ``integrations[*]`` value is defined in the canonical taxonomy
     under ``agent/taxonomy/``.
  3. ``id`` matches the directory name.
  4. ``requires[*]`` and ``replaces[*]`` reference skills that exist
     in the tree (warning rather than error if the target is a
     dependency from outside the framework boundary).
  5. If ``params.schema`` / ``params.defaults`` is declared, the
     referenced files exist relative to the manifest.

Run from the repo root::

    uv run --with pyyaml --with jsonschema python reconciler/validate_manifests.py

Exits non-zero on any error. Soft failures (missing dependency
referenced as informational) are printed but do not fail the run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("validate_manifests: PyYAML required\n")
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.stderr.write(
        "validate_manifests: jsonschema required "
        "(uv run --with jsonschema ...)\n"
    )
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
TAXONOMY_DIR = REPO_ROOT / "agent" / "taxonomy"
SCHEMA_PATH = REPO_ROOT / "reconciler" / "schemas" / "skill-manifest.schema.json"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_taxonomy() -> dict[str, set[str]]:
    return {
        "domains": {entry["id"] for entry in load_yaml(TAXONOMY_DIR / "domains.yaml")["domains"]},
        "audiences": {entry["id"] for entry in load_yaml(TAXONOMY_DIR / "audiences.yaml")["audiences"]},
        "risk-tiers": {entry["id"] for entry in load_yaml(TAXONOMY_DIR / "risk-tiers.yaml")["tiers"]},
        "integrations": {entry["id"] for entry in load_yaml(TAXONOMY_DIR / "integrations.yaml")["integrations"]},
    }


def discover_manifests() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.rglob("manifest.yaml"))


def discover_skill_ids() -> set[str]:
    """All directories under .claude/skills that contain SKILL.md."""
    if not SKILLS_DIR.is_dir():
        return set()
    ids: set[str] = set()
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        ids.add(skill_md.parent.name)
    return ids


def validate_against_taxonomy(
    manifest: dict, taxonomy: dict[str, set[str]]
) -> list[str]:
    errors: list[str] = []
    for entry in manifest.get("domains", []):
        if entry not in taxonomy["domains"]:
            errors.append(f"unknown domain '{entry}'")
    for entry in manifest.get("audiences", []):
        if entry not in taxonomy["audiences"]:
            errors.append(f"unknown audience '{entry}'")
    risk = manifest.get("risk-tier")
    if risk is not None and risk not in taxonomy["risk-tiers"]:
        errors.append(f"unknown risk-tier '{risk}'")
    for entry in manifest.get("integrations", []):
        if entry not in taxonomy["integrations"]:
            errors.append(f"unknown integration '{entry}'")
    return errors


def validate_manifest(
    path: Path,
    schema_validator: Draft202012Validator,
    taxonomy: dict[str, set[str]],
    known_skill_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single manifest file."""
    rel = path.relative_to(REPO_ROOT)
    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest = load_yaml(path)
    except yaml.YAMLError as exc:
        return [f"{rel}: YAML parse error: {exc}"], []

    for schema_error in sorted(
        schema_validator.iter_errors(manifest), key=lambda e: list(e.path)
    ):
        location = "/".join(str(p) for p in schema_error.path) or "<root>"
        errors.append(f"{rel}: schema: {location}: {schema_error.message}")

    for issue in validate_against_taxonomy(manifest, taxonomy):
        errors.append(f"{rel}: taxonomy: {issue}")

    declared_id = manifest.get("id")
    actual_id = path.parent.name
    if declared_id and declared_id != actual_id:
        errors.append(
            f"{rel}: id mismatch: manifest says '{declared_id}', directory is '{actual_id}'"
        )

    for dep in manifest.get("requires", []) or []:
        if dep not in known_skill_ids:
            warnings.append(
                f"{rel}: requires '{dep}' which is not a skill in this tree (cross-boundary dependency, informational)"
            )
    for dep in manifest.get("replaces", []) or []:
        if dep in known_skill_ids:
            warnings.append(
                f"{rel}: replaces '{dep}' but that skill still exists in the tree"
            )

    params = manifest.get("params") or {}
    for key in ("schema", "defaults"):
        target = params.get(key)
        if target and not (path.parent / target).is_file():
            errors.append(f"{rel}: params.{key} points to missing file '{target}'")

    return errors, warnings


def main() -> int:
    if not SCHEMA_PATH.is_file():
        sys.stderr.write(f"validate_manifests: missing schema at {SCHEMA_PATH}\n")
        return 2
    if not TAXONOMY_DIR.is_dir():
        sys.stderr.write(f"validate_manifests: missing taxonomy at {TAXONOMY_DIR}\n")
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    taxonomy = load_taxonomy()
    known_skill_ids = discover_skill_ids()
    manifests = discover_manifests()

    if not manifests:
        sys.stdout.write(
            "validate_manifests: no manifest.yaml found "
            "(expected during the manifest backfill in PRs 2-3)\n"
        )
        return 0

    total_errors: list[str] = []
    total_warnings: list[str] = []
    for path in manifests:
        errors, warnings = validate_manifest(path, validator, taxonomy, known_skill_ids)
        total_errors.extend(errors)
        total_warnings.extend(warnings)

    for warning in total_warnings:
        sys.stdout.write(f"  warning: {warning}\n")

    if total_errors:
        for err in total_errors:
            sys.stderr.write(f"  error: {err}\n")
        sys.stderr.write(
            f"validate_manifests: {len(total_errors)} error(s) across {len(manifests)} manifest(s)\n"
        )
        return 1

    sys.stdout.write(
        f"validate_manifests: ok ({len(manifests)} manifest(s), "
        f"{len(total_warnings)} warning(s))\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
