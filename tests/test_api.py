# -*- coding: utf-8 -*-
"""Tests Flask API endpoints qua test_client — không cần server thật."""
import pytest
from database.queries import thiet_bi, nhan_vien


@pytest.fixture
def client(temp_db):
    """Flask test client trỏ vào DB tạm của fixture temp_db."""
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ---------- Thiết bị CRUD ----------

def test_list_devices_empty(client):
    r = client.get('/api/thiet-bi')
    assert r.status_code == 200
    assert r.get_json() == []


def test_create_device(client):
    r = client.post('/api/thiet-bi', json={
        'ten_thiet_bi': 'Máy Fresenius số 1',
        'model': '4008S',
    })
    assert r.status_code == 201
    assert 'id' in r.get_json()


def test_get_device_by_id(client, temp_db):
    tb_id = thiet_bi.create(ten_thiet_bi='Máy A')
    r = client.get(f'/api/thiet-bi/{tb_id}')
    assert r.status_code == 200
    assert r.get_json()['ten_thiet_bi'] == 'Máy A'


def test_get_device_404(client):
    r = client.get('/api/thiet-bi/99999')
    assert r.status_code == 404


def test_update_device(client, temp_db):
    tb_id = thiet_bi.create(ten_thiet_bi='Old')
    r = client.put(f'/api/thiet-bi/{tb_id}', json={'ten_thiet_bi': 'New'})
    assert r.status_code == 200
    assert thiet_bi.get_by_id(tb_id)['ten_thiet_bi'] == 'New'


def test_delete_device(client, temp_db):
    tb_id = thiet_bi.create(ten_thiet_bi='X')
    r = client.delete(f'/api/thiet-bi/{tb_id}')
    assert r.status_code == 200
    assert thiet_bi.get_by_id(tb_id) is None


# ---------- Phiên điều trị — conflict 409 ----------

def test_create_session_detects_time_conflict(client, temp_db):
    tb_id = thiet_bi.create(ten_thiet_bi='Máy')
    client.post('/api/phien-dieu-tri', json={
        'ho_ten': 'BN 1',
        'thiet_bi_id': tb_id,
        'ngay_bat_dau': '2026-04-01 08:00:00',
        'ngay_ket_thuc': '2026-04-01 12:00:00',
    })
    r = client.post('/api/phien-dieu-tri', json={
        'ho_ten': 'BN 2',
        'thiet_bi_id': tb_id,
        'ngay_bat_dau': '2026-04-01 10:00:00',
        'ngay_ket_thuc': '2026-04-01 14:00:00',
    })
    assert r.status_code == 409
    assert 'Trùng khung giờ' in r.get_json()['error']


def test_create_session_no_conflict_different_machine(client, temp_db):
    tb1 = thiet_bi.create(ten_thiet_bi='A')
    tb2 = thiet_bi.create(ten_thiet_bi='B')
    client.post('/api/phien-dieu-tri', json={
        'ho_ten': 'BN 1', 'thiet_bi_id': tb1,
        'ngay_bat_dau': '2026-04-01 08:00:00', 'ngay_ket_thuc': '2026-04-01 12:00:00',
    })
    r = client.post('/api/phien-dieu-tri', json={
        'ho_ten': 'BN 2', 'thiet_bi_id': tb2,
        'ngay_bat_dau': '2026-04-01 08:00:00', 'ngay_ket_thuc': '2026-04-01 12:00:00',
    })
    assert r.status_code == 201


# ---------- Bàn giao — duplicate 409 ----------

def test_handover_duplicate_rejected(client, temp_db):
    tb_id = thiet_bi.create(ten_thiet_bi='Máy')
    client.post('/api/ban-giao', json={
        'thiet_bi_id': tb_id, 'ngay_ban_giao': '2026-04-01',
    })
    r = client.post('/api/ban-giao', json={
        'thiet_bi_id': tb_id, 'ngay_ban_giao': '2026-04-01',
    })
    assert r.status_code == 409


def test_handover_batch_skips_duplicates(client, temp_db):
    tb1 = thiet_bi.create(ten_thiet_bi='A')
    tb2 = thiet_bi.create(ten_thiet_bi='B')
    tb3 = thiet_bi.create(ten_thiet_bi='C')
    # Pre-existing: A đã bàn giao ngày đó
    client.post('/api/ban-giao', json={'thiet_bi_id': tb1, 'ngay_ban_giao': '2026-04-01'})

    r = client.post('/api/ban-giao/batch', json={
        'device_ids': [tb1, tb2, tb3],
        'ngay_ban_giao': '2026-04-01',
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data['count'] == 2   # B và C
    assert data['skipped_count'] == 1
    assert data['skipped'] == ['A']


# ---------- Dashboard + Config ----------

def test_dashboard_aggregates(client, temp_db):
    thiet_bi.create(ten_thiet_bi='A', tinh_trang='Hoạt động bình thường')
    thiet_bi.create(ten_thiet_bi='B', tinh_trang='Hỏng')
    r = client.get('/api/dashboard')
    assert r.status_code == 200
    d = r.get_json()
    assert d['total'] == 2
    assert d['active'] == 1
    assert d['error'] == 1


def test_config_endpoint(client):
    r = client.get('/api/config')
    data = r.get_json()
    assert 'chuc_vu' in data
    assert 'tan_suat' in data
    assert 'loai_bao_duong' in data


# ---------- Nhân viên CRUD ----------

def test_staff_crud_roundtrip(client, temp_db):
    create = client.post('/api/nhan-vien', json={
        'ho_ten': 'Nguyễn A', 'chuc_vu_trinh_do': 'Bác sĩ',
    })
    assert create.status_code == 201
    nv_id = create.get_json()['id']

    listing = client.get('/api/nhan-vien').get_json()
    assert any(s['id'] == nv_id for s in listing)

    upd = client.put(f'/api/nhan-vien/{nv_id}', json={'ho_ten': 'Nguyễn B'})
    assert upd.status_code == 200
    assert nhan_vien.get_by_id(nv_id)['ho_ten'] == 'Nguyễn B'

    deld = client.delete(f'/api/nhan-vien/{nv_id}')
    assert deld.status_code == 200
