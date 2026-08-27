# SPDX-License-Identifier: GPL-3.0-or-later
"""Application CSS (loaded once by FlowstateWindow)."""

APP_CSS = b""".todo-entry {
  font-size: 1.05em;
  margin: 8px 12px;
}
.todo-row-title {
  font-size: 1.05em;
}
.todo-row-title.completed {
  opacity: 0.55;
  text-decoration: line-through;
}
.filter-bar {
  padding: 6px 12px 10px;
}
.status-bar {
  padding: 8px 12px;
  opacity: 0.8;
}
.clock-display {
  font-size: 128px;
  font-weight: 800;
  letter-spacing: 4px;
  padding: 20px 12px;
}
.timer-picker {
  margin-top: 8px;
}
.timer-picker spinbutton {
  font-size: 22px;
  font-weight: 600;
  font-feature-settings: "tnum";
  min-height: 40px;
}
.timer-picker label {
  font-size: 13px;
}

/* ---- Daily Planner (Structured-inspired) ---- */
.planner-root {
  background-color: #121212;
}
.planner-inbox {
  background-color: #1a1a1a;
  border-radius: 18px;
  padding: 12px;
}
.planner-inbox-btn {
  background-color: #E8837A;
  color: white;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 999px;
}
.planner-inbox-entry {
  background-color: #2a2a2a;
  border-radius: 12px;
  padding: 8px;
  color: #eee;
}
.planner-month {
  font-size: 1.35rem;
  font-weight: 700;
  color: #f2f2f2;
}
.planner-week {
  padding: 4px 0 8px;
}
.planner-day-chip {
  border-radius: 14px;
  padding: 6px 4px;
  color: #ccc;
}
.planner-day-chip:checked {
  background-color: rgba(232, 131, 122, 0.25);
}
.planner-day-today .planner-day-num {
  background-color: #E8837A;
  color: white;
  border-radius: 999px;
  min-width: 28px;
  padding: 2px 0;
  font-weight: 700;
}
.planner-timeline-frame {
  background-color: #1c1c1c;
  border-radius: 20px;
}
.planner-event-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: #f5f5f5;
}
.planner-event-icon {
  font-size: 1.1rem;
  min-width: 36px;
  min-height: 36px;
  border-radius: 999px;
  padding: 6px;
}
.planner-event-icon-coral {
  background-color: #E8837A;
  color: white;
}
.planner-event-icon-blue {
  background-color: #3a4560;
  color: #8eb0ff;
}
.planner-gap {
  color: #E8837A;
  font-size: 0.95rem;
  opacity: 0.9;
}
.planner-fab {
  background-color: #E8837A;
  color: white;
  min-width: 52px;
  min-height: 52px;
}
.planner-panel {
  background-color: #1c1c1c;
  border-radius: 20px;
  min-width: 320px;
}
.planner-panel-header {
  background-color: #E8837A;
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
}
.planner-icon-pill {
  background-color: white;
  color: #E8837A;
  border-radius: 999px;
  min-width: 34px;
  min-height: 52px;
  padding: 8px 6px;
  font-size: 1.1rem;
}
.planner-header-time {
  color: rgba(255,255,255,0.85);
  font-size: 0.85rem;
}
.planner-header-repeat {
  color: rgba(255,255,255,0.9);
  font-size: 0.85rem;
}
.planner-title-entry {
  background: transparent;
  color: white;
  font-size: 1.45rem;
  font-weight: 700;
  border: none;
  box-shadow: none;
  padding: 0;
}
.planner-header-btn {
  color: white;
}
.planner-row {
  background-color: #2a2a2a;
  border-radius: 14px;
  padding: 10px 12px;
}
.planner-time-box {
  background-color: #242424;
  border-radius: 14px;
  padding: 12px;
}
.planner-preset {
  background-color: #333;
  color: #eee;
  border-radius: 999px;
  margin: 2px;
}
.planner-preset-active {
  border: 2px solid #E8837A;
}
.planner-daily:checked {
  background-color: rgba(232, 131, 122, 0.3);
  color: #E8837A;
}
.planner-notes {
  background-color: transparent;
  color: #eee;
  min-height: 80px;
}
.planner-save {
  background-color: #E8837A;
  color: white;
  font-weight: 700;
  padding: 10px 22px;
  border-radius: 999px;
}
"""
