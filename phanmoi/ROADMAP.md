# ROADMAP — nâng cấp sau v0

Nguyên tắc: **chỉ nâng cấp khi đã đụng trần thật sự**, không nâng cấp vì
nghe có vẻ chuyên nghiệp hơn. Mỗi mục dưới đây ghi rõ *triệu chứng* báo
hiệu đã đến lúc làm.

---

## Giai đoạn 1 — Vá những chỗ v0 cố tình bỏ ngỏ

### 1.1 Dedupe thật (~half day)
**Triệu chứng:** tìm một chủ đề tin tức, 15 kết quả nhưng thực chất là 4 bài.

```python
# adapters/../dedupe.py
from simhash import Simhash
def text_fingerprint(text: str) -> int:
    return Simhash(text.lower().split()).value
# Hamming distance <= 3 giữa hai bài -> coi là trùng, giữ bài đăng sớm nhất
```

Ảnh dùng pHash (`ImageHash` + `Pillow`), ngưỡng khoảng cách <= 5. Bắt được
cùng một ảnh ở kích thước khác hoặc có watermark.

Thêm cột `simhash INTEGER` và `phash TEXT` vào bảng `docs`, đánh index.

### 1.2 Tải media về máy (~2h)
**Triệu chứng:** mở lại kết quả cũ, ảnh 404; hoặc cần dùng offline.

Tải vào `data/media/<source>/<hash>.<ext>`, lưu đường dẫn local vào
`metadata["local_path"]`. Pixabay ToS cũng yêu cầu điều này.

### 1.3 Chỉnh ranking bằng dữ liệu thật (~liên tục)
**Triệu chứng:** kết quả đầu tiên thường không phải cái bạn muốn.

Cách làm rẻ: thêm `--debug-score` in ra từng thành phần điểm. Chạy 20 truy
vấn quen thuộc, xem cái nào xếp sai, chỉnh `MODE_WEIGHTS`. Đừng đoán.

### 1.4 Health check tự động (~1h)
**Triệu chứng:** một nguồn im lặng nhiều ngày mà không ai biết.

Cron chạy `python main.py health` hàng ngày, ghi kết quả vào bảng
`adapter_health`. Cảnh báo khi một adapter trả 0 kết quả 3 lần liên tiếp —
đây là dấu hiệu nguồn đổi cấu trúc, không phải hết dữ liệu.

---

## Giai đoạn 2 — Mở rộng nguồn

Thứ tự theo độ khó tăng dần. Làm từng cái, mỗi cái xong mới sang tiếp.

| Nguồn | Công cụ | Độ khó | Ghi chú |
|---|---|---|---|
| Unsplash | REST API | Dễ | Cần duyệt app để lên production; demo mode hạn mức thấp |
| Wikimedia Commons | API | Dễ | Ảnh public domain/CC, không cần key |
| Hacker News | Firebase API | Dễ | Không key, không hạn mức thực tế |
| Stack Exchange | REST API | Dễ | Có key miễn phí, hạn mức rộng |
| Forum nền Discourse | thêm `.json` vào URL | Dễ | Rất nhiều forum kỹ thuật dùng Discourse |
| GDELT 2.0 | REST/CSV | Trung bình | Tin toàn cầu cập nhật ~15 phút — mạnh nhất cho `news_fast` |
| arXiv | API + GROBID | Trung bình | GROBID cho PDF khoa học có cấu trúc |
| Trang SPA/infinite scroll | Playwright | Khó | Chỉ bật khi HTTP thuần thất bại — xem 3.1 |

**Cách thêm nhanh nhất:** nếu nguồn có RSS, chỉ thêm một dòng vào
`feeds.txt`. Google News RSS theo từ khoá là mẹo rẻ nhất để có "tin theo
chủ đề" mà không cần viết adapter:

```
https://news.google.com/rss/search?q=TU+KHOA&hl=vi&gl=VN&ceid=VN:vi | gnews-tukhoa
```

---

## Giai đoạn 3 — Khi v0 đụng trần kỹ thuật

### 3.1 Playwright fallback
**Triệu chứng:** một trang trả về HTML rỗng hoặc thiếu nội dung chính.

