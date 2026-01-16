import os
from tkinter import *
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont

# ------------------------------ App State ------------------------------
class EditorState:
    def __init__(self):
        self.img = None              # current full-res PIL image
        self.original = None         # original full-res image
        self.display = None          # resized PIL for display
        self.tkimg = None            # PhotoImage for canvas
        self.canvas_img_id = None

        self.history = []            # undo stack
        self.redo = []               # redo stack

        self.canvas_w = 820
        self.canvas_h = 540
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # tools
        self.mode = "none"           # none | draw | crop | text
        self.brush_color = "#ff0000"
        self.brush_size = 6
        self.last_cx = None
        self.last_cy = None

        # crop
        self.crop_start = None
        self.crop_rect_id = None

        # rotate
        self.rotate_angle = 0

        # text
        self.text_color = "#ffffff"
        self.text_string = "Sample Text"

state = EditorState()

# ------------------------------ Helpers ------------------------------
def push_history():
    if state.img is not None:
        state.history.append(state.img.copy())
        state.redo.clear()

def undo():
    if state.history:
        state.redo.append(state.img.copy())
        state.img = state.history.pop()
        render()
        set_status("Undo")

def redo():
    if state.redo:
        state.history.append(state.img.copy())
        state.img = state.redo.pop()
        render()
        set_status("Redo")

def set_status(msg):
    status_var.set(msg)

def fit_to_canvas(img):
    cw, ch = state.canvas_w, state.canvas_h
    iw, ih = img.size
    scale = min(cw/iw, ch/ih)
    nw, nh = int(iw*scale), int(ih*scale)
    disp = img.resize((nw, nh), Image.LANCZOS)
    off_x = (cw - nw)//2
    off_y = (ch - nh)//2
    return disp, scale, off_x, off_y

def canvas_to_image_coords(cx, cy):
    if state.img is None:
        return 0, 0
    x = int((cx - state.offset_x) / state.scale)
    y = int((cy - state.offset_y) / state.scale)
    x = max(0, min(state.img.width-1, x))
    y = max(0, min(state.img.height-1, y))
    return x, y

def render():
    if state.img is None:
        canvas.delete("all")
        return
    state.display, state.scale, state.offset_x, state.offset_y = fit_to_canvas(state.img)
    state.tkimg = ImageTk.PhotoImage(state.display)
    canvas.delete("all")
    state.canvas_img_id = canvas.create_image(state.offset_x, state.offset_y, anchor=NW, image=state.tkimg)
    if state.mode == "crop" and state.crop_start and state.crop_rect_id:
        pass

# ------------------------------ File Ops ------------------------------
def open_image():
    path = filedialog.askopenfilename(
        title="Open Image",
        filetypes=[("Image files","*.png *.jpg *.jpeg *.bmp *.tiff *.webp")]
    )
    if not path:
        return
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        messagebox.showerror("Error", f"Cannot open image:\n{e}")
        return
    state.img = img
    state.original = img.copy()
    state.history.clear()
    state.redo.clear()
    state.mode = "none"
    state.rotate_angle = 0
    render()
    set_status(f"Loaded: {os.path.basename(path)}")

def save_image():
    if state.img is None:
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG","*.png"),("JPEG","*.jpg"),("WEBP","*.webp"),("BMP","*.bmp"),("TIFF","*.tiff")]
    )
    if not path:
        return
    try:
        state.img.save(path)
        set_status("Saved image 💾")
    except Exception as e:
        messagebox.showerror("Error", f"Cannot save image:\n{e}")

def reset_image():
    if state.original is None:
        return
    push_history()
    state.img = state.original.copy()
    render()
    set_status("Reset to original 🔄")

# ------------------------------ Adjustments ------------------------------
def adjust(val, mode):
    if state.img is None:
        return
    val = float(val)
    base = state.img
    if mode == "brightness":
        out = ImageEnhance.Brightness(base).enhance(val)
    elif mode == "contrast":
        out = ImageEnhance.Contrast(base).enhance(val)
    elif mode == "sharpness":
        out = ImageEnhance.Sharpness(base).enhance(val)
    elif mode == "color":
        out = ImageEnhance.Color(base).enhance(val)
    else:
        return
    state.img = out
    render()

