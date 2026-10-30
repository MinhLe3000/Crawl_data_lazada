"""
Script kiểm tra DOM thực tế của Lazada để xác định selector chính xác.
Chạy headful (có UI) để quan sát, lưu HTML ra file để phân tích.
"""
from playwright.sync_api import sync_playwright
import time

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

    # Chờ nội dung load
    time.sleep(5)

    # Kiểm tra xem có CAPTCHA / block không
    title = page.title()
    print(f"[PAGE TITLE] {title}")

    body_text = page.inner_text("body")[:500]
    print(f"[BODY SNIPPET] {body_text}")

    # Lưu toàn bộ HTML để phân tích
    html = page.content()
    with open("lazada_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] Saved lazada_page.html")

    # Thử một số selector phổ biến và đếm số phần tử tìm thấy
    selectors_to_try = [
        # Product card containers
        "[data-qa-locator='product-item']",
        "div[data-tracking='product-card']",
        ".Bm3ON",          # class thường thấy trên Lazada VN
        "._95X4G",
        "div.buTCk",
        "div[class*='product']",
        # Product name
        "div.RfADt a",
        "._6uN7R",
        "a[title]",
        # Price
        "span.aBrP0",
        "div[class*='price']",
        # Rating
        "span[class*='score']",
        "div[class*='rating']",
    ]

    print("\n[SELECTOR PROBE]")
    for sel in selectors_to_try:
        try:
            count = page.locator(sel).count()
            if count > 0:
                print(f"  FOUND {count:3d}  |  {sel}")
                # Lấy thêm text mẫu nếu là product item
                if count >= 3:
                    try:
                        sample = page.locator(sel).first.inner_text()[:120].replace("\n", " ")
                        print(f"           sample: {sample}")
                    except Exception:
                        pass
        except Exception as e:
            print(f"  ERROR        |  {sel}  -> {e}")

    # Lấy các thẻ <a> bên trong product listing để xem URL pattern
    print("\n[SAMPLE PRODUCT LINKS]")
    try:
        links = page.locator("//div[contains(@class,'Bm3ON')]//a").all()[:5]
        for lnk in links:
            href = lnk.get_attribute("href")
            txt = lnk.inner_text()[:80]
            print(f"  {txt!r:80}  {href}")
    except Exception as e:
        print(f"  {e}")

    # Chụp screenshot
    page.screenshot(path="lazada_screenshot.png", full_page=False)
    print("\n[OK] Saved lazada_screenshot.png")

    browser.close()
print("\nDOM inspection done.")
