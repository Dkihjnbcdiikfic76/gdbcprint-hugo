#!/usr/bin/env python3
"""Comprehensive curl-based visual quality audit for gdbcprint.com.

QUICK START (no editing needed — auto-discovers fetched pages):
  1. Fetch 6 pages into /tmp/gdbc-*.html:
     curl -sL -o /tmp/gdbc-HOMEPAGE.html https://gdbcprint.com/
     curl -sL -o /tmp/gdbc-prod1.html "https://.../products/detail/<slug>/"
     curl -sL -o /tmp/gdbc-prod2.html "https://.../products/detail/<slug>/"
     curl -sL -o /tmp/gdbc-prod3.html "https://.../products/detail/<slug>/"
     curl -sL -o /tmp/gdbc-blog.html "https://.../blog/<slug>/"
     curl -sL -o /tmp/gdbc-industry.html "https://.../industries/<slug>/"
  2. Run: python3 scripts/visual-audit.py
  3. Auto-discovers /tmp/gdbc-*.html, infers page type from filename.

WHEN PAGES DON'T MATCH (different slugs fetched):
  The script auto-discover mode reads ALL /tmp/gdbc-*.html files.
  Name inference: files containing 'HOMEPAGE' → "Homepage", 'prod' → "Product-*",
  'blog' → "Blog", 'industry' → "Industry". Just use the standard filenames
  above — the discovery regex handles any product slug.

HARDCODED FALLBACK (when /tmp is empty — used in dev/testing):
  Edit the PAGES list below to point at specific files. Used when running
  from a non-standard directory or when curl output lands elsewhere.

Checks: DM Sans loading, body line-height, card CSS, CTA CSS, Quick Specs
padding (5px stale trap), image-category mapping, emoji contamination,
1.5M legacy figures, alt=Home trap, hero-banner fallback, blog/industry
CTAs, article wrapper presence, homepage section inventory, image lazy
loading + async decoding, generic alt text detection, thin-content
detection, duplicate H2 sections, cross-page section consistency,
and more.

Cron-safe: no execute_code, no pipes, no subprocess — pure file reads.
"""

import re
import os
import glob as _glob

# ── Page registry ──────────────────────────────────────────────────
# AUTO-DISCOVER: Scans /tmp/gdbc-*.html. Infers type from filename:
#   HOMEPAGE → Homepage, prod → Product, blog → Blog, industry → Industry.
# Falls back to this hardcoded list when /tmp is empty (dev/testing).
# To override: edit this list and comment out the auto-discover block in main().
PAGES = [
    ("Homepage",      "/tmp/gdbc-HOMEPAGE.html"),
    ("Product-Rigid", "/tmp/gdbc-prod1.html"),
    ("Product-Fold",  "/tmp/gdbc-prod2.html"),
    ("Product-Corr",  "/tmp/gdbc-prod3.html"),
    ("Blog",          "/tmp/gdbc-blog.html"),
    ("Industry",      "/tmp/gdbc-industry.html"),
]

CANONICAL_CATS = {
    "rigid-gift-boxes", "folding-cartons", "corrugated-mailers",
    "magnetic-closure-boxes", "kraft-eco-boxes", "jewelry-boxes",
}

GENERIC_ALT_PATTERNS = [
    "Bincai Blog",
    "Bincai Product",
    "Bincai Paper Box",
    "Category Image",
    "Product Image",
    "Image",
    "Photo",
]


