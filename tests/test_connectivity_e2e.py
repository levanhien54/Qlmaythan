# -*- coding: utf-8 -*-
"""Kiểm tra KẾT NỐI GIAO DIỆN ↔ BACKEND theo từng màn hình.

Mỗi test mô phỏng đúng chuỗi lời gọi API mà 1 trang web thực hiện (xem web/js/*.js):
list → create → get → update → (action) → delete. Dùng Flask test_client = chính
backend thật (routing + query + SQLite), nên PASS nghĩa là luồng UI→API→DB→API
chạy thông suốt đầu-cuối.
"""
import io
import pytest
import openpyxl


@pytest.fixture
def client(temp_db):
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def _id(resp):
    assert resp.status_code in (200, 201), f"{resp.status_code}: {resp.get_data(as_text=True)[:200]}"
    return resp.get_json().get('id')


# ---------- Màn hình Dashboard ----------

def test_screen_dashboard(client):
    r = client.get('/api/dashboard')
    assert r.status_code == 200
    d = r.get_json()
    for key in ('total', 'active', 'error', 'sessions_today', 'status', 'usage', 'alerts'):
        assert key in d, f"dashboard thiếu khóa {key}"


# ---------- Màn hình Nhân viên (staff.js) ----------

def test_screen_staff_crud(client):
    nid = _id(client.post('/api/nhan-vien', json={'ho_ten': 'NV Test', 'chuc_vu_trinh_do': 'Bác sĩ'}))
    assert any(s['id'] == nid for s in client.get('/api/nhan-vien').get_json())
    assert client.get(f'/api/nhan-vien/{nid}').get_json()['ho_ten'] == 'NV Test'
    assert client.put(f'/api/nhan-vien/{nid}', json={'ho_ten': 'NV Sửa'}).status_code == 200
    assert client.get(f'/api/nhan-vien/{nid}').get_json()['ho_ten'] == 'NV Sửa'
    assert client.delete(f'/api/nhan-vien/{nid}').status_code == 200


# ---------- Màn hình Thiết bị + Cài đặt (devices.js / settings.js) ----------

def test_screen_devices_crud_and_detail(client):
    did = _id(client.post('/api/thiet-bi', json={
        'ten_thiet_bi': 'Máy HDF số 1', 'model': '4008S',
        'tinh_trang': 'Hoạt động bình thường', 'tan_suat_su_dung': 2,
    }))
    assert client.get('/api/thiet-bi').status_code == 200
    assert client.get('/api/thiet-bi/models').status_code == 200
    # Trang chi tiết thiết bị gọi 4 endpoint song song:
    assert client.get(f'/api/thiet-bi/{did}').status_code == 200
    assert client.get(f'/api/phien-dieu-tri?thiet_bi_id={did}').status_code == 200
    assert client.get(f'/api/bao-duong?thiet_bi_id={did}').status_code == 200
    assert client.get(f'/api/ban-giao?thiet_bi_id={did}').status_code == 200
    assert client.put(f'/api/thiet-bi/{did}', json={'tinh_trang': 'Hỏng'}).status_code == 200
    assert client.delete(f'/api/thiet-bi/{did}').status_code == 200


# ---------- Màn hình Phiên điều trị (sessions.js) ----------

def test_screen_sessions_crud(client):
    did = _id(client.post('/api/thiet-bi', json={'ten_thiet_bi': 'Máy A'}))
    nid = _id(client.post('/api/nhan-vien', json={'ho_ten': 'PTV A', 'chuc_vu_trinh_do': 'KTV'}))
    sid = _id(client.post('/api/phien-dieu-tri', json={
        'ho_ten': 'BN Test', 'tuoi': 60, 'thiet_bi_id': did, 'ptv_chinh_id': nid,
        'may_thuc_hien': 'Máy A',
        'ngay_bat_dau': '2026-04-01 08:00:00', 'ngay_ket_thuc': '2026-04-01 12:00:00',
    }))
    assert client.get('/api/phien-dieu-tri?from_date=2026-04-01&to_date=2026-04-01').status_code == 200
    assert client.get(f'/api/phien-dieu-tri/{sid}').get_json()['ho_ten'] == 'BN Test'
    assert client.put(f'/api/phien-dieu-tri/{sid}', json={
        'ho_ten': 'BN Sửa', 'thiet_bi_id': did,
        'ngay_bat_dau': '2026-04-01 08:00:00', 'ngay_ket_thuc': '2026-04-01 13:00:00',
    }).status_code == 200
    assert client.get('/api/phien-dieu-tri/stats').status_code == 200
    assert client.delete(f'/api/phien-dieu-tri/{sid}').status_code == 200


