from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
 b=p.chromium.launch(headless=True); page=b.new_page(locale='vi-VN'); page.goto('https://www.lazada.vn/products/i279648338.html',wait_until='domcontentloaded');page.wait_for_timeout(3000)
 print(page.evaluate('typeof window.lib?.mtop?.request'))
 r=page.evaluate('''async()=>{try{return await window.lib.mtop.request({api:'mtop.lazada.review.item.getPcReviewList',v:'1.0',type:'POST',dataType:'json',data:{itemId:279648338,pageSize:100,pageNo:1,ratingFilter:0,sort:0,tagId:0}})}catch(e){return {error:String(e),ret:e.ret}}}''')
 open('lazada-cosmetics/mtop-test.json','w',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2)); print(str(r)[:150].encode('ascii','backslashreplace').decode()); print(len(r.get('data',{}).get('module',{}).get('reviews',[])))
 b.close()
