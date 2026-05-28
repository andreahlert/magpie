# SPDX-License-Identifier: Apache-2.0
"""Build ``registry/skills-index.json`` from every skill manifest.

The registry is the aggregated, canonical-serialised view that the
reconciler (PR 5+) loads instead of walking the skill tree on every
``magpie plan``. CI runs this script, compares the result to the
committed ``registry/skills-index.json``, and fails the build if the
two diverge — so a manifest change without a registry rebuild is
caught before merge.

Run from the repo root::

    uv run --with pyyaml python reconciler/build_registry.py

Use ``--check`` to verify the on-disk file matches what would be
generated (CI mode, no write):

    python reconciler/build_registry.py --check

Pure stdlib + PyYAML.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("build_registry: PyYAML required\n")
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
TAXONOMY_DIR = REPO_ROOT / "agent" / "taxonomy"
PYPROJECT = REPO_ROOT / "pyproject.toml"
REGISTRY_PATH = REPO_ROOT / "registry" / "skills-index.json"

MANIFEST_KEYS = (
    "version",
    "domains",
    "audiences",
    "risk-tier",
    "integrations",
    "requires",
    "templates",
    "params",
    "status",
    "replaces",
)


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def read_framework_version() -> str:
    """Best-effort framework version from pyproject.toml.

    Avoids tomllib import for older runtimes; the framework version
    line is grep-friendly.
    """
    if not PYPROJECT.is_file():
        return "0.0.0"
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version") and "=" in stripped:
            _, _, value = stripped.partition("=")
            return value.strip().strip('"').strip("'")
    return "0.0.0"


def collect_manifests() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.rglob("manifest.yaml"))


def project_manifest(manifest: dict) -> dict:
    """Slim view of a manifest carrying only registry-relevant fields."""
    return {
        key: manifest[key]
        for key in MANIFEST_KEYS
        if key in manifest and manifest[key] not in (None, [], {})
    }


def serialise(payload: dict) -> str:
    """Canonical JSON: sorted keys, 2-space indent, trailing newline."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build(generated_at: str | None = None) -> str:
    manifests = collect_manifests()
    skills: dict[str, dict] = {}
    for path in manifests:
        manifest = load_yaml(path)
        skill_id = manifest["id"]
        if skill_id in skills:
            raise ValueError(f"duplicate skill id '{skill_id}' from {path}")
        skills[skill_id] = project_manifest(manifest)

    taxonomy_files = ["domains.yaml", "audiences.yaml", "risk-tiers.yaml", "integrations.yaml"]
    taxonomy_summary: dict[str, int] = {}
    for filename in taxonomy_files:
        data = load_yaml(TAXONOMY_DIR / filename)
        list_key = next(iter(data.keys() - {"schema-version"}))
        taxonomy_summary[filename] = len(data.get(list_key, []))

    payload = {
        "schema-version": 1,
        "framework-version": read_framework_version(),
        "generated-at": generated_at or "",
        "taxonomy": taxonomy_summary,
        "skill-count": len(skills),
        "skills": skills,
    }

    # Compute checksum over the canonical-serialised payload excluding
    # the checksum field itself.
    canonical = serialise(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload["checksum"] = f"sha256:{digest}"

    return serialise(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write. Exit non-zero if the on-disk registry is stale.",
    )
    parser.add_argument(
        "--stable-timestamp",
        action="store_true",
        help="Use a fixed timestamp ('1970-01-01T00:00:00Z') so the checksum is stable across runs. Default off; CI uses this flag.",
    )
    args = parser.parse_args()

    generated_at = (
        "1970-01-01T00:00:00Z"
        if args.stable_timestamp
        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    fresh = build(generated_at=generated_at)

    if args.check:
        if not REGISTRY_PATH.is_file():
            sys.stderr.write(
                f"build_registry: {REGISTRY_PATH.relative_to(REPO_ROOT)} does not exist; "
                "regenerate with `python reconciler/build_registry.py --stable-timestamp`.\n"
            )
            return 1
        on_disk = REGISTRY_PATH.read_text(encoding="utf-8")
        if on_disk != fresh:
            sys.stderr.write(
                "build_registry: on-disk registry is stale. Regenerate with:\n"
                "  python reconciler/build_registry.py --stable-timestamp\n"
            )
            return 1
        sys.stdout.write("build_registry: up to date\n")
        return 0

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(fresh, encoding="utf-8")
    sys.stdout.write(f"build_registry: wrote {REGISTRY_PATH.relative_to(REPO_ROOT)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
