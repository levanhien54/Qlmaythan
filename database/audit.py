# -*- coding: utf-8 -*-
"""
Nhật ký thao tác (audit) + KHÔI PHỤC bản ghi đã xóa.

Mọi create/update/delete đi qua tầng database.queries.* sẽ gọi record() để ghi
lại (hành động, bảng, id, dữ liệu). delete lưu SNAPSHOT cả dòng → restore() có
thể chèn lại đúng id, khôi phục cả quan hệ khóa ngoại.

Lưu ý: audit_log được ghi trực tiếp (không qua query module) nên KHÔNG tự-đệ-quy.
"""
import json
from database.connection import db

# Chỉ cho phép khôi phục vào các bảng thực thể đã biết (chống SQL injection qua
# tên bảng lưu trong audit_log).
_RESTORABLE = {
    'thiet_bi', 'nhan_vien', 'phien_dieu_tri', 'bao_duong', 'ban_giao',
}


def record(action: str, entity: str, entity_id, data: dict = None) -> None:
    """Ghi một mục nhật ký. data (dict) sẽ được lưu dạng JSON.
    KHÔNG bao giờ làm hỏng thao tác chính nếu ghi log lỗi."""
    try:
        payload = json.dumps(data, ensure_ascii=False, default=str) if data is not None else None
        db.execute(
            "INSERT INTO audit_log (action, entity, entity_id, data) VALUES (?, ?, ?, ?)",
            (action, entity, entity_id, payload),
        )
    except Exception:
        pass  # log lỗi không được chặn nghiệp vụ


def recent(limit: int = 100, entity: str = "", action: str = "") -> list:
    """Liệt kê nhật ký mới nhất (kèm parse data JSON)."""
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if entity:
        query += " AND entity = ?"
        params.append(entity)
    if action:
        query += " AND action = ?"
        params.append(action)
    query += " ORDER BY id DESC"
    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(limit)
    rows = db.fetch_all(query, tuple(params))
    for r in rows:
        try:
            r['data_obj'] = json.loads(r['data']) if r['data'] else None
        except Exception:
            r['data_obj'] = None
    return rows


class RestoreError(Exception):
    """Không khôi phục được (mục không phải delete, bảng lạ, hoặc id đã tồn tại)."""


def restore(audit_id: int) -> int:
    """Khôi phục bản ghi đã xóa từ một mục nhật ký action='delete'.

    Chèn lại đúng id gốc (giữ quan hệ FK). Trả id đã khôi phục.
    Raise RestoreError nếu mục không hợp lệ / bảng lạ / id đã tồn tại lại.
    """
    row = db.fetch_one("SELECT * FROM audit_log WHERE id = ?", (audit_id,))
    if not row:
        raise RestoreError("Không tìm thấy mục nhật ký.")
    if row['action'] != 'delete' or not row['data']:
        raise RestoreError("Mục này không phải bản xóa có dữ liệu để khôi phục.")
    entity = row['entity']
    if entity not in _RESTORABLE:
        raise RestoreError(f"Bảng '{entity}' không hỗ trợ khôi phục.")

    data = json.loads(row['data'])
    rec_id = data.get('id')
    if rec_id is not None:
        existing = db.fetch_one(f"SELECT 1 FROM {entity} WHERE id = ?", (rec_id,))
        if existing:
            raise RestoreError(f"Bản ghi id={rec_id} đã tồn tại (không cần khôi phục).")

    cols = list(data.keys())
    placeholders = ", ".join(["?"] * len(cols))
    collist = ", ".join(cols)
    try:
        db.execute(
            f"INSERT INTO {entity} ({collist}) VALUES ({placeholders})",
            tuple(data[c] for c in cols),
        )
    except Exception as e:
        raise RestoreError(f"Khôi phục thất bại: {e}") from e

    record('restore', entity, rec_id, data)
    return rec_id
