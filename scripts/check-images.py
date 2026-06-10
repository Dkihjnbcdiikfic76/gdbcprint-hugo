#!/usr/bin/env python3
"""Verify all product images match their assigned categories for gdbcprint.com.

Usage: python3 scripts/check-images.py [--fix]

Without --fix: prints a report of matches/mismatches.
With --fix: replaces wrong images with the correct defaults.

Runs from the Hugo source directory (/Users/hg/gdbcprint-hugo).
Works in cron mode (no execute_code needed — call via terminal directly).
"""

import os
import sys
import re
import yaml

CONTENT_DIR = "content/products/detail"

# Category → default image (what should appear on the product page)
CATEGORY_IMAGE = {
    "rigid-gift-boxes":      "/images/cat-rigid-others.jpg",
    "folding-cartons":       "/images/cat-fold-cosmetic.jpg",
    "corrugated-mailers":    "/images/corrugated-mailer.jpg",
    "magnetic-closure-boxes": "/images/cat-rigid-others.jpg",
    "kraft-eco-boxes":       "/images/kraft-eco-box.jpg",
    "jewelry-boxes":         "/images/cat-rigid-jewelry.jpg",
}

# Folding-carton sub-images that are acceptable alternatives to the default
FOLDING_CARTON_OK = {
    "/images/cat-fold-cosmetic.jpg",
    "/images/cat-fold-autolock.jpg",
    "/images/cat-fold-health.jpg",
    "/images/cat-fold-gift.jpg",
    "/images/cat-fold-mailer.jpg",
    "/images/cat-fold-aircraft.jpg",
}


def extract_frontmatter(path: str) -> tuple[str, str, list[str]]:
    """Return (title, first_category, first_image_path) from a Hugo .md file."""
    with open(path) as fh:
        content = fh.read()

    parts = content.split("---")
    if len(parts) < 3:
        return ("?", "?", "NO_IMAGE")

    fm = yaml.safe_load(parts[1])
    cats = fm.get("categories", [])
    category = cats[0] if cats else "?"

    imgs = re.findall(r"!\[.*?\]\((/images/[^)]+)\)", content)
    image = imgs[0] if imgs else "NO_IMAGE"

    title = fm.get("title", os.path.basename(path))
    return (title, category, image)


def check_image(category: str, image: str) -> str:
    """Return 'ok', 'mismatch', or 'unknown_cat'."""
    if category not in CATEGORY_IMAGE:
        return "unknown_cat"

    expected = CATEGORY_IMAGE[category]

    if category == "folding-cartons":
        if image in FOLDING_CARTON_OK:
            return "ok"
        elif image == expected:
            return "ok"
        else:
            return "mismatch"
    else:
        return "ok" if image == expected else "mismatch"


def scan(report_only: bool = True):
    """Scan all product files. Print report. Optionally fix mismatches."""
    if not os.path.isdir(CONTENT_DIR):
        print(f"ERROR: {CONTENT_DIR} not found — run from Hugo source root")
        sys.exit(1)

    files = sorted(f for f in os.listdir(CONTENT_DIR) if f.endswith(".md"))
    results = []
    mismatches = 0
    stats = {}

    for fname in files:
        path = os.path.join(CONTENT_DIR, fname)
        title, category, image = extract_frontmatter(path)
        status = check_image(category, image)
        results.append((fname, category, image, status, title))

        stats[category] = stats.get(category, 0) + 1
        if status == "mismatch":
            mismatches += 1

    # Print report
    print(f"=== Image Check: {len(files)} products ===\n")

    # Distribution
    print("Category distribution:")
    for cat, count in sorted(stats.items()):
        print(f"  {cat}: {count}")
    print()

    # Mismatches
    if mismatches > 0:
        print(f"❌ {mismatches} MISMATCHES found:\n")
        for fname, category, image, status, title in results:
            if status == "mismatch":
                expected = CATEGORY_IMAGE.get(category, "?")
                print(f"  {fname}")
                print(f"    Category: {category}")
                print(f"    Current:  {image}")
                print(f"    Expected: {expected}")
                print()

                if not report_only:
                    # Fix it
                    fix_path = os.path.join(CONTENT_DIR, fname)
                    with open(fix_path) as fh:
                        content = fh.read()
                    old_img = image
                    new_img = expected
                    content = content.replace(
                        f"]({old_img})", f"]({new_img})"
                    )
                    with open(fix_path, "w") as fh:
                        fh.write(content)
                    print(f"    ✅ FIXED → {new_img}")
                    print()
    else:
        print("✅ All images match categories. No mismatches.\n")

    # Unknown categories
    unknowns = [(f, c) for f, c, _, s, _ in results if s == "unknown_cat"]
    if unknowns:
        print(f"⚠️  {len(unknowns)} files with unknown categories:")
        for fname, cat in unknowns:
            print(f"  {fname}: '{cat}'")
        print()

    return mismatches


if __name__ == "__main__":
    report_only = "--fix" not in sys.argv
    mismatches = scan(report_only=report_only)
    sys.exit(0 if mismatches == 0 else 1)
