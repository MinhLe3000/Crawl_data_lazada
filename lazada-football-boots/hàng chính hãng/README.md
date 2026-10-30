# Thu thập sản phẩm từ 5 shop được chỉ định

Cấu hình shop trong `shops.json`. Script độc lập với `../scraper.py` và mặc định lấy tất cả loại sản phẩm trong danh mục của từng shop.

Chạy từ thư mục gốc dự án bằng PowerShell:

```powershell
& .\.venv\Scripts\python.exe '.\hàng chính hãng\crawl_shops.py'
```

Tùy chọn: `--shop nike-flagship-store`, `--max-pages 10` (mặc định 200 trang/shop). Khi đạt giới hạn, báo cáo ghi `page_limit_reached`, không coi là đã lấy đủ.

Nếu tạo môi trường mới: chạy `python -m pip install -r "hàng chính hãng/requirements.txt"`, sau đó chạy `python -m playwright install chromium`.

Mỗi lần chạy tạo thư mục thời gian riêng trong `data/`, gồm CSV/JSON riêng từng shop, `all_products.*`, `football_boot_candidates.*`, `summary.json`, log và HTML/ảnh kiểm tra. Lưu checkpoint sau từng trang. Tập con giày bóng đá chỉ là lọc tên bằng quy tắc, cần kiểm tra lại nếu dùng làm nhãn huấn luyện.

Quy tắc nhãn ở cấp shop: `official_shop_confirmed: true` trong `shops.json` nghĩa là người dùng đã xác nhận shop có nhãn “Gian hàng chính hãng”. Tất cả sản phẩm lấy từ danh mục shop đó được gán `badge_observed: true`, với `official_source: "user_confirmed_shop_badge"`. Giữ tên trường `badge_observed` để tương thích dữ liệu cũ; ý nghĩa hiện tại là nhãn cấp shop được kế thừa xuống sản phẩm, không còn là kết quả tìm chữ tự động trên trang. Shop mới chưa được xác nhận sẽ có `badge_observed: false` và `official_source: "unconfirmed"`; không tự gán true chỉ vì nằm trong file cấu hình.

`rating_approx` được suy ra từ icon sao (bước 0,5). Giá gốc không có trên card được để trống; phần trăm giảm giá có trường riêng. Ảnh placeholder dạng `data:` không được lưu làm URL ảnh.

Xem trạng thái từng shop trong `summary.json`: `complete` chỉ khi nút trang kế tiếp bị vô hiệu hóa hoặc có thông báo hết kết quả; lỗi, CAPTCHA, trang lặp, thiếu selector và giới hạn trang đều được ghi riêng. Mã thoát 2 nghĩa là có shop chưa xác nhận hoàn tất. Script dừng shop khi gặp CAPTCHA, không vượt cơ chế bảo vệ.
