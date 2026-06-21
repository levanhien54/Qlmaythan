# -*- coding: utf-8 -*-
"""
CRUD queries cho bảng phien_dieu_tri.
"""
from database.connection import db


def get_all(from_date: str = "", to_date: str = "",
            thiet_bi_id: int = None, ptv_chinh_id: int = None,
            search: str = "", limit: int = 0, offset: int = 0) -> list:
    """Lấy danh sách phiên điều trị với filter và phân trang."""
    query = """
        SELECT pdt.*,
               tb.ten_thiet_bi,
               nv1.ho_ten AS ptv_chinh_ten,
               nv2.ho_ten AS phu_1_ten
        FROM phien_dieu_tri pdt
        LEFT JOIN thiet_bi tb ON pdt.thiet_bi_id = tb.id
        LEFT JOIN nhan_vien nv1 ON pdt.ptv_chinh_id = nv1.id
        LEFT JOIN nhan_vien nv2 ON pdt.phu_1_id = nv2.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (pdt.ho_ten LIKE ? OR pdt.so_ho_so LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if from_date:
        query += " AND DATE(pdt.ngay_bat_dau) >= ?"
        params.append(from_date)

    if to_date:
        query += " AND DATE(pdt.ngay_bat_dau) <= ?"
        params.append(to_date)

    if thiet_bi_id:
        query += " AND pdt.thiet_bi_id = ?"
        params.append(thiet_bi_id)

    if ptv_chinh_id:
        query += " AND pdt.ptv_chinh_id = ?"
        params.append(ptv_chinh_id)

    query += " ORDER BY pdt.ngay_bat_dau DESC"
    if limit > 0:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    return db.fetch_all(query, tuple(params))


def get_by_id(pdt_id: int) -> dict | None:
    """Lấy phiên theo ID."""
    return db.fetch_one("""
        SELECT pdt.*,
               tb.ten_thiet_bi,
               nv1.ho_ten AS ptv_chinh_ten,
               nv2.ho_ten AS phu_1_ten
        FROM phien_dieu_tri pdt
        LEFT JOIN thiet_bi tb ON pdt.thiet_bi_id = tb.id
        LEFT JOIN nhan_vien nv1 ON pdt.ptv_chinh_id = nv1.id
        LEFT JOIN nhan_vien nv2 ON pdt.phu_1_id = nv2.id
        WHERE pdt.id = ?
    """, (pdt_id,))


def check_time_overlap(thiet_bi_id: int, ngay_bat_dau: str,
                        ngay_ket_thuc: str = None, exclude_id: int = None) -> dict | None:
    """Check if a session overlaps with existing sessions on the same device.
    Returns the conflicting session or None."""
    if not thiet_bi_id or not ngay_bat_dau:
        return None

    # Build query: find sessions on same device that overlap the given time range
    # Overlap logic: new_start < existing_end AND new_end > existing_start
    # When ngay_ket_thuc is NULL, treat as "still in progress" (use far-future date)
    query = """
        SELECT pdt.id, pdt.ho_ten, pdt.ngay_bat_dau, pdt.ngay_ket_thuc
        FROM phien_dieu_tri pdt
        WHERE pdt.thiet_bi_id = ?
          AND ? < COALESCE(pdt.ngay_ket_thuc, '9999-12-31 23:59:59')
          AND COALESCE(?, '9999-12-31 23:59:59') > pdt.ngay_bat_dau
    """
    params = [thiet_bi_id, ngay_bat_dau, ngay_ket_thuc]

    if exclude_id:
        query += " AND pdt.id != ?"
        params.append(exclude_id)

    query += " LIMIT 1"
    return db.fetch_one(query, tuple(params))


class DuplicateSessionError(Exception):
    """UNIQUE(thiet_bi_id, ngay_bat_dau) violation — race-condition guard."""


def create(ho_ten: str, may_thuc_hien: str = "",
           thiet_bi_id: int = None, tuoi: int = 0,
           dia_chi: str = "", so_ho_so: str = "",
           ngay_bat_dau: str = None, ngay_ket_thuc: str = None,
           ptv_chinh_id: int = None, phu_1_id: int = None,
           ghi_chu: str = "") -> int:
    """Thêm phiên điều trị mới.

    Raise DuplicateSessionError nếu vi phạm UNIQUE(thiet_bi_id, ngay_bat_dau) —
    xảy ra khi race condition concurrent import cùng phiên.
    """
    import sqlite3
    try:
        cursor = db.execute("""
            INSERT INTO phien_dieu_tri
            (thiet_bi_id, may_thuc_hien, ho_ten, tuoi, dia_chi, so_ho_so,
             ngay_bat_dau, ngay_ket_thuc, ptv_chinh_id, phu_1_id, ghi_chu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (thiet_bi_id, may_thuc_hien, ho_ten, tuoi, dia_chi, so_ho_so,
              ngay_bat_dau, ngay_ket_thuc, ptv_chinh_id, phu_1_id, ghi_chu))
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        if 'UNIQUE' in str(e) or 'ux_phien_tb_bd' in str(e):
            raise DuplicateSessionError(
                f'Phiên trùng: máy {thiet_bi_id} @ {ngay_bat_dau}'
            ) from e
        raise


