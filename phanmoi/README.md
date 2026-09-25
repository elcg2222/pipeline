# crawler-tool v0

Bộ khung thu thập dữ liệu đa nguồn: ảnh thương mại, video, tin tức — gộp
sau **một giao diện duy nhất** để AI Agent gọi được.

Cố ý giữ nhỏ: SQLite thay Postgres, `asyncio.gather` thay Redis/Celery,
không Docker. Nâng từng mảnh sau mà không phải viết lại adapter.

---

## Chạy trong 15 phút

```bash
pip install -r requirements.txt
cp .env.example .env        # rồi dán API key vào
```

Lấy key (miễn phí, mỗi cái ~2 phút):
- Pexels: https://www.pexels.com/api/
- Pixabay: https://pixabay.com/api/docs/
- Openverse: không cần key vẫn chạy

```bash
# 1. Kiểm tra adapter nào sống
python main.py health

# 2. Tìm ảnh, chỉ lấy loại dùng thương mại được
python main.py search "ocean sunset" --mode image --commercial-only

# 3. Kéo tin tức vào kho
python main.py crawl news

# 4. Tin mới nhất về một chủ đề
python main.py search "AI agent" --mode news_fast

# 5. Tìm trong kho (không gọi mạng, gần như tức thì)
python main.py local "AI agent"

# 6. Xem kho có gì
python main.py stats
```

---

## Cấu trúc

```
models.py        Doc + License      ← schema chung MỌI nguồn phải tuân theo
storage.py       SQLite + FTS5
router.py        fan-out song song + dedupe + ranking   ← Query Loop
config.py        đọc .env, lắp ráp adapter
main.py          CLI
mcp_server.py    cửa cho AI Agent
feeds.txt        danh sách RSS (thêm nguồn = thêm một dòng)
adapters/
  base.py        hợp đồng chung
  pexels.py      ảnh + video
  pixabay.py     ảnh
  openverse.py   ảnh CC (có license engine thật)
  rss_news.py    tin tức
```

**Hai vòng lặp, đừng lẫn:**
- `crawl` = Ingest Loop — chạy theo lịch, nuôi kho.
- `search` / `local` = Query Loop — trả lời khi bạn hoặc agent hỏi.

---

## Thêm một nguồn mới

Tạo file trong `adapters/`, kế thừa `SourceAdapter`, trả về `list[Doc]`.
Rồi thêm một dòng vào `config.build_adapters()`. Không đụng gì khác.

```python
class MyAdapter(SourceAdapter):
    name = "mysite"
    source_type = "image"
    capabilities = {"search"}

    async def search(self, query, limit=20):
        async with self.client() as c:
            r = await c.get("https://mysite.com/api", params={"q": query})
        return [Doc(source_type="image", source_name=self.name,
                    source_url=x["url"], title=x["title"],
                    license=License(id="...", commercial_use=True))
                for x in r.json()["items"]]
```

Thêm RSS thì chỉ cần một dòng trong `feeds.txt`, không viết code.

---

## Dùng với AI Agent

```bash
pip install "mcp[cli]"
python mcp_server.py
```

Khai báo trong Claude Desktop / Claude Code:

```json
{
  "mcpServers": {
    "crawler-tool": {
      "command": "python",
      "args": ["/duong/dan/tuyet/doi/crawler-tool/mcp_server.py"]
    }
  }
}
```

Agent sẽ có 3 tool: `search_topic`, `search_archive`, `archive_stats`.

---

## Trường `license` — đừng bỏ qua

Đây là lý do tool này khác một script tải ảnh.

| Nguồn | Thương mại | Ghi chú |
|---|---|---|
| Pexels | Có | Không bắt ghi nguồn |
| Pixabay | Có | ToS yêu cầu tải file về, không hotlink |
| Openverse | **Tuỳ từng ảnh** | Giấy phép có `nc` = CẤM thương mại |
| RSS báo | Không | Nội dung có bản quyền, chỉ để đọc/phân tích |

`--commercial-only` lọc theo `commercial_use = True` **đã xác minh**.
Chưa xác minh thì là `None`, không bao giờ mặc định `True`.

---

## Đã biết v0 còn yếu ở đâu

Không phải bug, là giới hạn có chủ ý. Chi tiết và cách sửa: `ROADMAP.md`.

1. **Dedupe chỉ bắt trùng tuyệt đối.** Báo Việt đăng lại bài của nhau đổi
   vài chữ ở tiêu đề — v0 sẽ trả cả 5 bản. Cần SimHash.
2. **Ranking là phỏng đoán.** Trọng số trong `router.MODE_WEIGHTS` do tôi
   đặt bừa. Nhìn kết quả thật rồi chỉnh.
3. **Adapter có thể chết âm thầm.** Nguồn đổi cấu trúc thì tool vẫn chạy,
   chỉ trả về rỗng. `python main.py health` phát hiện được, nhưng phải
   nhớ chạy.
4. **Ảnh chưa được tải về máy.** Mới lưu URL. Link có thể chết sau này.
