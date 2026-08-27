# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shim — use todo.store instead."""

from todo.store import PlanTask, PlannerStore

__all__ = ["PlanTask", "PlannerStore"]
