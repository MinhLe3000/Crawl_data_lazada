# VIET TIEN STORE - Authorized dealer

Shop: https://www.lazada.vn/shop/viet-tien-store?path=index.htm&lang=vi&pageTypeId=1

The storefront screenshot was visually checked: LazMall - authorized dealer. The storeIcon asset is recorded in shop.json. Products from this catalog receive is_authentic=true and is_authorized_dealer=true only when this badge is found. Each product detail must link back to the matching seller shop URL. This shop is separate from viettien-online.

Run from PowerShell: ./run.ps1
Slower: ./run.ps1 -PageWait 20 -ReviewWait 10
Default: 12 seconds after loading each page; 6 seconds between review pages. Stop on CAPTCHA/403/429/API restrictions, without bypass. Re-run to resume checkpoint.

Outputs: data/products.json (product details, highlights, description HTML/text/images, specifications, variants, galleries, prices, rating summary) and data/reviews.json (reviews linked by string product_id, rating, date, SKU, images/videos, seller reply). data/crawl_report.json records actual counts, evidence, progress and errors. Complete requires confirmed catalog end, every product detail and review pagination end. Empty or partial files do not indicate completion. Image-only descriptions preserve image URLs and HTML; SKU details include only variants loaded by the page.

## Recover reviews for the existing product list

Run `./run_reviews.ps1`. To process all three clothing shops, run `../lazada-football-boots/.venv/Scripts/python.exe -u ../crawl_clothing_reviews.py` from this folder. A single visible persistent browser is used; manually solve Lazada verification in that window when requested. Do not close the window while the crawler is waiting. The workflow prioritizes products known to have reviews, retrieves details then all review pages for each product, saves checkpoints and preserves existing data. Explicit zero-review totals are recorded per product, with the observation date, rather than leaving an ambiguous empty reviews file. Default waits: 15 seconds after navigation, 8 seconds between review pages. Progress is in data/crawl_report.json and ../clothing_reviews.log.
