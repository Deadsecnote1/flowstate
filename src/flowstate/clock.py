# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shim — use flowstate.views.clock_view instead."""

from flowstate.views.clock_view import ClockPage, StopwatchView, TimerView

__all__ = ["ClockPage", "StopwatchView", "TimerView"]