def analyze_page(name, path, html):
    """Return a dict of visual checks for a single fetched page."""
    info = {}
    info["size"] = len(html)
    info["style_blocks"] = len(re.findall(r"<style[^>]*>", html))
    info["dm_sans"] = "fonts.googleapis.com" in html and "DM+Sans" in html
    info["has_card"] = "class=card" in html
    info["has_pill"] = ".pill-" in html

    # Body styling
    lh = re.search(r"body\s*\{[^}]*line-height:\s*([^;]+)", html)
    info["body_lh"] = lh.group(1).strip() if lh else "NOT SET"
    ff = re.search(r"body\s*\{[^}]*font-family:\s*([^;]+)", html)
    info["body_font"] = ff.group(1).strip()[:60] if ff else "NOT SET"

    # Images
    imgs = re.findall(r"<img [^>]*>", html)
    info["img_count"] = len(imgs)
    info["img_srcs"] = [
        re.search(r"src=([^\s>]+)", i).group(1)
        for i in imgs[:6]
        if re.search(r"src=([^\s>]+)", i)
    ]
    info["img_alts"] = [
        re.search(r"alt=([^\s>]+)", i).group(1)
        for i in imgs[:6]
        if re.search(r"alt=([^\s>]+)", i)
    ]

    # Image loading attributes (render-image hook check)
    info["img_lazy_count"] = len(re.findall(r"<img [^>]*loading=lazy", html))
    info["img_async_count"] = len(re.findall(r"<img [^>]*decoding=async", html))
    # Content images (non-homepage) MUST have lazy+async
    info["img_missing_lazy"] = info["img_count"] - info["img_lazy_count"]
    info["img_missing_async"] = info["img_count"] - info["img_async_count"]
    # Generic alt text traps
    info["generic_alt_count"] = sum(html.count(f'alt={p}') for p in GENERIC_ALT_PATTERNS)
    info["no_alt_count"] = info["img_count"] - len(re.findall(r"<img [^>]*alt=", html))

    # Tables
    info["table_count"] = len(re.findall(r"<table", html))
    td_pads = re.findall(r"padding:\s*(\d+px\s+\d+px)[^;]*;", html)
    info["td_paddings"] = td_pads[:5]

    # Quick Specs
    info["has_quick_specs"] = "Quick Specs" in html

    # CTA buttons
    ctas = re.findall(r"class=btn-cta[^>]*>(.*?)</a>", html)
    info["cta_buttons"] = ctas[:3]
    info["cta_count"] = len(ctas)

    # Headings
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1", html)
    info["h1"] = h1s[0][:80] if h1s else "NOT FOUND"
    h2s = re.findall(r"<h2[^>]*>(.*?)</h2", html)
    info["h2s"] = [h.strip()[:60] for h in h2s[:8]]
    info["h2_count"] = len(h2s)

    # Duplicate H2 detection (added 2026-06-12 — catches redundant sections
    # like two "Why" headings on one page, invisible to pure CSS checks)
    all_h2s = re.findall(r"<h2[^>]*>(.*?)</h2", html)
    h2_texts = [h.strip() for h in all_h2s]
    seen = {}
    dups = []
    for txt in h2_texts:
        seen[txt] = seen.get(txt, 0) + 1
    for txt, count in seen.items():
        if count > 1:
            dups.append(f"'{txt}' ({count}x)")
    info["duplicate_h2s"] = dups

    # Semantic duplicate Why detection (added 2026-06-12 — catches
    # "Why Bincai for X" + generic "Why Bincai" which exact-match
    # duplicate H2 detection misses because headings differ).
    # Pattern: any H2 starting with "Why" appearing alongside another
    # H2 starting with "Why" that is shorter (the generic table).
    why_h2s = [h for h in h2_texts if h.startswith("Why")]
    if len(why_h2s) > 1:
        # Check if one is the bare "Why Bincai" (or "Why Choose Bincai")
        # and another is a specific "Why Bincai for X" — that's a duplicate pair
        bare_why = [h for h in why_h2s if h in ("Why Bincai", "Why Choose Bincai")]
        specific_why = [h for h in why_h2s if h not in ("Why Bincai", "Why Choose Bincai")]
        if bare_why and specific_why:
            dups.append(
                f"SEMANTIC DUP: {specific_why[0]} + {bare_why[0]} "
                f"(generic table follows specific section — visual redundancy)"
            )
    info["duplicate_h2s"] = dups

    # Key section presence (for cross-page consistency checks)
    info["has_faq"] = bool(re.search(r"<h2[^>]*>(?:FAQ|Frequently Asked Questions)</h", html))
    info["has_related"] = bool(re.search(r"<h2[^>]*>Related Products<", html))

    # Card/CTA CSS
    card_css = re.search(r"\.card\s*\{([^}]+)\}", html)
    info["card_css"] = card_css.group(1).strip()[:200] if card_css else "NOT FOUND"
    cta_css = re.search(r"\.btn-cta\s*\{([^}]+)\}", html)
    info["cta_css"] = cta_css.group(1).strip()[:200] if cta_css else "NOT FOUND"

    # Article wrapper (MUST come before is_thin which depends on article_len)
    article = re.findall(r"<article[ >](.*?)</article", html, re.DOTALL)
    info["article_present"] = len(article) > 0
    info["article_len"] = len(article[0]) if article else 0

    # Content density (thin page detection — added 2026-06-12)
    # Thin = few images + few H2s + small article body
    # ⚠️  Must be AFTER article_len is set (above) — accessed in condition below
    info["is_thin"] = (
        info["img_count"] <= 2
        and info["h2_count"] <= 1
        and info["article_len"] > 0
        and info["article_len"] < 3000
    )

    # Image styling
    img_bd = re.findall(r"img[^}]*border-radius:\s*(\d+px)", html)
    info["img_border_radius"] = img_bd[:3]

    # TH background styling (pitfall check)
    th_bg = re.findall(r"article table th\{[^}]*background:\s*([^;]+)", html)
    info["th_background"] = th_bg[0] if th_bg else "NOT SET"

    # Legacy figure traps
    # has_1_7m: matches both abbreviated "1.7M" (stats bar) and prose "1.7 million" (body text).
    # The abbreviated-only check was a false-negative source — many product pages write the
    # figure out in prose (e.g. "1.7 million color boxes") and the old check reported "N".
    info["has_1_7m"] = "1.7M" in html or bool(re.search(r"1\.7\s*million", html))
    info["has_1_5m"] = bool(re.search(r"1\.5\s*million", html))

    # Emojis (4-byte UTF-8)
    emoji = len(
        re.findall(
            rb"[\xf0][\x9f][\x80-\xbf][\x80-\xbf]",
            html.encode("utf-8", errors="ignore"),
        )
    )
    info["emoji_count"] = emoji

    # Non-canonical categories in HTML
    non_canon = [
        cat
        for cat in ["special-shape-boxes", "toy-boxes", "christmas-gift-boxes", "paper-bags"]
        if f"/products/{cat}/" in html
    ]
    info["non_canonical_cats"] = non_canon

    # Quick Specs padding check (stale 5px trap)
    info["p5_count"] = len(re.findall(r"padding:\s*5px\s+0\s*;", html))
    info["p10_count"] = len(re.findall(r"padding:\s*10px\s+12px[^;]*;", html))

    # Footer
    info["has_footer"] = "<footer" in html

    # Cert badges (was a known pitfall — class defined with no CSS rule)
    info["has_cert_badge_css"] = ".cert-badge" in html

    # Card-image ratio (industry pages: 4 cards, all must have images)
    info["card_count"] = html.count("class=card")
    # Count images inside card divs (approx: <img after class=card)
    info["card_img_count"] = len(re.findall(r"class=card[^>]*><img", html))

    # Blog/industry: check if product-category images appear in IMG tags (not body text)
    # Only search within <img ...> tags to avoid false positives from footer nav links
    img_tags_blob = " ".join(re.findall(r"<img [^>]*>", html))
    info["blog_has_product_img"] = bool(
        re.search(r"src=(?:[^ ]*)(?:cat-rigid|cat-fold|corrugated-mailer)", img_tags_blob)
    )

    return info


