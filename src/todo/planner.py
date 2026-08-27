# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shim — use todo.views.planner_view instead."""

from todo.views.planner_view import PlannerPage, TaskEditor

__all__ = ["PlannerPage", "TaskEditor"]