def adjustment_apply():
    if state.img is None:
        return
    push_history()
    set_status("Adjustments applied ✅")

# ------------------------------ Filters ------------------------------
def apply_filter(kind):
    if state.img is None:
        return
    push_history()
    img = state.img
    if kind == "grayscale":
        img = ImageOps.grayscale(img).convert("RGB")
    elif kind == "invert":
        img = ImageOps.invert(img.convert("RGB"))
    elif kind == "sepia":
        img = ImageOps.colorize(img.convert("L"), "#704214", "#C0A080")
    elif kind == "blur":
        img = img.filter(ImageFilter.BLUR)
    elif kind == "emboss":
        img = img.filter(ImageFilter.EMBOSS)
    elif kind == "edge":
        img = img.filter(ImageFilter.FIND_EDGES)
    elif kind == "red":
        r, g, b = img.split()
        img = Image.merge("RGB", (r, g.point(lambda p: p*0.5), b.point(lambda p: p*0.5)))
    elif kind == "green":
        r, g, b = img.split()
        img = Image.merge("RGB", (r.point(lambda p: p*0.5), g, b.point(lambda p: p*0.5)))
    elif kind == "blue":
        r, g, b = img.split()
        img = Image.merge("RGB", (r.point(lambda p: p*0.5), g.point(lambda p: p*0.5), b))
    elif kind == "warm":
        img = ImageOps.colorize(img.convert("L"), "#FFB347", "#FFCC33")
    elif kind == "cool":
        img = ImageOps.colorize(img.convert("L"), "#3366FF", "#33CCFF")
    state.img = img
    render()
    set_status(f"{kind.capitalize()} applied ✨")

def custom_tint():
    if state.img is None:
        return
    color = colorchooser.askcolor(title="Pick a tint color")
    if not color or not color[1]:
        return
    push_history()
    hexcol = color[1]
    img = ImageOps.colorize(state.img.convert("L"), "#000000", hexcol)
    state.img = img
    render()
    set_status(f"Custom tint {hexcol} applied 🎨")

# ------------------------------ Rotate ------------------------------
def rotate_live(val):
    if state.img is None:
        return
    state.rotate_angle = float(val)
    preview = state.img.rotate(state.rotate_angle, expand=True)
    state.display, state.scale, state.offset_x, state.offset_y = fit_to_canvas(preview)
    state.tkimg = ImageTk.PhotoImage(state.display)
    canvas.delete("all")
    state.canvas_img_id = canvas.create_image(state.offset_x, state.offset_y, anchor=NW, image=state.tkimg)

def rotate_apply():
    if state.img is None:
        return
    push_history()
    state.img = state.img.rotate(state.rotate_angle, expand=True)
    render()
    set_status(f"Rotated {state.rotate_angle:.1f}°")

# ------------------------------ Crop ------------------------------
def set_mode_crop():
    if state.img is None:
        return
    state.mode = "crop"
    set_status("Crop mode: drag to select, then 'Apply Crop'")

def crop_start(event):
    if state.mode != "crop" or state.img is None:
        return
    state.crop_start = (event.x, event.y)
    if state.crop_rect_id:
        canvas.delete(state.crop_rect_id)
        state.crop_rect_id = None

def crop_drag(event):
    if state.mode != "crop" or state.img is None or state.crop_start is None:
        return
    x0, y0 = state.crop_start
    x1, y1 = event.x, event.y
    if state.crop_rect_id:
        canvas.coords(state.crop_rect_id, x0, y0, x1, y1)
    else:
        state.crop_rect_id = canvas.create_rectangle(x0, y0, x1, y1, outline="#00ff88", width=2, dash=(4,2))

