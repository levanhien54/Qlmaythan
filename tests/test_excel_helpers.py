# -*- coding: utf-8 -*-
"""Tests cho parse_excel_datetime, check_session_overlap, is_device_blocked."""
import datetime as dt
import pytest
from matching import (
    parse_excel_datetime,
    check_session_overlap,
    is_device_blocked,
    safe_str,
)


# ---------- safe_str ----------

@pytest.mark.parametrize("raw,expected", [
    (None, ''),
    ('', ''),
    ('   ', ''),
    ('  hello  ', 'hello'),
    ('line1\nline2', 'line1 line2'),
    ('line1\r\nline2', 'line1 line2'),
    (123, '123'),
    (12.5, '12.5'),
])
def test_safe_str(raw, expected):
    assert safe_str(raw) == expected


# ---------- parse_excel_datetime ----------

def test_parse_dt_from_python_datetime():
    v = dt.datetime(2026, 4, 21, 15, 30, 0)
    assert parse_excel_datetime(v) == '2026-04-21 15:30:00'


def test_parse_dt_from_python_date():
    v = dt.date(2026, 4, 21)
    assert parse_excel_datetime(v) == '2026-04-21 00:00:00'


@pytest.mark.parametrize("raw,expected", [
    ('21/04/2026',              '2026-04-21 00:00:00'),
    ('21/04/2026 08:00',        '2026-04-21 08:00:00'),
    ('21/04/2026 08:00:00',     '2026-04-21 08:00:00'),
    ('2026-04-21',              '2026-04-21 00:00:00'),
    ('2026-04-21 08:00:00',     '2026-04-21 08:00:00'),
    ('21-04-2026',              '2026-04-21 00:00:00'),
    ('21.04.2026',              '2026-04-21 00:00:00'),
    ('21.04.2026 08:30',        '2026-04-21 08:30:00'),
    ('  21/04/2026  ',          '2026-04-21 00:00:00'),  # whitespace trim
])
def test_parse_dt_from_string_formats(raw, expected):
    assert parse_excel_datetime(raw) == expected


def test_parse_dt_invalid_string_returns_none():
    assert parse_excel_datetime('abc') is None
    assert parse_excel_datetime('2026/13/45') is None
    assert parse_excel_datetime('not a date') is None


def test_parse_dt_none_and_empty():
    assert parse_excel_datetime(None) is None
    assert parse_excel_datetime('') is None


def test_parse_dt_excel_serial_windows():
    """Excel serial 46127 = 2026-04-15 (Windows datemode=0)."""
    r = parse_excel_datetime(46127.0, xls_datemode=0)
    assert r == '2026-04-15 00:00:00'


def test_parse_dt_excel_serial_mac_differs():
    """Cùng serial, datemode=1 (Mac 1904) phải lệch ~4 năm so Windows."""
    win = parse_excel_datetime(46127.0, xls_datemode=0)
    mac = parse_excel_datetime(46127.0, xls_datemode=1)
    assert win != mac
    assert win.startswith('2026')
    assert mac.startswith('2030')


def test_parse_dt_ignores_bool():
    """`True`/`False` không được nhận nhầm là số serial."""
    assert parse_excel_datetime(True) is None
    assert parse_excel_datetime(False) is None


def test_parse_dt_ignores_small_numbers():
    """Số nhỏ (age, STT, …) không được coi là ngày."""
    assert parse_excel_datetime(42) is None
    assert parse_excel_datetime(1000) is None


# ---------- is_device_blocked ----------

@pytest.mark.parametrize("status,expected", [
    ('Hỏng', True),
    ('hỏng', True),
    ('Máy bị hỏng', True),
    ('Báo lỗi', True),
    ('báo lỗi', True),
    ('Thanh lý', True),
    ('Đã thanh lý', True),   # B1: bug cũ miss chuỗi này → giờ phải True
    ('ĐÃ THANH LÝ', True),
    ('Hoạt động bình thường', False),
    ('Hoạt động', False),
    ('Đang bảo dưỡng', False),   # bảo dưỡng không block
    ('', False),
    (None, False),
])
def test_is_device_blocked(status, expected):
    assert is_device_blocked(status) == expected


# ---------- check_session_overlap ----------

def _s(tb_id, start, end=None, name='BN'):
    return {'thiet_bi_id': tb_id, 'ngay_bat_dau': start,
            'ngay_ket_thuc': end, 'ho_ten': name}


def test_overlap_empty_existing_returns_none():
    assert check_session_overlap(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00', []) is None


def test_overlap_missing_params_returns_none():
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    assert check_session_overlap(None, '2026-04-01 08:00:00', None, existing) is None
    assert check_session_overlap(1, None, None, existing) is None


def test_overlap_exact_same_start_is_duplicate():
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00', 'A')]
    r = check_session_overlap(1, '2026-04-01 08:00:00', '2026-04-01 14:00:00', existing)
    assert r is not None
    assert 'Trùng lặp' in r
    assert 'A' in r


def test_overlap_partial_start_detected():
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    r = check_session_overlap(1, '2026-04-01 10:00:00', '2026-04-01 14:00:00', existing)
    assert r is not None


def test_overlap_partial_end_detected():
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    r = check_session_overlap(1, '2026-04-01 06:00:00', '2026-04-01 10:00:00', existing)
    assert r is not None


def test_overlap_contained_detected():
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    r = check_session_overlap(1, '2026-04-01 09:00:00', '2026-04-01 11:00:00', existing)
    assert r is not None


def test_overlap_back_to_back_ok():
    """Phiên mới bắt đầu đúng lúc phiên cũ kết thúc → không trùng."""
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    r = check_session_overlap(1, '2026-04-01 12:00:00', '2026-04-01 16:00:00', existing)
    assert r is None


def test_overlap_different_device_ok():
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    r = check_session_overlap(2, '2026-04-01 09:00:00', '2026-04-01 11:00:00', existing)
    assert r is None


def test_overlap_both_open_ended_blocked():
    """B2 FIX: 2 phiên mở cùng máy — phải phát hiện trùng."""
    existing = [_s(1, '2026-04-01 08:00:00', None, 'BN cũ')]
    r = check_session_overlap(1, '2026-04-01 09:00:00', None, existing)
    assert r is not None
    assert 'chưa kết thúc' in r or 'BN cũ' in r


def test_overlap_existing_open_new_starts_after():
    """Phiên cũ không đóng, phiên mới bắt đầu sau → vẫn phải chặn."""
    existing = [_s(1, '2026-04-01 08:00:00', None)]
    r = check_session_overlap(1, '2026-04-05 10:00:00', '2026-04-05 12:00:00', existing)
    assert r is not None


def test_overlap_new_open_starts_during_existing():
    """Phiên mới không đóng, bắt đầu giữa phiên cũ → chặn."""
    existing = [_s(1, '2026-04-01 08:00:00', '2026-04-01 12:00:00')]
    r = check_session_overlap(1, '2026-04-01 10:00:00', None, existing)
    assert r is not None
