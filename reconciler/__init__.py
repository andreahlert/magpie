# SPDX-License-Identifier: Apache-2.0
"""Magpie reconciler.

Resolves an adopter's ``intent.yaml`` against the framework
registry into a concrete ``lock`` describing exactly which skills
to enable, at which version, with which parameters. This module
ships ``plan`` (PR 5). ``apply`` lands in PR 6.

The reconciler is the only place capability resolution lives. The
engine is rule-based: every decision is derivable from data in
``agent/taxonomy/`` and ``registry/skills-index.json``.
"""

__all__ = ["resolve", "plan"]
