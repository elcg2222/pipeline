"""Run with python -m tests.studio_handoff_ui_smoke only if tests is a package,
or via runpy.run_path. Hidden Tk smoke; no API calls or downloads."""
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from studio_bridge.project import write
from ui_studio_handoff import StudioHandoff


def main():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        (folder / "image.png").write_bytes(b"fixture")
        write(folder / "preview_profile.json", {"project_id": "ui-smoke", "scenes": [
            {"scene_id": "s1", "media": "image.png", "narration": "Xin chào", "estimated_duration_sec": 1}]})
        root = tk.Tk(); root.withdraw()
        errors = []
        with patch("ui_studio_handoff.messagebox.showerror", side_effect=lambda *a, **k: errors.append(a)):
            pane = StudioHandoff(root, folder); pane.win.withdraw()
            deadline = time.monotonic() + 10
            while pane.busy and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            assert not pane.busy and not errors, errors
            assert pane.project["project_id"] == "ui-smoke"
            assert len(pane.tree.get_children()) == 1
            pane.close()
            root.destroy()
    print("Studio handoff Tk construction and asynchronous import: OK")


if __name__ == "__main__":
    main()
