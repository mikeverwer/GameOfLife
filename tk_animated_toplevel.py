"""
A borderless Toplevel that slides up from the bottom of its parent with a
fade-in, and slides down with a fade-out. The Toplevel itself is exposed
as `self.top` so the caller builds its contents however they like.

Usage:
    from animated_toplevel import AnimatedToplevel

    panel = AnimatedToplevel(root, width=300, height=180)
    frame = Frame(panel.top, bg='#2d2d30')
    frame.pack(fill='both', expand=True)
    ttk.Button(frame, text='Close', command=panel.hide).pack()

    ttk.Button(root, text='Open', command=panel.show).pack()
"""

from tkinter import Toplevel
import time


class AnimatedToplevel:
    def __init__(self, parent, width=300, height=180,
                 duration=0.30, bottom_offset=30):
        """
        parent         — Tk or Toplevel the panel will appear above
        width, height  — panel dimensions in pixels
        duration       — animation length in seconds (each direction)
        bottom_offset  — gap from the parent's bottom edge when at rest
        """
        self.parent = parent
        self.width = width
        self.height = height
        self.duration = duration
        self.bottom_offset = bottom_offset

        self.top = Toplevel(parent)
        self.top.overrideredirect(True)
        self.top.attributes('-topmost', True)
        self.top.attributes('-alpha', 0.0)

        # start in the hidden position
        self._y = self._y_hidden()
        self._alpha = 0.0
        self._apply(self._y, self._alpha)

        self._anim_id = None

    # ---- public API ----

    def show(self):
        """Animate the panel into view."""
        self._animate(opening=True)

    def hide(self):
        """Animate the panel out of view."""
        self._animate(opening=False)

    def destroy(self):
        """Cancel any running animation and destroy the underlying Toplevel."""
        self._cancel_animation()
        self.top.destroy()

    def resize(self, width, height):
        self.width = width
        self.height = height
        # if at rest and visible, snap to the new resting position;
        # otherwise just refresh in place so horizontal centering updates
        if self._alpha >= 1.0 and not self.is_animating:
            self._y = self._y_resting()
        elif self._alpha <= 0.0 and not self.is_animating:
            self._y = self._y_hidden()
        self._apply(self._y, self._alpha)

    @property
    def is_animating(self):
        return self._anim_id is not None

    # ---- geometry (absolute screen coords) ----

    def _x(self):
        self.parent.update_idletasks()
        return self.parent.winfo_rootx() + (self.parent.winfo_width() - self.width) // 2

    def _y_resting(self):
        self.parent.update_idletasks()
        return (self.parent.winfo_rooty() + self.parent.winfo_height()
                - self.height - self.bottom_offset)

    def _y_hidden(self):
        self.parent.update_idletasks()
        return self.parent.winfo_rooty() + self.parent.winfo_height() + 20

    def _apply(self, y, alpha):
        self.top.geometry(f"{self.width}x{self.height}+{self._x()}+{int(y)}")
        self.top.attributes('-alpha', alpha)
        self._y = y
        self._alpha = alpha

    # ---- animation ----

    def _cancel_animation(self):
        if self._anim_id is not None:
            self.top.after_cancel(self._anim_id)
            self._anim_id = None

    def _animate(self, opening):
        self._cancel_animation()

        target_y = self._y_resting() if opening else self._y_hidden()
        target_a = 1.0 if opening else 0.0
        y_from = self._y
        a_from = self._alpha

        start = time.perf_counter()

        def step():
            t = min(1.0, (time.perf_counter() - start) / self.duration)
            eased = t * t * (3 - 2 * t)        # smoothstep
            y = y_from + (target_y - y_from) * eased
            alpha = a_from + (target_a - a_from) * eased
            self._apply(y, alpha)
            if t < 1.0:
                self._anim_id = self.top.after(16, step)
            else:
                self._anim_id = None

        step()
