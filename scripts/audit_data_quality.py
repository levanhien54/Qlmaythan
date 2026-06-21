# -*- coding: utf-8 -*-
"""Audit toàn diện data quality DB production.

Báo cáo:
  1. Staff fragmentation — cùng 1 người nhưng có nhiều record (VD 'Bs. X' và 'X')
  2. Phiên không gắn máy (thiet_bi_id IS NULL) — match Excel thất bại
  3. Phiên không gắn PTV chính — có thể nhập thiếu
  4. Tuổi ngoài phạm vi bất thường
  5. Ngày kết thúc < bắt đầu
  6. Phiên có thời lượng bất thường (<10 phút hoặc >12 giờ)
  7. Khoảng trống ID (có thể bằng chứng phiên đã bị xóa)
  8. Orphan references (thiet_bi_id trỏ vào máy không tồn tại)
"""
import os
import sys
import io

if sys.platform == 'win32' and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db


def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def audit_staff_fragmentation():
    """Tên nhân viên gần giống nhau → có thể fragmentation."""
    section("1. STAFF FRAGMENTATION")
    rows = db.fetch_all("SELECT id, ho_ten, chuc_vu_trinh_do FROM nhan_vien ORDER BY ho_ten")
    # So từng cặp: normalize (lower, strip title) rồi check substring
    import re
    def norm(s):
        s = s.lower().strip()
        s = re.sub(r'^(ths\.?bs\.?|bsckii\.?|bscki\.?|ths\.?|bs\.?|ts\.?|cn\.?)\s*', '', s).strip()
        return s

    normalized = [(r['id'], r['ho_ten'], norm(r['ho_ten'])) for r in rows]
    flagged = []
    for i, (id1, name1, norm1) in enumerate(normalized):
        for id2, name2, norm2 in normalized[i+1:]:
            if norm1 and norm2 and (norm1 == norm2 or norm1 in norm2 or norm2 in norm1):
                flagged.append((id1, name1, id2, name2))
    if not flagged:
        print("✓ Không thấy staff fragmentation.")
    else:
        print(f"⚠️  {len(flagged)} cặp tên trùng/gần trùng:")
        for a_id, a, b_id, b in flagged:
            print(f"  [{a_id}] {a!r}  ↔  [{b_id}] {b!r}")


def audit_orphan_sessions():
    section("2. PHIÊN KHÔNG GẮN MÁY (thiet_bi_id IS NULL)")
    rows = db.fetch_all("""
        SELECT id, ho_ten, may_thuc_hien, ngay_bat_dau
        FROM phien_dieu_tri
        WHERE thiet_bi_id IS NULL
        ORDER BY ngay_bat_dau
    """)
    if not rows:
        print(f"✓ Tất cả phiên đều có máy.")
    else:
        print(f"⚠️  {len(rows)} phiên mồ côi:")
        for r in rows[:20]:
            print(f"  id={r['id']} {r['ho_ten']!r} @ {r['ngay_bat_dau']} — may={r['may_thuc_hien']!r}")


def audit_no_ptv():
    section("3. PHIÊN KHÔNG CÓ PTV CHÍNH")
    rows = db.fetch_all("""
        SELECT id, ho_ten, ngay_bat_dau FROM phien_dieu_tri
        WHERE ptv_chinh_id IS NULL
    """)
    print(f"Có {len(rows)} phiên không ghi PTV chính"
          f" ({len(rows)*100//max(db.fetch_one('SELECT COUNT(*) c FROM phien_dieu_tri')['c'], 1)}%)")


def audit_age_outliers():
    section("4. TUỔI BẤT THƯỜNG")
    rows = db.fetch_all("""
        SELECT id, ho_ten, tuoi FROM phien_dieu_tri
        WHERE tuoi < 0 OR tuoi > 120
    """)
    if not rows:
        print("✓ Tuổi trong phạm vi hợp lệ.")
    else:
        print(f"⚠️  {len(rows)} phiên có tuổi bất thường:")
        for r in rows[:10]:
            print(f"  id={r['id']} {r['ho_ten']!r} tuoi={r['tuoi']}")


def audit_date_inversion():
    section("5. NGÀY KẾT THÚC < NGÀY BẮT ĐẦU")
    rows = db.fetch_all("""
        SELECT id, ho_ten, ngay_bat_dau, ngay_ket_thuc FROM phien_dieu_tri
        WHERE ngay_ket_thuc IS NOT NULL
          AND ngay_ket_thuc <= ngay_bat_dau
    """)
    if not rows:
        print("✓ Không có phiên ngược ngày.")
    else:
        print(f"🔴 {len(rows)} phiên có ngày KT ≤ BĐ:")
        for r in rows:
            print(f"  id={r['id']} {r['ho_ten']!r}: {r['ngay_bat_dau']} → {r['ngay_ket_thuc']}")


def audit_session_duration():
    section("6. THỜI LƯỢNG PHIÊN BẤT THƯỜNG")
    rows = db.fetch_all("""
        SELECT id, ho_ten, ngay_bat_dau, ngay_ket_thuc,
               CAST((julianday(ngay_ket_thuc) - julianday(ngay_bat_dau)) * 24 * 60 AS INTEGER) AS phut
        FROM phien_dieu_tri
        WHERE ngay_ket_thuc IS NOT NULL
    """)
    too_short = [r for r in rows if r['phut'] is not None and r['phut'] < 10]
    too_long = [r for r in rows if r['phut'] is not None and r['phut'] > 720]
    if not too_short and not too_long:
        print("✓ Thời lượng hợp lý (10 phút – 12 giờ).")
    if too_short:
        print(f"⚠️  {len(too_short)} phiên <10 phút:")
        for r in too_short[:5]:
            print(f"  id={r['id']} {r['ho_ten']!r} {r['phut']} phút")
    if too_long:
        print(f"⚠️  {len(too_long)} phiên >12 giờ:")
        for r in too_long[:5]:
            print(f"  id={r['id']} {r['ho_ten']!r} {r['phut']} phút")


def audit_orphan_fk():
    section("7. FOREIGN KEY ORPHAN (máy/NV bị xóa nhưng phiên vẫn trỏ)")
    orphan_tb = db.fetch_all("""
        SELECT p.id, p.ho_ten, p.thiet_bi_id FROM phien_dieu_tri p
        LEFT JOIN thiet_bi tb ON p.thiet_bi_id = tb.id
        WHERE p.thiet_bi_id IS NOT NULL AND tb.id IS NULL
    """)
    orphan_nv = db.fetch_all("""
        SELECT p.id, p.ho_ten, p.ptv_chinh_id FROM phien_dieu_tri p
        LEFT JOIN nhan_vien nv ON p.ptv_chinh_id = nv.id
        WHERE p.ptv_chinh_id IS NOT NULL AND nv.id IS NULL
    """)
    print(f"Phiên orphan thiết bị: {len(orphan_tb)}")
    print(f"Phiên orphan PTV chính: {len(orphan_nv)}")


if __name__ == "__main__":
    audit_staff_fragmentation()
    audit_orphan_sessions()
    audit_no_ptv()
    audit_age_outliers()
    audit_date_inversion()
    audit_session_duration()
    audit_orphan_fk()
