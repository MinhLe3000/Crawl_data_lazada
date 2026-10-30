"""
Phân tích chi tiết các trường dữ liệu bên trong một product card.
"""
from playwright.sync_api import sync_playwright
import time, json

URL = "https://www.lazada.vn/catalog/?q=gi%C3%A0y+b%C3%B3ng+%C4%91%C3%A1&_keyori=ss&from=input&spm=a2o4n.home.search.go.6fda9d4fy8kLGT"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 900},
        locale="vi-VN",
    )
    page = context.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)

    cards = page.locator("[data-qa-locator='product-item']")
    print(f"Total cards on page: {cards.count()}")

    results = []
    for i in range(min(5, cards.count())):  # Kiểm tra 5 card đầu
        card = cards.nth(i)
        info = {}

        # --- Tên sản phẩm ---
        for sel in ["div.RfADt a", "a[title]", "div[class*='title'] a"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    info["name_sel"] = sel
                    info["name"] = el.inner_text().strip()
                    info["url"] = el.get_attribute("href") or ""
                    break
            except Exception:
                pass

        # --- Giá bán (sale price) ---
        for sel in ["span.aBrP0", "div[class*='price'] span", "span[class*='price']"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    txt = el.inner_text().strip()
                    if txt:
                        info["price_sel"] = sel
                        info["price"] = txt
                        break
            except Exception:
                pass

        # --- Giá gốc (original price, gạch ngang) ---
        for sel in ["del span", "span[class*='origin']", "del", "s span", "div[class*='origin']"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    txt = el.inner_text().strip()
                    if txt:
                        info["orig_price_sel"] = sel
                        info["orig_price"] = txt
                        break
            except Exception:
                pass

        # --- Rating / số sao ---
        for sel in ["span[class*='score']", "i[class*='star']", "div[class*='rating']", 
                    "span.raFAu", "div.mdmmT span"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    txt = el.inner_text().strip()
                    if txt:
                        info["rating_sel"] = sel
                        info["rating"] = txt
                        break
            except Exception:
                pass

        # --- Số lượt đánh giá ---
        for sel in ["span.qzqFw", "div[class*='review']", "._1y_90"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    txt = el.inner_text().strip()
                    if txt:
                        info["review_count_sel"] = sel
                        info["review_count"] = txt
                        break
            except Exception:
                pass

        # --- URL ảnh ---
        for sel in ["img[type='product']", "img.jF4aX", "div[class*='img'] img", "img[src*='lazada']", "img"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                    if src:
                        info["img_sel"] = sel
                        info["img_url"] = src
                        break
            except Exception:
                pass

        # --- Tên người bán ---
        for sel in ["span[class*='seller']", "div[class*='seller']", "a[class*='seller']",
                    "._6uN7R span", "span.c3gUW0"]:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    txt = el.inner_text().strip()
                    if txt:
                        info["seller_sel"] = sel
                        info["seller"] = txt
                        break
            except Exception:
                pass

        # Dump toàn bộ text của card để tham khảo
        try:
            info["card_text"] = card.inner_text().strip()[:300]
        except Exception:
            pass

        # Dump inner HTML tóm tắt của card đầu tiên
        if i == 0:
            try:
                html_snippet = card.inner_html()
                with open(f"card_{i}_html.txt", "w", encoding="utf-8") as f:
                    f.write(html_snippet)
                print(f"[OK] Saved card_{i}_html.txt")
            except Exception as e:
                print(f"[WARN] Cannot save card html: {e}")

        results.append(info)
        print(f"\n--- Card {i} ---")
        for k, v in info.items():
            print(f"  {k:20s}: {str(v)[:120]}")

    browser.close()

print("\nField inspection done.")
