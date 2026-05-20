from tkinter import *
from tkinter import ttk
from tooltip import ToolTip
import tk_dark_mode


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
        event = Event()
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
                cell = self.cells[existing[0]]
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
        x0, y0 = (x // scaled_size) * scaled_size, (y // scaled_size) * scaled_size
        x1, y1 = x0 + scaled_size, y0 + scaled_size
        return x0, y0, x1, y1  
    
    def get_state(self):
        self.saved_configuration = []
        for id, cell in self.cells.items():
            cell: Cell
            if cell.alive:
                self.saved_configuration.append(cell.grid_location)
                pass

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

        # header_frame = Frame(control_panel, bg='red', border=1)
        # header_frame.grid(row=0, column=0, sticky=W, pady=10)
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

        about_button = ttk.Button(control_panel, text='About')
        about_button.grid(row=0, column=2)
        # self.add_logging_text(content_frame)
        
    
    def add_logging_text(self, content_frame):
        # Logging Text
        self.log_text = Text(content_frame, width=40, height=8, font='Helvetica 9', background="#252525", foreground='white', wrap='word', borderwidth=1)
        self.log_text.grid(row=0, column=2, rowspan=2)
        self.log_text.insert('1.0', "Logging Window\n\n")
        self.log_text["state"] = "disabled"
        self.board.log_widget = self.log_text
        clear_log_button = ttk.Button(content_frame, text='X', command=self.clear_log)
        clear_log_button.grid(row=0, column=3)
        clear_log_button.config(width=2)


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
        if end is None:
            end = '\n'
        log_widget.insert(END, args[0] + kwargs['end'])
        log_widget.see('end')
        log_widget['state'] = 'disabled'

    
if __name__ == '__main__':
    main()
