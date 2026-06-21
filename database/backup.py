# -*- coding: utf-8 -*-
"""
Sao lưu CSDL SQLite an toàn (online backup API — đúng cả khi đang ghi/WAL),
kèm xoay vòng giữ N bản gần nhất.

Dùng bởi:
  - server.py / main.py: tự sao lưu khi khởi động.
  - scripts/backup_db.py: chạy thủ công hoặc lập lịch (Task Scheduler / cron).
"""
import os
import glob
import sqlite3
from datetime import datetime

from config import DB_PATH, BACKUP_DIR, BACKUP_KEEP

_PREFIX = "ql_may_than_"


def backup_database(db_path: str = DB_PATH, backups_dir: str = BACKUP_DIR,
                    keep: int = BACKUP_KEEP) -> str | None:
    """Tạo 1 bản sao lưu DB vào backups_dir (tên có timestamp), giữ `keep` bản
    mới nhất. Trả đường dẫn file backup, hoặc None nếu DB chưa tồn tại.

    Dùng sqlite3 online backup (conn.backup) — an toàn kể cả khi DB đang mở/WAL,
    khác với copy file thô có thể bắt trạng thái dở.
    """
    if not os.path.exists(db_path):
        return None
    os.makedirs(backups_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backups_dir, f"{_PREFIX}{ts}.db")
    # Tránh ghi đè nếu cùng giây (đặt thêm hậu tố).
    n = 1
    while os.path.exists(dest):
        dest = os.path.join(backups_dir, f"{_PREFIX}{ts}_{n}.db")
        n += 1

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()

    _rotate(backups_dir, keep)
    return dest


def _rotate(backups_dir: str, keep: int) -> None:
    """Xoá các bản sao lưu cũ, chỉ giữ `keep` bản mới nhất (theo tên = thời gian)."""
    if keep is None or keep <= 0:
        return
    files = sorted(glob.glob(os.path.join(backups_dir, f"{_PREFIX}*.db")))
    for old in files[:-keep]:
        try:
            os.remove(old)
        except OSError:
            pass


def safe_backup_on_startup() -> str | None:
    """Sao lưu khi khởi động, KHÔNG bao giờ làm hỏng việc khởi động nếu lỗi."""
    try:
        return backup_database()
    except Exception as e:  # noqa: BLE001 — backup hỏng không được chặn app chạy
        print(f"[Backup] ⚠️  Không sao lưu được: {e}")
        return None
