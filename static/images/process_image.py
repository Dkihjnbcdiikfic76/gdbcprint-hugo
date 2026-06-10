#!/usr/bin/env python3
"""Process Seedream API b64_json response: decode, crop watermark, resize, save."""
import sys, json, base64, io
from PIL import Image

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <output_path> <b64_json>")
    sys.exit(1)

output_path = sys.argv[1]
b64_data = sys.argv[2]

# Decode base64
img_bytes = base64.b64decode(b64_data)
img = Image.open(io.BytesIO(img_bytes))

# Crop bottom-right 150px watermark
w, h = img.size
img = img.crop((0, 0, w - 150, h - 150))

# Resize to 800x800
img = img.resize((800, 800), Image.LANCZOS)

# Save as JPEG quality 85
img.save(output_path, "JPEG", quality=85)
print(f"OK: {output_path} ({w}x{h} -> 800x800)")
