# -*- coding: utf-8 -*-
"""Tests column mapping — header-based indexing, resilient to layout drift."""
import io
import pytest
import openpyxl
from matching import (
    find_header_row, build_column_mapping, DEFAULT_COLUMN_LAYOUT,
)
from database.queries import thiet_bi, nhan_vien, phien_dieu_tri
from tests.test_excel_import_e2e import build_xlsx, make_row, post_excel


# ---------- Pure function: find_header_row ----------

def test_find_header_row_tt():
    rows = [
        [''] * 5,
        [''] * 5,
        ['TT', 'Họ và tên', 'Tuổi', 'Địa chỉ'],
        [''] * 5,
    ]
    assert find_header_row(rows) == 2


def test_find_header_row_ho_va_ten_only():
    rows = [[''] * 5] * 3 + [['', 'Họ và tên', '', '']]
    assert find_header_row(rows) == 3


def test_find_header_row_fallback():
    """Không tìm thấy → fallback default=9."""
    rows = [['random']] * 20
    assert find_header_row(rows, default=9) == 9


def test_find_header_row_case_insensitive_nfc():
    """HEADER uppercase + NFD vẫn detect được."""
    import unicodedata
    rows = [[''] * 3, [unicodedata.normalize('NFD', 'Họ Và Tên'), 'xxx', '']]
    assert find_header_row(rows) == 1


# ---------- build_column_mapping ----------

def test_build_column_mapping_default_layout():
    rows = [[''] * 29] * 9
    rows.append(['TT', 'Họ và tên', 'Tuổi', '', 'Địa chỉ', 'Số hồ sơ',
                 '', '', 'Ngày bắt đầu', 'Ngày kết thúc'] + [''] * 19)
    sub = [''] * 29
    sub[2] = 'Nam'
    sub[3] = 'Nữ'
    sub[18] = 'PTV chính'
    sub[19] = 'Phụ 1'
    rows.append(sub)
    # Data
    rows[10][28] = ''  # placeholder
    row_with_may = [''] * 29
    row_with_may[28] = 'Máy thực hiện'
    rows[9][28] = 'Máy thực hiện'  # header col 28
    m = build_column_mapping(rows, 9)
    assert m['ho_ten'] == 1
    assert m['tuoi_nam'] == 2
    assert m['tuoi_nu'] == 3
    assert m['ngay_bat_dau'] == 8
    assert m['ngay_ket_thuc'] == 9
    assert m['ptv_chinh'] == 18
    assert m['phu_1'] == 19
    assert m['may'] == 28


def test_build_column_mapping_shifted_right():
    """Cột 'Họ và tên' bị đẩy từ index 1 sang 2 — mapping phải follow."""
    rows = [[''] * 30] * 9
    header = [''] * 30
    header[2] = 'Họ và tên'   # shifted
    header[9] = 'Ngày bắt đầu'
    header[29] = 'Máy thực hiện'
    rows.append(header)
    rows.append([''] * 30)  # sub
    m = build_column_mapping(rows, 9)
    assert m['ho_ten'] == 2
    assert m['ngay_bat_dau'] == 9
    assert m['may'] == 29


def test_build_column_mapping_fallback_when_not_detected():
    """Header row không có keyword → trả về default."""
    rows = [['abc'] * 29] * 12
    m = build_column_mapping(rows, 9)
    assert m == DEFAULT_COLUMN_LAYOUT


# ---------- E2E: import file với layout khác ----------

@pytest.fixture
def client_basic(temp_db):
    thiet_bi.create(ten_thiet_bi='Máy chạy thận Fresinius số 1',
                    tinh_trang='Hoạt động bình thường')
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def _build_xlsx_custom_layout(data_row, header_layout):
    """Tạo xlsx với layout tùy chỉnh.
    header_layout: dict {logical_name: col_idx}.
    data_row: dict {logical_name: value}.
    """
    wb = openpyxl.Workbook()
    sh = wb.active
    max_col = max(header_layout.values()) + 1
    for _ in range(9):
        sh.append([''] * max_col)
    header = [''] * max_col
    sub = [''] * max_col
    labels = {
        'stt': 'TT', 'ho_ten': 'Họ và tên',
        'tuoi_nam': 'Nam', 'tuoi_nu': 'Nữ',
        'dia_chi': 'Địa chỉ', 'so_ho_so': 'Số hồ sơ',
        'ngay_bat_dau': 'Ngày bắt đầu', 'ngay_ket_thuc': 'Ngày kết thúc',
        'ptv_chinh': 'PTV chính', 'phu_1': 'Phụ 1',
        'ghi_chu': 'Ghi chú', 'may': 'Máy thực hiện',
    }
    for name, idx in header_layout.items():
        # Some labels go on sub-row (Nam/Nữ/PTV/Phụ) trong file chuẩn,
        # nhưng để test đơn giản tôi đặt hết lên header row.
        header[idx] = labels[name]
    sh.append(header)
    sh.append(sub)
    row = [''] * max_col
    for name, val in data_row.items():
        row[header_layout[name]] = val
    sh.append(row)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf


def test_import_with_shifted_columns_works(client_basic):
    """File với header shift 1 cột phải: [2]=họ tên, [9]=ngày BĐ, [29]=máy."""
    layout = {
        'stt': 1, 'ho_ten': 2, 'tuoi_nam': 3, 'tuoi_nu': 4,
        'dia_chi': 5, 'so_ho_so': 6,
        'ngay_bat_dau': 9, 'ngay_ket_thuc': 10,
        'ptv_chinh': 19, 'phu_1': 20,
        'ghi_chu': 26, 'may': 29,
    }
    data = {
        'stt': 1, 'ho_ten': 'BN Shifted',
        'ngay_bat_dau': '2026-04-01 08:00:00',
        'ngay_ket_thuc': '2026-04-01 12:00:00',
        'may': 'Máy chạy thận Fresinius số 1',
    }
    buf = _build_xlsx_custom_layout(data, layout)
    d = post_excel(client_basic, buf, 'shifted.xlsx').get_json()
    assert d['success'] == 1
    rows = phien_dieu_tri.get_all(search='BN Shifted')
    assert len(rows) == 1


def test_import_with_reordered_columns(client_basic):
    """Thay đổi hoán vị: máy ở col 3, họ tên ở col 10."""
    layout = {
        'stt': 0, 'may': 3, 'ho_ten': 10,
        'tuoi_nam': 11, 'tuoi_nu': 12,
        'dia_chi': 13, 'so_ho_so': 14,
        'ngay_bat_dau': 15, 'ngay_ket_thuc': 16,
        'ptv_chinh': 20, 'phu_1': 21,
        'ghi_chu': 22,
    }
    data = {
        'stt': 1, 'ho_ten': 'BN Reordered',
        'ngay_bat_dau': '2026-04-01 08:00:00',
        'ngay_ket_thuc': '2026-04-01 12:00:00',
        'may': 'Máy chạy thận Fresinius số 1',
    }
    buf = _build_xlsx_custom_layout(data, layout)
    d = post_excel(client_basic, buf, 'reorder.xlsx').get_json()
    assert d['success'] == 1


def test_import_fallback_to_default_when_no_header(client_basic):
    """Không có header keyword → default layout (compat với file cũ)."""
    buf = build_xlsx([make_row(
        ho_ten='BN Default',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy chạy thận Fresinius số 1',
    )])
    d = post_excel(client_basic, buf).get_json()
    assert d['success'] == 1
