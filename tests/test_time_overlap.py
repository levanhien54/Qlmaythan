# -*- coding: utf-8 -*-
"""Tests cho phien_dieu_tri.check_time_overlap."""
import pytest
from database.queries import phien_dieu_tri, thiet_bi, nhan_vien


@pytest.fixture
def seeded_db(temp_db):
    tb_id = thiet_bi.create(ten_thiet_bi="Máy A", model="M1")
    nv_id = nhan_vien.create(ho_ten="PTV 1", chuc_vu_trinh_do="KTV")
    phien_dieu_tri.create(
        ho_ten="Bệnh nhân 1",
        thiet_bi_id=tb_id,
        ngay_bat_dau="2026-04-01 08:00:00",
        ngay_ket_thuc="2026-04-01 12:00:00",
    )
    return {"tb_id": tb_id, "nv_id": nv_id}


def test_no_overlap_non_overlapping_range(seeded_db):
    """Phiên mới sau phiên cũ → không trùng."""
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 12:00:00", "2026-04-01 16:00:00"
    )
    assert r is None


def test_no_overlap_before(seeded_db):
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 04:00:00", "2026-04-01 08:00:00"
    )
    assert r is None


def test_overlap_partial_start(seeded_db):
    """Phiên mới bắt đầu giữa phiên cũ."""
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 10:00:00", "2026-04-01 14:00:00"
    )
    assert r is not None
    assert r["ho_ten"] == "Bệnh nhân 1"


def test_overlap_partial_end(seeded_db):
    """Phiên mới kết thúc giữa phiên cũ."""
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 06:00:00", "2026-04-01 10:00:00"
    )
    assert r is not None


def test_overlap_contained(seeded_db):
    """Phiên mới nằm trong phiên cũ."""
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 09:00:00", "2026-04-01 11:00:00"
    )
    assert r is not None


def test_overlap_contains(seeded_db):
    """Phiên mới bao phiên cũ."""
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 07:00:00", "2026-04-01 13:00:00"
    )
    assert r is not None


def test_different_device_no_conflict(seeded_db):
    """Cùng thời gian nhưng máy khác → không trùng."""
    other_id = thiet_bi.create(ten_thiet_bi="Máy B")
    r = phien_dieu_tri.check_time_overlap(
        other_id, "2026-04-01 09:00:00", "2026-04-01 11:00:00"
    )
    assert r is None


def test_exclude_self_for_update(seeded_db):
    """Khi PUT, exclude_id loại bỏ chính nó khỏi kiểm tra."""
    sessions = phien_dieu_tri.get_all()
    sid = sessions[0]["id"]
    r = phien_dieu_tri.check_time_overlap(
        seeded_db["tb_id"], "2026-04-01 09:00:00", "2026-04-01 11:00:00",
        exclude_id=sid,
    )
    assert r is None


def test_open_ended_session_blocks_everything_after(temp_db):
    """Phiên chưa kết thúc (ngay_ket_thuc=NULL) → chặn mọi phiên sau."""
    tb_id = thiet_bi.create(ten_thiet_bi="Máy C")
    phien_dieu_tri.create(
        ho_ten="BN mở",
        thiet_bi_id=tb_id,
        ngay_bat_dau="2026-04-01 08:00:00",
        ngay_ket_thuc=None,
    )
    r = phien_dieu_tri.check_time_overlap(
        tb_id, "2026-04-02 08:00:00", "2026-04-02 12:00:00"
    )
    assert r is not None


def test_new_open_ended_overlaps_existing(temp_db):
    """Phiên mới không ghi end, bắt đầu trước end cũ → trùng."""
    tb_id = thiet_bi.create(ten_thiet_bi="Máy D")
    phien_dieu_tri.create(
        ho_ten="BN cũ",
        thiet_bi_id=tb_id,
        ngay_bat_dau="2026-04-01 08:00:00",
        ngay_ket_thuc="2026-04-01 12:00:00",
    )
    r = phien_dieu_tri.check_time_overlap(
        tb_id, "2026-04-01 10:00:00", None
    )
    assert r is not None


def test_missing_params_returns_none(temp_db):
    assert phien_dieu_tri.check_time_overlap(None, "2026-04-01") is None
    assert phien_dieu_tri.check_time_overlap(1, None) is None
