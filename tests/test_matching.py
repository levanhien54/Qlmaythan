# -*- coding: utf-8 -*-
"""Tests cho matching.find_device và find_staff."""
import pytest
from matching import find_device, find_staff, strip_title


# ---------- find_device ----------

def test_find_device_empty_returns_none(sample_devices):
    assert find_device("", sample_devices) == (None, "", None)
    assert find_device(None, sample_devices) == (None, "", None)
    assert find_device("   ", sample_devices) == (None, "", None)


def test_find_device_exact_full_name(sample_devices):
    id_, ten, tt = find_device("Máy thận HDF Fresinius số 1", sample_devices)
    assert id_ == 1
    assert "Fresinius" in ten


def test_find_device_partial_substring(sample_devices):
    """Tên raw là substring của tên DB (sau khi normalize)."""
    id_, ten, _ = find_device("Fresinius số 2", sample_devices)
    assert id_ == 2


def test_find_device_number_suffix_with_keyword(sample_devices):
    """'HDF_01' → match keyword hdf + số 1."""
    id_, ten, _ = find_device("HDF_01", sample_devices)
    assert id_ == 1


def test_find_device_number_suffix_nipro(sample_devices):
    id_, ten, _ = find_device("nipro số 3", sample_devices)
    assert id_ == 3


def test_find_device_braun_number(sample_devices):
    id_, ten, _ = find_device("B.Braun_10", sample_devices)
    assert id_ == 4


def test_find_device_returns_status(sample_devices):
    """Trả về tinh_trang để caller chặn nhập phiên cho máy hỏng."""
    _, _, tt = find_device("NIPRO số 12", sample_devices)
    assert tt == "Hỏng"


def test_find_device_not_found(sample_devices):
    id_, raw, tt = find_device("Máy không tồn tại", sample_devices)
    assert id_ is None
    assert raw == "Máy không tồn tại"
    assert tt is None


def test_find_device_keyword_disambiguates_same_number(sample_devices):
    """Nếu 2 máy cùng số mà khác hãng, keyword phải lọc đúng."""
    devices = [
        (10, "Máy HDF số 5", "", "OK"),
        (11, "Máy NIPRO số 5", "", "OK"),
    ]
    id_, _, _ = find_device("nipro_05", devices)
    assert id_ == 11


# ---------- find_staff ----------

def test_find_staff_empty(sample_staff):
    assert find_staff("", sample_staff) == (None, None)
    assert find_staff(None, sample_staff) == (None, None)


def test_find_staff_exact(sample_staff):
    id_, _ = find_staff("Nguyễn Văn A", sample_staff)
    assert id_ == 1


def test_find_staff_case_insensitive(sample_staff):
    id_, _ = find_staff("nguyễn văn a", sample_staff)
    assert id_ == 1


def test_find_staff_strip_title(sample_staff):
    """Nhập 'Lê Văn C' phải match 'BS. Lê Văn C'."""
    id_, matched = find_staff("Lê Văn C", sample_staff)
    assert id_ == 3


def test_find_staff_with_title_matches_plain_db(sample_staff):
    staff = [{"id": 99, "ho_ten": "Nguyễn Văn X"}]
    id_, _ = find_staff("BS. Nguyễn Văn X", staff)
    assert id_ == 99


def test_find_staff_not_found(sample_staff):
    id_, raw = find_staff("Người lạ", sample_staff)
    assert id_ == -1
    assert raw == "Người lạ"


# ---------- strip_title ----------

@pytest.mark.parametrize("raw,expected", [
    ("BS. Nguyễn", "nguyễn"),
    ("ThS.BS. Phạm", "phạm"),
    ("TS. Trần", "trần"),
    ("CN. Lê", "lê"),
    ("BSCKI. Hoàng", "hoàng"),
    ("BSCKII. Vũ", "vũ"),
    ("Nguyễn Văn A", "nguyễn văn a"),
])
def test_strip_title(raw, expected):
    assert strip_title(raw) == expected