# Cột hợp lệ cho update() — chặn SQL injection / mass-assignment qua key JSON.
_UPDATABLE_COLS = {
    "thiet_bi_id", "may_thuc_hien", "ho_ten", "tuoi", "dia_chi", "so_ho_so",
    "ngay_bat_dau", "ngay_ket_thuc", "ptv_chinh_id", "phu_1_id", "ghi_chu",
}


def update(pdt_id: int, **kwargs):
    """Cập nhật phiên điều trị (chỉ cột hợp lệ)."""
    kwargs = {k: v for k, v in kwargs.items() if k in _UPDATABLE_COLS}
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [pdt_id]
    db.execute(
        f"UPDATE phien_dieu_tri SET {set_clause} WHERE id = ?",
        tuple(values),
    )


def delete(pdt_id: int):
    """Xóa phiên điều trị."""
    db.execute("DELETE FROM phien_dieu_tri WHERE id = ?", (pdt_id,))


def count() -> int:
    """Đếm tổng số phiên."""
    row = db.fetch_one("SELECT COUNT(*) as total FROM phien_dieu_tri")
    return row["total"] if row else 0


def count_unmatched() -> int:
    """Đếm phiên CHƯA gán được máy (thiet_bi_id NULL) — dữ liệu import không
    khớp tên thiết bị; các phiên này bị bỏ khỏi thống kê theo máy."""
    row = db.fetch_one(
        "SELECT COUNT(*) AS total FROM phien_dieu_tri WHERE thiet_bi_id IS NULL"
    )
    return row["total"] if row else 0


def count_today() -> int:
    """Đếm số phiên hôm nay (theo giờ ĐỊA PHƯƠNG, không phải UTC).
    date('now') của SQLite trả ngày UTC → lệch tới 7h ở VN (UTC+7); dùng
    'localtime' để 'hôm nay' khớp lịch người dùng."""
    row = db.fetch_one("""
        SELECT COUNT(*) as total FROM phien_dieu_tri
        WHERE date(ngay_bat_dau) = date('now', 'localtime')
    """)
    return row["total"] if row else 0


def sessions_per_machine() -> list:
    """Số phiên theo máy.

    Gom theo thiet_bi_id (join tên thiết bị) để KHÔNG bị tách nhỏ vì biến thể
    chữ của may_thuc_hien (vd 'Máy 1' vs 'May 1'), và để KHÔNG bỏ sót phiên
    import có thiet_bi_id nhưng may_thuc_hien rỗng. Phiên chưa map được máy
    (thiet_bi_id NULL) gom theo chính chuỗi may_thuc_hien.
    Khóa hiển thị giữ tên 'may_thuc_hien' để tương thích caller cũ.
    """
    return db.fetch_all("""
        SELECT COALESCE(tb.ten_thiet_bi, p.may_thuc_hien) AS may_thuc_hien,
               COUNT(*) AS so_phien
        FROM phien_dieu_tri p
        LEFT JOIN thiet_bi tb ON p.thiet_bi_id = tb.id
        WHERE COALESCE(tb.ten_thiet_bi, p.may_thuc_hien) != ''
        GROUP BY COALESCE(p.thiet_bi_id, p.may_thuc_hien)
        ORDER BY so_phien DESC
    """)


def sessions_per_day(from_date: str = "", to_date: str = "") -> list:
    """Số phiên theo ngày."""
    query = """
        SELECT date(ngay_bat_dau) AS ngay, COUNT(*) AS so_phien
        FROM phien_dieu_tri
        WHERE ngay_bat_dau IS NOT NULL
    """
    params = []
    if from_date:
        query += " AND DATE(ngay_bat_dau) >= ?"
        params.append(from_date)
    if to_date:
        query += " AND DATE(ngay_bat_dau) <= ?"
        params.append(to_date)
    query += " GROUP BY ngay ORDER BY ngay"
    return db.fetch_all(query, tuple(params))
