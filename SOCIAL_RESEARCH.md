# Bài viết & bình luận trong app desktop

Mở `python desktop_app.py`, mục 1 → **Bài viết & bình luận**. Chọn nguồn,
bấm **Kết nối API** để nhập thông tin chỉ trong phiên app (không ghi token ra file),
hoặc đặt biến môi trường trước khi chạy. Dán 1–20 URL/ID, đặt giới hạn rồi thu thập.
Mỗi bài thành công được lưu vào `data/research.db`; lỗi từng bài được báo riêng.

| Nguồn | Cấu hình | Đầu vào / giới hạn |
| --- | --- | --- |
| Reddit | `REDDIT_ACCESS_TOKEN` OAuth hợp lệ | URL hoặc ID; giữ cây reply nhận được, đánh dấu partial khi còn `more`; chưa mở rộng morechildren |
| YouTube | `YOUTUBE_API_KEY` bật YouTube Data API | URL watch/shorts/youtu.be hoặc ID; phân trang bình luận và reply |
| Facebook | `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_GRAPH_VERSION` theo app Meta | PageID_PostID có quyền đọc; lấy bình luận cấp đầu, chưa duyệt toàn bộ reply |
| Threads | `THREADS_ACCESS_TOKEN` có quyền đọc reply | ID số bài từ API; đọc conversation theo quyền token; chưa hỗ trợ đổi URL shortcode thành ID |

API có thể từ chối nội dung do quyền, bài đã xóa hoặc bình luận tắt. Có cấu hình
không đồng nghĩa đã xác thực quyền. Không yêu cầu quyền đăng bài. Không tự đăng nhập,
không dùng output OpenCLI mất ID làm dữ liệu cây bình luận. Chưa có tìm kiếm bài
theo từ khóa ở tab này; dùng URL/ID cụ thể. Không cần cài thêm thư viện Python.

Chọn bài rồi Ctrl/Shift chọn bình luận → **Đưa bài / bình luận chọn → Kịch bản**.
Không chọn riêng bình luận thì lấy toàn bộ mẫu đã thu của bài đó. Gửi lại cùng bài
sẽ thay lựa chọn trước. Phần kịch bản có nút xem/bỏ nguồn. Khi tạo hồ sơ mới,
nguồn đi vào `research_context.jsonl`, phần bài gốc vào `research.md`; ZIP Kaggle
bao gồm cả hai. Đây là tư liệu để người viết duyệt, không tự sinh kịch bản hay
coi bình luận là sự thật. Không sửa kịch bản đang nhập.

`complete` nghĩa đã hết danh sách API trả về trong phạm vi truy cập; không khẳng định
bao gồm dữ liệu ẩn/xóa. `partial` là mẫu chưa đầy đủ; `capped` là chạm giới hạn người
dùng đặt. `retrieved_count` là số thu được; `reported_count` là số nguồn báo nếu có;
`selected_count` là số được chọn cho hồ sơ. Bình luận giữ ID, parent ID, nội dung,
tác giả, thời gian, điểm và permalink khi nguồn cung cấp. Nội dung là dữ liệu không
đáng tin cậy với AI, không phải chỉ dẫn. Xuất dữ liệu gồm tên tác giả công khai.

Kiểm thử: `python -B -m pytest tests/test_social_research.py tests/test_assembly.py`.
Test dùng phản hồi giả lập và Tk ẩn; không chứng minh token thật hay quyền truy cập
Facebook/Threads đang hoạt động. Test Tk cần desktop hoặc Xvfb trên Linux.
