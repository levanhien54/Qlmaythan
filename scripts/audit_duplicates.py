# -*- coding: utf-8 -*-
"""Audit DB production tìm phiên điều trị bị duplicate.

Xuất ra list các nhóm phiên trùng (cùng thiet_bi_id + ngay_bat_dau).
Chạy: python scripts/audit_duplicates.py
"""
import os
import sys
import io

if sys.platform == 'win32' and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db


def find_exact_duplicates():
    """Phiên cùng thiet_bi_id + ngay_bat_dau (bản ghi bị insert lặp)."""
    return db.fetch_all("""
        SELECT thiet_bi_id, ngay_bat_dau,
               COUNT(*) AS n,
               GROUP_CONCAT(id) AS ids,
               GROUP_CONCAT(ho_ten, ' | ') AS names
        FROM phien_dieu_tri
        WHERE thiet_bi_id IS NOT NULL
          AND ngay_bat_dau IS NOT NULL
        GROUP BY thiet_bi_id, ngay_bat_dau
        HAVING n > 1
        ORDER BY thiet_bi_id, ngay_bat_dau
    """)


def find_overlapping_sessions():
    """Phiên khác ID nhưng khoảng giờ chồng lấn trên cùng máy."""
    return db.fetch_all("""
        SELECT a.id AS id_a, a.ho_ten AS name_a, a.ngay_bat_dau AS start_a, a.ngay_ket_thuc AS end_a,
               b.id AS id_b, b.ho_ten AS name_b, b.ngay_bat_dau AS start_b, b.ngay_ket_thuc AS end_b,
               a.thiet_bi_id
        FROM phien_dieu_tri a
        JOIN phien_dieu_tri b
          ON a.thiet_bi_id = b.thiet_bi_id
         AND a.id < b.id
         AND a.ngay_bat_dau < COALESCE(b.ngay_ket_thuc, '9999-12-31 23:59:59')
         AND COALESCE(a.ngay_ket_thuc, '9999-12-31 23:59:59') > b.ngay_bat_dau
        WHERE a.ngay_bat_dau IS NOT NULL
          AND b.ngay_bat_dau IS NOT NULL
        ORDER BY a.thiet_bi_id, a.ngay_bat_dau
    """)


def main():
    print("=" * 60)
    print("AUDIT: DUPLICATE SESSIONS")
    print("=" * 60)
    dups = find_exact_duplicates()
    if not dups:
        print("✓ Không có phiên cùng (thiet_bi_id, ngay_bat_dau) bị trùng.")
    else:
        print(f"⚠️  {len(dups)} nhóm phiên trùng tuyệt đối:")
        for d in dups:
            print(f"  tb={d['thiet_bi_id']} @ {d['ngay_bat_dau']}  "
                  f"n={d['n']}  ids={d['ids']}")
            print(f"    BN: {d['names']}")

    print()
    print("=" * 60)
    print("AUDIT: OVERLAPPING SESSIONS (cùng máy, trùng thời gian)")
    print("=" * 60)
    overlaps = find_overlapping_sessions()
    if not overlaps:
        print("✓ Không có phiên chồng lấn thời gian trên cùng máy.")
    else:
        print(f"⚠️  {len(overlaps)} cặp phiên chồng lấn:")
        for o in overlaps:
            print(f"  tb={o['thiet_bi_id']}")
            print(f"    [{o['id_a']}] {o['name_a']:30s} {o['start_a']} → {o['end_a']}")
            print(f"    [{o['id_b']}] {o['name_b']:30s} {o['start_b']} → {o['end_b']}")

    print()
    print("=" * 60)
    print("Gợi ý: xóa phiên trùng bằng")
    print("  DELETE FROM phien_dieu_tri WHERE id IN (<id cần xóa>)")
    print("⚠️  BACKUP file data/ql_may_than.db trước khi xóa!")


if __name__ == "__main__":
    main()