Đừng bật mặc định. Kiến trúc đúng là *fallback theo tầng*:

```python
async def fetch(url):
    html = await http_get(url)
    if is_content_sufficient(html):   # vd: > 500 ký tự sau trafilatura
        return html
    return await browser_get(url)     # chỉ tới đây khi cần
```

Playwright tốn RAM gấp 10–50 lần. Bật bừa là chết máy.

### 3.2 Đổi SQLite sang PostgreSQL
**Triệu chứng:** > ~500k bản ghi, hoặc cần nhiều tiến trình ghi cùng lúc.

Chỉ phải viết lại `storage.py`. Adapter và router không đụng tới — đó là
lý do tồn tại của lớp `Doc`.

### 3.3 Tìm kiếm ngữ nghĩa
**Triệu chứng:** tìm "xe điện" mà bỏ sót bài viết "ô tô chạy pin".

Thêm `pgvector` + embedding, kết hợp điểm BM25 và cosine (hybrid search).
Đây là lúc thật sự cần Postgres, không phải trước đó.

### 3.4 Queue thật
**Triệu chứng:** `crawl` chạy quá lâu, cần retry thông minh, cần chạy nền.

Redis + ARQ là bước nhỏ nhất. Celery chỉ khi cần nhiều worker trên nhiều máy.

---

## Giai đoạn 4 — Mạng xã hội (tách riêng, không chặn tiến độ)

Đây là **mục tiêu di động theo chính sách nền tảng**, không phải bài toán
kỹ thuật giải dứt điểm được. Đừng để nó chặn giai đoạn 1–3.

### Reddit
**Việc gấp, làm trước khi viết code:** Reddit thông báo ngày 5/8/2026 sẽ
dần hạn chế mọi request mới vào Data API công khai và chuyển hướng sang
Developer Platform chạy JavaScript/TypeScript (Python không nằm trong lộ
trình của họ). App đang có phải đăng ký trước **30/9/2026**. Nếu có ý định
dùng Reddit, đăng ký app ngay — mất 15 phút, miễn phí.

Nếu có credentials: `praw` + adapter `source_type="discussion"`.
Cho dữ liệu lịch sử số lượng lớn: Arctic Shift (dump hàng tháng).

### X
Ba đường, chọn một:
- API chính thức pay-per-use — không rủi ro tài khoản, tính tiền theo lượt đọc.
- `twscrape` / `Twikit` — cần tài khoản X thật, có rủi ro bị khoá.
- Bỏ qua.

Nitter (mirror đọc X không cần đăng nhập) đã đóng cửa tháng 8/2026 sau thư
pháp lý từ X Corp, `snscrape` chết với X từ 2023 — các hướng dẫn cũ trên
mạng phần lớn đã lỗi thời.

### Facebook / Instagram
- Graph API: chỉ Page/tài khoản Business **bạn sở hữu hoặc được cấp quyền**.
- Meta Content Library: dữ liệu công khai diện rộng, nhưng chỉ mở cho nhà
  nghiên cứu học thuật/phi lợi nhuận qua thẩm định ICPSR.
- `Instaloader`: đọc profile Instagram công khai, không cần đăng nhập.

Coi cả nhóm này là module "best-effort, có thể mất bất cứ lúc nào". Đừng
thiết kế tính năng cốt lõi nào phụ thuộc vào nó.

---

## Không nằm trong kế hoạch

**Trang truyện/sách vi phạm bản quyền.** Cào và lưu trữ nội dung từ nguồn
lậu biến chính tool này thành công cụ phân phối lại, và chặn đường thương
mại hoá sau này.

Nguồn hợp pháp cho kho văn bản lớn: Project Gutenberg (~75k sách public
domain, có dump cho máy), Standard Ebooks, Wikisource, phần public domain
của Internet Archive.

---

## Thứ tự khuyến nghị

```
v0 (3 ngày)  →  1.1 dedupe  →  1.3 chỉnh ranking  →  GĐ2 thêm nguồn
                                                        │
                        chỉ khi đụng trần thật ─────────┤
                                                        ▼
                                              GĐ3 nâng hạ tầng
```

Giai đoạn 4 chạy song song, độc lập, và không bao giờ là đường găng.