def crop_apply():
    if state.mode != "crop" or state.img is None or state.crop_start is None or not state.crop_rect_id:
        return
    x0, y0, x1, y1 = canvas.coords(state.crop_rect_id)
    if x0 > x1: x0, x1 = x1, x0
    if y0 > y1: y0, y1 = y1, y0
    ix0, iy0 = canvas_to_image_coords(x0, y0)
    ix1, iy1 = canvas_to_image_coords(x1, y1)
    if ix1 - ix0 <= 1 or iy1 - iy0 <= 1:
        set_status("Crop area too small")
        return
    push_history()
    state.img = state.img.crop((ix0, iy0, ix1, iy1))
    state.mode = "none"
    if state.crop_rect_id:
        canvas.delete(state.crop_rect_id)
        state.crop_rect_id = None
    state.crop_start = None
    render()
    set_status("Cropped ✂️")

def crop_cancel():
    state.mode = "none"
    if state.crop_rect_id:
        canvas.delete(state.crop_rect_id)
        state.crop_rect_id = None
    state.crop_start = None
    set_status("Crop canceled")

# ------------------------------ Draw ------------------------------
def set_mode_draw():
    if state.img is None:
        return
    state.mode = "draw"
    set_status("Draw mode: press & drag on image ✏️")
    push_history()

def pick_brush_color():
    col = colorchooser.askcolor(title="Brush color")
    if col and col[1]:
        state.brush_color = col[1]
        set_status(f"Brush color {state.brush_color}")

def on_draw_start(event):
    if state.mode != "draw":
        return
    state.last_cx, state.last_cy = event.x, event.y

def on_draw_move(event):
    if state.mode != "draw" or state.last_cx is None:
        return
    canvas.create_line(state.last_cx, state.last_cy, event.x, event.y,
                       fill=state.brush_color, width=state.brush_size, capstyle=ROUND, smooth=True)
    x0, y0 = canvas_to_image_coords(state.last_cx, state.last_cy)
    x1, y1 = canvas_to_image_coords(event.x, event.y)
    draw = ImageDraw.Draw(state.img)
    draw.line((x0, y0, x1, y1), fill=state.brush_color, width=max(1, int(state.brush_size / max(1e-3, state.scale))))
    state.last_cx, state.last_cy = event.x, event.y

def on_draw_end(event):
    if state.mode != "draw":
        return
    state.last_cx, state.last_cy = None, None
    render()

# ------------------------------ Text ------------------------------
def set_mode_text():
    if state.img is None:
        return
    state.mode = "text"
    txt = simpledialog.askstring("Add Text", "Enter text:")
    if txt:
        state.text_string = txt
    col = colorchooser.askcolor(title="Text color")
    if col and col[1]:
        state.text_color = col[1]
    set_status("Text mode: click on image to place text 📝")

def on_text_place(event):
    if state.mode != "text":
        return
    push_history()
    ix, iy = canvas_to_image_coords(event.x, event.y)
    draw = ImageDraw.Draw(state.img)
    font = ImageFont.load_default()
    draw.text((ix, iy), state.text_string, fill=state.text_color, font=font)
    state.mode = "none"
    render()
    set_status("Text placed")

# ------------------------------ UI Setup ------------------------------
root = Tk()
root.title("🎨 Advanced Interactive Image Editor")
root.geometry("1200x750")
root.minsize(1100, 700)

style = ttk.Style()
try:
    style.theme_use("clam")
except:
    pass
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"))

# Toolbar
toolbar = Frame(root, bg="#2b2b2b")
toolbar.pack(side=TOP, fill=X)
ttk.Button(toolbar, text="📂 Open", command=open_image).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="💾 Save", command=save_image).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="🔄 Reset", command=reset_image).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="↶ Undo", command=undo).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="↷ Redo", command=redo).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="✏️ Draw", command=set_mode_draw).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="📝 Text", command=set_mode_text).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="🎯 Crop", command=set_mode_crop).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="Apply Crop", command=crop_apply).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="Cancel Crop", command=crop_cancel).pack(side=LEFT, padx=6, pady=6)
ttk.Button(toolbar, text="🎨 Custom Tint", command=custom_tint).pack(side=LEFT, padx=6, pady=6)

