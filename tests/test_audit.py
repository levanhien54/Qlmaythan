# -*- coding: utf-8 -*-
"""Tests cho nhật ký (audit) + khôi phục bản ghi đã xóa."""
import pytest

from database import audit
from database.queries import thiet_bi, nhan_vien, phien_dieu_tri


# ---------- Ghi nhật ký create/update/delete ----------

def test_create_update_delete_logged(temp_db):
    tid = thiet_bi.create(ten_thiet_bi='Máy X', tinh_trang='Hoạt động bình thường')
    thiet_bi.update(tid, tinh_trang='Hỏng')
    thiet_bi.delete(tid)
    actions = [r['action'] for r in audit.recent(entity='thiet_bi')]
    assert 'create' in actions and 'update' in actions and 'delete' in actions


# ---------- Delete lưu snapshot + khôi phục đúng id ----------

def test_delete_snapshot_and_restore_roundtrip(temp_db):
    tid = thiet_bi.create(ten_thiet_bi='Máy Khôi Phục', model='4008S',
                          tinh_trang='Hoạt động bình thường')
    thiet_bi.delete(tid)
    assert thiet_bi.get_by_id(tid) is None  # đã xóa khỏi bảng chính

    dels = [r for r in audit.recent(action='delete', entity='thiet_bi')
            if r['entity_id'] == tid]
    assert dels, 'Phải có mục delete kèm snapshot'
    audit.restore(dels[0]['id'])

    row = thiet_bi.get_by_id(tid)
    assert row is not None
    assert row['id'] == tid and row['ten_thiet_bi'] == 'Máy Khôi Phục'  # đúng id gốc


def test_restore_session_keeps_fk(temp_db):
    """Khôi phục phiên giữ nguyên thiet_bi_id (quan hệ FK)."""
    tid = thiet_bi.create(ten_thiet_bi='Máy A')
    sid = phien_dieu_tri.create(ho_ten='BN Test', thiet_bi_id=tid,
                                ngay_bat_dau='2026-04-01 08:00:00',
                                ngay_ket_thuc='2026-04-01 12:00:00')
    phien_dieu_tri.delete(sid)
    aid = [r for r in audit.recent(action='delete', entity='phien_dieu_tri')
           if r['entity_id'] == sid][0]['id']
    audit.restore(aid)
    row = phien_dieu_tri.get_by_id(sid)
    assert row and row['thiet_bi_id'] == tid and row['ho_ten'] == 'BN Test'


# ---------- Khôi phục lỗi ----------

def test_restore_rejects_already_existing(temp_db):
    nid = nhan_vien.create(ho_ten='NV', chuc_vu_trinh_do='KTV')
    nhan_vien.delete(nid)
    aid = audit.recent(action='delete', entity='nhan_vien')[0]['id']
    audit.restore(aid)              # lần 1 OK
    with pytest.raises(audit.RestoreError):
        audit.restore(aid)         # lần 2: id đã tồn tại → từ chối


def test_restore_rejects_non_delete_entry(temp_db):
    tid = thiet_bi.create(ten_thiet_bi='M')  # tạo ra mục 'create'
    create_entry = audit.recent(action='create', entity='thiet_bi')[0]
    with pytest.raises(audit.RestoreError):
        audit.restore(create_entry['id'])


# ---------- HTTP endpoints ----------

@pytest.fixture
def client(temp_db):
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_api_audit_list_and_restore(client):
    tid = thiet_bi.create(ten_thiet_bi='Máy API')
    sid = phien_dieu_tri.create(ho_ten='BN API', thiet_bi_id=tid,
                                ngay_bat_dau='2026-04-01 08:00:00')
    phien_dieu_tri.delete(sid)

    log = client.get('/api/audit?entity=phien_dieu_tri&action=delete').get_json()
    aid = [e['id'] for e in log if e['entity_id'] == sid][0]

    r = client.post(f'/api/audit/{aid}/restore')
    assert r.status_code == 200 and r.get_json()['ok'] is True
    assert phien_dieu_tri.get_by_id(sid) is not None

    # khôi phục lại lần nữa → 409
    assert client.post(f'/api/audit/{aid}/restore').status_code == 409
