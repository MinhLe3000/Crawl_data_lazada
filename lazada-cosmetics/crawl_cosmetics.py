"""Crawl Paula's Choice catalog, product details and public reviews; resumable."""
import argparse
import hashlib
import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'paulas-choice'
SHOP = 'https://www.lazada.vn/shop/paulas-choice/'
BADGE = 'O1CN015YrwXU24LLfbHexea_!!6000000007374-2-tps-299-24.png'

def stamp():
    return datetime.now(ZoneInfo('Asia/Bangkok')).isoformat()

def save(name, value):
    dest = OUT / name
    tmp = dest.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    for n in range(8):
        try:
            tmp.replace(dest)
            return
        except PermissionError:
            time.sleep(.2 * (n+1))
    raise RuntimeError('Cannot replace ' + str(dest))

def load(name, default):
    path = OUT / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def plain(value):
    return '\n'.join(s.strip() for s in html.unescape(re.sub('<[^>]+>', '', re.sub(r'</(?:p|div|li|h[1-6])>|<br\s*/?>', '\n', value or '', flags=re.I))).splitlines() if s.strip())

def goto(page, url):
    response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(1800)
    body = page.locator('body').inner_text().lower()
    if (response and response.status in (403,429)) or any(s in page.title().lower() + body for s in ['captcha', 'access denied', 'slide to verify', 'verify you are human', 'unusual traffic', 'ki?m tra xem b?n c? ph?i l? robot', 't?i kh?ng ph?i l? ng??i m?y']):
        raise RuntimeError('BLOCKED: CAPTCHA/access restriction; stopped without bypass')
    if response and response.status >= 400:
        raise RuntimeError('HTTP ' + str(response.status))

