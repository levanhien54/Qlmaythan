# -*- coding: utf-8 -*-
"""Sao lưu CSDL thủ công / theo lịch.

Chạy:
  python scripts/backup_db.py

Lập lịch hằng ngày:
  - Windows: Task Scheduler → action `python D:\\QL may than\\scripts\\backup_db.py`
  - Linux/macOS: cron `0 1 * * * cd /path && python scripts/backup_db.py`
"""
import sys
import os
import io

if (sys.platform == 'win32' and sys.stdout is not None and hasattr(sys.stdout, 'buffer')
        and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.backup import backup_database
from config import BACKUP_KEEP

if __name__ == "__main__":
    dest = backup_database()
    if dest:
        print(f"✓ Đã sao lưu: {dest}")
        print(f"  (giữ {BACKUP_KEEP} bản gần nhất)")
    else:
        print("⚠️  Không có DB để sao lưu.")
