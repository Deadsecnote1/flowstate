# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shim — use todo.views.clock_view instead."""

from todo.views.clock_view import ClockPage, StopwatchView, TimerView

__all__ = ["ClockPage", "StopwatchView", "TimerView"]
