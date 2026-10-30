# Viettien Online

Shop: https://www.lazada.vn/shop/viettien-online/

Run from this folder: `powershell -ExecutionPolicy Bypass -File ./run.ps1`

Slower: `./run.ps1 -PageWait 20 -ReviewWait 10`. Show browser: add `-Headed`.
Default: wait 12 seconds after page navigation, 6 seconds between review requests. Only one browser page is used. These waits cannot guarantee absence of CAPTCHA. Stop on CAPTCHA/403/429; no bypass or automatic retry of a challenge.

Outputs: `data/products.json` (products, descriptions, highlights, specifications, variants, images) and `data/reviews.json` (reviews linked by string `product_id`, ratings, dates, media, seller replies). Run again to resume. Check `data/crawl_report.json` for completeness and errors. Empty files mean no records collected, not an empty shop.

Dataset label: `official`, supplied by the user. For official shop, `is_authentic=true` requires the known official LazMall store badge asset, previously visually verified. Unrecognized badge means null, not false. For fake dataset, `is_authentic=false` represents the user-provided label, with `authenticity_source=user_provided_label` and `counterfeit_independently_verified=false`. Absence of LazMall is not proof of counterfeiting. Product seller URL must match this shop before details are accepted.

Only variants loaded by the product page have SKU details; available option definitions are preserved. Image-only descriptions keep HTML and image URLs. Review totals advertised by Lazada may differ from the reviews publicly returned. Complete requires confirmed catalog end, all details and confirmed review pagination end.

## Recover reviews for the existing product list

Run `./run_reviews.ps1`. To process all three clothing shops, run `../lazada-football-boots/.venv/Scripts/python.exe -u ../crawl_clothing_reviews.py` from this folder. A single visible persistent browser is used; manually solve Lazada verification in that window when requested. Do not close the window while the crawler is waiting. The workflow prioritizes products known to have reviews, retrieves details then all review pages for each product, saves checkpoints and preserves existing data. Explicit zero-review totals are recorded per product, with the observation date, rather than leaving an ambiguous empty reviews file. Default waits: 15 seconds after navigation, 8 seconds between review pages. Progress is in data/crawl_report.json and ../clothing_reviews.log.
