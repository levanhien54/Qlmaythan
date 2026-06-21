# -*- coding: utf-8 -*-
"""Đóng gói GIAO DIỆN WEB trong cửa sổ Chromium (WebView2) thành 1 file .exe.

Chạy:
  python scripts/build_web_exe.py

Kết quả: dist/QuanLyMayThanWeb.exe — mở giao diện web trong cửa sổ ứng dụng,
không cần trình duyệt, không cần cài Python.

Yêu cầu máy đích: WebView2 Runtime (Microsoft) — có sẵn trên hầu hết Windows
10/11 (kèm theo Edge). Nếu máy thiếu, tải "Evergreen WebView2 Runtime" của MS.

Dữ liệu (DB/backup/log) tạo CẠNH file exe lúc chạy (config.py xử lý sys.frozen).
KHÔNG đóng gói file Excel/DB bệnh nhân.
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON = os.path.join(ROOT, "icon.ico")
WEB = os.path.join(ROOT, "web")
SEP = os.pathsep

CMD = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",            # 1 file .exe duy nhất
    "--windowed",           # app GUI → không cửa sổ console
    "--noconfirm", "--clean",
    "--name", "QuanLyMayThanWeb",
    # Giao diện web → giải nén vào _MEIPASS/web (server.py đọc qua sys._MEIPASS)
    "--add-data", f"{WEB}{SEP}web",
    # pywebview + backend EdgeChromium + DLL WebView2 loader + cầu nối JS
    "--collect-all", "webview",
    # pythonnet (pywebview dùng .NET/WinForms để nhúng WebView2)
    "--collect-all", "pythonnet",
    "--collect-all", "clr_loader",
    "--hidden-import", "clr",
    "--hidden-import", "webview.platforms.edgechromium",
    "--hidden-import", "webview.platforms.winforms",
    # Backend Flask + import nạp trễ
    "--hidden-import", "flask_cors",
    "--hidden-import", "openpyxl",
    "--hidden-import", "xlrd",
]
if os.path.exists(ICON):
    CMD += ["--icon", ICON, "--add-data", f"{ICON}{SEP}."]
CMD.append(os.path.join(ROOT, "desktop_web.py"))

if __name__ == "__main__":
    print("Đang build .exe giao diện web (Chromium/WebView2)... có thể mất vài phút")
    subprocess.run(CMD, cwd=ROOT, check=True)
    exe = os.path.join(ROOT, "dist", "QuanLyMayThanWeb.exe")
    print(f"\n✓ Xong: {exe}" if os.path.exists(exe) else "\n⚠️  Không thấy exe — xem log ở trên.")