def print_page_report(name, info):
    """Print a formatted report for one page."""
    print(f"\n── {name} ({info['size']:,} bytes) ──")
    print(f"  Font: DM={'Y' if info['dm_sans'] else 'N'} | body-font: {info['body_font']} | lh: {info['body_lh']}")
    print(f"  Style blocks: {info['style_blocks']} | Imgs: {info['img_count']} | Tables: {info['table_count']}")
    print(f"  Cards: {'Y' if info['has_card'] else 'N'} | CTAs: {info['cta_count']} | Pills: {'Y' if info['has_pill'] else 'N'}")
    print(f"  Card CSS: {info['card_css'][:100]}")
    print(f"  CTA CSS: {info['cta_css'][:100]}")
    print(f"  TH background: {info['th_background']}")
    print(f"  H1: {info['h1']}")
    print(f"  H2s: {info['h2s'][:4]}")
    print(f"  CTA text: {info['cta_buttons']}")
    print(f"  Img alts: {info['img_alts'][:3]}")
    print(f"  Img border-radius: {info['img_border_radius']}")
    print(f"  Lazy-load: {info['img_lazy_count']}/{info['img_count']} | Async: {info['img_async_count']}/{info['img_count']}")
    print(f"  Generic alts: {info['generic_alt_count']} | No alt: {info['no_alt_count']}")
    print(f"  Quick Specs: {'Y' if info['has_quick_specs'] else 'N'} | Article: {'Y' if info['article_present'] else 'N'} ({info['article_len']}ch)")
    print(f"  1.7M: {'Y' if info['has_1_7m'] else 'N'} | 1.5M trap: {'Y' if info['has_1_5m'] else 'N'}")
    print(f"  P5-stale: {info['p5_count']} | P10: {info['p10_count']}")
    print(f"  Emojis: {info['emoji_count']} | Non-canonical: {info['non_canonical_cats']}")
    print(f"  Cert-badge CSS: {'Y' if info['has_cert_badge_css'] else 'N'} | Cards: {info['card_count']} (imgs: {info['card_img_count']})")
    if info.get('is_thin'):
        print(f"  ⚠  THIN CONTENT: {info['img_count']} imgs, {info['h2_count']} H2s, {info['article_len']}ch article — needs expansion")
    if info.get('duplicate_h2s'):
        for d in info['duplicate_h2s']:
            print(f"  ⚠  DUPLICATE H2: {d} — consider merging or removing redundant section")
    if "Blog" in name:
        print(f"  Blog product-cat img: {'Y' if info['blog_has_product_img'] else 'N'}")


