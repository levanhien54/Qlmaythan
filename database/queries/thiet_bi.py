# -*- coding: utf-8 -*-
"""
CRUD queries cho bảng thiet_bi.
"""
from database.connection import db
from database import audit


def get_all(search: str = "", tinh_trang: str = "",
            model: str = "", hang_sx: str = "",
            from_date: str = "", to_date: str = "",
            limit: int = 0, offset: int = 0) -> list:
    """Lấy danh sách thiết bị với filter, lọc theo ngày hoạt động, phân trang."""
    # Build so_phien subquery with optional date filter
    phien_conditions = "p.thiet_bi_id = tb.id"
    sub_params = []
    if from_date:
        phien_conditions += " AND DATE(p.ngay_bat_dau) >= ?"
        sub_params.append(from_date)
    if to_date:
        phien_conditions += " AND DATE(p.ngay_bat_dau) <= ?"
        sub_params.append(to_date)

    query = f"""
        SELECT tb.*, nv.ho_ten AS nguoi_quan_ly_ten,
               (SELECT COUNT(*) FROM phien_dieu_tri p WHERE {phien_conditions}) AS so_phien
        FROM thiet_bi tb
        LEFT JOIN nhan_vien nv ON tb.nguoi_quan_ly_id = nv.id
        WHERE 1=1
    """
    params = list(sub_params)

    if search:
        query += " AND (tb.ten_thiet_bi LIKE ? OR tb.so_may LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if tinh_trang:
        query += " AND tb.tinh_trang LIKE ?"
        params.append(f"%{tinh_trang}%")

    if model:
        query += " AND tb.model = ?"
        params.append(model)

    if hang_sx:
        query += " AND tb.hang_san_xuat = ?"
        params.append(hang_sx)

    query += " ORDER BY tb.id"
    if limit > 0:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    return db.fetch_all(query, tuple(params))


def get_by_id(tb_id: int) -> dict | None:
    """Lấy thiết bị theo ID."""
    return db.fetch_one("""
        SELECT tb.*, nv.ho_ten AS nguoi_quan_ly_ten,
               (SELECT COUNT(*) FROM phien_dieu_tri p WHERE p.thiet_bi_id = tb.id) AS so_phien
        FROM thiet_bi tb
        LEFT JOIN nhan_vien nv ON tb.nguoi_quan_ly_id = nv.id
        WHERE tb.id = ?
    """, (tb_id,))


