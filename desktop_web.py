# -*- coding: utf-8 -*-
"""
Đóng gói GIAO DIỆN WEB (Flask + thư mục web/) trong một cửa sổ Chromium
(WebView2/Edge) thành ứng dụng desktop một-file.

Cách hoạt động: chạy server Flask nội bộ trên một cổng tự do của 127.0.0.1
trong luồng nền, rồi mở cửa sổ pywebview trỏ vào địa chỉ đó. Người dùng thấy
y hệt bản web nhưng là một cửa sổ ứng dụng, không cần trình duyệt.

Build:  python scripts/build_web_exe.py  →  dist/QuanLyMayThanWeb.exe
Dữ liệu (DB, backup, log) tạo CẠNH file exe (config.py xử lý sys.frozen).
KHÔNG đóng gói dữ liệu bệnh nhân.
"""
import sys
import io
import os
import threading
import time


# stdout/stderr là None ở bản build --windowed (không console) → bọc an toàn để
# bất kỳ print nào cũng không gây 'NoneType has no attribute buffer'.
if sys.platform == 'win32':
    for _n in ('stdout', 'stderr'):
        _s = getattr(sys, _n, None)
        if _s is not None and hasattr(_s, 'buffer') and getattr(_s, 'encoding', '').lower() != 'utf-8':
            try:
                setattr(sys, _n, io.TextIOWrapper(_s.buffer, encoding='utf-8', errors='replace'))
            except Exception:
                pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _fatal(msg: str):
    """Hiện hộp thoại lỗi gốc của Windows (không cần console) rồi thoát êm — để
    người dùng thấy LÝ DO thay vì cửa sổ trắng / app im lặng."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, 'Quản lý Máy Chạy Thận', 0x10)
    except Exception:
        print(msg)


def _wait_until_up(port: int, timeout: float = 20.0) -> bool:
    """Chờ server Flask sẵn sàng trả lời trước khi mở cửa sổ."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def main():
    # 1) Đảm bảo schema + sao lưu khi khởi động (DB nằm cạnh exe qua config.frozen)
    from database.models import create_all_tables
    from database.backup import safe_backup_on_startup
    create_all_tables()
    safe_backup_on_startup()

    # 2) Chạy Flask nội bộ trong luồng nền
    from server import app
    # Bind server vào cổng TỰ DO (port 0) ngay trong LUỒNG CHÍNH: hệ điều hành cấp
    # một cổng trống và GIỮ socket — không có khe hở TOCTOU như kiểu "xin cổng →
    # đóng → bind lại". Lỗi bind (hiếm) nổi ngay tại đây để xử lý, thay vì chết
    # âm thầm trong luồng nền rồi mở ra cửa sổ trắng.
    from werkzeug.serving import make_server
    try:
        srv = make_server('127.0.0.1', 0, app, threaded=True)
    except OSError as e:
        _fatal(f'Không khởi động được server nội bộ:\n{e}')
        return
    port = srv.server_port

    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if not _wait_until_up(port):
        _fatal('Server nội bộ không phản hồi sau khi khởi động. Vui lòng thử lại.')
        return

    # 3) Mở cửa sổ Chromium (Windows: tự dùng EdgeChromium/WebView2)
    import webview
    from config import APP_NAME, APP_VERSION
    webview.create_window(
        f'{APP_NAME} v{APP_VERSION}',
        f'http://127.0.0.1:{port}',
        width=1320, height=880, min_size=(1024, 700),
    )
    webview.start()


if __name__ == '__main__':
    main()
