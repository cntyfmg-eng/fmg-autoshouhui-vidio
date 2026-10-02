"""Compose the 16:9 cover: hand-drawn art on the right, title on the left."""
import os

from PIL import Image, ImageDraw, ImageFont

from config import ART, TITLE, WIDTH, HEIGHT, WORK, ensure_dirs
ensure_dirs()
OUT = str(WORK / "cover_16x9.png")

W, H = 1920, 1080
BG = (255, 255, 255)
INK = (23, 23, 20)
ACCENT = (216, 162, 74)

FONT_TITLE = r"C:/Windows/Fonts/msyhbd.ttc"   # Microsoft YaHei Bold
FONT_SUB = r"C:/Windows/Fonts/msyh.ttc"       # Microsoft YaHei

canvas = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(canvas)

# ---- artwork panel (right), matching the video's 16:9 layout ----
art = Image.open(ART).convert("RGB")
panel = (700, 70, W - 84, H - 70)
pw, ph = panel[2] - panel[0], panel[3] - panel[1]
scale = min(pw / art.width, ph / art.height)
art = art.resize((int(art.width * scale), int(art.height * scale)), Image.LANCZOS)
ax = panel[0] + (pw - art.width) // 2
ay = panel[1] + (ph - art.height) // 2
canvas.paste(art, (ax, ay))
d.rectangle([ax - 6, ay - 6, ax + art.width + 5, ay + art.height + 5],
            outline=(214, 206, 192), width=3)

# ---- title block (left): auto-fit inside the column ----
COL_L, COL_R = 96, 664           # keep clear of the art panel at x=798
COL_W = COL_R - COL_L
# TITLE comes from config (env TITLE); SUB/BYLINE are cosmetic and editable.
SUB = "彩铅日记 · 分享的滋味"
BYLINE = "AI 手绘动画"

def fit_font(text, path, max_w, start, floor=44):
    size = start
    while size > floor:
        f = ImageFont.truetype(path, size)
        box = d.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(path, floor)

def draw(text, font, x, y, fill):
    d.text((x, y), text, font=font, fill=fill)
    box = d.textbbox((x, y), text, font=font)
    return box[2] - box[0], box[3] - box[1]

title_font = fit_font(TITLE, FONT_TITLE, COL_W, 120)
sub_font = fit_font(SUB, FONT_SUB, COL_W, 40, floor=26)
by_font = fit_font(BYLINE, FONT_SUB, COL_W, 30, floor=22)

tx, ty = COL_L, 400
tw, th = draw(TITLE, title_font, tx, ty, INK)
d.rounded_rectangle([tx + 4, ty + th + 30, tx + 268, ty + th + 41],
                    radius=6, fill=ACCENT)
_, sh = draw(SUB, sub_font, tx + 4, ty + th + 74, (118, 110, 98))
draw(BYLINE, by_font, tx + 4, ty + th + 74 + sh + 26, (170, 162, 150))

canvas.save(OUT)
print("cover ->", OUT, canvas.size)
print("art box x: %d..%d" % (ax, ax + art.width))
print("title width:", tw, "column width:", COL_W,
      "| overlap:", max(0, (tx + tw) - ax))
