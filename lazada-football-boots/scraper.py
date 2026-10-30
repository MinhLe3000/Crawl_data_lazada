"""
Lazada Vietnam - Football Boots Scraper
Từ khóa: "giày bóng đá"
Thu thập: tên, giá bán, giá gốc, URL sản phẩm, URL ảnh,
          đánh giá (số sao), số lượt đánh giá, tên người bán / địa điểm
Output: lazada_football_boots.csv  &  lazada_football_boots.json
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlunparse, urlparse

import pandas as pd
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

# ──────────────────────────────────────────────
# Cấu hình
# ──────────────────────────────────────────────
KEYWORD        = "giày bóng đá"
BASE_URL       = (
    "https://www.lazada.vn/catalog/"
    "?q=gi%C3%A0y+b%C3%B3ng+%C4%91%C3%A1"
    "&_keyori=ss&from=input"
    "&spm=a2o4n.home.search.go.6fda9d4fy8kLGT"
)
MAX_PAGES      = 5          # Số trang tối đa cần thu thập (40 sp/trang)
PAGE_WAIT_SEC  = 4          # Thời gian chờ sau khi load trang
OUTPUT_CSV     = Path("lazada_football_boots.csv")
OUTPUT_JSON    = Path("lazada_football_boots.json")
HEADLESS       = True

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lazada-scraper")


# ──────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────
@dataclass
class Product:
    name: str
    price: Optional[str]        = None   # giá bán (đã định dạng)
    original_price: Optional[str] = None # giá gốc (nếu có giảm)
    product_url: str             = ""
    image_url: str               = ""
    rating: Optional[float]      = None  # số sao (0-5)
    review_count: Optional[int]  = None  # lượt đánh giá
    sold_info: Optional[str]     = None  # "4.3K Đã bán"
    location: Optional[str]      = None  # Thành phố Hồ Chí Minh
    page_number: int             = 0


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def normalize_url(href: str) -> str:
    """Đảm bảo URL có scheme https."""
    if not href:
        return ""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.lazada.vn" + href
    return href


def parse_review_count(text: str) -> Optional[int]:
    """'(976)' → 976"""
    m = re.search(r"\d[\d,.]*", text.replace(".", "").replace(",", ""))
    return int(m.group()) if m else None


def parse_price(text: str) -> Optional[str]:
    """Làm sạch giá, giữ nguyên định dạng tiền tệ VNĐ."""
    if not text:
        return None
    text = text.strip()
    return text if text else None


def page_url(page_num: int) -> str:
    """Tạo URL cho trang thứ N (1-indexed)."""
    if page_num == 1:
        return BASE_URL
    return BASE_URL + f"&page={page_num}"


# ──────────────────────────────────────────────
# Scrape một trang
# ──────────────────────────────────────────────
def scrape_page(page: Page, page_num: int) -> tuple[list[Product], bool]:
    """
    Trả về (danh sách sản phẩm, có_bị_block).
    """
    url = page_url(page_num)
    log.info("Đang tải trang %d → %s", page_num, url)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    except PWTimeout:
        log.error("Timeout khi tải trang %d", page_num)
        return [], False

    time.sleep(PAGE_WAIT_SEC)

    # Kiểm tra CAPTCHA / block
    title = page.title().lower()
    body  = page.inner_text("body")[:800].lower()

    block_signals = ["captcha", "robot", "verify", "403", "access denied",
                     "too many requests", "blocked"]
    if any(sig in title or sig in body for sig in block_signals):
        log.warning("PHÁT HIỆN CHẶN / CAPTCHA tại trang %d – dừng thu thập.", page_num)
        return [], True   # bị block

    # Kiểm tra có sản phẩm không
    cards = page.locator("[data-qa-locator='product-item']")
    count = cards.count()
    if count == 0:
        log.warning("Không tìm thấy sản phẩm ở trang %d – có thể hết trang.", page_num)
        return [], False

    log.info("Trang %d: tìm thấy %d sản phẩm", page_num, count)
    products: list[Product] = []

    for i in range(count):
        card = cards.nth(i)
        try:
            prod = extract_product(card, page_num)
            if prod:
                products.append(prod)
        except Exception as exc:
            log.debug("Lỗi khi đọc card %d trang %d: %s", i, page_num, exc)

    return products, False


def extract_product(card, page_num: int) -> Optional[Product]:
    """Trích xuất một sản phẩm từ card element."""
    # ── Tên & URL sản phẩm ──
    name_el = card.locator("div.RfADt a").first
    if name_el.count() == 0:
        return None
    name = name_el.inner_text().strip()
    if not name:
        return None
    raw_href = name_el.get_attribute("href") or ""
    product_url = normalize_url(raw_href)

    # ── Giá bán ──
    price = None
    price_el = card.locator("div.aBrP0 span").first
    if price_el.count() > 0:
        price = parse_price(price_el.inner_text())

    # ── Giá gốc (gạch ngang – chỉ xuất hiện khi có giảm giá) ──
    original_price = None
    orig_el = card.locator("div.WNoq3").first
    if orig_el.count() > 0:
        orig_text = orig_el.inner_text().strip()
        if orig_text:
            original_price = parse_price(orig_text)

    # ── Số sao (đếm sao đầy) ──
    rating = None
    try:
        full_stars  = card.locator("i._9-ogB.Dy1nx").count()   # sao đầy
        half_stars  = card.locator("i._9-ogB.i6t3-").count()   # sao nửa
        total_stars = card.locator("i._9-ogB").count()
        if total_stars > 0:
            rating = round(full_stars + half_stars * 0.5, 1)
    except Exception:
        pass

    # ── Số lượt đánh giá ──
    review_count = None
    rev_el = card.locator("span.qzqFw").first
    if rev_el.count() > 0:
        review_count = parse_review_count(rev_el.inner_text())

    # ── Sold info (số đã bán) ──
    sold_info = None
    sold_el = card.locator("span._1cEkb span").first
    if sold_el.count() > 0:
        sold_info = sold_el.inner_text().strip() or None

    # ── Địa điểm / người bán ──
    location = None
    loc_el = card.locator("span.oa6ri").first
    if loc_el.count() > 0:
        location = loc_el.inner_text().strip() or None

    # ── URL ảnh sản phẩm ──
    image_url = ""
    img_el = card.locator("img[type='product']").first
    if img_el.count() > 0:
        src = img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""
        image_url = normalize_url(src)

    return Product(
        name          = name,
        price         = price,
        original_price= original_price,
        product_url   = product_url,
        image_url     = image_url,
        rating        = rating,
        review_count  = review_count,
        sold_info     = sold_info,
        location      = location,
        page_number   = page_num,
    )


# ──────────────────────────────────────────────
# Làm sạch & dedup
# ──────────────────────────────────────────────
def clean_and_dedup(products: list[Product]) -> list[Product]:
    """
    - Loại bỏ sản phẩm không có tên hoặc URL.
    - Dedup dựa trên product_url (giữ bản xuất hiện đầu tiên).
    """
    seen_urls: set[str] = set()
    cleaned: list[Product] = []

    for p in products:
        if not p.name or not p.product_url:
            continue
        key = p.product_url.rstrip("/").lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        cleaned.append(p)

    return cleaned


# ──────────────────────────────────────────────
# Lưu file
# ──────────────────────────────────────────────
def save_outputs(products: list[Product]) -> None:
    records = [asdict(p) for p in products]

    # CSV
    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    log.info("Đã lưu CSV: %s (%d dòng)", OUTPUT_CSV, len(df))

    # JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    log.info("Đã lưu JSON: %s (%d records)", OUTPUT_JSON, len(records))


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main() -> None:
    log.info("=== Lazada Football Boots Scraper ===")
    log.info("Từ khóa: '%s' | Tối đa %d trang", KEYWORD, MAX_PAGES)

    all_products: list[Product] = []
    errors: list[str] = []
    blocked = False

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent = USER_AGENT,
            viewport   = {"width": 1440, "height": 900},
            locale     = "vi-VN",
            extra_http_headers = {
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        page = context.new_page()

        for page_num in range(1, MAX_PAGES + 1):
            try:
                products, was_blocked = scrape_page(page, page_num)
            except Exception as exc:
                msg = f"Lỗi nghiêm trọng trang {page_num}: {exc}"
                log.error(msg)
                errors.append(msg)
                continue

            if was_blocked:
                blocked = True
                errors.append(f"Bị chặn / CAPTCHA ở trang {page_num} – dừng sớm.")
                break

            all_products.extend(products)
            log.info("Tổng cộng đã thu thập: %d sản phẩm (thô)", len(all_products))

            # Nếu trang trả về ít hơn 5 sản phẩm → hết kết quả
            if len(products) < 5:
                log.info("Hết kết quả ở trang %d.", page_num)
                break

            # Nghỉ giữa trang để tránh bị rate-limit
            if page_num < MAX_PAGES:
                time.sleep(2)

        browser.close()

    # Làm sạch
    cleaned = clean_and_dedup(all_products)
    removed  = len(all_products) - len(cleaned)
    log.info("Sau khi làm sạch: %d sản phẩm (đã loại %d trùng/rỗng)", len(cleaned), removed)

    if not cleaned:
        log.warning("Không có dữ liệu để lưu.")
    else:
        save_outputs(cleaned)

    # ── Báo cáo tổng kết ──
    print("\n" + "=" * 60)
    print("  BÁO CÁO KẾT QUẢ")
    print("=" * 60)
    print(f"  Sản phẩm thu thập thành công : {len(cleaned)}")
    print(f"  Sản phẩm thô (trước dedup)   : {len(all_products)}")
    print(f"  Trùng lặp / thiếu dữ liệu   : {removed}")
    print(f"  File CSV                      : {OUTPUT_CSV.resolve()}")
    print(f"  File JSON                     : {OUTPUT_JSON.resolve()}")
    if blocked:
        print("\n  ⚠  CẢNH BÁO: Bị chặn hoặc phát hiện CAPTCHA – đã dừng sớm.")
    if errors:
        print(f"\n  Lỗi gặp phải ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    else:
        print("\n  Không có lỗi.")
    print("=" * 60)

    # Preview 5 dòng đầu
    if cleaned:
        print("\nMẫu 5 sản phẩm đầu tiên:")
        for i, p in enumerate(cleaned[:5], 1):
            print(f"  {i}. {p.name[:60]!r}")
            print(f"     Giá: {p.price}  |  Gốc: {p.original_price}")
            print(f"     Sao: {p.rating}  |  Đánh giá: {p.review_count}")
            print(f"     Đã bán: {p.sold_info}  |  Địa điểm: {p.location}")
            print(f"     URL: {p.product_url[:80]}")
        print()


if __name__ == "__main__":
    main()
