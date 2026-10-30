"""Recover clothing reviews and details; one browser, resumable per product."""
import argparse
import importlib.util
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
NAMES=['lazada-clothing-fake','lazada-clothing-official','lazada-clothing-authorized']

def now():return datetime.now(ZoneInfo('Asia/Bangkok')).isoformat()

def write(path,value):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    for attempt in range(8):
        try:tmp.replace(path);return
        except PermissionError:time.sleep(.25*(attempt+1))
    raise RuntimeError('Cannot save '+str(path))

def log(message):
    print(now(),message,flush=True)
    with (ROOT/'clothing_reviews.log').open('a',encoding='utf-8') as f:f.write(now()+' '+message+'\n')

def challenge(page,response=None):
    if page.is_closed():return False
    if response and response.status in (403,429):return True
    if '/punish' in page.url or '_____tmd_____' in page.url:return True
    try:
        text=(page.title()+' '+page.locator('body').inner_text(timeout=4000)).lower()
        return any(s in text for s in ['slide to verify','verify you are human','access denied','unusual traffic','ki\u1ec3m tra xem b\u1ea1n c\u00f3 ph\u1ea3i l\u00e0 robot']) or page.locator('iframe[src*="recaptcha"], iframe[src*="captcha"]').count()>0
    except Exception:return False

def modules():
    result=[]
    for name in NAMES:
        folder=ROOT/name;data=folder/'data'
        spec=importlib.util.spec_from_file_location(name.replace('-','_'),folder/'crawl_shop.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        result.append({'name':name,'folder':folder,'data':data,'m':m,'config':m.CONFIG,
          'products':json.loads((data/'products.json').read_text(encoding='utf-8')),
          'reviews':json.loads((data/'reviews.json').read_text(encoding='utf-8')),
          'report':json.loads((data/'crawl_report.json').read_text(encoding='utf-8'))})
    return result

def checkpoint(shop):
    r=shop['report'];products=shop['products'];reviews=shop['reviews']
    r.update(updated_at=now(),product_count=len(products),review_count=len(reviews),
      details_status='complete' if all(p.get('detail_status')=='complete' for p in products) else 'partial')
    r['reviews_status']='complete' if all(r.get('review_progress',{}).get(p['product_id'],{}).get('status')=='complete' for p in products) else 'partial'
    if r.get('status') not in ['blocked','waiting_for_verification','running','interrupted']:
        r['status']='complete' if r.get('catalog_status')=='complete' and r['details_status']=='complete' and r['reviews_status']=='complete' else 'partial'
    for file,value in [('products.json',products),('reviews.json',reviews),('crawl_report.json',r)]:write(shop['data']/file,value)


