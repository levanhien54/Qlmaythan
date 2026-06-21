# -*- coding: utf-8 -*-
"""E2E qua tầng HTTP (Flask test_client) cho các fix review — kiểm tra ĐÚNG
bề mặt tấn công thật (request JSON → endpoint → query), không chỉ gọi hàm.
"""
import pytest

from database.queries import thiet_bi, bao_duong, nhan_vien, phien_dieu_tri, ban_giao


@pytest.fixture
def client(temp_db):
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ---------- #1 mass-assignment / SQL injection qua PUT ----------

def test_put_device_ignores_unknown_and_protected_columns(client):
    tid = thiet_bi.create(ten_thiet_bi="Máy A", tinh_trang="Hoạt động bình thường")
    r = client.put(f'/api/thiet-bi/{tid}', json={
        'tinh_trang': 'Hỏng',          # hợp lệ → cập nhật
        'ghi_chu': 'cột không tồn tại',  # bỏ qua (trước đây gây lỗi SQL)
        'id': 99999,                    # cột bảo vệ → KHÔNG được đổi
    })
    assert r.status_code == 200
    row = thiet_bi.get_by_id(tid)
    assert row['tinh_trang'] == 'Hỏng'
    assert row['id'] == tid            # id không bị mass-assign


def test_put_device_injection_key_does_not_corrupt_table(client):
    t1 = thiet_bi.create(ten_thiet_bi="Máy 1", tinh_trang="Hoạt động bình thường")
    t2 = thiet_bi.create(ten_thiet_bi="Máy 2", tinh_trang="Hoạt động bình thường")
    before = thiet_bi.count()
    # Nếu key bị nội suy thẳng vào SQL, đây sẽ đổi/huỷ nhiều dòng.
    r = client.put(f'/api/thiet-bi/{t1}', json={
        "tinh_trang = 'HACKED' WHERE 1=1 --": "boom",
    })
    # Không 500, bảng nguyên vẹn, máy 2 không bị đổi sang HACKED.
    assert r.status_code == 200
    assert thiet_bi.count() == before
    assert thiet_bi.get_by_id(t2)['tinh_trang'] == 'Hoạt động bình thường'


# ---------- #4 bộ lọc bảo dưỡng theo ngày bao gồm phiếu có giờ ----------

def test_get_bao_duong_date_filter_includes_timed_record(client):
    tid = thiet_bi.create(ten_thiet_bi="Máy BD")
    bao_duong.create(thiet_bi_id=tid, loai="Sửa chữa",
                     ngay_thuc_hien="2026-04-01 14:30")
    r = client.get('/api/bao-duong?from_date=2026-04-01&to_date=2026-04-01')
    assert r.status_code == 200
    assert len(r.get_json()) == 1


# ---------- smoke: các endpoint đọc chính hoạt động sau refactor ----------

def test_core_read_endpoints_ok(client):
    nhan_vien.create(ho_ten="NV A", chuc_vu_trinh_do="KTV")
    thiet_bi.create(ten_thiet_bi="Máy A")
    for path in ('/api/dashboard', '/api/config', '/api/thiet-bi',
                 '/api/nhan-vien', '/api/statistics', '/api/phien-dieu-tri'):
        r = client.get(path)
        assert r.status_code == 200, f"{path} → {r.status_code}"


# ---------- D1 chặn xóa thiết bị còn lịch sử ----------

def test_delete_device_with_history_blocked(client):
    tid = thiet_bi.create(ten_thiet_bi="Máy A")
    bao_duong.create(thiet_bi_id=tid, loai="Sửa chữa", ngay_thuc_hien="2026-04-01")
    r = client.delete(f'/api/thiet-bi/{tid}')
    assert r.status_code == 409
    assert thiet_bi.get_by_id(tid) is not None  # vẫn còn, lịch sử không bị mất
    # Thiết bị KHÔNG có lịch sử thì xóa được bình thường
    tid2 = thiet_bi.create(ten_thiet_bi="Máy B")
    assert client.delete(f'/api/thiet-bi/{tid2}').status_code == 200


# ---------- D4 chặn xóa nhân viên đang được tham chiếu ----------

def test_delete_referenced_staff_blocked(client):
    nv = nhan_vien.create(ho_ten="NV A", chuc_vu_trinh_do="KTV")
    tid = thiet_bi.create(ten_thiet_bi="Máy")
    phien_dieu_tri.create(ho_ten="BN", thiet_bi_id=tid, ptv_chinh_id=nv,
                          ngay_bat_dau="2026-04-01 08:00:00")
    r = client.delete(f'/api/nhan-vien/{nv}')
    assert r.status_code == 409
    assert nhan_vien.get_by_id(nv) is not None
    # Nhân viên không bị tham chiếu thì xóa được
    nv2 = nhan_vien.create(ho_ten="NV B", chuc_vu_trinh_do="KTV")
    assert client.delete(f'/api/nhan-vien/{nv2}').status_code == 200


# ---------- D2 bàn giao hàng loạt nguyên tử ----------

def test_batch_handover_atomic_rollback_on_bad_fk(client):
    tid = thiet_bi.create(ten_thiet_bi="A")
    before = ban_giao.count()
    # 999999 là thiết bị không tồn tại → IntegrityError → 400, rollback CẢ LÔ
    r = client.post('/api/ban-giao/batch', json={
        'device_ids': [tid, 999999], 'ngay_ban_giao': '2026-04-05',
    })
    assert r.status_code == 400
    assert ban_giao.count() == before, "Lỗi FK phải rollback toàn bộ, không tạo phiếu nào"


# ---------- D3 đếm phiên chưa gán máy + cảnh báo dashboard ----------

def test_unmatched_sessions_counted_and_alerted(client):
    tid = thiet_bi.create(ten_thiet_bi="A")
    phien_dieu_tri.create(ho_ten="BN matched", thiet_bi_id=tid,
                          ngay_bat_dau="2026-04-01 08:00:00")
    phien_dieu_tri.create(ho_ten="BN unmatched", thiet_bi_id=None,
                          may_thuc_hien="Máy X", ngay_bat_dau="2026-04-02 08:00:00")
    assert phien_dieu_tri.count_unmatched() == 1
    d = client.get('/api/dashboard').get_json()
    assert any('chưa gán máy' in a['msg'] for a in d['alerts'])
