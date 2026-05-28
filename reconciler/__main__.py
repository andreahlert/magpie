# SPDX-License-Identifier: Apache-2.0
"""Command-line entry point for the Magpie reconciler.

PR 5 ships ``plan``. PR 6 will add ``apply``.

Usage::

    python -m reconciler plan
    python -m reconciler plan --intent path/to/intent.yaml --lock path/to/lock
    python -m reconciler plan --show-keeps

The CLI reads:

- the canonical taxonomy from ``agent/taxonomy/`` (relative to the
  framework checkout — discovered by walking up from the intent
  file or via ``--framework-root``);
- the registry from ``registry/skills-index.json`` (same
  framework root);
- the adopter intent from ``--intent`` (default
  ``.apache-steward.intent.yaml`` in cwd);
- the current lock (if present) from ``--lock`` (default
  ``.apache-steward.lock`` in cwd).

Exit codes:
  0 ok, no diff
  2 ok, plan has changes (CI gate)
  1 error (invalid intent, schema failure, missing file)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("reconciler: PyYAML required\n")
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.stderr.write("reconciler: jsonschema required\n")
    sys.exit(2)

from .apply import apply as run_apply
from .plan import compute_plan, format_plan
from .resolve import resolve


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_framework_root(intent_path: Path, explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    # When running inside the framework checkout the layout is fixed:
    # walk up from this file's location.
    return Path(__file__).resolve().parent.parent


def _load_taxonomy(framework_root: Path) -> dict:
    base = framework_root / "agent" / "taxonomy"
    return {
        "domains": _load_yaml(base / "domains.yaml"),
        "audiences": _load_yaml(base / "audiences.yaml"),
        "risk-tiers": _load_yaml(base / "risk-tiers.yaml"),
        "integrations": _load_yaml(base / "integrations.yaml"),
    }


def _load_skill_param_defaults(framework_root: Path) -> dict[str, dict]:
    skills_dir = framework_root / ".claude" / "skills"
    defaults: dict[str, dict] = {}
    if not skills_dir.is_dir():
        return defaults
    for manifest_path in skills_dir.rglob("manifest.yaml"):
        manifest = _load_yaml(manifest_path)
        params = manifest.get("params") or {}
        defaults_file = params.get("defaults")
        if not defaults_file:
            continue
        target = (manifest_path.parent / defaults_file).resolve()
        if target.is_file():
            defaults[manifest["id"]] = _load_yaml(target) or {}
    return defaults


def _validate_intent(intent: dict, framework_root: Path) -> list[str]:
    schema_path = framework_root / "reconciler" / "schemas" / "intent.schema.json"
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(intent), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{location}: {err.message}")
    return errors


def _cmd_plan(args: argparse.Namespace) -> int:
    intent_path = Path(args.intent).resolve()
    if not intent_path.is_file():
        sys.stderr.write(f"reconciler: intent file not found: {intent_path}\n")
        return 1
    lock_path = Path(args.lock).resolve()

    framework_root = _find_framework_root(intent_path, args.framework_root)
    registry_path = framework_root / "registry" / "skills-index.json"
    if not registry_path.is_file():
        sys.stderr.write(
            f"reconciler: registry not found at {registry_path}. "
            "Build with `python reconciler/build_registry.py --stable-timestamp`.\n"
        )
        return 1

    intent = _load_yaml(intent_path)
    intent_errors = _validate_intent(intent, framework_root)
    if intent_errors:
        sys.stderr.write("reconciler: intent fails schema validation:\n")
        for err in intent_errors:
            sys.stderr.write(f"  {err}\n")
        return 1

    registry = _load_json(registry_path)
    taxonomy = _load_taxonomy(framework_root)
    skill_param_defaults = _load_skill_param_defaults(framework_root)

    resolution = resolve(intent, registry, taxonomy, skill_param_defaults)

    current_lock = None
    if lock_path.is_file():
        current_lock = _load_yaml(lock_path)

    rows = compute_plan(current_lock, resolution)
    output = format_plan(rows, resolution.warnings, show_keeps=args.show_keeps)
    sys.stdout.write(output)

    if any(row.action != "keep" for row in rows):
        return 2
    return 0


def _framework_version_from_pyproject(framework_root: Path) -> str:
    pyproject = framework_root / "pyproject.toml"
    if not pyproject.is_file():
        return "0.0.0"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version") and "=" in stripped:
            _, _, value = stripped.partition("=")
            return value.strip().strip('"').strip("'")
    return "0.0.0"


def _cmd_apply(args: argparse.Namespace) -> int:
    if not args.experimental:
        sys.stderr.write(
            "reconciler: apply is opt-in during the PR 6 rollout. "
            "Pass --experimental to proceed. The legacy setup-steward "
            "family-based takeover remains the supported path until PR 9.\n"
        )
        return 1

    intent_path = Path(args.intent).resolve()
    if not intent_path.is_file():
        sys.stderr.write(f"reconciler: intent file not found: {intent_path}\n")
        return 1
    lock_path = Path(args.lock).resolve()

    framework_root = _find_framework_root(intent_path, args.framework_root)
    registry_path = framework_root / "registry" / "skills-index.json"
    if not registry_path.is_file():
        sys.stderr.write(
            f"reconciler: registry not found at {registry_path}. "
            "Build with `python reconciler/build_registry.py --stable-timestamp`.\n"
        )
        return 1

    intent = _load_yaml(intent_path)
    intent_errors = _validate_intent(intent, framework_root)
    if intent_errors:
        sys.stderr.write("reconciler: intent fails schema validation:\n")
        for err in intent_errors:
            sys.stderr.write(f"  {err}\n")
        return 1

    registry = _load_json(registry_path)
    taxonomy = _load_taxonomy(framework_root)
    skill_param_defaults = _load_skill_param_defaults(framework_root)

    resolution = resolve(intent, registry, taxonomy, skill_param_defaults)
    framework_version = _framework_version_from_pyproject(framework_root)

    try:
        intent_relpath = str(intent_path.relative_to(lock_path.parent))
    except ValueError:
        intent_relpath = str(intent_path)

    outcome = run_apply(
        resolution,
        lock_path=lock_path,
        intent_relpath=intent_relpath,
        framework_version=framework_version,
        framework_root=framework_root if args.symlink_target else None,
        symlink_dir=Path(args.symlink_target).resolve() if args.symlink_target else None,
        dry_run=args.dry_run,
    )

    action = "would write" if args.dry_run else "wrote"
    sys.stdout.write(f"apply: {action} lock to {outcome.lock_path}\n")
    sys.stdout.write(f"apply: lock checksum {outcome.checksum}\n")
    if args.symlink_target:
        verb = "would" if args.dry_run else ""
        sys.stdout.write(
            f"apply: symlinks {verb} create={len(outcome.symlinks_created)} "
            f"remove={len(outcome.symlinks_removed)} keep={len(outcome.symlinks_unchanged)}\n"
        )
    if resolution.warnings:
        sys.stdout.write("apply: warnings:\n")
        for warning in resolution.warnings:
            scope = f" [{warning.skill_id}]" if warning.skill_id else ""
            sys.stdout.write(f"  ! {warning.code}{scope}: {warning.message}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reconciler", description="Magpie adoption reconciler"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Show plan diff without applying")
    plan.add_argument(
        "--intent",
        default=".apache-steward.intent.yaml",
        help="Path to intent file (default: .apache-steward.intent.yaml in cwd)",
    )
    plan.add_argument(
        "--lock",
        default=".apache-steward.lock",
        help="Path to current lock (default: .apache-steward.lock in cwd)",
    )
    plan.add_argument(
        "--framework-root",
        type=Path,
        default=None,
        help="Path to the framework checkout. Default: inferred from this script's location.",
    )
    plan.add_argument(
        "--show-keeps",
        action="store_true",
        help="Show skills with no change. Off by default.",
    )

    apply = sub.add_parser(
        "apply",
        help="Write the resolved lock and (optionally) materialise symlinks",
    )
    apply.add_argument(
        "--intent",
        default=".apache-steward.intent.yaml",
        help="Path to intent file",
    )
    apply.add_argument(
        "--lock",
        default=".apache-steward.lock",
        help="Path to write lock to",
    )
    apply.add_argument(
        "--framework-root",
        type=Path,
        default=None,
        help="Path to the framework checkout",
    )
    apply.add_argument(
        "--symlink-target",
        type=str,
        default=None,
        help=(
            "If set, create one symlink per resolved skill in this directory "
            "pointing into the framework checkout. Existing framework-pointing "
            "symlinks that no longer correspond to a resolved skill are pruned."
        ),
    )
    apply.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the lock and the symlink delta but do not write.",
    )
    apply.add_argument(
        "--experimental",
        action="store_true",
        help=(
            "Required during the PR 6 rollout. Acknowledges that apply is "
            "opt-in and the legacy setup-steward takeover remains supported."
        ),
    )

    args = parser.parse_args(argv)
    if args.command == "plan":
        return _cmd_plan(args)
    if args.command == "apply":
        return _cmd_apply(args)
    parser.error(f"unknown command {args.command}")
    return 1  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
