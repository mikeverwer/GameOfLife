from tkinter import *
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk


def apply_dark_theme(root, custom_chk=True, **overrides):
    BG         = overrides.get('BG',         "#1e1e1e")
    SURFACE    = overrides.get('SURFACE',    "#252526")   # entries, listboxes, text
    SURFACE_HI = overrides.get('SURFACE_HI', "#2d2d30")   # buttons, combobox
    BORDER     = overrides.get('BORDER',     "#0047ab")   # "#3e3e42"
    FG         = overrides.get('FG',         "#e0e0e0")
    ACCENT     = overrides.get('ACCENT',     "#0047ab")
    SELECT     = overrides.get('SELECT',     "#264f78")

    # Classic tk widgets (Listbox, Text, Canvas, Toplevel, Menu) via the
    # option database. Must run BEFORE any of those widgets get created.
    opts = {
        "*Background": BG,
        "*Foreground": FG,
        "*Listbox.background": SURFACE,
        "*Listbox.foreground": FG,
        "*Listbox.selectBackground": SELECT,
        "*Listbox.selectForeground": FG,
        "*Listbox.borderWidth": "0",
        "*Listbox.highlightThickness": "0",
        "*Text.background": SURFACE,
        "*Text.foreground": FG,
        "*Text.insertBackground": FG,
        "*Text.selectBackground": SELECT,
        "*Text.borderWidth": "0",
        "*Text.highlightThickness": "1",
        "*Text.highlightBackground": BORDER,
        "*Text.highlightColor": ACCENT,
        "*Canvas.background": BG,
        "*Canvas.highlightThickness": "0",
        "*Toplevel.background": BG,
        "*Menu.background": SURFACE,
        "*Menu.foreground": FG,
        # ttk.Combobox dropdown is internally a tk Listbox:
        "*TCombobox*Listbox.background": SURFACE,
        "*TCombobox*Listbox.foreground": FG,
        "*TCombobox*Listbox.selectBackground": SELECT,
    }
    for k, v in opts.items():
        root.option_add(k, v)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")

    # Catch-all
    style.configure(".",
        background=BG, foreground=FG, fieldbackground=SURFACE,
        bordercolor=BORDER, lightcolor=BG, darkcolor=BG,
        troughcolor=SURFACE)

    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TSeparator", background=BORDER)

    style.configure("TButton",
        background=SURFACE_HI, foreground=FG,
        bordercolor=BORDER, focuscolor=BORDER, padding=4)
    style.map("TButton",
        background=[("active", BORDER), ("pressed", ACCENT)],
        bordercolor=[("focus", ACCENT)])

    style.configure("TEntry",
        fieldbackground=SURFACE, foreground=FG,
        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
        insertcolor=FG, padding=2)
    style.map("TEntry", bordercolor=[("focus", ACCENT)])

    style.configure("TCombobox",
        fieldbackground=SURFACE, background=SURFACE_HI, foreground=FG,
        bordercolor=BORDER, arrowcolor=FG,
        selectbackground=SELECT, selectforeground=FG)
    style.map("TCombobox",
        fieldbackground=[("readonly", SURFACE)],
        bordercolor=[("focus", ACCENT)])

    style.configure("TCheckbutton",
        background=BG, foreground=FG,
        focuscolor=BORDER,
        padding=(2, 2))
    style.map("TCheckbutton",
        background=[("active", BG)],)

    style.configure("Vertical.TScrollbar",
        background=SURFACE_HI, troughcolor=BG, bordercolor=BG,
        arrowcolor=FG, gripcount=0)
    style.map("Vertical.TScrollbar", background=[("active", ACCENT)])
    if custom_chk:
        apply_custom_checkbox(root, style, SURFACE, BORDER, ACCENT, FG, size=16)


def _checkbox_images(surface, border, accent, fg, size=14, gap=5, radius=3):
    # Unchecked: empty rounded square with border
    w = size + gap
    off = Image.new("RGBA", (w, size), (0, 0, 0, 0))
    ImageDraw.Draw(off).rounded_rectangle(
        [(0, 0), (size - 1, size - 1)], radius=radius,
        fill=surface, outline=border, width=1)

    # Checked: accent fill + rounded rectangle
    on = Image.new("RGBA", (w, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(on)
    d.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)], radius=radius,
        fill=accent, outline=accent, width=1)
    d.rounded_rectangle(
        [(5, 5), (size - 6, size - 6)],
        fill=fg, outline=None, radius=radius - 2
    )
    return ImageTk.PhotoImage(off), ImageTk.PhotoImage(on)


def apply_custom_checkbox(root, style, surface, border, accent, fg, size):
    # Keep references on root or they'll be garbage-collected
    root._chk_off, root._chk_on = _checkbox_images(surface, border, accent, fg, size)

    style.element_create(
        "Custom.Checkbutton.indicator", "image", root._chk_off,
        ("selected", root._chk_on),
        ("disabled", "selected", root._chk_on),
        padding=(2, 0, 6, 0), sticky="w")

    style.layout("TCheckbutton", [
        ("Checkbutton.padding", {"sticky": "nswe", "children": [
            ("Custom.Checkbutton.indicator", {"side": "left", "sticky": ""}),
            ("Checkbutton.focus", {"side": "left", "sticky": "", "children": [
                ("Checkbutton.label", {"sticky": "nswe"})
            ]})
        ]})
    ])