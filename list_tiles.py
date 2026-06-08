import fitz, io
from PIL import Image

doc = fitz.open("price_sample.pdf")
page = doc[0]

for i, img in enumerate(page.get_images(full=True)):
    xref = img[0]
    base = doc.extract_image(xref)
    pil = Image.open(io.BytesIO(base["image"]))
    print(f"[{i}] xref={xref} size={pil.size} mode={pil.mode} ext={base['ext']}")
    # Save each tile for inspection
    pil.save(f"tile_{i:02d}_xref{xref}.png")

doc.close()
print("Tiles saved.")
