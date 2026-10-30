"""Crawl only the five configured Lazada storefront catalogs; never bypass CAPTCHA."""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger("official-shops")
FIELDS = ["shop_name", "shop_slug", "shop_url", "official_source", "badge_observed",
          "product_id", "name", "price", "price_vnd", "original_price",
          "discount_percent", "product_url", "image_url", "rating_approx",
          "review_count", "sold_info", "location", "page_number", "source_url",
          "scraped_at", "is_football_boot_candidate"]

EXTRACT = r"""() => [...document.querySelectorAll('[data-qa-locator="product-item"]')].map(c => {
 const text = s => c.querySelector(s)?.innerText?.trim() || null;
 const a = c.querySelector('div.RfADt a') || c.querySelector('a[href*="/products/"]');
 const img = c.querySelector('img[type="product"]') || c.querySelector('img');
 const images = img ? [img.currentSrc, img.getAttribute('src'), img.getAttribute('data-src'), img.getAttribute('data-lazy-src')] : [];
 const image = images.find(s => s && /^(https?:)?\/\//.test(s)) || '';
 const full = c.querySelectorAll('i._9-ogB.Dy1nx').length;
 const half = c.querySelectorAll('i._9-ogB.i6t3-').length;
 return {name: a?.innerText?.trim() || a?.title || '', product_url: a?.href || '',
 price: text('div.aBrP0 span'), original_price: text('del') || text('s'),
 discount_text: text('div.WNoq3'), image_url: image,
 rating_approx: c.querySelectorAll('i._9-ogB').length ? full + half * .5 : null,
 review_text: text('span.qzqFw'), sold_info: text('span._1cEkb span'), location: text('span.oa6ri')};
})"""


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    replace_file(temp, path)


def replace_file(temp, target):
    # Windows indexers/antivirus can hold a destination briefly after a write.
    for attempt in range(8):
        try:
            temp.replace(target)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.25 * (attempt + 1))


def save_records(folder, records, stem="products"):
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / f"{stem}.json", records)
    temp = folder / f"{stem}.csv.tmp"
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    replace_file(temp, folder / f"{stem}.csv")


def money(text):
    if not text or not re.search(r"[₫đ]|VND", text, re.I):
        return None
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def review_count(text):
    if not text:
        return None
    m = re.search(r"([\d.,]+)\s*([kKmM]?)", text)
    if not m:
        return None
    n, suffix = m.groups()
    if suffix:
        return round(float(n.replace(",", ".")) * (1000 if suffix.lower() == "k" else 1000000))
    return int(re.sub(r"\D", "", n))


def football_candidate(name):
    return bool(re.search(r"giày.*(?:bóng đá|đá bóng|đá banh)|(?:soccer|football).*(?:shoes|boots)|(?:shoes|boots).*soccer", name, re.I))


def catalog_url(slug, number):
    # /shop/slug/ is decoration; /slug/ is the actual paginated catalog.
    return f"https://www.lazada.vn/{slug}/?" + urlencode({
        "q": "All-Products", "from": "wangpu", "langFlag": "vi", "pageTypeId": 2, "page": number})


def blocked(page, response):
    if response and response.status in (403, 429):
        return True
    title = page.title().lower()
    if any(s in title for s in ("captcha", "access denied", "verification", "security check")):
        return True
    body = page.locator("body").inner_text(timeout=10000)[:2500].lower()
    return any(s in body for s in ("slide to verify", "unusual traffic", "verify you are human", "access denied", "xác minh bạn"))


