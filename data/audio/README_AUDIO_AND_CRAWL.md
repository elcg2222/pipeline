# KHO ÂM THANH & QUY CHUẨN CÀO DỮ LIỆU PIPELINE

## 1. KHO ÂM THANH LOCAL (SOUND EFFECTS & BGM)

Kho âm thanh thương mại được phân loại và đánh số sẵn tại `D:\pipeline\data\audio\`:

### 🎵 Hiệu ứng âm thanh (SFX) — `data/audio/sfx/`
- `whoosh_chuyen_canh.wav`: Hiệu ứng chuyển cảnh giữa các clip.
- `ding_nhan_manh_tien_so_lieu.wav`: Tiếng ding khi xuất hiện số tiền, %, quà tặng.
- `pop_hien_anh_text.wav`: Tiếng pop khi nảy chữ hoặc popup ảnh.
- `notification_canh_bao.wav`: Tiếng chuông cảnh báo, mẹo, lưu ý.
- `bass_drop_khoang_lang_drama.wav`: Tiếng bass trầm kịch tính cho mốc khoảng lặng.

### 🎶 Nhạc nền (BGM) — `data/audio/bgm/`
- `upbeat_vui_tuoi_soi_dong.wav`: Nhạc vui tươi sôi động (Review đồ gia dụng, sản phẩm).
- `lofi_thu_gian_nhe_nhang.wav`: Nhạc Lo-fi nhẹ nhàng (Vlog, chia sẻ kinh nghiệm).
- `cinematic_kich_tinh_sang_trong.wav`: Nhạc kịch tính sang trọng (Phim ngắn, tin tức).

---

## 2. GIẢI PHÁP CÀO DỮ LIỆU FACEBOOK & INSTAGRAM

### 🔴 Instagram
1. **Dùng Cookie Clone (Khuyên dùng)**:
   - Dùng nick phụ đăng nhập Instagram trên Chrome.
   - Cài Extension `Get cookies.txt LOCALLY` xuất file `instagram_cookies.txt`.
   - Cấu hình file `config.yaml`:
     ```yaml
     providers:
       instagram:
         session_file: 'C:/Users/cuongle/instagram_cookies.txt'
     ```
2. **Kéo qua API Stock thay thế khi bị rate-limit**:
   - Tự động dùng `providers/stock_provider.py` (Pexels & Pixabay API) để lấy ảnh/video dọc 9:16 miễn phí 100% bản quyền khi Instagram chặn IP.

### 🔵 Facebook
1. **Lấy video lẻ Reels/Watch**:
   - Dùng `yt-dlp` trực tiếp qua link công khai, không cần đăng nhập:
     ```bash
     yt-dlp "https://www.facebook.com/reel/XXXXX" -o "downloads/%(title)s.%(ext)s"
     ```
2. **Cào hàng loạt (Batch Scrape)**:
   - Facebook đổi HTML liên tục và khóa IP nhanh. Tránh cào hàng loạt tự động bằng nick thật.
   - Ưu tiên cào ý tưởng/video gốc từ Douyin/TikTok/YouTube/Reddit, sau đó dùng Pexels bù tài nguyên.
