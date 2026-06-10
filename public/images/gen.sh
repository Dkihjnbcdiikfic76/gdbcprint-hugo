#!/bin/bash
set -e
API_URL="https://ark.cn-beijing.volces.com/api/v3/images/generations"
API_KEY="Bearer ark-8515b5a9-79fa-4bd4-9ffb-6dafeb3e1efb-d9042"
MODEL="doubao-seedream-4-5-251128"
OUT="/Users/hg/bincai-paperbox/images"

# Helper: call API, extract b64_json, save to temp file
call_api() {
    local outfile="$1" prompt="$2"
    local tmpjson="/tmp/sd_$$.json"
    local payload="{\"model\":\"${MODEL}\",\"prompt\":$(python3 -c "import sys,json;print(json.dumps(open('/dev/stdin').read()))" <<< "$prompt"),\"n\":1,\"size\":\"1920x1920\",\"response_format\":\"b64_json\"}"
    curl -s --max-time 120 -X POST "$API_URL" -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d "$payload" > "$tmpjson"
    # check error
    if python3 -c "import json;d=json.load(open('$tmpjson'));assert 'data' in d,'err'" 2>/dev/null; then
        python3 -c "
import json, base64, io, sys
from PIL import Image
d=json.load(open('$tmpjson'))
b64=d['data'][0]['b64_json']
img=Image.open(io.BytesIO(base64.b64decode(b64)))
w,h=img.size
img=img.crop((0,0,w-150,h-150))
img=img.resize((800,800),Image.LANCZOS)
img.save('$outfile','JPEG',quality=85)
print(f'OK {w}x{h}->800x800')
"
        return 0
    else
        echo "API_ERROR: $(python3 -c "import json;print(json.load(open('$tmpjson')))" 2>/dev/null)"
        return 1
    fi
}

i=0; ok=0; fail=0

echo "[1/5] folding-carton.jpg"
call_api "$OUT/folding-carton.jpg" "Professional B2B product photography of flat-folded paperboard carton box, printed with colorful retail packaging design, standalone on white background, studio lighting, commercial packaging product photo" && ok=$((ok+1)) || fail=$((fail+1))

echo "[2/5] corrugated-mailer.jpg"
call_api "$OUT/corrugated-mailer.jpg" "Professional B2B product photography of corrugated cardboard mailer/shipping box, kraft brown color, angled view showing corrugated edge structure, white background, studio lighting" && ok=$((ok+1)) || fail=$((fail+1))

echo "[3/5] kraft-eco-box.jpg"
call_api "$OUT/kraft-eco-box.jpg" "Professional B2B product photography of eco-friendly kraft paper box with natural texture, brown recycled material, simple clean design with green foliage accent, white background, studio lighting" && ok=$((ok+1)) || fail=$((fail+1))

echo "[4/5] jewelry-box.jpg"
call_api "$OUT/jewelry-box.jpg" "Professional B2B product photography of premium jewelry gift box with velvet interior and lid open, displaying a ring slot, black exterior with gold foil accents, white background, studio lighting" && ok=$((ok+1)) || fail=$((fail+1))

echo "[5/5] factory.jpg"
call_api "$OUT/factory.jpg" "Professional photograph of a modern Chinese printing factory production floor, automated die-cutting machines, workers in uniform inspecting paper boxes, clean organized workshop, industrial setting, bright lighting" && ok=$((ok+1)) || fail=$((fail+1))

echo "========"
echo "DONE: ${ok}/5 success, ${fail} failed"
ls -lh "$OUT"/folding-carton.jpg "$OUT"/corrugated-mailer.jpg "$OUT"/kraft-eco-box.jpg "$OUT"/jewelry-box.jpg "$OUT"/factory.jpg 2>/dev/null || true
