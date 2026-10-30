"""Validate exported JSON relationships and report source coverage."""
import json
from collections import Counter
from pathlib import Path

folder = Path(__file__).resolve().parent / 'data' / 'paulas-choice'
p = json.loads((folder/'products.json').read_text(encoding='utf-8'))
r = json.loads((folder/'reviews.json').read_text(encoding='utf-8'))
report = json.loads((folder/'crawl_report.json').read_text(encoding='utf-8'))
ids = [x['product_id'] for x in p]
assert len(ids) == len(set(ids)), 'Duplicate product IDs'
assert all(isinstance(x,str) and x.isdigit() for x in ids)
keys = [(x['product_id'],x['review_id']) for x in r]
assert len(keys) == len(set(keys)), 'Duplicate review IDs within product'
assert all(x['product_id'] in set(ids) for x in r), 'Orphan review'
assert all(isinstance(x['review_id'],str) and x['review_id'].isdigit() for x in r)
assert all(x.get('rating') in range(1,6) for x in r), 'Invalid rating'
counts = Counter(x['product_id'] for x in r)
for product in p:
    if product.get('detail_status') == 'complete':
        assert product['seller_id'] == '100169489'
        assert product['is_authentic'] is True
        assert product['name']
    progress = report.get('review_progress',{}).get(product['product_id'])
    if progress:
        assert progress['count'] == counts[product['product_id']], 'Checkpoint count mismatch'
print('PASS: product IDs, review IDs, foreign keys, ratings, seller and checkpoint counts')
print('Products:',len(p),'Details:',dict(Counter(x.get('detail_status') for x in p)))
print('Reviews:',len(r),'Products with reviews:',len(counts))
print('Catalog:',report.get('catalog_status'),'Run:',report.get('status','running'))
print('Review status:',dict(Counter(x.get('status') for x in report.get('review_progress',{}).values())))
