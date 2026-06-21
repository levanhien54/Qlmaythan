# -*- coding: utf-8 -*-
"""
CRUD queries cho bảng ban_giao.
"""
from database.connection import db


def get_all(thiet_bi_id: int = None, nhan_vien_id: int = None,
            from_date: str = "", to_date: str = "",
            limit: int = 0, offset: int = 0) -> list:
    """Lấy danh sách bàn giao với filter, tần suất phiên ĐT, phân trang."""
    query = """
        SELECT bg.*,
               tb.ten_thiet_bi,
               tb.tinh_trang AS tinh_trang_may,
               nv1.ho_ten AS nguoi_giao_ten,
               nv2.ho_ten AS nguoi_nhan_ten,
               (SELECT COUNT(*) FROM phien_dieu_tri pdt WHERE pdt.thiet_bi_id = bg.thiet_bi_id) AS tan_suat
        FROM ban_giao bg
        LEFT JOIN thiet_bi tb ON bg.thiet_bi_id = tb.id
        LEFT JOIN nhan_vien nv1 ON bg.nguoi_giao_id = nv1.id
        LEFT JOIN nhan_vien nv2 ON bg.nguoi_nhan_id = nv2.id
        WHERE 1=1
    """
    params = []

    if thiet_bi_id:
        query += " AND bg.thiet_bi_id = ?"
        params.append(thiet_bi_id)

    if nhan_vien_id:
        query += " AND (bg.nguoi_giao_id = ? OR bg.nguoi_nhan_id = ?)"
        params.extend([nhan_vien_id, nhan_vien_id])

    if from_date:
        query += " AND bg.ngay_ban_giao >= ?"
        params.append(from_date)

    if to_date:
        query += " AND bg.ngay_ban_giao <= ?"
        params.append(to_date)

    query += " ORDER BY bg.ngay_ban_giao DESC"
    if limit > 0:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    return db.fetch_all(query, tuple(params))


def get_by_id(bg_id: int) -> dict | None:
    """Lấy bàn giao theo ID."""
    return db.fetch_one("""
        SELECT bg.*,
               tb.ten_thiet_bi,
               nv1.ho_ten AS nguoi_giao_ten,
               nv2.ho_ten AS nguoi_nhan_ten
        FROM ban_giao bg
        LEFT JOIN thiet_bi tb ON bg.thiet_bi_id = tb.id
        LEFT JOIN nhan_vien nv1 ON bg.nguoi_giao_id = nv1.id
        LEFT JOIN nhan_vien nv2 ON bg.nguoi_nhan_id = nv2.id
        WHERE bg.id = ?
    """, (bg_id,))


def check_duplicates(device_ids: list, ngay: str, exclude_id: int = None) -> list:
    """Kiểm tra thiết bị đã có bàn giao trong ngày. Trả về danh sách trùng."""
    if not device_ids or not ngay:
        return []
    placeholders = ",".join(["?"] * len(device_ids))
    query = f"""
        SELECT DISTINCT bg.thiet_bi_id, tb.ten_thiet_bi
        FROM ban_giao bg
        LEFT JOIN thiet_bi tb ON bg.thiet_bi_id = tb.id
        WHERE bg.thiet_bi_id IN ({placeholders})
          AND bg.ngay_ban_giao = ?
    """
    params = list(device_ids) + [ngay]
    if exclude_id:
        query += " AND bg.id != ?"
        params.append(exclude_id)
    return db.fetch_all(query, tuple(params))


def create(thiet_bi_id: int, nguoi_giao_id: int = None,
           nguoi_nhan_id: int = None, ngay_ban_giao: str = None,
           trang_thai: str = "Đã bàn giao", ghi_chu: str = "") -> int:
    """Thêm phiếu bàn giao mới."""
    cursor = db.execute("""
        INSERT INTO ban_giao
        (thiet_bi_id, nguoi_giao_id, nguoi_nhan_id, ngay_ban_giao, trang_thai, ghi_chu)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (thiet_bi_id, nguoi_giao_id, nguoi_nhan_id, ngay_ban_giao, trang_thai, ghi_chu))
    return cursor.lastrowid


# Cột hợp lệ cho update() — chặn SQL injection / mass-assignment qua key JSON.
_UPDATABLE_COLS = {
    "thiet_bi_id", "nguoi_giao_id", "nguoi_nhan_id",
    "ngay_ban_giao", "trang_thai", "ghi_chu",
}


def update(bg_id: int, **kwargs):
    """Cập nhật phiếu bàn giao (chỉ cột hợp lệ)."""
    kwargs = {k: v for k, v in kwargs.items() if k in _UPDATABLE_COLS}
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [bg_id]
    db.execute(
        f"UPDATE ban_giao SET {set_clause} WHERE id = ?",
        tuple(values),
    )


def delete(bg_id: int):
    """Xóa phiếu bàn giao."""
    db.execute("DELETE FROM ban_giao WHERE id = ?", (bg_id,))


def count() -> int:
    """Đếm tổng số phiếu bàn giao."""
    row = db.fetch_one("SELECT COUNT(*) as total FROM ban_giao")
    return row["total"] if row else 0
