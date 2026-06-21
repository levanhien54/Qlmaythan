# -*- coding: utf-8 -*-
"""Tests cho ban_giao.check_duplicates và bao_duong.get_upcoming."""
from datetime import date, timedelta
import pytest
from database.queries import ban_giao, bao_duong, thiet_bi


# ---------- ban_giao.check_duplicates ----------

@pytest.fixture
def handover_setup(temp_db):
    tb1 = thiet_bi.create(ten_thiet_bi="Máy A")
    tb2 = thiet_bi.create(ten_thiet_bi="Máy B")
    tb3 = thiet_bi.create(ten_thiet_bi="Máy C")
    bg1 = ban_giao.create(thiet_bi_id=tb1, ngay_ban_giao="2026-04-01")
    bg2 = ban_giao.create(thiet_bi_id=tb2, ngay_ban_giao="2026-04-01")
    return {"tb1": tb1, "tb2": tb2, "tb3": tb3, "bg1": bg1, "bg2": bg2}


def test_check_duplicates_empty_device_list(handover_setup):
    assert ban_giao.check_duplicates([], "2026-04-01") == []


def test_check_duplicates_empty_date(handover_setup):
    assert ban_giao.check_duplicates([handover_setup["tb1"]], "") == []


def test_check_duplicates_detects_existing(handover_setup):
    """Máy đã có bàn giao cùng ngày → phải trả về."""
    dups = ban_giao.check_duplicates(
        [handover_setup["tb1"], handover_setup["tb2"]],
        "2026-04-01",
    )
    ids = {d["thiet_bi_id"] for d in dups}
    assert ids == {handover_setup["tb1"], handover_setup["tb2"]}


def test_check_duplicates_different_date_no_match(handover_setup):
    """Cùng máy, khác ngày → không trùng."""
    dups = ban_giao.check_duplicates([handover_setup["tb1"]], "2026-04-02")
    assert dups == []


def test_check_duplicates_device_not_in_handover(handover_setup):
    """Máy chưa từng bàn giao → không có."""
    dups = ban_giao.check_duplicates([handover_setup["tb3"]], "2026-04-01")
    assert dups == []


def test_check_duplicates_mixed(handover_setup):
    """Một máy trùng, một máy không."""
    dups = ban_giao.check_duplicates(
        [handover_setup["tb1"], handover_setup["tb3"]],
        "2026-04-01",
    )
    assert len(dups) == 1
    assert dups[0]["thiet_bi_id"] == handover_setup["tb1"]


def test_check_duplicates_exclude_self_for_update(handover_setup):
    """Khi PUT chính phiếu đó, exclude_id loại bỏ nó khỏi kiểm tra."""
    dups = ban_giao.check_duplicates(
        [handover_setup["tb1"]],
        "2026-04-01",
        exclude_id=handover_setup["bg1"],
    )
    assert dups == []


def test_check_duplicates_returns_device_name(handover_setup):
    dups = ban_giao.check_duplicates([handover_setup["tb1"]], "2026-04-01")
    assert dups[0]["ten_thiet_bi"] == "Máy A"


# ---------- bao_duong.get_upcoming ----------

@pytest.fixture
def maintenance_setup(temp_db):
    tb = thiet_bi.create(ten_thiet_bi="Máy X")
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()
    in_5_days = (today + timedelta(days=5)).isoformat()
    in_10_days = (today + timedelta(days=10)).isoformat()

    bd_past = bao_duong.create(
        thiet_bi_id=tb, loai="Bảo dưỡng định kỳ",
        ngay_thuc_hien=yesterday, ngay_du_kien_tiep_theo=yesterday,
    )
    bd_tomorrow = bao_duong.create(
        thiet_bi_id=tb, loai="Bảo dưỡng định kỳ",
        ngay_thuc_hien=today.isoformat(), ngay_du_kien_tiep_theo=tomorrow,
    )
    bd_5 = bao_duong.create(
        thiet_bi_id=tb, loai="Bảo dưỡng định kỳ",
        ngay_thuc_hien=today.isoformat(), ngay_du_kien_tiep_theo=in_5_days,
    )
    bd_10 = bao_duong.create(
        thiet_bi_id=tb, loai="Bảo dưỡng định kỳ",
        ngay_thuc_hien=today.isoformat(), ngay_du_kien_tiep_theo=in_10_days,
    )
    bd_null = bao_duong.create(
        thiet_bi_id=tb, loai="Sửa chữa",
        ngay_thuc_hien=today.isoformat(), ngay_du_kien_tiep_theo=None,
    )
    return {
        "tb": tb,
        "bd_past": bd_past, "bd_tomorrow": bd_tomorrow,
        "bd_5": bd_5, "bd_10": bd_10, "bd_null": bd_null,
    }


def test_get_upcoming_default_7_days(maintenance_setup):
    """Default 7 ngày → chỉ lấy tomorrow + in_5_days (bỏ qua past, in_10, null)."""
    up = bao_duong.get_upcoming(7)
    ids = {r["id"] for r in up}
    assert maintenance_setup["bd_tomorrow"] in ids
    assert maintenance_setup["bd_5"] in ids
    assert maintenance_setup["bd_past"] not in ids
    assert maintenance_setup["bd_10"] not in ids
    assert maintenance_setup["bd_null"] not in ids


def test_get_upcoming_larger_window(maintenance_setup):
    """14 ngày → thêm in_10_days."""
    up = bao_duong.get_upcoming(14)
    ids = {r["id"] for r in up}
    assert maintenance_setup["bd_10"] in ids


def test_get_upcoming_zero_days(maintenance_setup):
    """days=0 → chỉ máy đến hạn đúng hôm nay (không có trong fixture)."""
    up = bao_duong.get_upcoming(0)
    assert maintenance_setup["bd_tomorrow"] not in [r["id"] for r in up]


def test_get_upcoming_sorted_ascending(maintenance_setup):
    """Phải sort theo ngày_du_kien_tiep_theo tăng dần."""
    up = bao_duong.get_upcoming(30)
    dates = [r["ngay_du_kien_tiep_theo"] for r in up]
    assert dates == sorted(dates)


def test_get_upcoming_includes_device_name(maintenance_setup):
    up = bao_duong.get_upcoming(7)
    assert up[0]["ten_thiet_bi"] == "Máy X"


def test_get_upcoming_empty_when_no_records(temp_db):
    assert bao_duong.get_upcoming(7) == []