def cross_page_audit(pages_data):
    """Run cross-page checks and return a list of issue strings.
    pages_data: list of (name, info_dict, path) tuples.
    """
    issues = []

    for name, info, _path in pages_data:
        # Blog and industry pages must have CTAs
        if info["cta_count"] == 0 and ("Blog" in name or "Industry" in name):
            issues.append(f"{name}: Missing CTA button (0 .btn-cta)")

        # Quick Specs must NOT leak to blog/industry
        if info["has_quick_specs"] and ("Blog" in name or "Industry" in name):
            issues.append(f"{name}: Quick Specs leaked to non-product page")

        # Product DETAIL pages must have Quick Specs — but product SECTION/LISTING pages
        # (e.g., /products/rigid-gift-boxes/ rendered by products/list.html) should NOT.
        # Auto-discovery names section pages "Product-GDBC-PROD-SECTION.HTML" or "Product-GDBC-PRODUCTS.HTML".
        # Only flag pages whose slug suggests a detail page (has the /detail/ path or a long product-style slug).
        is_section_page = "PROD-SECTION" in name or "PRODUCTS" in name or "LIST" in name.upper()
        if not info["has_quick_specs"] and "Product" in name and not is_section_page:
            issues.append(f"{name}: Product page missing Quick Specs")

        # Stale 5px padding
        if info["p5_count"] > 0 and "Product" in name:
            issues.append(f"{name}: Stale padding:5px 0 ({info['p5_count']} occurrences)")

        # Missing footer
        if not info["has_footer"]:
            issues.append(f"{name}: Missing footer")

        # TH background styling
        if info["th_background"] == "NOT SET" and info["table_count"] > 1:
            issues.append(f"{name}: article table th missing background styling")

        # 1.5M trap
        if info["has_1_5m"]:
            issues.append(f"{name}: Legacy 1.5M figure detected")

        # Emoji
        if info["emoji_count"] > 0:
            issues.append(f"{name}: {info['emoji_count']} emoji characters found")

        # Image loading attributes (render-image hook check)
        if info["img_count"] > 0 and info["img_missing_lazy"] > 0:
            # Homepage card images already have lazy in home.html, but content pages MUST
            if "Product" in name or "Blog" in name or "Industry" in name:
                issues.append(f"{name}: {info['img_missing_lazy']}/{info['img_count']} images missing loading=lazy (render-image hook?)")
        if info["img_count"] > 0 and info["img_missing_async"] > 0:
            if "Product" in name or "Blog" in name or "Industry" in name:
                issues.append(f"{name}: {info['img_missing_async']}/{info['img_count']} images missing decoding=async (render-image hook?)")

        # Generic alt text
        if info["generic_alt_count"] > 0:
            issues.append(f"{name}: {info['generic_alt_count']} images with generic alt text (e.g. 'Bincai Blog')")

        # Missing alt text entirely
        if info["no_alt_count"] > 0:
            issues.append(f"{name}: {info['no_alt_count']} images missing alt attribute")

        # Blog posts should NOT use product-category images (hero-banner instead)
        if info["blog_has_product_img"] and "Blog" in name:
            issues.append(f"{name}: Blog post using product category image in <img> tag (should use hero-banner)")

        # Industry pages: card count should equal card image count
        if "Industry" in name and info["card_count"] > 0 and info["card_img_count"] == 0:
            issues.append(f"{name}: {info['card_count']} cards but 0 card images (text-only cards)")

        # Thin content detection (product pages with few images + few H2s + small body)
        if info.get("is_thin") and "Product" in name:
            issues.append(
                f"{name}: THIN CONTENT — {info['img_count']} imgs, "
                f"{info['h2_count']} H2s, {info['article_len']}ch article "
                f"(consider expanding with H2 sections + FAQ + Related Products)"
            )

        # Duplicate H2 detection (same heading text appearing twice — redundant sections)
        if info.get("duplicate_h2s") and "Product" in name:
            for d in info["duplicate_h2s"]:
                issues.append(f"{name}: DUPLICATE H2 — {d} (visual redundancy; merge or remove)")

    # ─── Product page section consistency (cross-page) ───
    # Check whether FAQ/Related are present on some products but missing on others
    prod_pages = [(n, i) for n, i, _p in pages_data if "Product" in n]
    if len(prod_pages) >= 2:
        faq_present = any(i.get("has_faq") for _, i in prod_pages)
        rel_present = any(i.get("has_related") for _, i in prod_pages)
        for name, info in prod_pages:
            if faq_present and not info.get("has_faq"):
                issues.append(f"{name}: Missing FAQ section (other sampled products have it — content inconsistency)")
            if rel_present and not info.get("has_related"):
                issues.append(f"{name}: Missing Related Products section (other sampled products have it — content inconsistency)")

    # Homepage-specific checks
    homepage_path = None
    for name, info, p in pages_data:
        if name == "Homepage":
            homepage_path = p
            break
    if homepage_path and os.path.exists(homepage_path):
        with open(homepage_path) as f:
            hhtml = f.read()
        hero_count = hhtml.count("hero-banner-wide.jpg")
        if hero_count < 3:
            issues.append(f"Homepage: Only {hero_count} hero-banner fallbacks (<3)")
        alt_home = hhtml.count("alt=Home")
        if alt_home > 0:
            issues.append(f"Homepage: {alt_home} alt=Home ($.Title trap)")
        # Get the homepage info for DM Sans / cert-badge checks
        hp_info = next((i for n, i, _p in pages_data if n == "Homepage"), None)
        if hp_info:
            if not hp_info["dm_sans"]:
                issues.append("Homepage: DM Sans not loaded")
            if not hp_info["has_cert_badge_css"]:
                issues.append("Homepage: No .cert-badge CSS rule (badges may be unstyled)")
            if hp_info["card_count"] > 0 and hp_info["card_img_count"] == 0:
                issues.append(f"Homepage: {hp_info['card_count']} cards but 0 card images")

    return issues