CATALOG_JS = """() => [...document.querySelectorAll('[data-qa-locator="product-item"]')].map(c=>{
const a=c.querySelector('div.RfADt a')||c.querySelector('a[href*="/products/"]');
return {name:a?.innerText?.trim()||a?.title,product_url:a?.href,listing_text:c.innerText};}).filter(x=>x.product_url)"""
MTOP_JS = """async ({id,no}) => {try {return await window.lib.mtop.request({api:'mtop.lazada.review.item.getPcReviewList',v:'1.0',type:'POST',dataType:'json',data:{itemId:Number(id),pageSize:5,pageNo:no,ratingFilter:0,sort:0,tagId:0}})}catch(e){return {error:String(e),ret:e.ret}}}"""

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--details-only',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    products=load('products.json',[])
    reviews=load('reviews.json',[])
    report=load('crawl_report.json',{'started_at':stamp(),'catalog_status':'pending','review_progress':{}})
    def checkpoint():
        report.update(updated_at=stamp(),product_count=len(products),review_count=len(reviews))
        save('products.json',products);save('reviews.json',reviews);save('crawl_report.json',report)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(locale='vi-VN',viewport={'width':1440,'height':1000})
        page=context.new_page()
        try:
            goto(page,SHOP)
            icon=page.locator('img[alt="storeIcon"]')
            icons=icon.evaluate_all('(es)=>es.map(e=>e.src)')
            confirmed=any(BADGE in s for s in icons)
            if not confirmed:
                raise RuntimeError('Storefront badge not recognized; no authenticity labels assigned')
            page.screenshot(path=str(OUT/'storefront.png'))
            (OUT/'storefront.html').write_text(page.content(),encoding='utf-8')
            report['official_shop_evidence']={'is_authentic':True,'source':'storefront_badge','badge_text':'LazMall - Gian hàng chính hãng','badge_asset_urls':icons,'verification':'Known badge asset visually verified in live storefront screenshot','shop_url':SHOP,'observed_at':stamp(),'screenshot':'storefront.png'}
            if report['catalog_status']!='complete':
                seen={p['product_id'] for p in products}
                for number in range(1,501):
                    url=f'https://www.lazada.vn/paulas-choice/?q=All-Products&from=wangpu&langFlag=vi&pageTypeId=2&page={number}'
                    goto(page,url)
                    if '/paulas-choice/' not in page.url:
                        raise RuntimeError('Unexpected catalog redirect: '+page.url)
                    page.locator('[data-qa-locator="product-item"]').first.wait_for(timeout=20000)
                    cards=page.evaluate(CATALOG_JS)
                    added=0
                    for card in cards:
                        m=re.search(r'-i(\d+)',card['product_url'])
                        if not m or m[1] in seen: continue
                        pid=m[1];seen.add(pid);added+=1
                        products.append({'product_id':pid,'name':card['name'],'product_url':card['product_url'].split('?')[0],'shop_name':"Paula's Choice",'shop_url':SHOP,'is_authentic':True,'authenticity_source':'storefront_badge','catalog_page':number,'listing_text':card['listing_text'],'detail_status':'pending'})
                    print(f'Catalog page {number}: {len(cards)} cards, {added} new; total {len(products)}',flush=True)
                    next_btn=page.locator('li.ant-pagination-next')
                    if next_btn.count() and ('disabled' in (next_btn.first.get_attribute('class') or '') or next_btn.first.get_attribute('aria-disabled')=='true'):
                        report['catalog_status']='complete';checkpoint();break
                    checkpoint()
                    if added==0: raise RuntimeError('Repeated/empty catalog page; completion unconfirmed')
                    if not next_btn.count(): raise RuntimeError('Catalog pagination missing; completion unconfirmed')
                else: raise RuntimeError('Catalog page limit reached')
            # Sample requested by the user is processed first, only if present in shop catalog.
            products.sort(key=lambda x:x['product_id']!='279648338')
            for index,product in enumerate(products,1):
                if product.get('detail_status')=='complete':continue
                pid=product['product_id']
                print(f'Detail {index}/{len(products)}: {pid}',flush=True)
                goto(page,product['product_url'])
                page.wait_for_function('window.__moduleData__?.data?.root?.fields?.product',timeout=20000)
                f=page.evaluate('window.__moduleData__.data.root.fields')
                seller=f.get('seller',{})
                key=f.get('primaryKey',{})
                if str(key.get('itemId'))!=pid or str(seller.get('sellerId'))!='100169489':
                    product.update(detail_status='seller_or_item_mismatch',is_authentic=None)
                    checkpoint();continue
                raw=f['product'];sku=f.get('skuInfos',{});selected=sku.get(str(key.get('skuId')),sku.get('0',{}));price=selected.get('price',{})
                product.update(name=raw.get('title'),brand=raw.get('brand',{}).get('name'),seller_id=str(seller.get('sellerId')),shop_id=seller.get('shopId'),description_html=raw.get('desc'),description_text=plain(raw.get('desc')),description_image_urls=re.findall(r'<img[^>]+src=[\"\']([^\"\']+)',raw.get('desc','')),highlights_html=raw.get('highlights'),highlights_text=plain(raw.get('highlights')),specifications=f.get('specifications',{}),variants=f.get('productOption',{}).get('skuBase',{}),sku_details={k:{x:v.get(x) for x in ['skuId','itemId','image','price','quantity']} for k,v in sku.items() if k!='0'},gallery=f.get('skuGalleries'),price_vnd=price.get('salePrice',{}).get('value'),original_price_vnd=price.get('originalPrice',{}).get('value'),coupon_price_vnd=price.get('coupon',{}).get('priceNumber'),rating=raw.get('rating'),review_summary=f.get('review'),categories=f.get('Breadcrumb'),warranties=f.get('warranties'),certificates=f.get('qualification'),detail_status='complete',scraped_at=stamp())
                checkpoint()
            report['details_status']='complete' if all(p.get('detail_status')=='complete' for p in products) else 'partial'
            checkpoint()
            if args.details_only:return
            known={(r['product_id'],r['review_id']) for r in reviews}
            for index,product in enumerate(products,1):
                pid=product['product_id']
                if product.get('detail_status')!='complete':continue
                progress=report['review_progress'].setdefault(pid,{'next_page':1,'status':'pending','count':0})
                if progress['status']=='complete':continue
                goto(page,product['product_url'])
                page.wait_for_function('typeof window.lib?.mtop?.request === "function"',timeout=20000)
                for no in range(progress['next_page'],100001):
                    result=page.evaluate(MTOP_JS,{'id':pid,'no':no})
                    if not any(str(v).startswith('SUCCESS') for v in result.get('ret',[])):
                        progress.update(status='api_error',error=result.get('ret') or result.get('error'));checkpoint()
                        raise RuntimeError('Review API stopped: '+str(progress['error']))
                    module=result.get('data',{}).get('module')
                    if not isinstance(module,dict) or 'reviews' not in module:
                        raise RuntimeError('Unexpected review response schema')
                    rows=module['reviews'];added=0
                    for r in rows:
                        rid=str(r.get('reviewId',''))
                        if not rid:raise RuntimeError('Review without ID')
                        if (pid,rid) in known:continue
                        known.add((pid,rid));added+=1
                        reviews.append({'product_id':pid,'review_id':rid,'buyer_name':r.get('buyerName'),'rating':r.get('rating'),'review_date':r.get('reviewTime'),'content':'\n'.join(x.get('content','') for x in r.get('reviewContentList',[])),'content_attributes':r.get('reviewContentList',[]),'sku_info':r.get('skuInfo'),'like_count':r.get('likeCount'),'media':r.get('mediaList',[]),'seller_reply':r.get('reply'),'page_number':no,'source_url':product['product_url'],'scraped_at':stamp()})
                    progress.update(next_page=no+1,count=sum(r['product_id']==pid for r in reviews),status='running')
                    if not rows:
                        progress['status']='complete'
                    elif added==0:
                        progress['status']='repeated_page_unconfirmed'
                    checkpoint()
                    print(f'Reviews {index}/{len(products)} {pid} page {no}: +{added}, product={progress["count"]}, total={len(reviews)}, {progress["status"]}',flush=True)
                    if progress['status']!='running':break
                    page.wait_for_timeout(500)
            report['status']='complete' if report['catalog_status']=='complete' and report['details_status']=='complete' and all(report['review_progress'].get(p['product_id'],{}).get('status')=='complete' for p in products) else 'partial'
        except Exception as exc:
            body = ''
            try: body = page.locator('body').inner_text().lower()
            except Exception: pass
            captcha = any(x in body for x in ['ki?m tra xem b?n c? ph?i l? robot', 't?i kh?ng ph?i l? ng??i m?y', 'slide to verify', 'verify you are human'])
            report.update(status='blocked' if captcha else 'interrupted',error='CAPTCHA: manual verification required; stopped without bypass' if captcha else str(exc),last_url=page.url)
            report['details_status']='complete' if all(p.get('detail_status')=='complete' for p in products) else 'partial'
            print('STOP:',str(exc),flush=True)
            try: page.screenshot(path=str(OUT/'last_page.png'))
            except Exception:pass
        finally:
            checkpoint();browser.close()
    return 0 if report.get('status')=='complete' else 2

if __name__=='__main__':raise SystemExit(main())
