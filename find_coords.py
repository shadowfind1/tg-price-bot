"""
Запусти этот скрипт для калибровки координат цены в PDF.
Использование:
    python find_coords.py price_sample.pdf

- Кликни на левый верхний угол числа
- Кликни на правый нижний угол числа (знак валюты не включай!)
- Скрипт выведет готовую строку для config.py
"""

import sys
import fitz
from PIL import Image
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from config import RENDER_ZOOM


def run(pdf_path: str):
    doc = fitz.open(pdf_path)
    page = doc[0]
    matrix = fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM)
    pix = page.get_pixmap(matrix=matrix)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()

    print(f"Размер отрендеренного изображения: {img.width} x {img.height} px")
    print("Кликни 2 раза: сначала верхний-левый угол числа, потом нижний-правый.")
    print("Знак валюты не включай!\n")

    fig, ax = plt.subplots(figsize=(7, 10))
    ax.imshow(img)
    ax.set_title("Клик 1: верх-лево  |  Клик 2: низ-право")

    clicks = []

    def on_click(event):
        if event.xdata is None:
            return
        x, y = int(event.xdata), int(event.ydata)
        color = img.getpixel((x, y))
        clicks.append((x, y))
        print(f"Клик {len(clicks)}: x={x}, y={y}  |  цвет: RGB{color}")
        ax.plot(x, y, "ro", markersize=8)
        fig.canvas.draw()

        if len(clicks) == 2:
            x0, y0 = clicks[0]
            x1, y1 = clicks[1]
            print(f"\n--- Скопируй в config.py ---")
            print(f"PRICE_REGION = ({x0}, {y0}, {x1}, {y1})")
            # Цвет текста из центра выделенной области
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            text_color = img.getpixel((cx, cy))
            print(f"TEXT_COLOR = {text_color[:3]}")
            # Цвет фона — пиксель чуть выше области
            bg_color = img.getpixel((cx, max(0, y0 - 5)))
            print(f"BG_COLOR = {bg_color[:3]}")
            print(f"---------------------------\n")

    fig.canvas.mpl_connect("button_press_event", on_click)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python find_coords.py путь_к_файлу.pdf")
        sys.exit(1)
    run(sys.argv[1])
