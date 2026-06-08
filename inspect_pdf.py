import fitz

doc = fitz.open("price_sample.pdf")
page = doc[0]
print("Страниц:", len(doc))
print("Размер страницы:", page.rect)
print()
print("Текстовые блоки:")
for block in page.get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            t = span["text"].strip()
            if t:
                bbox = tuple(round(x, 1) for x in span["bbox"])
                size = round(span["size"], 1)
                print(f"  {repr(t):<35} bbox={bbox}  size={size}")

print()
print("Изображений на странице:", len(page.get_images()))
doc.close()
