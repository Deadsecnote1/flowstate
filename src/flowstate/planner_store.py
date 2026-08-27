# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shim — use flowstate.store instead."""

from flowstate.store import PlanTask, PlannerStore

__all__ = ["PlanTask", "PlannerStore"]
