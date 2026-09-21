"""One-off script: generates resources/icon.ico (a small automaton glyph)."""
from PIL import Image, ImageDraw

SIZE = 256
bg = (30, 33, 38, 0)
img = Image.new("RGBA", (SIZE, SIZE), bg)
draw = ImageDraw.Draw(img)

circle_blue = (74, 144, 217, 255)
circle_green = (46, 158, 91, 255)
edge_color = (90, 98, 112, 255)
border = (28, 30, 33, 255)
white = (255, 255, 255, 255)

# rounded square background
draw.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=48, fill=(30, 33, 38, 255))

# state A (start) - top left
a_center = (78, 168)
a_r = 42
# state B - top right
b_center = (178, 88)
b_r = 42
# state C (accept) - bottom right
c_center = (198, 198)
c_r = 42

# edges (draw before circles so circles cover the line ends)
draw.line([a_center, b_center], fill=edge_color, width=8)
draw.line([b_center, c_center], fill=edge_color, width=8)
draw.line([a_center, c_center], fill=edge_color, width=8)

# arrowhead on b->c edge
import math
dx, dy = c_center[0] - b_center[0], c_center[1] - b_center[1]
dist = math.hypot(dx, dy)
ux, uy = dx / dist, dy / dist
tip = (c_center[0] - ux * c_r, c_center[1] - uy * c_r)
left = (tip[0] - ux * 22 + uy * 12, tip[1] - uy * 22 - ux * 12)
right = (tip[0] - ux * 22 - uy * 12, tip[1] - uy * 22 + ux * 12)
draw.polygon([tip, left, right], fill=edge_color)

# start arrow into A
draw.line([(10, 168), (a_center[0] - a_r, 168)], fill=(224, 138, 30, 255), width=8)
draw.polygon([
    (a_center[0] - a_r, 168),
    (a_center[0] - a_r - 20, 158),
    (a_center[0] - a_r - 20, 178),
], fill=(224, 138, 30, 255))

def circle(center, r, fill, double=False):
    x, y = center
    draw.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=border, width=5)
    if double:
        r2 = r - 9
        draw.ellipse([x - r2, y - r2, x + r2, y + r2], outline=border, width=4)

circle(a_center, a_r, circle_blue)
circle(b_center, b_r, circle_blue)
circle(c_center, c_r, circle_green, double=True)

sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("resources/icon.ico", sizes=sizes)
print("Icon saved to resources/icon.ico")
