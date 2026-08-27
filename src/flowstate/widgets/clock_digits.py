# SPDX-License-Identifier: GPL-3.0-or-later
"""Cairo-drawn huge clock digits."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import cairo
from gi.repository import Adw, Gtk


class ClockDigits(Gtk.DrawingArea):
    """Huge centered time digits drawn with Cairo (ignores theme font CSS).

    Digits use fixed (tabular) advance so the display does not jitter when
    the seconds / fractional place changes width (e.g. 1 vs 8).
    """

    def __init__(self, initial: str = "00:00", min_height: int = 200) -> None:
        super().__init__()
        self._text = initial
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_content_height(min_height)
        self.set_size_request(-1, min_height)
        self.set_draw_func(self._on_draw)

    def set_time_text(self, text: str) -> None:
        if text == self._text:
            return
        self._text = text
        self.queue_draw()

    def _fg_rgba(self) -> tuple[float, float, float, float]:
        style = self.get_style_context()
        for name in ("view_fg_color", "theme_fg_color", "foreground_color"):
            ok, color = style.lookup_color(name)
            if ok:
                return (color.red, color.green, color.blue, color.alpha)
        if Adw.StyleManager.get_default().get_dark():
            return (1.0, 1.0, 1.0, 1.0)
        return (0.12, 0.12, 0.12, 1.0)

    @staticmethod
    def _slot_char(ch: str) -> str:
        """Map each character to a stable-width stand-in for layout."""
        if ch.isdigit():
            return "0"
        if ch == ".":
            return "."
        if ch in ":":
            return ":"
        return ch

    def _on_draw(self, _area, cr: cairo.Context, width: int, height: int) -> None:
        if width <= 1 or height <= 1:
            return

        text = self._text
        if not text:
            return

        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

        # Size against a zeroed reference so font size never pulses with digits.
        reference = "".join(self._slot_char(ch) for ch in text)
        size = max(64.0, height * 0.78)
        cr.set_font_size(size)
        ref_ext = cr.text_extents(reference)
        max_w = width * 0.94
        if ref_ext.width > max_w > 0:
            size *= max_w / ref_ext.width
            cr.set_font_size(size)

        # Tabular digit width = widest glyph among 0-9 at this size.
        digit_w = 0.0
        for d in "0123456789":
            digit_w = max(digit_w, cr.text_extents(d).x_advance)
        if digit_w <= 0:
            digit_w = cr.text_extents("0").x_advance

        colon_w = max(cr.text_extents(":").x_advance, size * 0.28)
        dot_w = max(cr.text_extents(".").x_advance, size * 0.22)

        def char_advance(ch: str) -> float:
            if ch.isdigit():
                return digit_w
            if ch == ":":
                return colon_w
            if ch == ".":
                return dot_w
            return cr.text_extents(ch).x_advance

        total_w = sum(char_advance(ch) for ch in text)
        # Vertical centering from a reference digit (stable ascent/descent).
        ref_digit = cr.text_extents("0")
        y = (height - ref_digit.height) / 2 - ref_digit.y_bearing
        x = (width - total_w) / 2

        r, g, b, a = self._fg_rgba()
        cr.set_source_rgba(r, g, b, a)

        for ch in text:
            slot = char_advance(ch)
            ext = cr.text_extents(ch)
            # Center each glyph inside its fixed slot.
            glyph_x = x + (slot - ext.width) / 2 - ext.x_bearing
            cr.move_to(glyph_x, y)
            cr.show_text(ch)
            x += slot


def make_clock_label(initial: str) -> ClockDigits:
    return ClockDigits(initial)


def set_clock_text(widget: ClockDigits, text: str) -> None:
    widget.set_time_text(text)
