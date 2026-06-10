#!/usr/bin/env python3
"""Single-image test: curl + process"""
import subprocess, json, base64, io, sys
from PIL import Image

prompt = "Professional B2B product photography of corrugated cardboard mailer/shipping box, kraft brown color, angled view showing corrugated edge structure, white background, studio lighting"
outfile = "/Users/hg/bincai-paperbox/images/corrugated-mailer.jpg"

payload = json.dumps({
    "model": "doubao-seedream-4-5-251128",
    "prompt": prompt,
    "n": 1,
    "size": "1920x1920",
    "response_format": "b64_json"
})

print("Calling API via curl...", flush=True)
r = subprocess.run([
    "curl", "-s", "--max-time", "120",
    "-X", "POST",
    "https://ark.cn-beijing.volces.com/api/v3/images/generations",
    "-H", "Authorization: Bearer ark-8515b5a9-79fa-4bd4-9ffb-6dafeb3e1efb-d9042",
    "-H", "Content-Type: application/json",
    "-d", payload
], capture_output=True, text=True, timeout=130)

print(f"curl exit: {r.returncode}", flush=True)
if r.returncode != 0:
    print(f"stderr: {r.stderr}", flush=True)
    sys.exit(1)

resp = r.stdout
print(f"Response length: {len(resp)} chars", flush=True)

# Check for error
data = json.loads(resp)
if "error" in data:
    print(f"API error: {data['error']}", flush=True)
    sys.exit(1)

b64 = data["data"][0]["b64_json"]
print(f"b64 length: {len(b64)}", flush=True)

# Decode and process
img_bytes = base64.b64decode(b64)
img = Image.open(io.BytesIO(img_bytes))
w, h = img.size
print(f"Image: {w}x{h}", flush=True)

img = img.crop((0, 0, w-150, h-150))
img = img.resize((800, 800), Image.LANCZOS)
img.save(outfile, "JPEG", quality=85)
print(f"Saved: {outfile}", flush=True)
