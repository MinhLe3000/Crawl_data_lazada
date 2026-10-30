from playwright.sync_api import sync_playwright
import json
from pathlib import Path
with sync_playwright() as p:
 b=p.chromium.launch(headless=True); page=b.new_page(locale='vi-VN')
 page.goto('https://www.lazada.vn/shop/paulas-choice/',wait_until='domcontentloaded'); page.wait_for_timeout(3000)
 Path('lazada-cosmetics/shop-elements.json').write_text(json.dumps(page.locator('[class*="header"], [class*="Header"]').evaluate_all('(es)=>es.filter(e=>e.innerText.includes("413700")).map(e=>e.outerHTML)'),ensure_ascii=False),encoding='utf-8')
 def capture(r):
  if 'getpcreviewlist' in r.url.lower():
   try: Path('lazada-cosmetics/review-response.json').write_text(json.dumps({'url':r.url,'request':r.request.post_data,'data':r.json()},ensure_ascii=False,indent=2),encoding='utf-8')
   except Exception as e: print(e)
 page.on('response',capture)
 page.goto('https://www.lazada.vn/products/i279648338.html',wait_until='domcontentloaded'); page.wait_for_timeout(2000)
 Path('lazada-cosmetics/module.json').write_text(json.dumps(page.evaluate('window.__moduleData__'),ensure_ascii=False,indent=2),encoding='utf-8')
 for y in range(0,9000,700):
  page.evaluate('(y)=>scrollTo(0,y)',y); page.wait_for_timeout(300)
 page.wait_for_timeout(2000); b.close()
