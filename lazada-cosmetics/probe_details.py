from playwright.sync_api import sync_playwright
import json
from pathlib import Path
with sync_playwright() as p:
 b=p.chromium.launch(headless=True); page=b.new_page(locale='vi-VN')
 page.goto('https://www.lazada.vn/shop/paulas-choice/',wait_until='domcontentloaded'); page.wait_for_timeout(2500)
 print('BADGES',json.dumps(page.locator('img').evaluate_all('(es)=>es.filter(e=>/mall|official|flagship|chính hãng/i.test(e.outerHTML)).map(e=>e.outerHTML)'),ensure_ascii=True))
 page.on('response',lambda r: print('API',r.url[:400]) if any(s in r.url.lower() for s in ['review','ratings']) else None)
 page.goto('https://www.lazada.vn/products/i279648338.html',wait_until='domcontentloaded'); page.wait_for_timeout(2500)
 print('GLOBALS',page.evaluate('Object.keys(window).filter(x=>/data|pdp/i.test(x))'))
 for y in range(0,14000,700):
  page.evaluate('(y)=>scrollTo(0,y)',y); page.wait_for_timeout(250)
 page.wait_for_timeout(2500)
 Path('lazada-cosmetics/deep.html').write_text(page.content(),encoding='utf-8')
 Path('lazada-cosmetics/deep.txt').write_text(page.inner_text('body'),encoding='utf-8')
 print('REVIEW',json.dumps(page.locator('[class*="review"]').evaluate_all('(es)=>es.slice(0,25).map(e=>({tag:e.tagName,c:e.className,text:e.innerText.slice(0,120)}))'),ensure_ascii=True))
 print('DATA',page.evaluate('JSON.stringify(window.__moduleData__ || window.__INIT_DATA__ || {}).slice(0,1000)'))
 b.close()