# Main content
content = Frame(root)
content.pack(fill=BOTH, expand=True)

# Filters
filters = LabelFrame(content, text="Filters & Tints")
filters.pack(side=LEFT, fill=Y, padx=10, pady=10)
for title, key in [("Grayscale","grayscale"),("Invert","invert"),("Sepia","sepia"),
                   ("Blur","blur"),("Emboss","emboss"),("Edge","edge"),
                   ("Red Tint","red"),("Green Tint","green"),("Blue Tint","blue"),
                   ("Warm","warm"),("Cool","cool")]:
    ttk.Button(filters, text=title, command=lambda k=key: apply_filter(k)).pack(fill=X, pady=4)

# Canvas
canvas_frame = Frame(content, bd=1, relief=GROOVE)
canvas_frame.pack(side=LEFT, padx=10, pady=10, expand=True)
canvas = Canvas(canvas_frame, width=state.canvas_w, height=state.canvas_h, bg="#111")
canvas.pack()

# Tools
tools = LabelFrame(content, text="Adjustments & Tools")
tools.pack(side=RIGHT, fill=Y, padx=10, pady=10)
Label(tools, text="Brightness").pack(anchor=W, padx=6)
ttk.Scale(tools, from_=0.2, to=2.5, value=1.0, orient=HORIZONTAL, command=lambda v: adjust(v,"brightness")).pack(fill=X, padx=6, pady=4)
Label(tools, text="Contrast").pack(anchor=W, padx=6)
ttk.Scale(tools, from_=0.2, to=2.5, value=1.0, orient=HORIZONTAL, command=lambda v: adjust(v,"contrast")).pack(fill=X, padx=6, pady=4)
Label(tools, text="Sharpness").pack(anchor=W, padx=6)
ttk.Scale(tools, from_=0.2, to=3.0, value=1.0, orient=HORIZONTAL, command=lambda v: adjust(v,"sharpness")).pack(fill=X, padx=6, pady=4)
Label(tools, text="Color").pack(anchor=W, padx=6)
ttk.Scale(tools, from_=0.2, to=2.5, value=1.0, orient=HORIZONTAL, command=lambda v: adjust(v,"color")).pack(fill=X, padx=6, pady=4)
ttk.Button(tools, text="Apply Adjustments", command=adjustment_apply).pack(fill=X, padx=6, pady=10)

# Rotate
ttk.Separator(tools, orient=HORIZONTAL).pack(fill=X, padx=6, pady=6)
Label(tools, text="Rotate (°)").pack(anchor=W, padx=6)
rotate_scale = ttk.Scale(tools, from_=0, to=360, value=0, orient=HORIZONTAL, command=rotate_live)
rotate_scale.pack(fill=X, padx=6, pady=4)
ttk.Button(tools, text="Apply Rotation", command=rotate_apply).pack(fill=X, padx=6, pady=6)

# Brush
ttk.Separator(tools, orient=HORIZONTAL).pack(fill=X, padx=6, pady=6)
Label(tools, text="Draw: Brush Size").pack(anchor=W, padx=6)
ttk.Scale(tools, from_=1, to=40, value=state.brush_size, orient=HORIZONTAL, command=lambda v: setattr(state,'brush_size',int(float(v)))).pack(fill=X, padx=6, pady=4)
ttk.Button(tools, text="Pick Brush Color", command=pick_brush_color).pack(fill=X, padx=6, pady=6)

# Status
status_var = StringVar(value="Welcome! Open an image to begin 🎉")
status = Label(root, textvariable=status_var, anchor=W, bd=1, relief=SUNKEN)
status.pack(side=BOTTOM, fill=X)

# Canvas bindings
canvas.bind("<Button-1>", crop_start)
canvas.bind("<B1-Motion>", crop_drag)
canvas.bind("<ButtonPress-1>", on_draw_start, add="+")
canvas.bind("<B1-Motion>", on_draw_move, add="+")
canvas.bind("<ButtonRelease-1>", on_draw_end, add="+")
canvas.bind("<Button-1>", on_text_place, add="+")

# Start app
root.mainloop()
