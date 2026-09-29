"""One-click launcher: mở thẳng cửa sổ Preview CapCut cho 1 dự án cụ thể, không phải bấm trong app.
Cách dùng:
    python open_preview.py [project_dir]
Hoặc bấm đúp open_preview.vbs / .bat cùng cấu trúc.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from desktop_app import PreviewWindow, _apply_style  # noqa: E402


DEFAULT_PROJECT = ROOT / "outputs" / "project_0d47746d7239"  # Sigma Mỹ-Trung LHQ


def main() -> int:
    proj = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_PROJECT
    if not proj.is_dir():
        print(f"Không tìm thấy thư mục dự án: {proj}")
        return 1

    root = tk.Tk()
    _apply_style(root)
    root.withdraw()  # ẩn root rỗng, chỉ hiện PreviewWindow
    PreviewWindow(root, str(proj))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
