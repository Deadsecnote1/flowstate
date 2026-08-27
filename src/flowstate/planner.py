# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shim — use flowstate.views.planner_view instead."""

from flowstate.views.planner_view import PlannerPage, TaskEditor

__all__ = ["PlannerPage", "TaskEditor"]
