from pathlib import Path

from core.store import Store
from core.schema import VideoItem
from stages import qc
import media_bridge


def test_restricted_document_is_not_saved_by_default(tmp_path):
    doc = {
        "id": "news:1", "type": "news", "source": "example",
        "title": "Restricted", "url": "https://example.test/article",
        "content": "copyrighted", "commercial_use": False,
        "attribution_required": True,
    }
    result = media_bridge.download([doc], "topic", str(tmp_path))
    assert result["downloaded"]["news"] == 0
    assert result["skipped"][0]["reason"] == "restricted_license"


def test_qc_promotes_downloaded_to_qc_passed(tmp_path, monkeypatch):
    store = Store(tmp_path / "pipeline.db")
    video = tmp_path / "video.mp4"
    video.write_bytes(b"placeholder")
    item = VideoItem(platform="test", url="https://example.test/video", native_id="1")
    item.state = "downloaded"
    item.local_path = str(video)
    store.upsert(item)
    store.set_state(item.uid, "downloaded", local_path=str(video))

    monkeypatch.setattr(qc, "which", lambda _: "ffprobe")
    monkeypatch.setattr(qc, "ffprobe", lambda _: {
        "streams": [{"codec_type": "video", "height": 1080}, {"codec_type": "audio"}],
        "format": {"duration": "20"},
    })
    monkeypatch.setattr(qc, "video_phash", lambda _: "")

    result = qc.run(store, {"qc": {"require_audio": True, "check_phash": True}}, 10)
    row = store.conn.execute("SELECT state,last_error FROM videos WHERE uid=?", (item.uid,)).fetchone()
    assert result["ok"] == 1
    assert row["state"] == "qc_passed"
    assert row["last_error"] == ""
    store.close()
