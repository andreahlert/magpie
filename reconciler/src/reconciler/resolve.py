# SPDX-License-Identifier: Apache-2.0
"""Resolve an adopter intent against the framework registry.

Pure function ``resolve(intent, registry, taxonomy) -> Resolution``.
No I/O. The CLI in ``reconciler.__main__`` loads files and hands
them in.

The resolver applies five sequential rules:

1. **Capability filter.** A skill survives only if every one of
   its declared domains, audiences, risk-tier, and integrations
   passes the intent's declared bounds.
2. **Override apply.** ``intent.overrides.exclude`` drops a skill
   (logged as ``overrides.exclude``). ``intent.overrides
   .force-include`` re-adds a skill that the filter dropped
   (logged as ``overrides.force-include``); if that skill
   violates ``risk-tier-max`` a warning is emitted but the skill
   is included.
3. **Dependency closure.** Every ``requires`` on an included
   skill is pulled in transitively (logged as ``skill.requires``).
   Cycles are detected and reported.
4. **Version pinning.** ``intent.overrides.pin[<id>]`` wins over
   the registry version.
5. **Param merge.** Defaults from each skill's ``params.defaults``
   merge with ``intent.overrides.params[<id>]``. Override wins
   per-key.

This module is intentionally I/O-free so it can be exercised in
unit tests without a filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResolvedSkill:
    skill_id: str
    version: str
    source: str
    integrations_resolved: list[str]
    params: dict


@dataclass
class Exclusion:
    skill_id: str
    reason: str


@dataclass
class Warning:
    code: str
    message: str
    skill_id: str | None = None


@dataclass
class Resolution:
    skills: dict[str, ResolvedSkill] = field(default_factory=dict)
    exclusions: dict[str, Exclusion] = field(default_factory=dict)
    warnings: list[Warning] = field(default_factory=list)


def _tier_order(taxonomy: dict) -> dict[str, int]:
    return {
        tier["id"]: tier["order"]
        for tier in taxonomy["risk-tiers"]["tiers"]
    }


def _filter_one(
    skill_id: str,
    skill: dict,
    intent: dict,
    tier_order: dict[str, int],
) -> tuple[bool, str | None]:
    """Apply the capability filter. Return (kept, reason-if-dropped)."""
    cap = intent["capabilities"]
    domains = set(cap["domains"])
    audiences = set(cap["audiences"])
    integrations = set(cap["integrations"])
    risk_max = tier_order[cap["risk-tier-max"]]

    skill_domains = set(skill.get("domains") or [])
    skill_audiences = set(skill.get("audiences") or [])
    skill_integrations = set(skill.get("integrations") or [])
    skill_risk = tier_order[skill["risk-tier"]]

    if not skill_domains & domains:
        return False, "intent.capabilities.domains"
    if not skill_audiences & audiences:
        return False, "intent.capabilities.audiences"
    if skill_risk > risk_max:
        return False, "intent.capabilities.risk-tier-max"
    if not skill_integrations.issubset(integrations):
        return False, "intent.capabilities.integrations"
    return True, None


def _resolve_requires(
    seed: set[str],
    registry_skills: dict[str, dict],
    resolution: Resolution,
) -> set[str]:
    """Transitive closure over `requires`. Returns the closed set."""
    closed: set[str] = set()
    stack = list(seed)
    seen: set[tuple[str, str]] = set()
    in_progress: set[str] = set()

    def walk(node: str, chain: tuple[str, ...]) -> None:
        if node in closed:
            return
        if node in in_progress:
            cycle = " -> ".join(chain + (node,))
            resolution.warnings.append(
                Warning(
                    code="dependency-cycle",
                    message=f"cycle detected: {cycle}",
                    skill_id=node,
                )
            )
            return
        in_progress.add(node)
        if node not in registry_skills:
            resolution.warnings.append(
                Warning(
                    code="missing-dependency",
                    message=f"skill '{node}' required but absent from registry",
                    skill_id=node,
                )
            )
            in_progress.discard(node)
            return
        for dep in registry_skills[node].get("requires") or []:
            if (node, dep) in seen:
                continue
            seen.add((node, dep))
            walk(dep, chain + (node,))
        in_progress.discard(node)
        closed.add(node)

    for entry in stack:
        walk(entry, ())
    return closed


def _merge_params(
    skill_id: str,
    registry_skill: dict,
    intent: dict,
    skill_param_defaults: dict[str, dict],
) -> dict:
    defaults = skill_param_defaults.get(skill_id, {}) or {}
    overrides = (
        (intent.get("overrides") or {})
        .get("params", {})
        .get(skill_id, {})
        or {}
    )
    merged = dict(defaults)
    merged.update(overrides)
    return merged


def resolve(
    intent: dict,
    registry: dict,
    taxonomy: dict,
    skill_param_defaults: dict[str, dict] | None = None,
) -> Resolution:
    """Pure resolution. See module docstring for rule sequence.

    ``taxonomy`` is the dict ``{"risk-tiers": <parsed risk-tiers.yaml>,
    "domains": ..., "audiences": ..., "integrations": ...}``. Only
    risk-tiers is required for ordering; the others are passed for
    completeness and forward compatibility.

    ``skill_param_defaults`` maps skill id to the parsed contents of
    that skill's ``params.defaults.yaml``. The CLI reads them; this
    function only consumes them.
    """
    skill_param_defaults = skill_param_defaults or {}
    tier_order = _tier_order(taxonomy)

    registry_skills: dict[str, dict] = dict(registry["skills"])
    overrides = (intent.get("overrides") or {})
    excludes: set[str] = set(overrides.get("exclude") or [])
    force_include: set[str] = set(overrides.get("force-include") or [])
    pin: dict[str, str] = dict(overrides.get("pin") or {})

    resolution = Resolution()
    surviving: set[str] = set()

    for skill_id, skill in registry_skills.items():
        kept, reason = _filter_one(skill_id, skill, intent, tier_order)
        if kept:
            surviving.add(skill_id)
        else:
            resolution.exclusions[skill_id] = Exclusion(
                skill_id=skill_id, reason=reason or "unknown"
            )

    sources: dict[str, str] = {sid: "intent.domains" for sid in surviving}

    for sid in excludes:
        if sid in surviving:
            surviving.discard(sid)
            sources.pop(sid, None)
        resolution.exclusions[sid] = Exclusion(
            skill_id=sid, reason="intent.overrides.exclude"
        )

    cap_risk_max = tier_order[intent["capabilities"]["risk-tier-max"]]
    for sid in force_include:
        if sid not in registry_skills:
            resolution.warnings.append(
                Warning(
                    code="unknown-force-include",
                    message=f"force-include references unknown skill '{sid}'",
                    skill_id=sid,
                )
            )
            continue
        if registry_skills[sid].get("status") == "off":
            resolution.warnings.append(
                Warning(
                    code="force-include-off",
                    message=f"'{sid}' has status=off (MISSION sequencing); force-include overrides this",
                    skill_id=sid,
                )
            )
        skill_tier = tier_order[registry_skills[sid]["risk-tier"]]
        if skill_tier > cap_risk_max:
            resolution.warnings.append(
                Warning(
                    code="force-include-violates-risk-tier",
                    message=(
                        f"'{sid}' has risk-tier '{registry_skills[sid]['risk-tier']}' "
                        f"above intent.capabilities.risk-tier-max"
                    ),
                    skill_id=sid,
                )
            )
        surviving.add(sid)
        sources[sid] = "intent.overrides.force-include"
        resolution.exclusions.pop(sid, None)

    closure = _resolve_requires(surviving, registry_skills, resolution)
    for sid in closure - surviving:
        sources[sid] = "skill.requires"
        resolution.exclusions.pop(sid, None)
    surviving = closure

    for sid in sorted(surviving):
        if sid not in registry_skills:
            continue
        skill = registry_skills[sid]
        version = pin.get(sid, skill["version"])
        if sid in pin and pin[sid] != skill["version"]:
            resolution.warnings.append(
                Warning(
                    code="pinned-version-mismatch",
                    message=(
                        f"'{sid}' pinned to {pin[sid]} but registry has {skill['version']}"
                    ),
                    skill_id=sid,
                )
            )
        params = _merge_params(sid, skill, intent, skill_param_defaults)
        resolution.skills[sid] = ResolvedSkill(
            skill_id=sid,
            version=version,
            source=sources[sid],
            integrations_resolved=sorted(skill.get("integrations") or []),
            params=params,
        )

    return resolution
