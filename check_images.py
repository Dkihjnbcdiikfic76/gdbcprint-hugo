import os, re, yaml

detail_dir = 'content/products/detail/'

cat_to_image_prefix = {
    'rigid-gift-boxes': ['cat-rigid'],
    'folding-cartons': ['cat-fold'],
    'corrugated-mailers': ['cat-corrugated', 'cat-mailer'],
    'magnetic-closure-boxes': ['cat-magnetic'],
    'kraft-eco-boxes': ['cat-kraft'],
    'jewelry-boxes': ['cat-jewelry'],
}

# Default images for each category
default_images = {
    'rigid-gift-boxes': '/images/cat-rigid-others.jpg',
    'folding-cartons': ['/images/cat-fold-cosmetic.jpg', '/images/cat-fold-mailer.jpg'],
    'corrugated-mailers': '/images/cat-corrugated-mailers.jpg',
    'magnetic-closure-boxes': '/images/cat-magnetic.jpg',
    'kraft-eco-boxes': '/images/cat-kraft.jpg',
    'jewelry-boxes': '/images/cat-jewelry.jpg',
}

mismatches = []
total = 0

for fname in sorted(os.listdir(detail_dir)):
    if not fname.endswith('.md'):
        continue
    total += 1
    
    with open(detail_dir + fname) as f:
        content = f.read()
    
    # Extract YAML frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        mismatches.append((fname, 'NO FRONTMATTER', ''))
        continue
    
    try:
        fm = yaml.safe_load(fm_match.group(1))
    except:
        mismatches.append((fname, 'BAD YAML', ''))
        continue
    
    categories = fm.get('categories', [])
    if not categories:
        mismatches.append((fname, 'NO CATEGORIES', ''))
        continue
    
    cat = categories[0]  # primary category
    
    # Extract image from markdown body
    img_match = re.search(r'!\[.*?\]\((/images/[^)]+)\)', content)
    img = img_match.group(1) if img_match else 'NO IMAGE'
    
    if cat in cat_to_image_prefix:
        expected = cat_to_image_prefix[cat]
        matched = any(e.lower() in img.lower() for e in expected)
        if not matched:
            mismatches.append((fname, cat, img))
    else:
        mismatches.append((fname, f'UNKNOWN CAT: {cat}', img))

print(f'Total products: {total}')
print(f'Mismatches: {len(mismatches)}')
for m in mismatches:
    print(f'  MISMATCH: {m[0]}')
    print(f'    category={m[1]}  image={m[2]}')

# Summary by category
from collections import Counter
cat_counts = Counter()
for m in mismatches:
    cat_counts[m[1]] += 1
print('\nBy category:')
for cat, count in cat_counts.most_common():
    print(f'  {cat}: {count}')
