from playwright.sync_api import sync_playwright
from pathlib import Path
import json
out=Path('hàng chính hãng');out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 page=b.new_page(locale='vi-VN',viewport={'width':1440,'height':900})
 for slug in ['nike-flagship-store']:
  try:
   response=page.goto('https://www.lazada.vn/'+slug+'/?q=All-Products&from=wangpu&langFlag=vi&pageTypeId=2',wait_until='domcontentloaded',timeout=60000)
   page.wait_for_timeout(6000)
   (out/(slug+'_catalog.html')).write_text(page.content(),encoding='utf-8')
   print(json.dumps({'shop':slug,'status':response.status if response else None,'url':page.url,'title':page.title(),'body':page.inner_text('body')[:1800],'cards':page.locator('[data-qa-locator="product-item"]').count(),'links':page.locator('a[href*="/products/"]').count()},ensure_ascii=True),flush=True)
  except Exception as e: print(slug,str(e),flush=True)
 b.close()