def test_screen_sessions_import_excel(client):
    client.post('/api/thiet-bi', json={'ten_thiet_bi': 'Máy thận HDF số 1',
                                       'tinh_trang': 'Hoạt động bình thường'})
    # Tạo file .xlsx tối thiểu đúng layout (header dòng 10, data từ dòng 12)
    wb = openpyxl.Workbook(); sh = wb.active
    for _ in range(10):
        sh.append([''] * 29)
    hdr = [''] * 29; hdr[0] = 'TT'; hdr[1] = 'Họ và tên'; hdr[28] = 'Máy thực hiện'
    sh.append(hdr); sh.append([''] * 29)
    row = [''] * 29
    row[0] = 1; row[1] = 'Nguyễn Văn Test'; row[8] = '2026-04-01 08:00:00'
    row[9] = '2026-04-01 12:00:00'; row[28] = 'HDF_01'
    sh.append(row)
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    r = client.post('/api/phien-dieu-tri/import-excel',
                    data={'file': (buf, 'test.xlsx')}, content_type='multipart/form-data')
    assert r.status_code == 200
    assert r.get_json()['success'] == 1


# ---------- Màn hình Bảo dưỡng (maintenance.js) ----------

def test_screen_maintenance_crud(client):
    did = _id(client.post('/api/thiet-bi', json={'ten_thiet_bi': 'Máy BD'}))
    bid = _id(client.post('/api/bao-duong', json={
        'thiet_bi_id': did, 'loai': 'Sửa chữa',
        'ngay_thuc_hien': '2026-04-01 14:30', 'chi_phi': 500000,
    }))
    # Bộ lọc cùng ngày phải thấy phiếu (fix #4)
    assert len(client.get('/api/bao-duong?from_date=2026-04-01&to_date=2026-04-01').get_json()) == 1
    assert client.get('/api/bao-duong/upcoming').status_code == 200
    assert client.get(f'/api/bao-duong/{bid}').status_code == 200
    assert client.put(f'/api/bao-duong/{bid}', json={'trang_thai': 'Hoàn thành'}).status_code == 200
    assert client.delete(f'/api/bao-duong/{bid}').status_code == 200


# ---------- Màn hình Bàn giao (handover.js) ----------

def test_screen_handover_crud_batch_pdf(client):
    d1 = _id(client.post('/api/thiet-bi', json={'ten_thiet_bi': 'A'}))
    d2 = _id(client.post('/api/thiet-bi', json={'ten_thiet_bi': 'B'}))
    hid = _id(client.post('/api/ban-giao', json={'thiet_bi_id': d1, 'ngay_ban_giao': '2026-04-01'}))
    assert client.get('/api/ban-giao').status_code == 200
    assert client.get(f'/api/ban-giao/{hid}').status_code == 200
    assert client.put(f'/api/ban-giao/{hid}', json={'ghi_chu': 'đã kiểm tra'}).status_code == 200
    # Bàn giao hàng loạt (d1 trùng ngày → skip, d2 tạo mới)
    rb = client.post('/api/ban-giao/batch', json={
        'device_ids': [d1, d2], 'ngay_ban_giao': '2026-04-01',
    })
    assert rb.status_code == 201
    assert rb.get_json()['count'] == 1 and rb.get_json()['skipped_count'] == 1
    # Xuất PDF (kiểm font fallback + reportlab)
    rp = client.get('/api/ban-giao/export-pdf?from_date=2026-04-01&to_date=2026-04-01')
    assert rp.status_code == 200
    assert rp.mimetype == 'application/pdf'
    assert client.delete(f'/api/ban-giao/{hid}').status_code == 200


# ---------- Màn hình Thống kê (statistics.js) ----------

def test_screen_statistics(client):
    did = _id(client.post('/api/thiet-bi', json={'ten_thiet_bi': 'Máy A', 'tan_suat_su_dung': 3}))
    client.post('/api/phien-dieu-tri', json={
        'ho_ten': 'BN', 'thiet_bi_id': did, 'may_thuc_hien': 'Máy A',
        'ngay_bat_dau': '2026-04-01 08:00:00', 'ngay_ket_thuc': '2026-04-01 12:00:00',
    })
    s = client.get('/api/statistics').get_json()
    for key in ('total_cost', 'top_machine', 'active_rate', 'usage_per_device', 'sessions_per_machine'):
        assert key in s, f"statistics thiếu khóa {key}"
    assert s['active_rate'] == 100  # 1 máy hoạt động / 1 tổng


# ---------- Config (dùng bởi mọi form) ----------

def test_screen_config(client):
    d = client.get('/api/config').get_json()
    for key in ('tan_suat', 'loai_bao_duong', 'trang_thai_bao_duong', 'chuc_vu'):
        assert key in d
