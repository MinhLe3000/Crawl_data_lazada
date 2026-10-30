from playwright.sync_api import sync_playwright
from pathlib import Path
with sync_playwright() as p:
 b=p.chromium.launch(headless=True); page=b.new_page(locale='vi-VN')
 for name,url in [('catalog','https://www.lazada.vn/paulas-choice/?q=All-Products&from=wangpu&langFlag=vi&pageTypeId=2&page=1'),('product','https://www.lazada.vn/products/i279648338.html')]:
  page.goto(url,wait_until='domcontentloaded',timeout=60000); page.wait_for_timeout(4000)
  Path('lazada-cosmetics/'+name+'.html').write_text(page.content(),encoding='utf-8')
  Path('lazada-cosmetics/'+name+'.txt').write_text(page.inner_text('body'),encoding='utf-8')
  print(name,page.title().encode('ascii','backslashreplace').decode(),len(page.content()))
 b.close()
