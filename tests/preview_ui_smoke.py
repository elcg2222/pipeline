"""Run manually on a desktop Python with tkinter; no network, no API calls."""
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from brain.project import create_project
from brain.scenes import Scene
from desktop_app import PreviewWindow, PipelineApp


def main():
    with tempfile.TemporaryDirectory() as tmp:
        project = create_project({}, "", "", [Scene("a", narration="Giọng mẫu"), Scene("b")], [], Path(tmp), "smoke")
        root = tk.Tk()
        root.withdraw()
        preview = PreviewWindow(root, str(project))
        preview.win.withdraw()
        root.update_idletasks()
        preview.title_var.set("Kiểm tra chữ")
        preview.effect_var.set("pop")
        preview.apply_notes()
        preview.speed_var.set("2.0")
        preview.apply_speed()
        duration = preview.scenes[0]["estimated_duration_sec"]
        preview.speed_var.set("2.0")
        preview.apply_speed()
        assert duration == preview.scenes[0]["estimated_duration_sec"]
        with patch("desktop_app.messagebox.showinfo"):
            preview.save_scenes()
        assert (project / "preview_profile.json").exists()
        preview._show_scene(1)
        preview.title_var.set("Cảnh B")
        preview.move_scene(-1)
        assert preview.scenes[0]["on_screen_text"] == "Cảnh B"
        preview._show_scene(1)
        with patch("desktop_app.messagebox.askyesno", return_value=True):
            preview.cut_scene()
        assert len(preview.scenes) == 1
        preview.play()
        preview.pause()
        preview._on_close()
        root.destroy()
        with patch("desktop_app.ROOT", Path(tmp)), patch("desktop_app.DB", Path(tmp) / "absent.db"):
            app = PipelineApp()
            app.root.withdraw()
            assert len(app.sections.tabs()) == 2
            app.assembly.script.insert("1.0", "## Mèo vui\nMột chú mèo đang chơi.")
            app.assembly.split_script()
            assert len(app.assembly.scenes) == 1
            app.show_preview(project)
            assert app.preview.embedded
            assert not isinstance(app.preview.win, tk.Toplevel)
            app.preview.title_var.set("Chưa lưu")
            assert app.preview._has_changes()
            with patch("desktop_app.messagebox.askyesnocancel", return_value=False):
                app.close_app()
    print("Tk preview construction/edit/save/play/pause: OK")


if __name__ == "__main__":
    main()