def discover_pages():
    """Auto-discover pages from /tmp/gdbc-*.html. Returns list of (name, path)."""
    _files = sorted(_glob.glob("/tmp/gdbc-*.html"))
    if not _files:
        return None  # caller falls back to hardcoded PAGES
    discovered = []
    for fp in _files:
        fn = os.path.basename(fp).upper()
        if "HOMEPAGE" in fn:
            discovered.append(("Homepage", fp))
        elif "PROD" in fn:
            # Preserve order: prod1→Product-1, prod2→Product-2, prod3→Product-3
            idx = fn.replace("Gdbc-Prod", "").replace(".html", "").strip()
            discovered.append((f"Product-{idx or '?'}", fp))
        elif "BLOG" in fn:
            discovered.append(("Blog", fp))
        elif "INDUSTRY" in fn:
            discovered.append(("Industry", fp))
        else:
            discovered.append((fn.lower().replace(".html", ""), fp))
    return discovered if discovered else None


def main():
    print("=" * 64)
    print("VISUAL QUALITY AUDIT — gdbcprint.com")
    print("=" * 64)

    # Auto-discover /tmp/gdbc-*.html first; fall back to hardcoded PAGES
    pages_to_check = discover_pages()
    if pages_to_check is None:
        pages_to_check = PAGES
        print("  (using hardcoded PAGES — no /tmp/gdbc-*.html found)")
    else:
        print(f"  (auto-discovered {len(pages_to_check)} pages from /tmp/gdbc-*.html)")

    pages_data = []
    for name, path in pages_to_check:
        if not os.path.exists(path):
            print(f"\n  SKIP {name}: file not found ({path})")
            continue
        with open(path) as f:
            html = f.read()
        info = analyze_page(name, path, html)
        pages_data.append((name, info, path))  # store path for homepage re-read in cross_page_audit
        print_page_report(name, info)

    # Cross-page
    print("\n" + "=" * 64)
    print("CROSS-PAGE ISSUES")
    print("=" * 64)

    issues = cross_page_audit(pages_data)
    if issues:
        for i in issues:
            print(f"  ⚠  {i}")
    else:
        print("  PASS: No cross-page issues found.")

    print("\nDone.")


if __name__ == "__main__":
    main()
