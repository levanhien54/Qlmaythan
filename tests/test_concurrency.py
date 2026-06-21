# -*- coding: utf-8 -*-
"""Concurrency tests — phơi bày race condition khi 2 người upload Excel cùng lúc."""
import io
import threading
import pytest
import openpyxl

from database.queries import thiet_bi, nhan_vien, phien_dieu_tri
from tests.test_excel_import_e2e import build_xlsx, make_row


def _build_test_xlsx():
    return build_xlsx([
        make_row(stt=i + 1, ho_ten=f'BN Concurrent {i:02d}',
                 ngay_bd=f'2026-05-{(i % 28) + 1:02d} {(i % 12) * 2:02d}:00:00',
                 ngay_kt=f'2026-05-{(i % 28) + 1:02d} {(i % 12) * 2 + 1:02d}:00:00',
                 may='Máy chạy thận Fresinius số 1')
        for i in range(30)
    ])


@pytest.fixture
def concurrent_client(temp_db):
    thiet_bi.create(ten_thiet_bi='Máy chạy thận Fresinius số 1',
                    tinh_trang='Hoạt động bình thường')
    from server import app
    app.config['TESTING'] = True
    yield app


def test_sequential_uploads_no_duplicate(concurrent_client):
    """2 upload tuần tự: lần 2 skip hết (idempotent verified trước)."""
    app = concurrent_client

    # Lần 1
    with app.test_client() as c:
        r1 = c.post('/api/phien-dieu-tri/import-excel',
                    data={'file': (_build_test_xlsx(), 'f.xlsx')},
                    content_type='multipart/form-data')
    d1 = r1.get_json()
    assert d1['success'] == 30

    # Lần 2 (khác client, khác file-like object)
    with app.test_client() as c:
        r2 = c.post('/api/phien-dieu-tri/import-excel',
                    data={'file': (_build_test_xlsx(), 'f.xlsx')},
                    content_type='multipart/form-data')
    d2 = r2.get_json()
    assert d2['success'] == 0
    assert d2['skipped'] == 30

    # Dùng query module để qua monkeypatch
    import database.queries.phien_dieu_tri as pdt_mod
    dups = pdt_mod.db.fetch_all("""
        SELECT thiet_bi_id, ngay_bat_dau, COUNT(*) c
        FROM phien_dieu_tri
        GROUP BY thiet_bi_id, ngay_bat_dau HAVING c > 1
    """)
    assert len(dups) == 0


def test_concurrent_upload_race_blocked_by_unique_index(concurrent_client):
    """Sau fix UNIQUE INDEX: 2 thread cùng POST → phiên trùng bị DB reject,
    không còn duplicate trong DB."""
    app = concurrent_client
    results = []
    errors = []

    def upload():
        try:
            with app.test_client() as c:
                r = c.post('/api/phien-dieu-tri/import-excel',
                           data={'file': (_build_test_xlsx(), 'f.xlsx')},
                           content_type='multipart/form-data')
                results.append(r.get_json())
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=upload)
    t2 = threading.Thread(target=upload)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert not errors, f'Crash: {errors}'
    # Sau race, DB có thể có duplicate (row bị insert 2 lần trước khi
    # bên kia kịp load existing_sessions cập nhật).
    total = phien_dieu_tri.count()
    import database.queries.phien_dieu_tri as pdt_mod
    dups = pdt_mod.db.fetch_all("""
        SELECT thiet_bi_id, ngay_bat_dau, COUNT(*) c
        FROM phien_dieu_tri
        GROUP BY thiet_bi_id, ngay_bat_dau HAVING c > 1
    """)
    assert total == 30, f'Sau fix UNIQUE: phải đúng 30 phiên, không nhân đôi (got {total})'
    assert len(dups) == 0, f'Sau fix UNIQUE: không được có duplicate (got {len(dups)})'


def test_unique_constraint_blocks_duplicate_insert(concurrent_client):
    """UNIQUE INDEX (thiet_bi_id, ngay_bat_dau) chặn duplicate — phòng race."""
    tb_id = thiet_bi.get_all()[0]['id']

    phien_dieu_tri.create(
        ho_ten='BN A', thiet_bi_id=tb_id,
        ngay_bat_dau='2026-05-01 08:00:00',
        ngay_ket_thuc='2026-05-01 12:00:00',
    )
    # Insert trùng → raise DuplicateSessionError thay vì âm thầm thêm
    with pytest.raises(phien_dieu_tri.DuplicateSessionError):
        phien_dieu_tri.create(
            ho_ten='BN B', thiet_bi_id=tb_id,
            ngay_bat_dau='2026-05-01 08:00:00',
            ngay_ket_thuc='2026-05-01 14:00:00',
        )
    assert phien_dieu_tri.count() == 1


def test_concurrent_different_data_no_race(concurrent_client):
    """2 thread upload 2 file KHÁC nhau → cả 2 đều success, không chặn nhau."""
    app = concurrent_client
    results = []

    def upload_file_a():
        buf = build_xlsx([make_row(
            ho_ten='BN File A',
            ngay_bd='2026-05-01 08:00:00', ngay_kt='2026-05-01 12:00:00',
            may='Máy chạy thận Fresinius số 1',
        )])
        with app.test_client() as c:
            r = c.post('/api/phien-dieu-tri/import-excel',
                       data={'file': (buf, 'a.xlsx')},
                       content_type='multipart/form-data')
            results.append(('A', r.get_json()))

    def upload_file_b():
        buf = build_xlsx([make_row(
            ho_ten='BN File B',
            ngay_bd='2026-05-02 08:00:00', ngay_kt='2026-05-02 12:00:00',
            may='Máy chạy thận Fresinius số 1',
        )])
        with app.test_client() as c:
            r = c.post('/api/phien-dieu-tri/import-excel',
                       data={'file': (buf, 'b.xlsx')},
                       content_type='multipart/form-data')
            results.append(('B', r.get_json()))

    t1 = threading.Thread(target=upload_file_a)
    t2 = threading.Thread(target=upload_file_b)
    t1.start(); t2.start()
    t1.join(); t2.join()

    total_success = sum(r[1]['success'] for r in results)
    assert total_success == 2
    assert phien_dieu_tri.count() == 2
