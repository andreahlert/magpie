# SPDX-License-Identifier: Apache-2.0
"""Validate the canonical taxonomy under ``agent/taxonomy/``.

Run from the repo root::

    python reconciler/validate_taxonomy.py

Exits non-zero on any inconsistency. Intended to run in CI from PR 4 onwards
and locally during taxonomy edits. Pure standard library: no dependency on
the reconciler engine which arrives in PR 5.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "validate_taxonomy: PyYAML is required. Install with `pip install pyyaml` "
        "or run via `uv run --with pyyaml python reconciler/validate_taxonomy.py`.\n"
    )
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_DIR = REPO_ROOT / "agent" / "taxonomy"

EXPECTED_FILES: dict[str, str] = {
    "domains.yaml": "domains",
    "audiences.yaml": "audiences",
    "risk-tiers.yaml": "tiers",
    "integrations.yaml": "integrations",
}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_file(path: Path, list_key: str) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(REPO_ROOT)

    if not path.is_file():
        return [f"{rel}: missing"]

    data = load_yaml(path)
    if not isinstance(data, dict):
        return [f"{rel}: top-level must be a mapping"]

    if data.get("schema-version") != 1:
        errors.append(f"{rel}: schema-version must be 1")

    items = data.get(list_key)
    if not isinstance(items, list) or not items:
        errors.append(f"{rel}: '{list_key}' must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for index, item in enumerate(items):
        prefix = f"{rel}[{list_key}][{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be a mapping")
            continue

        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"{prefix}: 'id' missing or not a string")
        elif item_id in seen_ids:
            errors.append(f"{prefix}: duplicate id '{item_id}'")
        else:
            seen_ids.add(item_id)

        if "description" not in item:
            errors.append(f"{prefix}: 'description' missing")

        if list_key == "tiers":
            order = item.get("order")
            if not isinstance(order, int):
                errors.append(f"{prefix}: 'order' must be an integer")

    if list_key == "tiers":
        orders = [item.get("order") for item in items if isinstance(item, dict)]
        if orders != sorted(orders):
            errors.append(f"{rel}: tiers must be listed in ascending order")
        if len(set(orders)) != len(orders):
            errors.append(f"{rel}: tier orders must be unique")
        contiguous = list(range(min(orders), max(orders) + 1))
        if sorted(orders) != contiguous:
            errors.append(
                f"{rel}: tier orders must be contiguous "
                f"(found {sorted(orders)})"
            )

    return errors


def main() -> int:
    if not TAXONOMY_DIR.is_dir():
        sys.stderr.write(f"validate_taxonomy: {TAXONOMY_DIR} does not exist\n")
        return 1

    all_errors: list[str] = []
    for filename, key in EXPECTED_FILES.items():
        all_errors.extend(validate_file(TAXONOMY_DIR / filename, key))

    if all_errors:
        for err in all_errors:
            sys.stderr.write(f"  {err}\n")
        sys.stderr.write(f"validate_taxonomy: {len(all_errors)} error(s)\n")
        return 1

    summary: dict[str, int] = {}
    for filename, key in EXPECTED_FILES.items():
        data = load_yaml(TAXONOMY_DIR / filename)
        summary[filename] = len(data.get(key, []))

    sys.stdout.write("validate_taxonomy: ok\n")
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
