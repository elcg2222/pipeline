# 📦 Social Video Pipeline - Hướng Dẫn Sử Dụng

## ✅ Các Providers Đã Hỗ Trợ

| Provider | Trạng thái | Yêu cầu | Ghi chú |
|----------|------------|---------|---------|
| **YouTube** | ✅ Sẵn sàng | Không | Hoạt động ngay |
| **Instagram** | ⚠️ Cần session | `session_user` + `session_file` | Dùng instaloader |
| **Discord** | ⚠️ Cần token | `bot_token` hoặc `user_token` | Lấy từ Discord Dev Portal |
| **Reddit** | ⚠️ Cần OpenCLI | `npm i -g @jackwener/opencli` | Hoặc dùng API credentials |
| **Facebook** | ⚠️ Cần access_token | `access_token` từ Graph API | Giới hạn với public pages |
| **Douyin** | ❌ Chưa config | Cookie hoặc DTK backend | Cần cookie từ browser |
| **TikTok** | ❌ Chưa config | Cookie hoặc DTK backend | Cần cookie từ browser |
| **1688** | Tắt | - | Marketplace Trung Quốc |

---

## 🚀 Cài Đặt Nhanh

### 1. Cài Dependencies
```bash
# Python packages
pip install praw requests instaloader

# OpenCLI cho Reddit (optional)
npm i -g @jackwener/opencli

# FFmpeg (đã cài sẵn)
ffmpeg -version
```

### 2. Cấu Hình Instagram
```bash
# Tạo session file
python -c "import instaloader; L = instaloader.Instaloader(); L.login('YOUR_USERNAME', 'YOUR_PASSWORD'); L.save_session_to_file('session-instagram')"

# Cập nhật config.yaml
instagram:
  session_user: "your_username"
  session_file: "session-instagram"
```

### 3. Cấu Hình Discord
1. Truy cập https://discord.com/developers/applications
2. Tạo application mới
3. Vào "Bot" > "Add Bot"
4. Copy token vào `config.yaml`:
```yaml
discord:
  bot_token: "YOUR_BOT_TOKEN_HERE"
  channel_ids: ["channel_id_1", "channel_id_2"]
  max_messages: 100
```

### 4. Cấu Hình Reddit (Optional - có thể dùng read-only)
1. Truy cập https://www.reddit.com/prefs/apps
2. Tạo application mới (script type)
3. Copy client_id và client_secret vào `config.yaml`:
```yaml
reddit:
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  user_agent: "VideoPipelineBot/1.0"
  subreddits: ["videos", "Shorts", "TikTokCringe"]
```

### 5. Cấu Hình Facebook (Optional)
1. Truy cập https://developers.facebook.com
2. Tạo app và lấy access token với permissions: `pages_read_engagement`, `groups_access_member`
3. Cập nhật `config.yaml`:
```yaml
facebook:
  access_token: "YOUR_ACCESS_TOKEN"
  pages: ["page_id_1", "page_id_2"]
  groups: ["group_id_1"]
```

---

## 📋 Chạy Pipeline

### Kiểm tra trạng thái
```bash
python run.py doctor
```

### Chạy discovery (tìm video mới)
```bash
# Dùng topics từ config
python run.py discover

# Topic cụ thể
python run.py discover -t "máy massage cổ"

# Nhiều topics
python run.py discover -t "đồ gia dụng thông minh"
```

### Xem trạng thái hàng đợi
```bash
python run.py status
```

### Tải videos
```bash
python run.py download
```

### Chạy toàn bộ pipeline
```bash
python run.py all
```

---

## 🔧 Xử Lý Sự Cố

### Provider bị bỏ qua?
Kiểm tra `python run.py doctor` để xem lý do:
- **Thiếu cookie/token**: Điền vào `config.yaml`
- **Chưa cài dependency**: Cài đặt theo hướng dẫn trên
- **DTK backend chưa chạy**: 
  ```bash
  cd Douyin_TikTok_Download_API
  docker compose up -d
  ```

### YouTube không hoạt động?
```bash
# Update yt-dlp
yt-dlp -U

# Thử download manual
yt-dlp "https://youtube.com/shorts/VIDEO_ID"
```

### Instagram bị lỗi login?
```bash
# Xóa session cũ và tạo lại
rm session-instagram
python -c "import instaloader; L = instaloader.Instaloader(); L.login('USER', 'PASS'); L.save_session_to_file('session-instagram')"
```

---

## 📊 Topics Hiện Tại

Config trong `config.yaml`:
```yaml
topics:
  - 颈椎按摩仪            # máy massage cổ
  - 厨房好物              # đồ gia dụng nhà bếp
  - 露营装备              # đồ cắm trại
  - máy massage cổ
  - đồ gia dụng thông minh
```

---

## 🎯 Next Steps

1. **Test với YouTube** (hoạt động ngay):
   ```bash
   python run.py discover
   python run.py download
   ```

2. **Thêm Instagram**:
   - Tạo session file
   - Chạy discover với instagram enabled

3. **Thêm Discord**:
   - Tạo bot token
   - Điền channel IDs
   - Test discover

4. **Test hàng loạt**:
   ```bash
   # Enable tất cả providers trong config
   # Chạy discover
   python run.py discover
   
   # Theo dõi kết quả
   python run.py status
   ```

---

## 📝 Lưu Ý Quan Trọng

- **Không lưu password** trong `config.yaml` - chỉ lưu session files
- **Rate limits**: Mỗi platform có giới hạn request khác nhau
- **Cookies expire**: Định kỳ update cookies từ browser
- **Storage**: Videos tải về trong `downloads/` folder
- **Database**: Metadata lưu trong `data/pipeline.db`

---

## 🆘 Support

- Check logs: `cat logs/pipeline.log`
- Debug mode: Thêm `--log-level DEBUG` vào commands
- Issues: Report bugs với log output từ `doctor` command
