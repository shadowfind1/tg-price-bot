from PIL import Image

img = Image.open("tile_04_xref10.png").convert("RGB")
w, h = img.size
print(f"Tile size: {w} x {h}")

# Sample background color (top-right corner, away from text)
bg = img.getpixel((w - 10, h // 2))
print(f"Background color: {bg}")

# Sample text color
text_color = None
for x in range(5, 200):
    r, g, b = img.getpixel((x, h // 2))
    if g > 80 and g > r * 1.3 and g > b * 1.3:
        text_color = (r, g, b)
        break
print(f"Text color sample: {text_color}")

# Find x bounds of "8100" (before the gap to "т")
print("\nScanning x at mid-height for green pixels:")
mid_y = h // 2
green_xs = []
for x in range(0, w):
    r, g, b = img.getpixel((x, mid_y))
    if g > 80 and g > r * 1.3 and g > b * 1.3:
        green_xs.append(x)

if green_xs:
    print(f"  Green x range: {min(green_xs)} - {max(green_xs)}")

# Find gap between "0" and "т"
gaps = []
prev = None
for x in green_xs:
    if prev is not None and x - prev > 10:
        gaps.append((prev, x))
    prev = x
if gaps:
    print(f"  Gaps (end of number - start of т): {gaps}")

# Find y extent of the number
print("\nScanning y at x=50 (inside '8'):")
for y in range(0, h):
    r, g, b = img.getpixel((50, y))
    is_green = g > 80 and g > r * 1.3 and g > b * 1.3
    if is_green:
        print(f"  Green y starts at: {y}")
        break
for y in range(h - 1, -1, -1):
    r, g, b = img.getpixel((50, y))
    is_green = g > 80 and g > r * 1.3 and g > b * 1.3
    if is_green:
        print(f"  Green y ends at: {y}")
        break
