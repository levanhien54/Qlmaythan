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
import socket
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


def _free_port() -> int:
    """Xin một cổng TCP trống trên localhost (tránh đụng cổng 5000/đang dùng)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


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
    port = _free_port()

    def _serve():
        # threaded: phục vụ song song; tắt reloader/debug trong bản đóng gói
        app.run(host='127.0.0.1', port=port, threaded=True, use_reloader=False, debug=False)

    threading.Thread(target=_serve, daemon=True).start()
    _wait_until_up(port)

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
