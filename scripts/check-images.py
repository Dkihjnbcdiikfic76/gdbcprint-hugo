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
    "magnetic-closure-boxes": "/images/magnetic-closure-box.jpg",
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
    "/images/folding-carton.jpg",
}

# Rigid-gift-boxes sub-images that are acceptable alternatives to the default
RIGID_BOX_OK = {
    "/images/cat-rigid-others.jpg",
    "/images/cat-rigid-perfume.jpg",
    "/images/cat-rigid-cosmetic.jpg",
    "/images/cat-rigid-health.jpg",
}

# Product-specific AI-generated images (product-category-N.jpg pattern)
# These are category-correct product images placed on individual product pages.
# They do NOT match canonical category images but ARE valid — they show the
# specific product, not the generic category placeholder.
PRODUCT_IMAGE_OK = {
    "rigid-gift-boxes":      {"/images/product-rigid-1.jpg", "/images/product-rigid-2.jpg"},
    "folding-cartons":       {"/images/product-fold-1.jpg", "/images/product-fold-2.jpg"},
    "corrugated-mailers":    {"/images/product-corr-1.jpg", "/images/product-corr-2.jpg"},
    "magnetic-closure-boxes": set(),   # Add product-magnetic-*.jpg as generated
    "kraft-eco-boxes":       set(),   # Add product-kraft-*.jpg as generated
    "jewelry-boxes":         set(),   # Add product-jewelry-*.jpg as generated
}

# Non-existent files that are known traps (referenced in markdown but never on disk)
# These should always be flagged as mismatches — they WILL render broken on the live site.
NONEXISTENT_IMAGE_TRAPS = {
    "/images/cat-rigid-gift.jpg",
    "/images/cat-rigid-magnetic.jpg",
    "/images/cat-kraft-box.jpg",
    "/images/cat-jewelry-necklace.jpg",
    "/images/cat-magnetic-closure.jpg",
    "/images/cat-kraft-eco.jpg",
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
    """Return 'ok', 'mismatch', 'broken_ref' (non-existent file), or 'unknown_cat'."""
    if category not in CATEGORY_IMAGE:
        return "unknown_cat"

    # Non-existent file traps — always flag as broken (these render broken on live site)
    if image in NONEXISTENT_IMAGE_TRAPS:
        return "broken_ref"

    # Product-specific AI images (product-category-N.jpg) — valid for their category
    allowed_product = PRODUCT_IMAGE_OK.get(category, set())
    if image in allowed_product:
        return "ok"

    expected = CATEGORY_IMAGE[category]

    if category == "folding-cartons":
        if image in FOLDING_CARTON_OK:
            return "ok"
        elif image == expected:
            return "ok"
        else:
            return "mismatch"
    elif category == "rigid-gift-boxes":
        if image in RIGID_BOX_OK:
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

    # Preload set of files that exist in static/images/ (for existence checks)
    static_images = set()
    static_images_dir = "static/images"
    if os.path.isdir(static_images_dir):
        static_images = set(
            f"/images/{f}" for f in os.listdir(static_images_dir)
            if os.path.isfile(os.path.join(static_images_dir, f))
        )

    files = sorted(f for f in os.listdir(CONTENT_DIR) if f.endswith(".md"))
    results = []
    mismatches = 0
    missing_files = 0
    broken_refs = 0
    no_image = 0
    stats = {}

    for fname in files:
        path = os.path.join(CONTENT_DIR, fname)
        title, category, image = extract_frontmatter(path)
        status = check_image(category, image)
        results.append((fname, category, image, status, title))

        stats[category] = stats.get(category, 0) + 1
        if status == "mismatch":
            mismatches += 1
        elif status == "broken_ref":
            broken_refs += 1
        elif image == "NO_IMAGE":
            no_image += 1

        # Also check that the image file actually exists on disk
        if image != "NO_IMAGE" and image not in static_images:
            missing_files += 1

    # Print report
    print(f"=== Image Check: {len(files)} products ===\n")

    # Distribution
    print("Category distribution:")
    for cat, count in sorted(stats.items()):
        print(f"  {cat}: {count}")
    print()

    # NO_IMAGE pages (critical — no image at all)
    if no_image > 0:
        print(f"{no_image} pages with NO IMAGE:\n")
        for fname, category, image, status, title in results:
            if image == "NO_IMAGE":
                expected = CATEGORY_IMAGE.get(category, "?")
                print(f"  {fname}")
                print(f"    Category: {category}")
                print(f"    Should use: {expected}")
                print()
        print()

    # Broken references (non-existent files — will render broken)
    if broken_refs > 0:
        print(f"{broken_refs} BROKEN REFERENCES (file doesn't exist):\n")
        for fname, category, image, status, title in results:
            if status == "broken_ref":
                expected = CATEGORY_IMAGE.get(category, "?")
                print(f"  {fname}")
                print(f"    Category: {category}")
                print(f"    Broken:    {image}")
                print(f"    Should be: {expected}")
                print()
        print()

    # Mismatches
    if mismatches > 0:
        print(f"{mismatches} MISMATCHES (wrong image for category):\n")
        for fname, category, image, status, title in results:
            if status == "mismatch":
                expected = CATEGORY_IMAGE.get(category, "?")
                print(f"  {fname}")
                print(f"    Category: {category}")
                print(f"    Current:  {image}")
                print(f"    Expected: {expected}")
                print()

                if not report_only:
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
                    print(f"    FIXED → {new_img}")
                    print()
    else:
        if no_image == 0 and broken_refs == 0:
            print("All images OK. No issues.\n")
        else:
            print(f"No category mismatches (but {no_image} NO_IMAGE + {broken_refs} broken refs above).\n")

    # Missing files on disk (image referenced but file doesn't exist)
    if missing_files > 0:
        print(f"{missing_files} referenced images DON'T EXIST on disk:\n")
        for fname, category, image, status, title in results:
            if image != "NO_IMAGE" and image not in static_images:
                print(f"  {fname}")
                print(f"    Category: {category}")
                print(f"    Missing:  {image}")
                print()

    # Unknown categories
    unknowns = [(f, c) for f, c, _, s, _ in results if s == "unknown_cat"]
    if unknowns:
        print(f"{len(unknowns)} files with unknown categories:")
        for fname, cat in unknowns:
            print(f"  {fname}: '{cat}'")
        print()

    return mismatches + broken_refs + no_image


if __name__ == "__main__":
    report_only = "--fix" not in sys.argv
    mismatches = scan(report_only=report_only)
    sys.exit(0 if mismatches == 0 else 1)
