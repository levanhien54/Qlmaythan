# -*- coding: utf-8 -*-
"""
CRUD queries cho bảng bao_duong.
"""
from database.connection import db


def get_all(thiet_bi_id: int = None, loai: str = "",
            trang_thai: str = "", from_date: str = "",
            to_date: str = "", limit: int = 0, offset: int = 0) -> list:
    """Lấy danh sách bảo dưỡng với filter và phân trang."""
    query = """
        SELECT bd.*, tb.ten_thiet_bi, nv.ho_ten AS nguoi_thuc_hien_ten
        FROM bao_duong bd
        LEFT JOIN thiet_bi tb ON bd.thiet_bi_id = tb.id
        LEFT JOIN nhan_vien nv ON bd.nguoi_thuc_hien_id = nv.id
        WHERE 1=1
    """
    params = []

    if thiet_bi_id:
        query += " AND bd.thiet_bi_id = ?"
        params.append(thiet_bi_id)

    if loai:
        query += " AND bd.loai = ?"
        params.append(loai)

    if trang_thai:
        query += " AND bd.trang_thai = ?"
        params.append(trang_thai)

    if from_date:
        # DATE() bỏ phần giờ — phiếu lưu 'YYYY-MM-DD HH:MM' vẫn lọt bộ lọc theo ngày.
        query += " AND DATE(bd.ngay_thuc_hien) >= ?"
        params.append(from_date)

    if to_date:
        query += " AND DATE(bd.ngay_thuc_hien) <= ?"
        params.append(to_date)

    query += " ORDER BY bd.ngay_thuc_hien DESC"
    if limit > 0:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    return db.fetch_all(query, tuple(params))


def get_by_id(bd_id: int) -> dict | None:
    """Lấy bảo dưỡng theo ID."""
    return db.fetch_one("""
        SELECT bd.*, tb.ten_thiet_bi, nv.ho_ten AS nguoi_thuc_hien_ten
        FROM bao_duong bd
        LEFT JOIN thiet_bi tb ON bd.thiet_bi_id = tb.id
        LEFT JOIN nhan_vien nv ON bd.nguoi_thuc_hien_id = nv.id
        WHERE bd.id = ?
    """, (bd_id,))


def create(thiet_bi_id: int, loai: str, ngay_thuc_hien: str,
           nguoi_thuc_hien_id: int = None,
           ngay_du_kien_tiep_theo: str = None,
           mo_ta: str = "", chi_phi: float = 0,
           trang_thai: str = "Chờ xử lý") -> int:
    """Thêm phiếu bảo dưỡng mới."""
    cursor = db.execute("""
        INSERT INTO bao_duong
        (thiet_bi_id, nguoi_thuc_hien_id, loai, ngay_thuc_hien,
         ngay_du_kien_tiep_theo, mo_ta, chi_phi, trang_thai)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (thiet_bi_id, nguoi_thuc_hien_id, loai, ngay_thuc_hien,
          ngay_du_kien_tiep_theo, mo_ta, chi_phi, trang_thai))
    return cursor.lastrowid


# Cột hợp lệ cho update() — chặn SQL injection / mass-assignment qua key JSON.
_UPDATABLE_COLS = {
    "thiet_bi_id", "nguoi_thuc_hien_id", "loai", "ngay_thuc_hien",
    "ngay_du_kien_tiep_theo", "mo_ta", "chi_phi", "trang_thai",
}


def update(bd_id: int, **kwargs):
    """Cập nhật phiếu bảo dưỡng (chỉ cột hợp lệ)."""
    kwargs = {k: v for k, v in kwargs.items() if k in _UPDATABLE_COLS}
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [bd_id]
    db.execute(
        f"UPDATE bao_duong SET {set_clause} WHERE id = ?",
        tuple(values),
    )


def delete(bd_id: int):
    """Xóa phiếu bảo dưỡng."""
    db.execute("DELETE FROM bao_duong WHERE id = ?", (bd_id,))


def get_upcoming(days: int = 7) -> list:
    """Lấy danh sách bảo dưỡng sắp đến hạn."""
    return db.fetch_all("""
        SELECT bd.*, tb.ten_thiet_bi
        FROM bao_duong bd
        LEFT JOIN thiet_bi tb ON bd.thiet_bi_id = tb.id
        WHERE bd.ngay_du_kien_tiep_theo IS NOT NULL
          AND bd.ngay_du_kien_tiep_theo <= date('now', '+' || ? || ' days')
          AND bd.ngay_du_kien_tiep_theo >= date('now')
        ORDER BY bd.ngay_du_kien_tiep_theo
    """, (days,))


def total_chi_phi(from_date: str = "", to_date: str = "") -> float:
    """Tổng chi phí bảo dưỡng."""
    query = "SELECT COALESCE(SUM(chi_phi), 0) AS total FROM bao_duong WHERE 1=1"
    params = []
    if from_date:
        query += " AND DATE(ngay_thuc_hien) >= ?"
        params.append(from_date)
    if to_date:
        query += " AND DATE(ngay_thuc_hien) <= ?"
        params.append(to_date)
    row = db.fetch_one(query, tuple(params))
    return row["total"] if row else 0


def count() -> int:
    """Đếm tổng số phiếu bảo dưỡng."""
    row = db.fetch_one("SELECT COUNT(*) as total FROM bao_duong")
    return row["total"] if row else 0
