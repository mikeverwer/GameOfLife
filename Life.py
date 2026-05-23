from tkinter import *
from tkinter import ttk
from tooltip import ToolTip
from tk_animated_toplevel import AnimatedToplevel
import tk_dark_mode
import json
from pathlib import Path

SAVE_FILE = Path(__file__).with_name('saved_configurations.json')

def main():
    app = GameOfLife(pan='y')
    app.mainloop()


class LifeBoard(Canvas):
    def __init__(self, parent, **kwargs):
        canvas_args: dict = {}
        self.app: GameOfLife = None
        self.make_pannable = False
        self.make_zoomable = False
        self.log_widget: Text = None
        self.max_zoom = 1
        self.min_zoom = -3
        self.factor = 1
        self.drawing_factor = 1
        self.zoom_level = self.max_zoom  # fully zoomed in
        for key, value in kwargs.items():
            if key in ["pan", "zoom", "app"]:
                self.handle_kwarg(key, value)
            else:
                canvas_args[key] = value       
        super().__init__(parent, **canvas_args)

        self.playing = False
        self.generation = 0
        frames_per_second = 4
        self.update_interval = 1000 // frames_per_second  # frames per second
        self.grid_spacing = 16
        self.cells: dict[int: Cell] = {}
        self.cells_to_activate: dict[int: Cell] = {}
        self.do_binds()
        self.saved_configuration = self.starting_config()
        self.draw_configuration()

    def handle_kwarg(self, key, value):
        if key == "pan" and value:
            self.make_pannable = True
        elif key == "zoom" and value:
            self.make_zoomable = True
        elif key == 'logger' and value:
            self.log_widget = value
        elif key == "app" and value:
            self.app = value
    
    def starting_config(self):
        s = self.grid_spacing
        config = [(s, s), (2*s, s), (3*s, s), (3*s, 0), (2*s, -1*s)]
        return config

    def draw_configuration(self, config: list = None):
        if config is None:
            config = self.saved_configuration
        scaled = self.grid_spacing * self.drawing_factor
        for x0, y0 in config:
            x1, y1 = x0 + scaled, y0 + scaled
            existing = self.find_withtag(f'x{x0}&&y{y0}')
            if existing:
                cell: Cell = self.cells[existing[0]]
                if not cell.alive:
                    cell.activate()
            else:
                cell = Cell(self, x0, y0, x1, y1)
                cell.activate()
                self.cells[cell.id] = cell

    def do_binds(self):
        self.bind("<Button-3>", self.alt_clicked)
        if self.make_zoomable:
            self.bind("<MouseWheel>", self.do_zoom) # WINDOWS ONLY
        if self.make_pannable:
            self.bind('<ButtonPress-2>', lambda event: self.scan_mark(event.x, event.y))
            self.bind("<B2-Motion>", lambda event: self.scan_dragto(event.x, event.y, gain=1))
            self.bind("<Button-4>", self.give_coords)
        self.bind("<Button-1>", self.clicked)

    def give_coords(self, event):
        canvasx = self.canvasx(event.x)
        canvasy = self.canvasy(event.y)
        self.log(f"\nCanvas: ({canvasx}, {canvasy})\nEvent : ({event.x}, {event.y})")
        # self.log(type(event.x))

    def do_zoom(self, event: Event):
        self.zoom_level += 1 if event.delta > 0 else -1
        if self.min_zoom <= self.zoom_level <= self.max_zoom:
            self.update_idletasks()
            self.log(f'zoomed: {self.zoom_level = }')
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
        self.log(f"\n(x0, y0) = ({x0}, {y0})")
        # check for cell
        clicked_cell_id = None
        try:
            clicked_cell_id = self.find_withtag(f'x{x0}&&y{y0}')[0]
        except Exception as e:
            pass
        if clicked_cell_id:
            clicked_cell: Cell = self.cells[clicked_cell_id]
            self.log(clicked_cell)

    def clicked(self, event=None, recursive=False):
        if self.playing:
            self.toggle_play_pause()
            # don't wipe saved_configuration here
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        x0, y0, x1, y1 = self.round_coords(x, y)

        clicked_cell_id = None
        try:
            clicked_cell_id = self.find_withtag(f'x{x0}&&y{y0}')[0]
        except Exception:
            pass

        if clicked_cell_id:
            cell = self.cells[clicked_cell_id]
            cell.activate()
        else:
            cell = Cell(self, x0, y0, x1, y1)
            cell.activate()
            self.cells[cell.id] = cell

        if not recursive:
            key = (x0, y0)                       # store the *grid* position
            if cell.alive:
                if key not in self.saved_configuration:
                    self.saved_configuration.append(key)
            else:
                if key in self.saved_configuration:
                    self.saved_configuration.remove(key)
    
    def round_coords(self, x, y):
        scaled_size = self.grid_spacing * self.drawing_factor
        x0 = int((x // scaled_size) * scaled_size)
        y0 = int((y // scaled_size) * scaled_size)
        x1 = x0 + int(scaled_size)
        y1 = y0 + int(scaled_size)
        return x0, y0, x1, y1  
    
    def get_state(self):
        self.saved_configuration = []
        for id, cell in self.cells.items():
            cell: Cell
            if cell.alive:
                self.saved_configuration.append(cell.grid_location)
        return self.saved_configuration

    def prime_cells_for_update(self):
        self.cells_to_activate = {} 
        for id, cell in self.cells.items():
            cell: Cell
            cell.compute_next_generation()

    def update_cells(self):
        for id, cell in self.cells_to_activate.items():
            cell: Cell
            cell.activate()
    
    def update_board(self):
        self.prime_cells_for_update()
        self.update_cells()
        self.generation += 1
        if self.playing:
            # self.prime_cells_id = self.after(10, self.prime_cells_for_update)
            # self.update_cells_id = self.after(10, self.update_cells)
            self.schedule_update_board()

    def schedule_update_board(self):
        self.playing = True
        self.update_board_id = self.after(self.update_interval, self.update_board)

    def toggle_play_pause(self):
        if self.playing:
            self.stop_update_board()
        else:
            self.schedule_update_board()
        self.app.play_pause_state.set(not self.app.play_pause_state.get())
        self.app.pp_button_text.set('Pause' if self.app.play_pause_state.get() else 'Play')

    def stop_update_board(self):
        self.after_cancel(self.update_board_id)
        # self.after_cancel(self.update_cells_id)
        # self.after_cancel(self.prime_cells_id)
        self.playing = False

    def log(self, *args, route_print=True, **kwargs):
        if self.log_widget is None:
            return
        self.log_widget['state'] = 'normal'
        if route_print:
            print(*args, **kwargs)
        end: str = None
        try:
            end = kwargs['end']
        except:
            end = '\n'
        obj: object = args[0]
        self.log_widget.insert(END, obj.__repr__() + end)
        self.log_widget.see('end')
        self.log_widget['state'] = 'disabled'


class Cell:
    board: LifeBoard = None
    FILL_COLOUR = '#0047ab'  # cobalt blue
    OUTLINE_COLOUR = "#aaaaaa"  # "#dcdcdc"
    OUTLINE_WIDTH = 2

    def __init__(self, board, x0, y0, x1, y1, **kwargs):
        self.board: LifeBoard = board
        self.alive: bool = False
        self.activate_next: bool = False
        self.grid_location = (x0, y0)
        self.id = self.board.create_rectangle(x0, y0, x1, y1, tags=(f"x{x0}", f"y{y0}"), outline=self.OUTLINE_COLOUR, width=self.OUTLINE_WIDTH)
        # self.board.create_text(text=f'{self.id}', x=self.grid_location[0], y=self.grid_location[1])
        self.neighbours: list = []; self.find_neighbours()
        # self.next_generation()  # sets self.next_state

    def __repr__(self) -> str:
        return f"Class: Cell\n  ID={self.id}\n  status={'alive' if self.alive else 'dead'}\n  co-ord={self.grid_location}\n  neighbours={[neighbour.id for neighbour in self.neighbours]}\n  living-neighbours={self.find_living_neighbours()}\n  next-gen={self.compute_next_generation()}"
    
    def __eq__(self, value: object) -> bool:
        return self.id == value
        
    def __hash__(self) -> int:
        return hash(self.id)

    def activate(self):
        self.alive = not self.alive
        if self.alive:
            self.board.addtag_withtag("alive", self.id)
            fill = self.FILL_COLOUR
        else:
            self.board.dtag(self.id, "alive")
            fill = ''
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
                        # self.log(f"{self.id=}, {i=}, {j=}  :  {e}")
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
    
    def compute_next_generation(self):
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
        tk_dark_mode.apply_dark_theme(self)
        self.header = "Game of Life"
        self.title(self.header)
        icon_data = b'iVBORw0KGgoAAAANSUhEUgAAAEMAAABDCAYAAADHyrhzAAAACXBIWXMAAA9hAAAPYQGoP6dpAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAATZJREFUeJzt2TFKA1EYReH7JPvIGrRPq9MG01u4jlRuw8Z+xDbW9skaspLfQpADg1jkTWDgfGWKO8mBR2Beq6rMqQ3jMclth6lTHXZ3HXb+dDPn+NIYA4wBxgBjgDHAGGAMMAYYA4wBxgBjgDHAGGAMMAasrvCMj1Q7XrzS6tzhu/zziJlf+y2JxwSMAcYAY8A1/k1m1YZxn2TbY2vxMVJtnVY9Lqk8JmQMMAYYA4wBxgBjgDHAGGAMMAYYA4wBxgBjgDFg+S93fu5TTn2mvDf55TEBY4AxwBjQcj++dtr6qs/Ht8kDhnGfauuL11ud67B7mXz88P6UZHPxfpJVWj33GEq1JJnESLLtdK9xSjKJkWTT6zd4TMAYYAwwBhgDjAHGAGOAMcAYYAwwBhgDjAHGAGOAMeAbxZYuqxlzi5AAAAAASUVORK5CYII='
        icon = PhotoImage(data=icon_data)
        self.iconphoto(True, icon)
        # self.iconbitmap(default='icon.ico')
        
        # Window Creation
        self.abt_panel: AnimatedToplevel = None
        self.compendium_panel: AnimatedToplevel = None
        self.build_window(scrollbars=scrollbars, scrollregion=scrollregion, pan=pan, zoom=zoom)
        self.wm_minsize(1200, 800)
        self.update_idletasks()  # wait until the window is finished
        self.position_window()
        self.build_about_panel()
        self.build_compendium_panel()
        self.do_bindings()

    
    def do_bindings(self):
        self._resize_after = None
        self.bind("<Configure>", self._on_resize)


    def _on_resize(self, event):
        if event.widget is not self:
            return
        if self._resize_after is not None:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(50, self._apply_resize)


    def _apply_resize(self):
        self._resize_after = None
        if not hasattr(self, "abt_panel"):
            return
        w = int(self.winfo_width() * 0.7)
        h = int(self.winfo_height() * 0.7)
        self.abt_panel.resize(w, h)
        self.center_on_living()
    

    def position_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        x_pos = (screen_width - window_width) // 2
        self.geometry(f"+{x_pos}+25")
        self.center_on_origin()


    def center_on_origin(self):
        # center view 
        self.update()
        center_x = (self.board.winfo_width() // 2) - (2 * self.board.grid_spacing)
        center_y = self.board.winfo_height() // 2
        self.board.scan_dragto(x=center_x, y=center_y, gain=1)


    def center_on_configured_drawing(self):
        self.update()
        # x0, y0, x1, y1 = self.board.bbox(ALL)
        # self.log(x0, y0, x1, y1)
        # drawing_width = abs(x1 - x0); drawing_height = abs(y1 - y0)
        # center_x = abs(self.board.winfo_width() - drawing_width) // 2
        # center_y = abs(self.board.winfo_height() - drawing_height) // 2
        # self.board.scan_dragto(x=center_x, y=center_y, gain=1)
        if len(self.board.saved_configuration) > 0:
            x0 = min(self.board.saved_configuration[0]);  y0 = min(self.board.saved_configuration[1])
            x1 = max(self.board.saved_configuration[0]);  y1 = max(self.board.saved_configuration[1])
            drawing_width = x1 - x0;                      drawing_height = y1 - y0
            center_x = abs(self.board.winfo_width() - drawing_width) // 2
            center_y = abs(self.board.winfo_height() - drawing_height) // 2
            self.board.scan_dragto(x=int(center_x), y=int(center_y), gain=1)


    def center_on_living(self):
        self.update_idletasks()
        bbox = self.board.bbox("alive")
        if not bbox:
            return
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        w = self.board.winfo_width()
        h = self.board.winfo_height()
        # where the cells currently appear in widget coords
        screen_cx = cx - self.board.canvasx(0)
        screen_cy = cy - self.board.canvasy(0)
        # how far we need to shift content to land them at widget centre
        dx = w / 2 - screen_cx
        dy = h / 2 - screen_cy
        # scan_mark(0,0) + scan_dragto(dx, dy) shifts content by exactly (dx, dy)
        self.board.scan_mark(0, 0)
        self.board.scan_dragto(int(dx), int(dy), gain=1)
        

    def build_window(self, scrollbars, scrollregion, pan, zoom):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        mainframe = ttk.Frame(self, padding=(4, 4, 4, 4))
        mainframe.grid(row=0, column=0, sticky=(N, E, S, W))
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)

        control_panel = ttk.Frame(mainframe)
        control_panel.grid(row=1, column=0, sticky=(E,W))

        self.board = LifeBoard(mainframe, app=self, pan=pan, zoom=zoom, bg="#AAAAAA", background='#AAAAAA', borderwidth=0)
        # self.board.config(scrollregion=self.board.bbox("all"))
        self.board.grid(row=0, column=0, sticky=(N, E, S, W))

        if "h" in scrollbars:
            self.sim_Hscrollbar = ttk.Scrollbar(mainframe, orient='horizontal', command=self.board.xview)
            self.sim_Hscrollbar.grid(row=1, column=1, sticky=(E, W))
            self.board['xscrollcommand'] = self.sim_Hscrollbar.set
        if "v" in scrollbars:
            self.sim_Vscrollbar = ttk.Scrollbar(mainframe, orient='vertical', command=self.board.yview)
            self.sim_Vscrollbar.grid(row=0, column=2, sticky=(N, S))
            self.board['yscrollcommand'] = self.sim_Vscrollbar.set

        self.build_control_panel(control_panel)
    

    def build_control_panel(self, control_panel: ttk.Frame):
        control_panel.columnconfigure(0, weight=1, uniform='cp')
        control_panel.columnconfigure(1, weight=1, uniform='cp')
        control_panel.columnconfigure(2, weight=1, uniform='cp')

        name_label = ttk.Label(control_panel, text=self.header, font="_ 24 bold")
        name_label.grid(row=0, column=0, padx=20, sticky=W, pady=10)

        button_frame = ttk.Frame(control_panel)
        button_frame.grid(row=0, column=1)   # no sticky → centred in its cell

        next_step_button = ttk.Button(button_frame, text='Next', command=self.board.update_board)
        next_step_button.grid(row=0, column=0, padx=5)

        self.play_pause_state = BooleanVar(value=FALSE)
        self.pp_button_text = StringVar(value='Play')
        play_button = ttk.Button(button_frame, textvariable=self.pp_button_text, command=self.toggle_pause_play)
        play_button.grid(row=0, column=1, padx=5)

        ttk.Separator(button_frame, orient='vertical').grid(row=0, column=2, padx=10, sticky=(N,S))

        clear_button = ttk.Button(button_frame, text='Clear', command=self.clear_board)
        clear_button.grid(row=0, column=3, padx=5)

        reset_button = ttk.Button(button_frame, text='Reset', command=self.reset_board)
        reset_button.grid(row=0, column=4, padx=5)

        info_frame = ttk.Frame(control_panel)
        info_frame.grid(row=0, column=2)
        ttk.Button(info_frame, text='About', command=self.open_about_panel).grid(row=0, column=0, padx=10)

        save_config_frame = ttk.Frame(info_frame)
        save_config_frame.grid(row=0, column=1)

        self.config_name_entry = ttk.Entry(save_config_frame, width=20)
        self.config_name_entry.grid(row=0, column=0, padx=5)
        ttk.Button(save_config_frame, text="Save", command=self.save_configuration).grid(row=0, column=1)

        ttk.Button(info_frame, text='Compendium', command=self.open_compendium)

        self.add_logging_text(control_panel, grid=False)
        
    
    def add_logging_text(self, content_frame, grid=True):
        # Logging Text
        self.log_text = Text(content_frame, width=40, height=8, font='Helvetica 9', background="#252525", foreground='white', wrap='word', borderwidth=1)
        self.log_text.insert('1.0', "Logging Window\n\n")
        self.log_text["state"] = "disabled"
        self.board.log_widget = self.log_text
        clear_log_button = ttk.Button(content_frame, text='X', command=self.clear_log)
        clear_log_button.config(width=2)
        if grid:
            self.log_text.grid(row=0, column=2, rowspan=2)
            clear_log_button.grid(row=0, column=3)


    def build_about_panel(self):
        BG="#18191B"
        self.wwidth = self.winfo_width();   self.wheight = self.winfo_height()
        self.abt_panel = AnimatedToplevel(self, duration=0.25, bottom_offset=100,
            width=int(self.wwidth * 0.7), height=int(self.wheight * 0.8))

        container = Frame(self.abt_panel.top, padx=10, pady=10, bg=BG)
        container.pack(fill='both', expand=True)
        container.rowconfigure(1, weight=1)   # let content_frame stretch vertically
        container.columnconfigure(0, weight=1)

        ttk.Button(container, text='Close', command=self.abt_panel.hide).grid(
            row=0, column=0, pady=(0, 10)
        )

        content_frame = Frame(container, bg=BG)
        content_frame.grid(row=1, column=0, sticky=(N,S,E,W))
        content_frame.columnconfigure(0, weight=1)

        explanation_string = """
The Game of Life is a cellular automaton created by John Conway in 1970. The game is played by setting an initial configuration of the board and observing how it evolves. 

The state of the board at any generation (or iteration) is completely determined by the initial configuration; in other words, the universe of the game is deterministic.

The game became widely known because it is Turing Complete despite consisting of a very simple ruleset. A Turing Complete system is one in which anything that can be algorithmically computed can be computed within it. Thus, it is possible (given a computer with enough memory) to build the Game of Life inside the Game of Life, or to build Minecraft in the Game of Life, etc.        
""" 
        rules_string = """
The universe of the Game of Life is an infinite two-dimensional grid of square cells that can be either "alive" or "dead".
The universe "evolves" one generation at a time based on the details below.

Each generation, every cell observes its eight adjacent neighbors and updates its state according to the following:

"""
        rule1 = "Any live cell with fewer than two live neighbors dies (underpopulation)."
        rule2 = "Any live cell with more than three live neighbors dies (overpopulation)."
        rule3 = "Any live cell with two or three live neighbors lives, unchanged, to the next generation."
        rule4 = "Any dead cell with exactly three live neighbors will come to life in the next generation."
        
        t = Text(
            content_frame, width=1, height=1, 
            font="Helvetica 12", wrap='word',
            highlightthickness=0, background=BG)
        t.tag_configure("h1", font=("Helvetica", 24, "bold"), foreground="#e0e0e0",
            spacing1=20, spacing3=12)
        t.tag_configure("p",      font=("Helvetica", 14), lmargin1=10, lmargin2=10)
        t.tag_configure("bold",   font=("Helvetica", 14, "bold"))
        t.tag_configure("italic", font=("Helvetica", 14, "italic"))
        t.tag_configure("list",
                        spacing1=10, spacing3=10,
                        lmargin1=40, lmargin2=80, tabs=(80,))
        t.tag_configure("li_num", font=("Helvetica", 16, "bold"), foreground="#0047ab")
        t.tag_configure("li_txt", font=("Helvetica", 14))

        def list_item(num: int | str, text: str, t: Text = t):
            t.insert("end", f"{str(num)}.",   ("list", "li_num"))
            t.insert("end", "\t",   "list")
            t.insert("end", text + "\n", ("list", "li_txt"))

        t.grid(row=1, column=0, padx=10, pady=10, sticky=(N,S,E,W))
        content_frame.rowconfigure(1, weight=1)

        # t.insert("end", "Explanation", "h1")
        t.insert("end", explanation_string, "p")
        t.insert("end", "Rules", "h1")
        t.insert("end", rules_string, "p")
        list_item(1, rule1)
        list_item(2, rule2)
        list_item(3, rule3)
        list_item(4, rule4)


    def build_compendium_panel(self):
        pass
        
    
    def open_about_panel(self):
        self.abt_panel.show()

    
    def open_compendium(self):
        pass


    def toggle_pause_play(self):
        self.board.toggle_play_pause()

    
    def clear_board(self, clear_memory=True):
        if self.play_pause_state.get():
            self.toggle_pause_play()
        if clear_memory:
            self.board.saved_configuration = []
        self.board.delete(ALL)
        self.board.cells = {}

    
    def reset_board(self):
        self.clear_board(clear_memory=False)
        self.update_idletasks()
        self.board.draw_configuration(self.board.saved_configuration)
        self.update_idletasks()        # let bbox see the new items
        self.center_on_living()


    def save_configuration(self):
        configuration = self.board.get_state()
        print(configuration)
        name = self.config_name_entry.get().strip()
        if not configuration:
            self.log("Nothing to save — board is empty.")
            return
        if not name:
            self.log("Please enter a name for the configuration.")
            return

        try:
            with SAVE_FILE.open('r') as f:
                saves = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            saves = {}

        saves[name] = configuration
        try:
            with SAVE_FILE.open('w') as f:
                json.dump(saves, f, indent=2, sort_keys=True)
        except OSError as e:
            self.log(f"Couldn't save: {e}")
            return

        self.log(f"Saved '{name}'.")

    
    def load_configuration(self, name):
        saves = {}
        try:
            with SAVE_FILE.open('r') as f:
                saves = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log("Error loading file: {e}")
            return
        
        if name not in saves:
            self.log(f"Unable to load - configuration {name} not found.")
            return
        
        self.board.draw_configuration(saves[name])


    def clear_log(self):
        self.log_text['state'] = 'normal'
        self.log_text.delete('1.0', END)
        self.log_text.insert('1.0', "Logging Window\n\n")
        self.log_text.see('end')
        self.log_text['state'] = 'disabled'


    def log(self, *args, route_print=True, **kwargs):
        log_widget = self.log_text
        log_widget['state'] = 'normal'
        if route_print:
            print(*args, **kwargs)
        if 'end' not in kwargs:
            kwargs['end'] = '\n'
        log_widget.insert(END, args[0] + kwargs['end'])
        log_widget.see('end')
        log_widget['state'] = 'disabled'

    
if __name__ == '__main__':
    main()
