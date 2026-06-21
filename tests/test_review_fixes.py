# -*- coding: utf-8 -*-
"""Regression tests cho các lỗi tìm thấy trong đợt review toàn dự án.

Khoá hành vi đúng cho các fix nghiêm trọng nhất:
  - #1 update() chống SQL injection / mass-assignment (whitelist cột)
  - #2 find_device khớp SỐ chính xác (không gán phiên sai máy)
  - #4 bộ lọc bảo dưỡng theo ngày bao gồm cả phiếu có giờ
"""
import pytest

from matching import find_device, parse_excel_datetime, find_staff
from database.queries import thiet_bi, bao_duong, phien_dieu_tri, ban_giao


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


def test_find_staff_prefix_not_mismatched():
    """'Lê Văn A' KHÔNG được gán nhầm 'Lê Văn An' (token cuối khác) — khớp
    chuỗi-con phải theo ranh giới từ."""
    staff = [{'id': 1, 'ho_ten': 'Lê Văn An'}]
    assert find_staff('Lê Văn A', staff)[0] == -1   # mơ hồ/sai → loại
    assert find_staff('Lê Văn An', staff)[0] == 1   # đúng tên đầy đủ → khớp


def test_find_device_ambiguous_returns_none_not_guess():
    """2 máy cùng SỐ + cùng keyword → MƠ HỒ: phải trả None, KHÔNG đoán bừa
    (pick-first cũ gán phiên sai máy âm thầm)."""
    devices = [
        (1, "Máy chạy thận B.Braun số 3", "", "Hoạt động bình thường"),
        (2, "Máy chạy thận B.Braun HDF số 3", "", "Hoạt động bình thường"),
    ]
    id_, raw, tt = find_device("Số 3", devices)
    assert id_ is None, f"Phải mơ hồ (None), không gán bừa; nhận id={id_}"


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


# ---------- R2 sessions_per_machine: gom theo thiet_bi_id ----------

def test_sessions_per_machine_groups_by_device_not_text(temp_db):
    """Cùng 1 máy (thiet_bi_id) nhưng may_thuc_hien khác chữ / rỗng → 1 nhóm."""
    tid = thiet_bi.create(ten_thiet_bi="Máy số 1")
    phien_dieu_tri.create(ho_ten="BN A", thiet_bi_id=tid, may_thuc_hien="Máy số 1",
                          ngay_bat_dau="2026-04-01 08:00:00")
    phien_dieu_tri.create(ho_ten="BN B", thiet_bi_id=tid, may_thuc_hien="May 1",
                          ngay_bat_dau="2026-04-02 08:00:00")
    phien_dieu_tri.create(ho_ten="BN C", thiet_bi_id=tid, may_thuc_hien="",
                          ngay_bat_dau="2026-04-03 08:00:00")
    rows = phien_dieu_tri.sessions_per_machine()
    assert len(rows) == 1, "3 phiên cùng máy phải gom 1 nhóm, không tách theo chữ"
    assert rows[0]["so_phien"] == 3
    assert rows[0]["may_thuc_hien"] == "Máy số 1"  # nhãn = tên thiết bị


def test_sessions_per_machine_unmatched_kept_by_text(temp_db):
    """Phiên chưa map máy (thiet_bi_id NULL) vẫn được gom theo may_thuc_hien."""
    phien_dieu_tri.create(ho_ten="BN X", thiet_bi_id=None, may_thuc_hien="Máy lạ",
                          ngay_bat_dau="2026-04-01 08:00:00")
    rows = phien_dieu_tri.sessions_per_machine()
    assert any(r["may_thuc_hien"] == "Máy lạ" and r["so_phien"] == 1 for r in rows)


# ---------- R7 check_duplicates: so khớp theo NGÀY kể cả khi lưu kèm giờ ----------

def test_check_duplicates_matches_datetime_stored_value(temp_db):
    """Bàn giao lưu '2026-04-01 08:00:00' vẫn bị bắt trùng khi nhập ngày '2026-04-01'."""
    tid = thiet_bi.create(ten_thiet_bi="Máy A")
    ban_giao.create(thiet_bi_id=tid, ngay_ban_giao="2026-04-01 08:00:00")
    dups = ban_giao.check_duplicates([tid], "2026-04-01")
    assert len(dups) == 1


# ---------- R8 _validate_session_payload: tuoi dạng chuỗi không gây 500 ----------

def test_validate_payload_string_age_no_crash():
    from server import _validate_session_payload
    base = {"ho_ten": "Nguyễn Văn A", "ngay_bat_dau": "2026-04-01 08:00:00"}
    # chuỗi số hợp lệ → OK
    assert _validate_session_payload({**base, "tuoi": "50"}) is None
    # chuỗi ngoài phạm vi → lỗi 400, KHÔNG raise TypeError
    err = _validate_session_payload({**base, "tuoi": "200"})
    assert err and err[1] == 400
    # chuỗi không phải số → lỗi 400
    err = _validate_session_payload({**base, "tuoi": "abc"})
    assert err and err[1] == 400


# ---------- D5 parse_excel_datetime: nhận ngày trước 2009, loại số nhỏ ----------

def test_parse_excel_serial_accepts_pre_2009_date():
    """Serial 38353 = 2005-01-01: trước đây ngưỡng >40000 làm rớt thành None."""
    r = parse_excel_datetime(38353, xls_datemode=0)
    assert r is not None and r.startswith("2005-01-01")


def test_parse_excel_serial_rejects_small_numbers():
    """Số nhỏ (vd tuổi 65) trong cột ngày KHÔNG bị hiểu nhầm thành ngày 1900."""
    assert parse_excel_datetime(65, xls_datemode=0) is None
    assert parse_excel_datetime(0, xls_datemode=0) is None
