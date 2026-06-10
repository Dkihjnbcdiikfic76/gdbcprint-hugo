#!/usr/bin/env python3
"""Generate all 5 images via Volcano Seedream API"""
import subprocess, json, base64, io, sys, time
from PIL import Image

API_KEY = "Bearer ark-8515b5a9-79fa-4bd4-9ffb-6dafeb3e1efb-d9042"
MODEL = "doubao-seedream-4-5-251128"
API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
OUT = "/Users/hg/bincai-paperbox/images"

IMAGES = [
    ("folding-carton.jpg", "Professional B2B product photography of flat-folded paperboard carton box, printed with colorful retail packaging design, standalone on white background, studio lighting, commercial packaging product photo"),
    ("corrugated-mailer.jpg", "Professional B2B product photography of corrugated cardboard mailer/shipping box, kraft brown color, angled view showing corrugated edge structure, white background, studio lighting"),
    ("kraft-eco-box.jpg", "Professional B2B product photography of eco-friendly kraft paper box with natural texture, brown recycled material, simple clean design with green foliage accent, white background, studio lighting"),
    ("jewelry-box.jpg", "Professional B2B product photography of premium jewelry gift box with velvet interior and lid open, displaying a ring slot, black exterior with gold foil accents, white background, studio lighting"),
    ("factory.jpg", "Professional photograph of a modern Chinese printing factory production floor, automated die-cutting machines, workers in uniform inspecting paper boxes, clean organized workshop, industrial setting, bright lighting"),
]

def generate(filename, prompt):
    outfile = f"{OUT}/{filename}"
    print(f"[GENERATING] {filename}", flush=True)

    payload = json.dumps({
        "model": MODEL, "prompt": prompt, "n": 1,
        "size": "1920x1920", "response_format": "b64_json"
    })

    t0 = time.time()
    r = subprocess.run([
        "curl", "-s", "--max-time", "120", "-X", "POST", API_URL,
        "-H", f"Authorization: {API_KEY}",
        "-H", "Content-Type: application/json",
        "-d", payload
    ], capture_output=True, text=True, timeout=130)

    elapsed = time.time() - t0
    print(f"  curl: {elapsed:.1f}s (exit {r.returncode})", flush=True)

    if r.returncode != 0:
        return f"FAILED: curl exit {r.returncode}: {r.stderr[:200]}"

    data = json.loads(r.stdout)
    if "error" in data:
        return f"FAILED: API error: {data['error'].get('message', str(data['error']))}"

    b64 = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size

    img = img.crop((0, 0, w - 150, h - 150))
    img = img.resize((800, 800), Image.LANCZOS)
    img.save(outfile, "JPEG", quality=85)

    return f"OK (orig:{w}x{h} -> 800x800)"

# --- main ---
results = []
for i, (fn, prompt) in enumerate(IMAGES):
    print(f"\n{'='*50}")
    print(f"[{i+1}/5] {fn}", flush=True)
    result = generate(fn, prompt)
    results.append((fn, result))
    print(f"  RESULT: {result}", flush=True)

print(f"\n{'='*50}")
print("FINAL SUMMARY:")
for fn, status in results:
    marker = "PASS" if status.startswith("OK") else "FAIL"
    print(f"  [{marker}] {fn}: {status}")

ok = sum(1 for _, s in results if s.startswith("OK"))
print(f"\nTotal: {ok}/{len(results)} generated successfully")
