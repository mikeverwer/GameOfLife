from tkinter import *
from tkinter import ttk

class ToolTip:
    def __init__(self, widget, text, child=None, delay=500):
        self.widget = widget
        self.text = text
        self.child = child
        self.delay = delay
        self.tooltip = None
        self.enter_id = None
        self.background = '#f0f0fa'

        if child:
            self.widget = self.widget.children[child]

        self.widget.bind('<Enter>', self.schedule_show_tooltip)
        self.widget.bind('<Leave>', self.hide_tooltip)

    def schedule_show_tooltip(self, event=None):
        self.enter_id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self, event=None):
        if self.enter_id:
            self.widget.after_cancel(self.enter_id)
            self.enter_id = None

        x, y, _, _ = self.widget.bbox('insert')
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(self.tooltip, text=self.text, background=self.background, justify=LEFT, relief='solid',
                          borderwidth=0, padding=(6, 6, 4, 4))
        label.grid()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
        if self.enter_id:
            self.widget.after_cancel(self.enter_id)
            self.enter_id = None


class Logger(Text):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
