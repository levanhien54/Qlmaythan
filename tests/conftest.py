# -*- coding: utf-8 -*-
"""
Pytest fixtures: temp SQLite DB + mock data.
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_db(monkeypatch):
    """Temp SQLite DB cho mỗi test — thay thế singleton db trong module."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")

    from database.connection import DatabaseConnection
    test_db = DatabaseConnection(db_path)

    # Patch singleton dùng ở mọi nơi
    import database.connection as conn_mod
    import database.models as models_mod
    import database.queries.thiet_bi as tb_mod
    import database.queries.nhan_vien as nv_mod
    import database.queries.phien_dieu_tri as pdt_mod
    import database.queries.bao_duong as bd_mod
    import database.queries.ban_giao as bg_mod

    for m in (conn_mod, models_mod, tb_mod, nv_mod, pdt_mod, bd_mod, bg_mod):
        monkeypatch.setattr(m, "db", test_db, raising=False)

    from database.models import create_all_tables
    create_all_tables()

    yield test_db

    test_db.close()
    try:
        os.remove(db_path)
        os.rmdir(tmpdir)
    except OSError:
        pass


@pytest.fixture
def sample_devices():
    """Các thiết bị mẫu theo format (id, ten, ten_norm, tinh_trang) của find_device."""
    return [
        (1, "Máy thận HDF Fresinius số 1", "", "Hoạt động bình thường"),
        (2, "Máy thận HDF Fresinius số 2", "", "Hoạt động bình thường"),
        (3, "Máy thận NIPRO số 3", "", "Báo lỗi"),
        (4, "Máy thận B.Braun số 10", "", "Hoạt động bình thường"),
        (5, "Máy thận NIPRO số 12", "", "Hỏng"),
    ]


@pytest.fixture
def sample_staff():
    return [
        {"id": 1, "ho_ten": "Nguyễn Văn A"},
        {"id": 2, "ho_ten": "Trần Thị B"},
        {"id": 3, "ho_ten": "BS. Lê Văn C"},
        {"id": 4, "ho_ten": "ThS.BS. Phạm D"},
    ]
