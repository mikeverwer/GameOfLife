from tkinter import *

class InfiniteCanvas(Canvas):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.pattern_image = self.create_pattern_image(20, 20)  # Create a pattern image
        self.bind("<Configure>", self.on_configure)
        self.bind("<Button-1>", self.give_coords)

    def give_coords(self, event):
        canvasx = self.canvasx(event.x)
        canvasy = self.canvasy(event.y)
        print(f"Canvas X/Y: ({canvasx}, {canvasy})\nEvent X/Y : ({event.x}, {event.y})")

    def create_pattern_image(self, width, height):
        pattern_image = PhotoImage(width=width, height=height)
        for x in range(width):
            for y in range(height):
                if x % 20 == 0:
                    pattern_image.put("#000000", (x, y))
                if y % 20 == 0:
                    pattern_image.put("#000000", (x, y))
        return pattern_image

    def on_configure(self, event):
        self.delete("pattern")  # Clear existing pattern
        width = event.width
        height = event.height
        for x in range(0, width, 20):
            for y in range(0, height, 20):
                self.create_image(x, y, image=self.pattern_image, anchor=NW, tags="pattern")

root = Tk()
canvas = InfiniteCanvas(root)
canvas.pack(fill=BOTH, expand=True)

# Add other elements to the canvas as needed

root.mainloop()