def collect_details(shop,product,f):
    import re
    pid=product['product_id'];seller=f.get('seller',{});key=f.get('primaryKey',{})
    if str(key.get('itemId'))!=pid or urlsplit(seller.get('url','')).path.rstrip('/')!='/shop/'+shop['config']['slug']:
        product['detail_status']='seller_or_item_mismatch'
        raise RuntimeError('Product/seller mismatch for '+pid)
    raw=f['product'];sku=f.get('skuInfos',{});selected=sku.get(str(key.get('skuId')),sku.get('0',{}));price=selected.get('price',{})
    product.update(name=raw.get('title'),brand=raw.get('brand',{}).get('name'),seller_id=str(seller.get('sellerId')),shop_id=seller.get('shopId'),description_html=raw.get('desc'),description_text=shop['m'].plain(raw.get('desc')),description_image_urls=re.findall(r'<img[^>]+src=[\"\']([^\"\']+)',raw.get('desc','')),highlights_html=raw.get('highlights'),highlights_text=shop['m'].plain(raw.get('highlights')),specifications=f.get('specifications',{}),variants=f.get('productOption',{}).get('skuBase',{}),sku_details={k:{x:v.get(x) for x in ['skuId','itemId','image','price','quantity']} for k,v in sku.items() if k!='0'},gallery=f.get('skuGalleries'),price_vnd=price.get('salePrice',{}).get('value'),original_price_vnd=price.get('originalPrice',{}).get('value'),coupon_price_vnd=price.get('coupon',{}).get('priceNumber'),rating=raw.get('rating'),review_summary=f.get('review'),categories=f.get('Breadcrumb'),warranties=f.get('warranties'),certificates=f.get('qualification'),detail_status='complete',scraped_at=now())


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--page-wait',type=float,default=15)
    ap.add_argument('--review-wait',type=float,default=8)
    ap.add_argument('--manual-timeout',type=int,default=600)
    ap.add_argument('--headless',action='store_true')
    ap.add_argument('--shop',choices=NAMES)
    args=ap.parse_args()
    if args.page_wait<0 or args.review_wait<0 or args.manual_timeout<0:ap.error('Wait times must be non-negative')
    shops=modules()
    if args.shop:shops=[s for s in shops if s['name']==args.shop]
    tasks=[]
    for shop in shops:
        r=shop['report'];r.update(status='running',recovery_started_at=now(),recovery_mode='reviews_per_product',pacing={'page_wait_seconds':args.page_wait,'review_wait_seconds':args.review_wait})
        r.pop('error',None)
        progress=r.setdefault('review_progress',{})
        for product in shop['products']:
            pid=product['product_id'];pr=progress.setdefault(pid,{'next_page':1,'count':sum(x['product_id']==pid for x in shop['reviews']),'status':'pending'})
            # Cached product detail explicitly reported zero; preserve its observation date.
            summary=product.get('review_summary',{}) or {}
            if product.get('detail_status')=='complete' and summary.get('reviews')==0 and pr['count']==0:
                pr.update(status='complete',count=0,expected_count=0,completion_reason='product_detail_explicit_zero_reviews',source_observed_at=product.get('scraped_at'))
            if pr['status']!='complete':tasks.append((0 if summary.get('reviews',0)>0 else 1,shop,product))
        checkpoint(shop)
        log(shop['name']+': '+str(sum(v['status']=='complete' for v in progress.values()))+' products have confirmed review status')
    tasks.sort(key=lambda t:t[0])
    with sync_playwright() as pw:
        context=pw.chromium.launch_persistent_context(str(ROOT/'.clothing-review-browser'),headless=args.headless,locale='vi-VN',viewport={'width':1440,'height':1000})
        page=context.pages[0] if context.pages else context.new_page()
        def verify(shop,product,response=None):
            if not challenge(page,response):return
            r=shop['report'];r.update(status='waiting_for_verification',error='Lazada CAPTCHA; solve manually in visible browser',blocked_product_id=product['product_id'])
            page.screenshot(path=str(shop['data']/'review_challenge.png'));checkpoint(shop)
            log('MANUAL VERIFICATION REQUIRED: '+shop['name']+' product '+product['product_id'])
            if args.headless:raise RuntimeError('CAPTCHA: manual verification required')
            deadline=time.monotonic()+args.manual_timeout
            while time.monotonic()<deadline:
                page.wait_for_timeout(2000)
                if not challenge(page):
                    page.wait_for_timeout(args.page_wait*1000)
                    r.update(status='running');r.pop('error',None);checkpoint(shop);return
            raise RuntimeError('CAPTCHA: manual verification timeout; no bypass attempted')
        try:
            for index,(_,shop,product) in enumerate(tasks,1):
                pid=product['product_id'];r=shop['report'];progress=r['review_progress'][pid]
                log(f'{index}/{len(tasks)} {shop["name"]} product {pid}')
                try:
                    response=page.goto(product['product_url'],wait_until='domcontentloaded',timeout=60000)
                    page.wait_for_timeout(args.page_wait*1000);verify(shop,product,response)
                    try:page.wait_for_function('window.__moduleData__?.data?.root?.fields?.product',timeout=30000)
                    except Exception:verify(shop,product);page.wait_for_function('window.__moduleData__?.data?.root?.fields?.product',timeout=15000)
                    collect_details(shop,product,page.evaluate('window.__moduleData__.data.root.fields'))
                    progress['expected_count']=(product.get('review_summary') or {}).get('reviews')
                    if progress['expected_count']==0 and progress['count']==0:
                        progress.update(status='complete',completion_reason='product_detail_explicit_zero_reviews',source_observed_at=now());checkpoint(shop);continue
                    page.wait_for_function('typeof window.lib?.mtop?.request === "function"',timeout=20000)
                    known={(x['product_id'],x['review_id']) for x in shop['reviews']}
                    for no in range(progress.get('next_page',1),100001):
                        verify(shop,product)
                        result=page.evaluate(shop['m'].MTOP_JS,{'id':pid,'no':no})
                        if not any(str(v).startswith('SUCCESS') for v in result.get('ret',[])):
                            progress.update(status='api_error',error=result.get('ret') or result.get('error'));checkpoint(shop)
                            raise RuntimeError('Review API denied request: '+str(progress['error']))
                        module=result.get('data',{}).get('module')
                        if not isinstance(module,dict) or not isinstance(module.get('reviews'),list):raise RuntimeError('Unexpected review response schema')
                        rows=module['reviews'];added=0
                        for row in rows:
                            rid=str(row.get('reviewId',''))
                            if not rid:raise RuntimeError('Review missing ID')
                            if (pid,rid) in known:continue
                            known.add((pid,rid));added+=1
                            shop['reviews'].append({'product_id':pid,'review_id':rid,'buyer_name':row.get('buyerName'),'rating':row.get('rating'),'review_date':row.get('reviewTime'),'content':'\n'.join(x.get('content','') for x in row.get('reviewContentList',[])),'content_attributes':row.get('reviewContentList',[]),'sku_info':row.get('skuInfo'),'like_count':row.get('likeCount'),'media':row.get('mediaList',[]),'seller_reply':row.get('reply'),'page_number':no,'source_url':product['product_url'],'scraped_at':now()})
                        progress.update(count=sum(x['product_id']==pid for x in shop['reviews']),next_page=no+1,status='running',updated_at=now())
                        if not rows:progress.update(status='complete',completion_reason='public_api_empty_page')
                        elif added==0:progress.update(status='repeated_page_unconfirmed',next_page=no)
                        checkpoint(shop);log(f'{shop["name"]} {pid} reviews page {no}: +{added}, total {progress["count"]}, {progress["status"]}')
                        if progress['status']!='running':break
                        page.wait_for_timeout(args.review_wait*1000)
                    checkpoint(shop)
                except Exception as exc:
                    blocked=challenge(page) or 'CAPTCHA' in str(exc) or 'denied request' in str(exc)
                    r.update(status='blocked' if blocked else 'interrupted',error=str(exc),blocked_product_id=pid)
                    if progress['status'] not in ['complete','api_error']:progress.update(status='blocked' if blocked else 'error',error=str(exc))
                    checkpoint(shop);log('STOP: '+str(exc))
                    return 2
            for shop in shops:
                shop['report']['status']='partial';checkpoint(shop)
        finally:
            for shop in shops:
                if shop['report'].get('status')=='running':
                    shop['report']['status']='partial'
                    checkpoint(shop)
            try:context.close()
            except Exception:pass
    return 0 if all(s['report'].get('status')=='complete' for s in shops) else 2

if __name__=='__main__':raise SystemExit(main())
