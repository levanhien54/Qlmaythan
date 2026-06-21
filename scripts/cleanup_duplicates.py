# -*- coding: utf-8 -*-
"""Xóa phiên trùng trong DB production. MẶC ĐỊNH dry-run.

Logic: trong mỗi nhóm (thiet_bi_id, ngay_bat_dau) giữ lại row có id nhỏ nhất,
xóa các row id lớn hơn.

Chạy:
  python scripts/cleanup_duplicates.py              # dry-run (chỉ in)
  python scripts/cleanup_duplicates.py --apply      # thực thi xóa
⚠️  BACKUP file data/ql_may_than.db trước khi --apply!
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


def find_dup_groups():
    return db.fetch_all("""
        SELECT thiet_bi_id, ngay_bat_dau,
               MIN(id) AS keep_id,
               GROUP_CONCAT(id) AS all_ids,
               COUNT(*) AS n
        FROM phien_dieu_tri
        WHERE thiet_bi_id IS NOT NULL
          AND ngay_bat_dau IS NOT NULL
        GROUP BY thiet_bi_id, ngay_bat_dau
        HAVING n > 1
    """)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Thực thi xóa (mặc định dry-run)')
    args = p.parse_args()

    groups = find_dup_groups()
    if not groups:
        print("✓ Không có phiên trùng.")
        return

    to_delete = []
    for g in groups:
        ids = [int(x) for x in g['all_ids'].split(',')]
        keep = g['keep_id']
        delete_ids = [i for i in ids if i != keep]
        to_delete.extend(delete_ids)
        print(f"tb={g['thiet_bi_id']} @ {g['ngay_bat_dau']}: "
              f"giữ {keep}, xóa {delete_ids}")

    print(f"\nTổng: {len(to_delete)} phiên sẽ bị xóa "
          f"(từ {len(groups)} nhóm duplicate).")

    if not args.apply:
        print("\n[DRY-RUN] Dùng --apply để thực thi.")
        return

    # Backup
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = f"{DB_PATH}.bak_{ts}"
    shutil.copy2(DB_PATH, bak)
    print(f"\n✓ Backup: {bak}")

    placeholders = ','.join('?' * len(to_delete))
    db.execute(f"DELETE FROM phien_dieu_tri WHERE id IN ({placeholders})",
               tuple(to_delete))
    print(f"✓ Đã xóa {len(to_delete)} phiên trùng.")


if __name__ == "__main__":
    main()
