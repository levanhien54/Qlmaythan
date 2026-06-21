# -*- coding: utf-8 -*-
"""Đóng gói ứng dụng DESKTOP (main.py, PyQt6) thành 1 file .exe độc lập.

Chạy:
  python scripts/build_exe.py

Kết quả: dist/QuanLyMayThan.exe — chạy độc lập, không cần cài Python.
Dữ liệu (DB, backups, log) tạo CẠNH file exe lúc chạy (config.py xử lý sys.frozen).
KHÔNG đóng gói file Excel dữ liệu bệnh nhân.
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON = os.path.join(ROOT, "icon.ico")

CMD = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",            # gói thành 1 file .exe duy nhất
    "--windowed",           # app GUI → không hiện cửa sổ console
    "--noconfirm", "--clean",
    "--name", "QuanLyMayThan",
    # Các import nạp trễ (lazy) — khai báo rõ để PyInstaller không bỏ sót
    "--hidden-import", "openpyxl",
    "--hidden-import", "xlrd",
    "--hidden-import", "import_data",
    "--hidden-import", "excel_import",
]
# Icon cho file .exe + đóng gói icon.ico để app set icon cửa sổ/taskbar lúc chạy
if os.path.exists(ICON):
    CMD += ["--icon", ICON, "--add-data", f"{ICON}{os.pathsep}."]
CMD.append(os.path.join(ROOT, "main.py"))

if __name__ == "__main__":
    print("Đang build .exe... (PyQt6 có thể mất vài phút)")
    subprocess.run(CMD, cwd=ROOT, check=True)
    exe = os.path.join(ROOT, "dist", "QuanLyMayThan.exe")
    print(f"\n✓ Xong: {exe}" if os.path.exists(exe) else "\n⚠️  Không thấy file exe — xem log ở trên.")
