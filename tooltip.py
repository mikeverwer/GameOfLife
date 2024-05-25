from tkinter import *
from tkinter import ttk

class ToolTip:
    def __init__(self, widget, text, child=None, delay=500):
        self.widget: Widget = widget
        self.text = text
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
        self.configure('wrap', 'word')
        super().__init__(parent, *args, **kwargs)
        self.route_print = True

    def clear_log(self):
        self['state'] = 'normal'
        self.delete('1.0', END)
        self.insert('1.0', "Logging Window\n\n")
        self.see('end')
        self['state'] = 'disabled'

    def log(self, *args, **kwargs):
        self['state'] = 'normal'
        if self.route_print:
            print(*args, **kwargs)
        end: str = None
        try:
            end = kwargs[end]
        except:
            end = '\n'
        if len(args) == 1:
            self.insert('end', )
        for key, value in kwargs:
            if key == 'end':
                end = value
            else:
                end = '\n'
        self.insert(END, args[0] + kwargs['end'])
        self.see('end')
        self['state'] = 'disabled'
