from tkinter import *
from tkinter import ttk
from tkinter import colorchooser
from tooltip import ToolTip
import os
import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SimulationDefault.MikeVerwer")


def main():
    app = GameOfLife(pan='y')
    app.mainloop()


class CFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        style = ttk.Style()
        super().__init__(parent, **kwargs)

class LifeBoard(Canvas):
    def __init__(self, parent, **kwargs):
        self.parent = parent
        canvas_args: dict = {}
        self.make_pannable = False
        self.make_zoomable = False
        self.max_zoom = 1
        self.min_zoom = -3
        self.factor = 1
        self.drawing_factor = 1
        self.zoom_level = self.max_zoom  # fully zoomed in
        for key, value in kwargs.items():
            if key in ["pan", "zoom"]:
                self.handle_kwarg(key, value)
            else:
                canvas_args[key] = value       
        super().__init__(parent, **canvas_args)

        self.playing = False
        self.grid_spacing = 16
        self.cells: dict[int: Cell] = {}
        self.cells_to_activate: dict[int: Cell] = {}
        self.do_binds()
        self.starting_config()

    
    def starting_config(self):
        event = Event()
        s = self.grid_spacing
        event.x = s; event.y = s
        self.clicked(event)
        event.x = 2 * s; event.y = s
        self.clicked(event)
        event.x = 3 * s; event.y = s
        self.clicked(event)
        event.x = 3 * s; event.y = 0
        self.clicked(event)
        event.x = 2 * s; event.y = -1 * s
        self.clicked(event)

    def handle_kwarg(self, key, value):
        if key == "pan" and value:
            self.make_pannable = True
        elif key == "zoom" and value:
            self.make_zoomable = True

    def do_binds(self):
        self.bind("<Button-3>", self.alt_clicked)
        if self.make_zoomable:
            self.bind("<MouseWheel>", self.do_zoom) # WINDOWS ONLY
        if self.make_pannable:
            self.bind('<ButtonPress-2>', lambda event: self.scan_mark(event.x, event.y))
            self.bind("<B2-Motion>", lambda event: self.scan_dragto(event.x, event.y, gain=1))
        self.bind("<Button-1>", self.clicked)

    def give_coords(self, event):
        canvasx = self.canvasx(event.x)
        canvasy = self.canvasy(event.y)
        print(f"Canvas X/Y: ({canvasx}, {canvasy})\nEvent X/Y : ({event.x}, {event.y})")
        print(type(event.x))

    def do_zoom(self, event: Event):
        self.zoom_level += 1 if event.delta > 0 else -1
        if self.min_zoom <= self.zoom_level <= self.max_zoom:
            self.update_idletasks()
            print(f'zoomed: {self.zoom_level = }')
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            self.factor = 1.001 ** event.delta
            self.drawing_factor *= self.factor
            self.scale(ALL, x, y, self.factor, self.factor)
        elif self.zoom_level > self.max_zoom:
            self.zoom_level = self.max_zoom
        elif self.zoom_level < self.min_zoom:
            self.zoom_level = self.min_zoom

    def alt_clicked(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        x0, y0, x1, y1 = self.round_coords(x, y)
        print(f"\n(x0, y0) = ({x0}, {y0})")
        # check for cell
        clicked_cell_id = None
        try:
            clicked_cell_id = self.find_withtag(f'x{x0}&&y{y0}')[0]
        except Exception as e:
            pass
        if clicked_cell_id:
            clicked_cell: Cell = self.cells[clicked_cell_id]
            print(clicked_cell)

    def clicked(self, event):
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        x0, y0, x1, y1 = self.round_coords(x, y)
        print(f"\n(x0, y0) = ({x0}, {y0})")
        # check for cell
        clicked_cell_id = None
        try:
            clicked_cell_id = self.find_withtag(f'x{x0}&&y{y0}')[0]
        except Exception as e:
            pass
        print(f'{clicked_cell_id = }')
        if clicked_cell_id:
            print('clicked an existing cell')
            clicked_cell: Cell = self.cells[clicked_cell_id]
            clicked_cell.activate()
        else:
            print('no existing cell', end=" ")
            new_cell = Cell(self, x0, y0, x1, y1)
            new_cell.activate()
            self.cells[new_cell.id] = new_cell
            print(f"created cell {new_cell.id}")
    
    def round_coords(self, x, y):
        scaled_size = self.grid_spacing * self.drawing_factor
        x0, y0 = (x // scaled_size) * scaled_size, (y // scaled_size) * scaled_size
        x1, y1 = x0 + scaled_size, y0 + scaled_size
        return x0, y0, x1, y1  

    def prime_cells_for_update(self):
        self.cells_to_activate = {} 
        for id, cell in self.cells.items():
            cell: Cell
            cell.next_generation()

    def update_cells(self):
        _cells = self.cells.copy()
        for id, cell in self.cells_to_activate.items():
            cell: Cell
            cell.activate()
    
    def update_board(self):
        self.after(100, self.prime_cells_for_update)
        self.after(10, self.update_cells)

    def schedule_update_board(self):
        self.after(200, self.update_board)
        self.after(200, self.schedule_update_board)


class Cell:
    board: LifeBoard = None
    FILL_COLOUR = '#0047ab'  # cobalt blue
    OUTLINE_COLOUR = 'black'  # "#dcdcdc"
    OUTLINE_WIDTH = 2

    def __init__(self, board, x0, y0, x1, y1, **kwargs):
        self.board: LifeBoard = board
        self.alive: bool = False
        self.activate_next: bool = False
        self.grid_location = (x0, y0)
        self.id = self.board.create_rectangle(x0, y0, x1, y1, tags=(f"x{x0}", f"y{y0}"), outline=self.OUTLINE_COLOUR, width=self.OUTLINE_WIDTH)
        # self.board.create_text(text=f'{self.id}', x=self.grid_location[0], y=self.grid_location[1])
        self.neighbourhood_region = self.get_neighbourhood()
        self.neighbours: list = []; self.find_neighbours()
        # self.board.tag_bind(self.id, "<Button-1>", lambda event: self.activate())
        self.board.tag_bind(self.id, "<Button-3>", lambda event: self.__repr__())
        # self.next_generation()  # sets self.next_state

    def __repr__(self) -> str:
        return f"Class: Cell\n  ID={self.id}\n  status={'alive' if self.alive else 'dead'}\n  co-ord={self.grid_location}\n  neighbours={[neighbour.id for neighbour in self.neighbours]}\n  living-neighbours={self.find_living_neighbours()}\n  next-gen={self.next_generation()}"
    
    def __eq__(self, value: object) -> bool:
        return self.id == value
        
    def __hash__(self) -> int:
        return hash(self.id)

    def activate(self):
        self.alive = not self.alive
        fill = self.FILL_COLOUR if self.alive else ''
        self.board.itemconfig(self.id, fill=fill)
        if len(self.neighbours) < 8:
            self.build_neighbours()

    def get_neighbourhood(self):
        # deprecated
        x, y = self.grid_location[0], self.grid_location[1]
        delta = self.board.grid_spacing + 1
        return (x - delta, y - (2 * delta), x + (2 * delta), y + delta + 2)

    def find_neighbours(self):
        # deprecated
        # self.neighbours = self.board.find_enclosed(*self.neighbourhood_region)

        # search by tags
        x, y = self.grid_location[0], self.grid_location[1]
        delta = self.board.grid_spacing
        self.neighbours: list = []  # __|__i________________________
        for i in range(-1, 2):      # j | (-1, -1)  (0, -1)  (1, -1)
            for j in range(-1, 2):  #   | (-1,  0)  (SELF )  (1,  0)
                if i == j == 0:     #   | (-1,  1)  (0,  1)  (1,  1) 
                    pass
                else:
                    try:
                        search_results = self.board.find_withtag(f'x{x + (i * delta)}&&y{y + (j * delta)}')
                        existing_cell_id = search_results[0]
                        existing_cell = self.board.cells[existing_cell_id]
                        self.neighbours.append(existing_cell)
                    except Exception as e:
                        # print(f"{self.id=}, {i=}, {j=}  :  {e}")
                        pass
        return self.neighbours

    def build_neighbours(self):
        x, y = self.grid_location[0], self.grid_location[1]
        delta = self.board.grid_spacing
        self.neighbours: list = []
        for i in range(-1, 2):      # (-1, -1)  (0, -1)  (1, -1)
            for j in range(-1, 2):  # (-1,  0)  (SELF )  (1,  0)
                if i == j == 0:     # (-1,  1)  (0,  1)  (1,  1) 
                    pass
                elif self.board.find_withtag(f'x{x + (i * delta)}&&y{y + (j * delta)}'):
                    existing_cell_id = self.board.find_withtag(f'x{x + (i * delta)}&&y{y + (j * delta)}')[0]
                    existing_cell = self.board.cells[existing_cell_id]
                    self.neighbours.append(existing_cell)
                else:
                    coords = self.board.round_coords(x + (i * delta), y + (j * delta))
                    new_cell = Cell(self.board, *coords)
                    self.board.cells[new_cell.id] = new_cell
                    self.neighbours.append(new_cell)
        self.neighbours = set(self.neighbours)
        self.neighbours = list(self.neighbours)
        for neighbor in self.neighbours:
            neighbor.find_neighbours()
    
    def find_living_neighbours(self):
        self.living_neighbours = 0
        for neighbour in self.neighbours:
            if neighbour.alive:
                self.living_neighbours += 1
        return self.living_neighbours
    
    def next_generation(self):
        self.find_living_neighbours()
        if self.alive:
            if self.living_neighbours in [2, 3]:
                return True   # will survive
            else:
                self.board.cells_to_activate[self.id] = self
                return False  # will die
        else:
            if self.living_neighbours == 3:
                self.board.cells_to_activate[self.id] = self
                return True   # will be born
            else:
                return False  # will remain dead



class GameOfLife(Tk):
    # The app is a subclass of a Tk() object. This way, we can simply call `self` instead of `self.root`.
    def __init__(self, scrollbars: str = "", scrollregion: tuple = None, pan: str = "", zoom: str = "", **kwargs):
        super().__init__(**kwargs)
        self.header = "Game of Life"
        self.title(self.header)
        icon_data = b'iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABUBJREFUaIHV2VuMXWUVB/DfmltvQy+2trRIgSGaWGIQIyKagg8+GG8kpBoTozFgwosWEh/EN030SZM+mRijidrESKIRAUNQ46UQaDTxFo1QFSilLWA70E7tTJnL8uHbp3PYPWc655yNA//ky5y99p69//+9Lt/6vh24Ds97fWLbCJ7PzGMrzaQfRIQhXLLSRAbBEA5ExK0rTaRfDGErfhIRP4iI8ZUm1CsC2XZ8CB/OzH+uEJ+eEBE7hmq2t+CxiNi9EoT6wRAer9k245cR8ckV4NMzhvBBfLdmX4X9EfGF/z+l3rEjM+FOzCs50T6+mJleiwM7zguoDHtwtiZgAXesNNllCaiMuzFVEzGLD6004WUJqE7chDM1EVO47tUnlVEfSwmol1GQmQfwMcy1mcfx44jY2FemLYEIEWFthA24FNuUargOoxFGIgxHiAv+V/FAx2YuIm7Hd2rmB/DRrF7BgMRXYRMm8AbswjDG8Cz+g+N4CcfwsqrQZMqI6BxCNTftc2Fl2jtgmAyRm8k95D7yIDlNPkeeqf6eJP9OPkx+mbyWvJxcS46Ue3TJgZqAUTxSE/BfXD2AgPeRXyWfqIjPkwtk1sYCeY48TD5I3kVeSa4rItZcdlEBlYidOFkT8St0TbAuxNeRHyHvJ6e6kO42zpF/Jr9Evo0cZ2LnsgRUIj7VIZQ+0wP5cfID5KPkXA/E28c0eYj8LPlm3j+xbAGViPtqAo5h3TLf/A3kveRMn+TbPfEYeRuf39WxjC6Bz1Xx38J2pQXpighjVbLdhpuVPmsQjCrr+Bu5ZaInAZn5jFKV2nF3RGztdH21ZN2MG/AOrO+d74W3VUS8l0u39+oB+LpSn1u4BHu7XLtGmZhuxBXVw5vAEC5na88hJDNP42s18x0RsabdEGFYEXeFEmqbNCegwpq39uMB+DZOtB1vQX0BNKq0AtuVMFro81ndsJqRDX0JyMxpRUQ77oqIoPQ2SjuwUemhRpUWoWHEeL8egG8qbXYL1+Bd1e9hiz1N6xntjWFDiLm+BVQN4L0188dbd8ZI9XtWacaaxjzzpwbxAPyodrynCqPWRDenrPDmmZ33ih2cgTHHzNFBBTyoLHRa2Il3Lz7ANGb4yyaOr204j09x4uBAAqpkfqBmvkV51fOYZf9VPPSe0nVMD/K4dpzDEQ4/OagH4Ke1493Oh889q9m/lyPBE0oqNJLLx/E9HjrchIDfeWVwv5PLVmOBu+/k+Mby+eEZHErytP6TIZW1+m/K+MbkwAIy8wW076WOcex6tlzLiU+XFDmKJzH3KKOP47QSYr1iGj/Ht3CYxVI3KB5W9lVb2M3kTYwNF65j2PI0N9+jzBcv4u3KDD7k4i1GKm78RUX+j5nmIpoT8Ahubzv+BLlrsRC9hImvsOqoEgInFQ+0+qT1lYh6RCxgRvFw680fy1wsZ00J+Eft+JrF589h5rfsu09pLc4qa4rncBWuxhurcxuUGbxF/Cn8XvHwrzHbTr5JAV2+J7Sq6fy+ivR8RexFJSSexZ+UZm99JWBGmb3/hSP4K6YyO5evRgRk5mRETCp7O/WzhzjbmisWKnJnMamszsax2mIezCiJM6VqQTK7V62mPAD/1lGA72fmAkScd8nLiohhJR+iGq1zC5nLq1JNCngK19dsiR+eP8jFHe+q5Z5ru27JN90NTQo41cF2MDOf7nRxm5iB0MRM3MKZDrb7G7x/RzQpYKqDrd7oNY5X0wMv4G8N3r8jmsyBP+BnyjbKm3CgiS34i2HJ7wOvdUTEjhFsqzYTXo/Y9j+E8Ah+V+UfsQAAAABJRU5ErkJggg=='
        icon = PhotoImage(data=icon_data)
        self.iconphoto(True, icon)
        # self.iconbitmap(default='icon.ico')
        
        # Window Creation
        self.build_window(scrollbars=scrollbars, scrollregion=scrollregion, pan=pan, zoom=zoom)
        self.do_bindings()
        self.wm_minsize(1200, 800)
        self.update_idletasks()  # wait until the window is finished
        self.position_window()

    
    def do_bindings(self):
        # self.bind("<>")
        return
    

    def position_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        x_pos = (screen_width - window_width) // 2
        self.geometry(f"+{x_pos}+25")
        # center view 
        self.update()
        center_x = (self.board.winfo_width() // 2) - (2 * self.board.grid_spacing)
        center_y = self.board.winfo_height() // 2
        self.board.scan_dragto(x=center_x, y=center_y, gain=1)

    
    def build_window(self, scrollbars, scrollregion, pan, zoom):
        self.set_styles()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        mainframe = ttk.Frame(self, padding=(4, 4, 4, 4))
        mainframe.grid(row=0, column=0, sticky=(N, E, S, W))
        mainframe.rowconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)

        control_panel = ttk.Frame(mainframe)
        control_panel.grid(row=0, column=0, sticky=('nsew'))

        self.board = LifeBoard(mainframe, background='white', pan=pan, zoom=zoom, bg='#dcdcdc')
        # self.board.config(scrollregion=self.board.bbox("all"))
        self.board.grid(row=0, column=1, sticky=(N, E, S, W))
        self.board.rowconfigure(0, weight=1)
        self.board.columnconfigure(0, weight=1)

        if "h" in scrollbars:
            self.sim_Hscrollbar = ttk.Scrollbar(mainframe, orient='horizontal', command=self.board.xview)
            self.sim_Hscrollbar.grid(row=1, column=1, sticky=(E, W))
            self.board['xscrollcommand'] = self.sim_Hscrollbar.set
        if "v" in scrollbars:
            self.sim_Vscrollbar = ttk.Scrollbar(mainframe, orient='vertical', command=self.board.yview)
            self.sim_Vscrollbar.grid(row=0, column=2, sticky=(N, S))
            self.board['yscrollcommand'] = self.sim_Vscrollbar.set

        self.build_control_panel(control_panel)
    

    def build_control_panel(self, control_panel):
        frame: ttk.Frame = control_panel
        frame.rowconfigure(1, weight=1)
        header_frame = ttk.Frame(frame)
        header_frame.grid(row=0, column=0, sticky=(N, W), padx=10, pady=10)
        name_label = ttk.Label(header_frame, text=self.header, font="_ 24 bold")
        name_label.grid(row=0, column=0, columnspan=1000, sticky=E)
        ToolTip(name_label, "This is a ToolTip.\nIt has multiple lines.\nanother one.\n\nand another.")

        content_frame = ttk.Frame(frame)
        content_frame.grid(row=1, column=0, sticky=(N, S))

        next_step_button = ttk.Button(content_frame, text='Next', command=self.board.schedule_update_board)
        next_step_button.grid()
        
        return
    
    def set_styles(self):
        style = ttk.Style()
        self.mode = 'dark'
        bg = '#eeeeee' if self.mode == 'light' else '#252525'
        style_args = {
            'background': bg,
            'foreground': 'white'
        }
        widget_names = [
            "TButton", "TCheckbutton", "TRadiobutton", "TEntry", "TLabel", 
            "TCombobox", "TSpinbox", "TScale", "TProgressbar", "Treeview", 
            "Notebook", "TFrame", "TLabelFrame"
        ]
        for widget in widget_names:
            style.configure(widget, **style_args)


    def update_game(self):
        # Perform batch updates for the cells
        # Update only the cells that have changed since the last update

        # Schedule the next update
        self.after(100, self.update_game)
    
if __name__ == '__main__':
    main()
