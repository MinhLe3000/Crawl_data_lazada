"""Check exported product/review keys, labels and checkpoint counts."""
import json
from collections import Counter
from pathlib import Path
f=Path(__file__).resolve().parent/'data'
products=json.loads((f/'products.json').read_text(encoding='utf-8'))
reviews=json.loads((f/'reviews.json').read_text(encoding='utf-8'))
report=json.loads((f/'crawl_report.json').read_text(encoding='utf-8'))
ids={p['product_id'] for p in products}
assert len(ids)==len(products), 'Duplicate products'
assert all(isinstance(p['product_id'],str) and p['product_id'].isdigit() for p in products)
assert all(p.get('shop_type')=='authorized_dealer' for p in products)
assert all(p.get('is_authentic') is True and p.get('is_authorized_dealer') is True for p in products if p.get('detail_status')!='seller_or_item_mismatch')
assert all(r['product_id'] in ids for r in reviews), 'Orphan review'
assert len({(r['product_id'],r['review_id']) for r in reviews})==len(reviews), 'Duplicate reviews'
assert all(r.get('rating') in range(1,6) for r in reviews), 'Invalid rating'
counts=Counter(r['product_id'] for r in reviews)
assert all(v['count']==counts[pid] for pid,v in report.get('review_progress',{}).items()), 'Checkpoint count mismatch'
print('PASS: product/review keys, dealer labels, rating values, checkpoint counts')
print('Products:',len(products),'Details:',dict(Counter(p.get('detail_status') for p in products)),'Reviews:',len(reviews))
print('Catalog:',report['catalog_status'],'Status:',report['status'])
