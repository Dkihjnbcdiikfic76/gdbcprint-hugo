#!/usr/bin/env python3
"""Fix duplicate "Why Bincai" / "Why Choose Bincai" sections across all products.

Two operations:
  1. Files with BOTH "Why Bincai" and "Why Choose Bincai": 
     Remove the generic "Why Choose Bincai" table (keep the specific "Why Bincai")
  2. Files with ONLY "Why Choose Bincai" (no "Why Bincai"):
     Rename heading to "Why Bincai" (canonical name)

Usage:
  cd /Users/hg/gdbcprint-hugo
  python3 scripts/fix-duplicate-why-sections.py

Safe: target pattern is an exact match for the generic table. Files with
category-specific variants (e.g. "Why Choose Bincai for Electronics Packaging")
are not matched and are left untouched.
"""

import os
import re

PRODUCT_DIR = '/Users/hg/gdbcprint-hugo/content/products/detail'

# The canonical generic "Why Choose Bincai" table to remove when it's a duplicate.
# Must be an exact match — slight variations (e.g. "Why Choose Bincai for X")
# intentionally won't match and will be skipped.
WHY_CHOOSE_TABLE = """## Why Choose Bincai

| Feature | Detail |
|---------|--------|
| Experience | 22 years since 2003 |
| Factory | 10,000m² with KBA & Heidelberg presses |
| Quality | ISO 9001:2015 certified |
| Eco | FSC certified sustainable materials |
| Capacity | 1.7M+ color boxes + 220K+ gift boxes daily |
| Clients | 200+ brands across 50+ countries |
| Custom | Any size, color, finish, insert |
| MOQ | 500-1000 pcs, trial orders accepted |
| Free Sample | Free pre-production sample (freight collect) |
| Shipping | Worldwide DHL/FedEx/UPS/Sea |

[Request your free quote →](/contact/)"""

removed_duplicates = 0
renamed_sole = 0
skipped = 0

for fname in sorted(os.listdir(PRODUCT_DIR)):
    if not fname.endswith('.md'):
        continue
    fpath = os.path.join(PRODUCT_DIR, fname)
    with open(fpath) as f:
        content = f.read()

    has_why_bincai = '## Why Bincai\n' in content
    has_why_choose = '## Why Choose Bincai\n' in content

    if has_why_bincai and has_why_choose:
        # Both sections exist — remove the generic "Why Choose Bincai" table
        if WHY_CHOOSE_TABLE in content:
            new_content = content.replace(WHY_CHOOSE_TABLE, '[Request your free quote →](/contact/)')
            with open(fpath, 'w') as f:
                f.write(new_content)
            removed_duplicates += 1
            print(f'  DEDUP: {fname}')
        else:
            skipped += 1
            print(f'  SKIP (variant): {fname} — "Why Choose Bincai" is not the standard generic table')
    elif not has_why_bincai and has_why_choose:
        # Only has "Why Choose Bincai" — rename to canonical
        new_content = content.replace('## Why Choose Bincai\n', '## Why Bincai\n')
        with open(fpath, 'w') as f:
            f.write(new_content)
        renamed_sole += 1

print(f'\nDone: {removed_duplicates} duplicates removed, '
      f'{renamed_sole} renamed to canonical, '
      f'{skipped} skipped (variants)')
