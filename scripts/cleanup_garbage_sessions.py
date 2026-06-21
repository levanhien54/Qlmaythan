# -*- coding: utf-8 -*-
"""Xóa phiên 'rác' trong DB production — bản ghi KHÔNG có danh tính bệnh nhân.

Tiêu chí RÁC (CHỈ dựa trên họ tên — KHÔNG xóa theo ngày):
  - ho_ten NULL, '' hoặc length(trim) < 2

⚠️ KHÔNG còn coi 'ngay_bat_dau NULL' là rác: một bệnh nhân THẬT có thể bị thiếu
ngày do ô Excel không parse được (xem import_data.parse_datetime_xls). Xóa theo
ngày sẽ huỷ hồ sơ y tế hợp lệ. Hãy sửa ngày cho các phiên đó thay vì xóa.

Mặc định dry-run. Chạy:
  python scripts/cleanup_garbage_sessions.py          # xem
  python scripts/cleanup_garbage_sessions.py --apply  # thực thi (có hỏi xác nhận)
"""
import argparse
import os
import sys
import io
import shutil
from datetime import datetime

if sys.platform == 'win32' and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from config import DB_PATH


def find_garbage():
    # CHỈ xóa phiên không có danh tính bệnh nhân (họ tên rỗng/quá ngắn).
    # KHÔNG lọc theo ngay_bat_dau để tránh huỷ hồ sơ thật bị thiếu ngày.
    return db.fetch_all("""
        SELECT id, ho_ten, ngay_bat_dau, ngay_ket_thuc, thiet_bi_id
        FROM phien_dieu_tri
        WHERE ho_ten IS NULL
           OR length(trim(ho_ten)) < 2
    """)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()

    rows = find_garbage()
    if not rows:
        print("✓ Không có phiên rác.")
        return

    print(f"Tìm thấy {len(rows)} phiên rác:")
    for r in rows:
        print(f"  id={r['id']}  ho_ten={r['ho_ten']!r}  "
              f"bắt đầu={r['ngay_bat_dau']!r}  tb={r['thiet_bi_id']}")

    if not args.apply:
        print("\n[DRY-RUN] Dùng --apply để xóa.")
        return

    # Xác nhận trước thao tác không thể hoàn tác — CHỈ khi chạy tương tác (TTY).
    # Khi chạy tự động/CI (stdin không phải TTY) thì --apply thực thi luôn.
    if sys.stdin.isatty():
        confirm = input(f"\n⚠️  Xóa vĩnh viễn {len(rows)} phiên trên? Gõ 'yes' để tiếp tục: ")
        if confirm.strip().lower() != 'yes':
            print("Đã huỷ.")
            return

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = f"{DB_PATH}.bak_{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"\n✓ Backup: {bak}")

    ids = [r['id'] for r in rows]
    placeholders = ','.join('?' * len(ids))
    db.execute(f"DELETE FROM phien_dieu_tri WHERE id IN ({placeholders})",
               tuple(ids))
    print(f"✓ Đã xóa {len(ids)} phiên rác.")


if __name__ == "__main__":
    main()
