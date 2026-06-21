# -*- coding: utf-8 -*-
"""
Quan ly May Chay Than — Entry Point
"""
import sys
import io
import os

def _fix_console_encoding():
    """Bọc stdout/stderr về UTF-8 để in tiếng Việt.

    AN TOÀN khi stdout/stderr là None: bản .exe build --windowed (không console)
    có sys.stdout/sys.stderr = None → truy cập .buffer sẽ crash ngay khi mở app.
    """
    if sys.platform != 'win32':
        return
    for name in ('stdout', 'stderr'):
        stream = getattr(sys, name, None)
        if (stream is not None and hasattr(stream, 'buffer')
                and getattr(stream, 'encoding', '').lower() != 'utf-8'):
            try:
                setattr(sys, name, io.TextIOWrapper(stream.buffer, encoding='utf-8', errors='replace'))
            except Exception:
                pass


_fix_console_encoding()

# Ensure correct path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon

from database.models import create_all_tables
from ui.main_window import MainWindow


def resource_path(rel: str) -> str:
    """Đường dẫn tài nguyên đóng gói — chạy được cả khi build .exe (PyInstaller
    giải nén vào sys._MEIPASS) lẫn khi chạy mã nguồn."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def create_splash() -> QSplashScreen:
    """Tạo splash screen trong khi load dữ liệu."""
    pixmap = QPixmap(500, 300)
    pixmap.fill(QColor("#1a1a2e"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(QColor("#e94560"))
    painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter,
                     "⚕️ Quản lý Máy Chạy Thận\nĐang tải dữ liệu...")

    painter.setPen(QColor("#8892b0"))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(pixmap.rect().adjusted(0, 0, 0, -20),
                     Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                     "Bệnh viện Đa khoa Bắc Ninh Số 2 — v1.0.0")
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
    return splash


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 12))

    # Icon ứng dụng (cửa sổ + taskbar). AppUserModelID giúp Windows hiện đúng
    # icon trên taskbar thay vì icon Python mặc định.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("QuanLyMayThan.v1")
        except Exception:
            pass
    _icon = resource_path("icon.ico")
    if os.path.exists(_icon):
        app.setWindowIcon(QIcon(_icon))

    # Show splash screen
    splash = create_splash()
    splash.show()
    app.processEvents()

    # Sao lưu DB hiện có trước khi tạo bảng/migration (an toàn nếu có sự cố)
    try:
        from database.backup import safe_backup_on_startup
        safe_backup_on_startup()
    except Exception as e:
        print(f"[Backup] {e}")
    app.processEvents()

    # Create DB tables
    create_all_tables()
    app.processEvents()

    # Import data (first run only)
    try:
        from import_data import run_import
        run_import()
    except Exception as e:
        print(f"[Import] Error: {e}")
    app.processEvents()

    # Create and show main window
    window = MainWindow()
    window.show()

    # Close splash after window is shown
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
