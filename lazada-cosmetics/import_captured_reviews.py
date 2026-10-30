import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from crawl_cosmetics import OUT,save,stamp
products=json.loads((OUT/'products.json').read_text(encoding='utf-8'))
reviews=json.loads((OUT/'reviews.json').read_text(encoding='utf-8'))
report=json.loads((OUT/'crawl_report.json').read_text(encoding='utf-8'))
known={(x['product_id'],x['review_id']) for x in reviews}
source=Path(__file__).resolve().parent/'review-response.json'
payload=json.loads(source.read_text(encoding='utf-8'))['data']['data']['module']
collected=datetime.fromtimestamp(source.stat().st_mtime,ZoneInfo('Asia/Bangkok')).isoformat()
product=next(x for x in products if x['product_id']=='279648338')
for r in payload['reviews']:
 pid='279648338';rid=str(r['reviewId'])
 if (pid,rid) in known:continue
 known.add((pid,rid))
 reviews.append({'product_id':pid,'review_id':rid,'buyer_name':r.get('buyerName'),'rating':r.get('rating'),'review_date':r.get('reviewTime'),'content':'\n'.join(x.get('content','') for x in r.get('reviewContentList',[])),'content_attributes':r.get('reviewContentList',[]),'sku_info':r.get('skuInfo'),'like_count':r.get('likeCount'),'media':r.get('mediaList',[]),'seller_reply':r.get('reply'),'page_number':1,'source_url':product['product_url'],'scraped_at':collected})
report.update(status='blocked',error='Lazada reCAPTCHA at detail product 2878087177; stopped without bypass',details_status='partial',updated_at=stamp(),review_count=len(reviews))
report['review_progress']['279648338']={'next_page':2,'status':'partial','count':sum(x['product_id']=='279648338' for x in reviews),'source':'Public review API response captured during initial inspection'}
report['pending_detail_ids']=[p['product_id'] for p in products if p.get('detail_status')!='complete']
report['last_url']=next(p['product_url'] for p in products if p['product_id']=='2878087177')
save('reviews.json',reviews);save('crawl_report.json',report)
print('Saved actual captured reviews:',len(reviews))
