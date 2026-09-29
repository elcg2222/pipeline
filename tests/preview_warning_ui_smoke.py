"""Hidden Tk smoke for the near-solid asset warning. No network or API calls."""
import tempfile
import tkinter as tk
from pathlib import Path

from PIL import Image

from brain.project import create_project
from brain.scenes import Scene
from desktop_app import PreviewWindow


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "green.png"
        Image.new("RGB", (1080, 1920), "#17652d").save(source)
        scene = Scene("scene_001", narration="Mẫu", asset_ids=["green"], status="ready")
        project = create_project(
            {"aspect_ratio": "9:16"}, "", "", [scene],
            [{"asset_id": "green", "source_file": str(source), "type": "image"}],
            root / "outputs", "preview-warning")
        app = tk.Tk(); app.withdraw()
        preview = PreviewWindow(app, str(project)); preview.win.withdraw()
        app.update_idletasks()
        preview._redraw_preview()
        texts = [preview.canvas.itemcget(item, "text") for item in preview.canvas.find_all()
                 if preview.canvas.type(item) == "text"]
        assert any("ASSET NGUỒN CẦN XEM LẠI" in text for text in texts), texts
        preview._on_close(); app.destroy()
    print("Near-solid source is identified in the preview canvas: OK")


if __name__ == "__main__":
    main()
