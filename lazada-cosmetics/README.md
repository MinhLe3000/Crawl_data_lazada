# Crawl mỹ phẩm Paula’s Choice trên Lazada

Chạy từ thư mục gốc dự án:

```powershell
& './lazada-football-boots/.venv/Scripts/python.exe' -u './lazada-cosmetics/crawl_cosmetics.py'
```

Script dùng Playwright có sẵn của dự án giày bóng đá. Có thể chạy lại lệnh để tiếp tục từ checkpoint. `--details-only` chỉ lấy danh mục và chi tiết sản phẩm.

## Hai file dữ liệu

- `data/paulas-choice/products.json`: một bản ghi cho mỗi `product_id` (chuỗi). Bao gồm tên, thương hiệu, giá bán, giá gốc, giá sau voucher riêng biệt, mô tả HTML và văn bản, ảnh trong mô tả, đặc điểm nổi bật/thành phần/hướng dẫn sử dụng, thông số, phân loại SKU, ảnh/video thư viện, tóm tắt sao và số đánh giá, chứng chỉ và bảo hành.
- `data/paulas-choice/reviews.json`: một bản ghi cho mỗi đánh giá, liên kết về sản phẩm qua `product_id`. `review_id` là chuỗi, giữ tên người mua đã được Lazada che, số sao, ngày, nội dung, phân loại SKU, ảnh/video và phản hồi của người bán.

`description_text` có thể rỗng nếu phần mô tả chỉ có ảnh; ảnh và HTML vẫn được lưu đầy đủ. Văn bản thành phần/công dụng thường nằm ở `highlights_text`. Không OCR hoặc tự điền nội dung không có trong dữ liệu nguồn. `sku_details` chỉ bao gồm SKU mà trang đã tải; danh sách phân loại đầy đủ mà trang cung cấp được giữ ở `variants`.

## Nhãn chính hãng

Script kiểm tra ảnh `storeIcon` ở đầu trang shop, không dùng chữ LazMall ở thanh điều hướng toàn website. Asset nhãn LazMall – Gian hàng chính hãng của shop này đã được đối chiếu trực quan với ảnh chụp trang thực tế. Chỉ khi asset phù hợp mới gán `is_authentic: true`; mỗi trang chi tiết còn được đối chiếu `seller_id = 100169489` và ID sản phẩm. Đây là nhãn kế thừa từ shop theo yêu cầu, không phải kiểm định vật lý sản phẩm.

Bằng chứng lưu tại `storefront.png`, `storefront.html` và `crawl_report.json` trong thư mục dữ liệu.

## Kiểm tra độ đầy đủ

`crawl_report.json` là file vận hành, không phải file dữ liệu thứ ba. Xem `catalog_status`, `details_status`, `review_progress[product_id].status`, số lượng và lỗi. Chỉ kết luận hoàn tất khi `status = complete`. Kết thúc danh mục cần nút trang tiếp bị vô hiệu hóa. Đánh giá kết thúc khi API phân trang công khai trả về danh sách rỗng; trang lặp hoặc lỗi không được coi là hoàn tất. Số đánh giá tổng trên sản phẩm có thể khác số bình luận API công khai trả về (ví dụ đánh giá chỉ có sao); giữ hai số riêng để đối chiếu.

Script lưu sau mỗi sản phẩm/trang đánh giá, loại trùng theo `(product_id, review_id)`, dừng khi bị CAPTCHA/chặn truy cập hoặc API báo lỗi. Không vượt CAPTCHA. Mã thoát 2 nghĩa là chưa hoàn tất.
