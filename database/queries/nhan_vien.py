# -*- coding: utf-8 -*-
"""
CRUD queries cho bảng nhan_vien.
"""
from database.connection import db


def get_all(search: str = "", chuc_vu: str = "",
            limit: int = 0, offset: int = 0) -> list:
    """Lấy danh sách nhân viên, hỗ trợ tìm kiếm, lọc, phân trang."""
    query = "SELECT * FROM nhan_vien WHERE 1=1"
    params = []

    if search:
        query += " AND ho_ten LIKE ?"
        params.append(f"%{search}%")

    if chuc_vu:
        query += " AND chuc_vu_trinh_do = ?"
        params.append(chuc_vu)

    query += " ORDER BY ho_ten"
    if limit > 0:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    return db.fetch_all(query, tuple(params))


def get_by_id(nv_id: int) -> dict | None:
    """Lấy nhân viên theo ID."""
    return db.fetch_one("SELECT * FROM nhan_vien WHERE id = ?", (nv_id,))


def create(ho_ten: str, chuc_vu_trinh_do: str) -> int:
    """Thêm nhân viên mới. Trả về ID."""
    cursor = db.execute(
        "INSERT INTO nhan_vien (ho_ten, chuc_vu_trinh_do) VALUES (?, ?)",
        (ho_ten, chuc_vu_trinh_do),
    )
    return cursor.lastrowid


# Cột hợp lệ cho update() — chặn SQL injection / mass-assignment qua key JSON.
_UPDATABLE_COLS = {"ho_ten", "chuc_vu_trinh_do"}


def update(nv_id: int, **kwargs):
    """Cập nhật nhân viên. Chỉ sửa các field hợp lệ được truyền vào."""
    kwargs = {k: v for k, v in kwargs.items() if k in _UPDATABLE_COLS}
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [nv_id]
    db.execute(
        f"UPDATE nhan_vien SET {set_clause} WHERE id = ?",
        tuple(values),
    )


def delete(nv_id: int):
    """Xóa nhân viên."""
    db.execute("DELETE FROM nhan_vien WHERE id = ?", (nv_id,))


def get_or_create(ho_ten: str, chuc_vu_trinh_do: str = "") -> int:
    """Lấy ID nhân viên theo tên, tạo mới nếu chưa có."""
    ho_ten = ho_ten.strip()
    if not ho_ten:
        return None
    row = db.fetch_one(
        "SELECT id FROM nhan_vien WHERE ho_ten = ?", (ho_ten,)
    )
    if row:
        return row["id"]
    return create(ho_ten, chuc_vu_trinh_do)


def count() -> int:
    """Đếm tổng số nhân viên."""
    row = db.fetch_one("SELECT COUNT(*) as total FROM nhan_vien")
    return row["total"] if row else 0
