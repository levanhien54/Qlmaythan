# -*- coding: utf-8 -*-
"""Regression tests cho các lỗi tìm thấy trong đợt review toàn dự án.

Khoá hành vi đúng cho các fix nghiêm trọng nhất:
  - #1 update() chống SQL injection / mass-assignment (whitelist cột)
  - #2 find_device khớp SỐ chính xác (không gán phiên sai máy)
  - #4 bộ lọc bảo dưỡng theo ngày bao gồm cả phiếu có giờ
"""
import pytest

from matching import find_device
from database.queries import thiet_bi, bao_duong


# ---------- #2 find_device: số đơn KHÔNG khớp số nhiều chữ số ----------

def test_find_device_single_digit_not_matching_multidigit():
    """'F1' phải khớp 'số 1', KHÔNG khớp nhầm 'số 10' (dù 'số 10' đứng trước)."""
    devices = [
        # Cố ý đặt 'số 10' TRƯỚC để bắt lỗi 'pick first' của code cũ.
        (10, "Máy thận Fresinius số 10", "", "Hoạt động bình thường"),
        (1, "Máy thận Fresinius số 1", "", "Hoạt động bình thường"),
    ]
    id_, ten, _ = find_device("F1", devices)
    assert id_ == 1, f"Phải khớp 'số 1' (id=1), nhưng nhận id={id_} ({ten})"


def test_find_device_two_digit_exact():
    """'F10' phải khớp đúng 'số 10', không phải 'số 1'."""
    devices = [
        (1, "Máy thận Fresinius số 1", "", "Hoạt động bình thường"),
        (10, "Máy thận Fresinius số 10", "", "Hoạt động bình thường"),
    ]
    id_, _, _ = find_device("F10", devices)
    assert id_ == 10


def test_find_device_leading_zero_matches():
    """'F09' (đệm 0) phải khớp 'số 9'."""
    devices = [
        (9, "Máy thận Fresinius số 9", "", "Hoạt động bình thường"),
        (10, "Máy thận Fresinius số 10", "", "Hoạt động bình thường"),
    ]
    id_, _, _ = find_device("F09", devices)
    assert id_ == 9


# ---------- #1 update(): whitelist cột ----------

def test_update_ignores_unknown_column(temp_db):
    """Key lạ (không phải cột) bị bỏ qua, không gây lỗi SQL."""
    tid = thiet_bi.create(ten_thiet_bi="Máy X", tinh_trang="Hoạt động bình thường")
    # 'ghi_chu' KHÔNG phải cột của thiet_bi (trước đây gây 'no such column').
    thiet_bi.update(tid, tinh_trang="Hỏng", ghi_chu="bậy", khong_ton_tai=123)
    row = thiet_bi.get_by_id(tid)
    assert row["tinh_trang"] == "Hỏng"          # cột hợp lệ vẫn cập nhật
    assert "ghi_chu" not in row                   # cột lạ không được tạo


def test_update_injection_key_is_neutralized(temp_db):
    """Key chứa SQL không phá được bảng (bị whitelist loại bỏ)."""
    tid = thiet_bi.create(ten_thiet_bi="Máy Y")
    before = thiet_bi.count()
    # Payload độc hại: nếu key được nội suy thẳng vào SQL sẽ hỏng/đổi nhiều dòng.
    thiet_bi.update(tid, **{"tinh_trang = 'x' WHERE 1=1 --": "boom"})
    # Bảng còn nguyên, không bị xoá/đổi hàng loạt.
    assert thiet_bi.count() == before
    assert thiet_bi.get_by_id(tid) is not None


def test_update_only_whitelisted_no_op(temp_db):
    """Chỉ truyền key lạ → update là no-op, không raise."""
    tid = thiet_bi.create(ten_thiet_bi="Máy Z", tinh_trang="Hoạt động bình thường")
    thiet_bi.update(tid, hacker="x")  # không có cột hợp lệ nào
    assert thiet_bi.get_by_id(tid)["tinh_trang"] == "Hoạt động bình thường"


# ---------- #4 bộ lọc bảo dưỡng theo ngày (có giờ) ----------

def test_maintenance_date_filter_includes_time_component(temp_db):
    """Phiếu lưu 'YYYY-MM-DD HH:MM' vẫn lọt bộ lọc to_date = chính ngày đó."""
    tid = thiet_bi.create(ten_thiet_bi="Máy BD")
    bao_duong.create(thiet_bi_id=tid, loai="Sửa chữa",
                     ngay_thuc_hien="2026-04-01 14:30")
    rows = bao_duong.get_all(from_date="2026-04-01", to_date="2026-04-01")
    assert len(rows) == 1, "Phiếu có giờ phải xuất hiện trong bộ lọc cùng ngày"