def collect_shop(context, shop, run_dir, max_pages):
    folder = run_dir / shop["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    page = context.new_page()
    page.set_default_timeout(12000)
    records, seen = [], set()
    # A confirmed storefront badge applies to all products in that shop.
    # Confirmation comes from shops.json, not a whole-page text heuristic.
    confirmed = shop.get("official_shop_confirmed") is True
    report = {"shop": shop, "status": "running", "pages": [], "badge_observed": confirmed,
              "official_source": "user_confirmed_shop_badge" if confirmed else "unconfirmed",
              "scope": "all shop products"}
    try:
        response = page.goto(shop["url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        if blocked(page, response):
            raise RuntimeError("CAPTCHA/block on storefront; stopped without bypass")
        report["store_title"] = page.title()
        (folder / "storefront.html").write_text(page.content(), encoding="utf-8")
        for number in range(1, max_pages + 1):
            url = catalog_url(shop["slug"], number)
            LOG.info("%s page %d", shop["slug"], number)
            for attempt in range(2):
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    break
                except PWTimeout:
                    if attempt == 1:
                        raise
                    page.wait_for_timeout(2500)
            page.wait_for_timeout(2000)
            if blocked(page, response):
                report["status"] = "blocked"
                break
            if response and response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}")
            if urlsplit(page.url).path.rstrip('/') != '/' + shop['slug']:
                raise RuntimeError(f"Unexpected redirect outside shop catalog: {page.url}")
            try:
                page.locator('[data-qa-locator="product-item"]').first.wait_for(timeout=20000)
            except PWTimeout:
                body = page.locator('body').inner_text().lower()
                report["status"] = "complete" if any(s in body for s in ["không tìm thấy", "no products", "no results"]) else "no_cards_unconfirmed"
                break
            # Trigger lazy images throughout the listing before extracting cards.
            for y in range(0, min(page.locator('body').evaluate('(e) => e.scrollHeight'), 24000), 650):
                page.evaluate('(y) => window.scrollTo(0,y)', y)
                page.wait_for_timeout(180)
            raw = page.evaluate(EXTRACT)
            stamp = datetime.now(ZoneInfo('Asia/Bangkok')).isoformat()
            added = 0
            for item in raw:
                match = re.search(r'-i(\d+)', item['product_url'])
                if not item['name'] or not match or match.group(1) in seen:
                    continue
                seen.add(match.group(1))
                parts = urlsplit(item['product_url'])
                item['product_url'] = urlunsplit(('https', parts.netloc, parts.path, '', ''))
                item['product_id'] = match.group(1)
                item['price_vnd'] = money(item['price'])
                if money(item['original_price']) is None:
                    item['original_price'] = None
                discount = re.search(r'(\d+)\s*%', item.pop('discount_text') or '')
                item['discount_percent'] = int(discount.group(1)) if discount else None
                item['review_count'] = review_count(item.pop('review_text'))
                if item['image_url'].startswith('//'):
                    item['image_url'] = 'https:' + item['image_url']
                item.update(shop_name=shop['name'], shop_slug=shop['slug'], shop_url=shop['url'],
                            official_source=report['official_source'], badge_observed=report['badge_observed'],
                            page_number=number, source_url=page.url, scraped_at=stamp,
                            is_football_boot_candidate=football_candidate(item['name']))
                records.append(item)
                added += 1
            report['pages'].append({'number': number, 'cards': len(raw), 'new_products': added, 'url': page.url})
            save_records(folder, records)
            write_json(folder / 'report.json', report)
            if number == 1:
                (folder / 'catalog_first.html').write_text(page.content(), encoding='utf-8')
            if added == 0:
                report['status'] = 'repeated_page_unconfirmed'
                break
            next_button = page.locator('li.ant-pagination-next')
            if next_button.count() and ('disabled' in (next_button.first.get_attribute('class') or '') or next_button.first.get_attribute('aria-disabled') == 'true'):
                report['status'] = 'complete'
                break
            if not next_button.count():
                report['status'] = 'pagination_unconfirmed'
                break
            page.wait_for_timeout(1500)
        else:
            report['status'] = 'page_limit_reached'
    except Exception as exc:
        report['status'] = 'error'
        report['error'] = str(exc)
        LOG.exception('%s failed', shop['slug'])
    finally:
        try:
            (folder / 'last_page.html').write_text(page.content(), encoding='utf-8')
            page.screenshot(path=str(folder / 'last_page.png'))
        except Exception:
            pass
        page.close()
        report['product_count'] = len(records)
        save_records(folder, records)
        write_json(folder / 'report.json', report)
    return records, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-pages', type=int, default=200)
    parser.add_argument('--shop', help='Run one configured shop slug')
    args = parser.parse_args()
    if args.max_pages < 1:
        parser.error('--max-pages must be positive')
    shops = json.loads((ROOT / 'shops.json').read_text(encoding='utf-8'))
    if args.shop:
        shops = [s for s in shops if s['slug'] == args.shop]
        if not shops:
            parser.error('Unknown shop slug')
    run_dir = ROOT / 'data' / datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y%m%d_%H%M%S_%f')
    run_dir.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(run_dir / 'crawl.log', encoding='utf-8')])
    all_records, reports = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(locale='vi-VN', viewport={'width': 1440, 'height': 900})
        try:
            for shop in shops:
                records, report = collect_shop(context, shop, run_dir, args.max_pages)
                all_records.extend(records)
                reports.append(report)
                save_records(run_dir, all_records, 'all_products')
                save_records(run_dir, [r for r in all_records if r['is_football_boot_candidate']], 'football_boot_candidates')
                write_json(run_dir / 'summary.json', reports)
                LOG.info('%s: %d products; %s', shop['slug'], len(records), report['status'])
        finally:
            browser.close()
    LOG.info('Output: %s', run_dir)
    return 0 if all(r['status'] == 'complete' for r in reports) else 2


if __name__ == '__main__':
    raise SystemExit(main())
