import fitz, io
from PIL import Image

doc = fitz.open("price_sample.pdf")
page = doc[0]

# Find xref=10
for img in page.get_images(full=True):
    xref = img[0]
    if xref == 10:
        print("Full img tuple:", img)
        print()

# Inspect xobject dictionary
obj_str = doc.xref_object(10)
print("xref=10 PDF object dict:")
print(obj_str)
print()

# Check if there's an SMask
import re
smask_match = re.search(r'/SMask\s+(\d+)\s+0\s+R', obj_str)
if smask_match:
    smask_xref = int(smask_match.group(1))
    print(f"SMask found at xref={smask_xref}")
    smask_obj = doc.xref_object(smask_xref)
    print("SMask dict:", smask_obj)
    # Extract SMask image
    base = doc.extract_image(smask_xref)
    pil = Image.open(io.BytesIO(base["image"]))
    print(f"SMask size: {pil.size}, mode: {pil.mode}")
    pil.save("smask_tile10.png")
    print("SMask saved as smask_tile10.png")
else:
    print("No SMask found")

# Check page content stream for blend modes around this image
doc.close()