def create(ten_thiet_bi: str, model: str = "", hang_san_xuat: str = "",
           nuoc_san_xuat: str = "", so_may: str = "",
           nam_su_dung: int = 0, tinh_trang: str = "Hoạt động bình thường",
           tan_suat_su_dung: int = 0,
           nguoi_quan_ly_id: int = None) -> int:
    """Thêm thiết bị mới."""
    cursor = db.execute("""
        INSERT INTO thiet_bi
        (ten_thiet_bi, model, hang_san_xuat, nuoc_san_xuat, so_may,
         nam_su_dung, tinh_trang, tan_suat_su_dung, nguoi_quan_ly_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ten_thiet_bi, model, hang_san_xuat, nuoc_san_xuat, so_may,
          nam_su_dung, tinh_trang, tan_suat_su_dung, nguoi_quan_ly_id))
    audit.record('create', 'thiet_bi', cursor.lastrowid, {
        'ten_thiet_bi': ten_thiet_bi, 'model': model, 'tinh_trang': tinh_trang,
    })
    return cursor.lastrowid


# Các cột được phép cập nhật qua update() — chặn SQL injection / mass-assignment
# vì tên cột được nội suy thẳng vào câu lệnh SET. Key lạ (vd 'ghi_chu' từ form,
# hoặc payload độc hại) bị loại bỏ thay vì ghi vào SQL.
_UPDATABLE_COLS = {
    "ten_thiet_bi", "model", "hang_san_xuat", "nuoc_san_xuat", "so_may",
    "nam_su_dung", "tinh_trang", "tan_suat_su_dung", "nguoi_quan_ly_id",
}


def update(tb_id: int, **kwargs):
    """Cập nhật thiết bị theo các trường được truyền vào (chỉ cột hợp lệ)."""
    kwargs = {k: v for k, v in kwargs.items() if k in _UPDATABLE_COLS}
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    set_clause += ", updated_at = CURRENT_TIMESTAMP"
    values = list(kwargs.values()) + [tb_id]
    db.execute(
        f"UPDATE thiet_bi SET {set_clause} WHERE id = ?",
        tuple(values),
    )
    audit.record('update', 'thiet_bi', tb_id, kwargs)


class DeviceHasHistoryError(Exception):
    """Thiết bị còn lịch sử bảo dưỡng/bàn giao — chặn xóa để tránh CASCADE
    xóa mất các bản ghi đó (an toàn dữ liệu y tế)."""


def delete(tb_id: int):
    """Xóa thiết bị. Raise DeviceHasHistoryError nếu còn phiếu bảo dưỡng hoặc
    bàn giao (vì FK ON DELETE CASCADE sẽ xóa luôn các bản ghi này)."""
    bd = db.fetch_one(
        "SELECT COUNT(*) AS c FROM bao_duong WHERE thiet_bi_id = ?", (tb_id,)
    )["c"]
    bg = db.fetch_one(
        "SELECT COUNT(*) AS c FROM ban_giao WHERE thiet_bi_id = ?", (tb_id,)
    )["c"]
    if bd or bg:
        raise DeviceHasHistoryError(
            f"Thiết bị còn {bd} phiếu bảo dưỡng và {bg} phiếu bàn giao. "
            f"Xóa sẽ mất toàn bộ lịch sử này — hãy xử lý các bản ghi đó trước."
        )
    snap = db.fetch_one("SELECT * FROM thiet_bi WHERE id = ?", (tb_id,))
    if snap:
        audit.record('delete', 'thiet_bi', tb_id, snap)  # snapshot để khôi phục
    db.execute("DELETE FROM thiet_bi WHERE id = ?", (tb_id,))


def get_models() -> list:
    """Lấy danh sách model (distinct)."""
    rows = db.fetch_all(
        "SELECT DISTINCT model FROM thiet_bi WHERE model != '' ORDER BY model"
    )
    return [r["model"] for r in rows]


def get_hang_sx() -> list:
    """Lấy danh sách hãng SX (distinct)."""
    rows = db.fetch_all(
        "SELECT DISTINCT hang_san_xuat FROM thiet_bi WHERE hang_san_xuat != '' ORDER BY hang_san_xuat"
    )
    return [r["hang_san_xuat"] for r in rows]


def count_by_tinh_trang() -> dict:
    """Đếm thiết bị theo tình trạng.
    Key trả về: 'Hoạt động', 'Báo lỗi', 'Hỏng', 'Đang bảo dưỡng', 'Đã thanh lý', 'Khác'.
    """
    rows = db.fetch_all("""
        SELECT
            CASE
                WHEN LOWER(tinh_trang) LIKE '%thanh lý%' OR LOWER(tinh_trang) LIKE '%thanh ly%'
                    THEN 'Đã thanh lý'
                WHEN LOWER(tinh_trang) LIKE '%bảo dưỡng%' OR LOWER(tinh_trang) LIKE '%bao duong%'
                    THEN 'Đang bảo dưỡng'
                WHEN LOWER(tinh_trang) LIKE '%hỏng%'
                    THEN 'Hỏng'
                WHEN LOWER(tinh_trang) LIKE '%lỗi%' OR LOWER(tinh_trang) LIKE '%nghỉ%'
                    THEN 'Báo lỗi'
                WHEN LOWER(tinh_trang) LIKE '%bình thường%' OR LOWER(tinh_trang) LIKE '%bt%'
                    OR LOWER(tinh_trang) LIKE '%hoạt động%'
                    THEN 'Hoạt động'
                ELSE 'Khác'
            END AS nhom,
            COUNT(*) AS so_luong
        FROM thiet_bi
        GROUP BY nhom
    """)
    return {r["nhom"]: r["so_luong"] for r in rows}


def count_by_tan_suat() -> dict:
    """Đếm thiết bị theo tần suất sử dụng."""
    rows = db.fetch_all("""
        SELECT tan_suat_su_dung, COUNT(*) AS so_luong
        FROM thiet_bi
        GROUP BY tan_suat_su_dung
        ORDER BY tan_suat_su_dung
    """)
    return {r["tan_suat_su_dung"]: r["so_luong"] for r in rows}


def count() -> int:
    """Đếm tổng số thiết bị."""
    row = db.fetch_one("SELECT COUNT(*) as total FROM thiet_bi")
    return row["total"] if row else 0


def find_by_name(name: str) -> dict | None:
    """Tìm thiết bị theo tên (tìm gần đúng)."""
    return db.fetch_one(
        "SELECT * FROM thiet_bi WHERE ten_thiet_bi LIKE ?",
        (f"%{name}%",),
    )
