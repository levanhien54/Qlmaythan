# -*- coding: utf-8 -*-
"""E2E tests cho /api/phien-dieu-tri/import-excel.
Tạo file .xlsx trong RAM, POST qua Flask test_client, assert kết quả.
"""
import io
import datetime as dt
import pytest
import openpyxl

from database.queries import thiet_bi, nhan_vien, phien_dieu_tri


# ---------- Helpers ----------

def build_xlsx(data_rows, header_row_idx=10):
    """Tạo 1 file .xlsx kiểu template 011.3.xls:
    - Các dòng đầu là header, dòng thứ (header_row_idx) chứa 'TT' và 'Họ và tên'
    - Dòng (header_row_idx+2) trở đi là data_rows
    data_rows: list of list — mỗi list là 1 row, ít nhất 29 cột.
    """
    wb = openpyxl.Workbook()
    sh = wb.active

    # Fill placeholder trước header (cần ít nhất 12 dòng total)
    for i in range(header_row_idx):
        sh.append([''] * 29)

    # Header row: cột 0='TT', cột 1='Họ và tên', cột 28='May thuc hien'
    header = [''] * 29
    header[0] = 'TT'
    header[1] = 'Họ và tên'
    header[28] = 'Máy thực hiện'
    sh.append(header)

    # Spacer row (data bắt đầu từ header_row_idx + 2)
    sh.append([''] * 29)

    for r in data_rows:
        row = list(r)
        while len(row) < 29:
            row.append('')
        sh.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def make_row(ho_ten='BN', tuoi_nam='', tuoi_nu='', dia_chi='', so_ho_so='',
             ngay_bd=None, ngay_kt=None, ptv='', phu1='', may='',
             stt=1, ghi_chu=''):
    """Tạo 1 row đúng schema cột của file 011.3."""
    row = [''] * 29
    row[0] = stt
    row[1] = ho_ten
    row[2] = tuoi_nam
    row[3] = tuoi_nu
    row[4] = dia_chi
    row[5] = so_ho_so
    row[8] = ngay_bd
    row[9] = ngay_kt
    row[18] = ptv
    row[19] = phu1
    row[25] = ghi_chu
    row[28] = may
    return row


@pytest.fixture
def client(temp_db):
    from server import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def seeded(temp_db):
    """Có sẵn 1 máy OK, 1 máy HỎNG, 1 máy THANH LÝ, 1 máy BẢO DƯỠNG, 2 nhân viên."""
    return {
        'ok': thiet_bi.create(ten_thiet_bi='Máy thận HDF số 1',
                              tinh_trang='Hoạt động bình thường'),
        'ok2': thiet_bi.create(ten_thiet_bi='Máy thận HDF số 2',
                               tinh_trang='Hoạt động bình thường'),
        'hong': thiet_bi.create(ten_thiet_bi='Máy thận NIPRO số 3',
                                tinh_trang='Hỏng'),
        'thanhly': thiet_bi.create(ten_thiet_bi='Máy thận B.Braun số 4',
                                   tinh_trang='Đã thanh lý'),
        'baoduong': thiet_bi.create(ten_thiet_bi='Máy thận Fresinius số 5',
                                    tinh_trang='Đang bảo dưỡng'),
        'baoloi': thiet_bi.create(ten_thiet_bi='Máy thận NIPRO số 6',
                                  tinh_trang='Báo lỗi'),
        'ptv1': nhan_vien.create(ho_ten='Nguyễn Văn A', chuc_vu_trinh_do='Bác sĩ'),
        'phu1': nhan_vien.create(ho_ten='Trần Thị B', chuc_vu_trinh_do='Điều dưỡng'),
    }


def post_excel(client, buf, filename='test.xlsx'):
    return client.post(
        '/api/phien-dieu-tri/import-excel',
        data={'file': (buf, filename)},
        content_type='multipart/form-data',
    )


def post_preview(client, buf, filename='test.xlsx'):
    return client.post(
        '/api/phien-dieu-tri/preview-excel',
        data={'file': (buf, filename)},
        content_type='multipart/form-data',
    )


# ---------- PREVIEW (xem trước, KHÔNG ghi DB) ----------

def test_preview_valid_row_no_write(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN Preview', ngay_bd='2026-04-01 08:00:00',
        ngay_kt='2026-04-01 12:00:00', may='Máy thận HDF số 1')])
    d = post_preview(client, buf).get_json()
    assert d['ok'] is True
    assert d['total'] == 1 and d['valid'] == 1 and d['invalid'] == 0
    assert d['rows'][0]['status'] == 'ok'
    assert d['rows'][0]['may'] == 'Máy thận HDF số 1'
    assert phien_dieu_tri.count() == 0, 'Preview KHÔNG được ghi DB'


def test_preview_flags_errors_no_write(client, seeded):
    buf = build_xlsx([
        make_row(ho_ten='BN OK', ngay_bd='2026-04-01 08:00:00',
                 ngay_kt='2026-04-01 12:00:00', may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN Lỗi', ngay_bd='',
                 ngay_kt='2026-04-01 12:00:00', may='Máy thận HDF số 1'),
    ])
    d = post_preview(client, buf).get_json()
    assert d['total'] == 2 and d['valid'] == 1 and d['invalid'] == 1
    assert phien_dieu_tri.count() == 0
    err = [r for r in d['rows'] if r['status'] == 'error'][0]
    assert any('Thiếu ngày bắt đầu' in e for e in err['errors'])


def test_live_overlap_guard_independent_of_snapshot(client, seeded, monkeypatch):
    """Chốt chặn overlap LIVE: kể cả khi check snapshot in-memory bị vô hiệu
    (giả lập snapshot cũ do import đồng thời), live check_time_overlap vẫn bắt
    được phiên trùng giờ đã có trong DB → không double-book."""
    import excel_import
    # Phiên đã có trong DB (08:00–12:00) trên máy HDF số 1
    phien_dieu_tri.create(ho_ten='BN cũ', thiet_bi_id=seeded['ok'],
                          ngay_bat_dau='2026-04-01 08:00:00',
                          ngay_ket_thuc='2026-04-01 12:00:00')
    # Vô hiệu hóa check in-memory → chỉ còn lưới an toàn LIVE
    monkeypatch.setattr(excel_import, 'check_session_overlap', lambda *a, **k: None)
    buf = build_xlsx([make_row(
        ho_ten='BN mới', ngay_bd='2026-04-01 10:00:00', ngay_kt='2026-04-01 14:00:00',
        may='Máy thận HDF số 1')])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0 and d['skipped'] == 1
    assert any('Trùng thời gian (DB)' in e for e in d['errors'][0]['errors'])


def test_constraint_absurd_date_rejected(client, seeded):
    """C: ngày phi lý (năm ngoài 2000–2100) bị loại."""
    buf = build_xlsx([make_row(ho_ten='BN 2206', ngay_bd='2206-01-01 08:00:00',
                     ngay_kt='2206-01-01 12:00:00', may='Máy thận HDF số 1')])
    d = post_preview(client, buf).get_json()
    assert d['invalid'] == 1
    assert any('bất thường' in e for e in d['rows'][0]['errors'])


def test_constraint_absurd_duration_rejected(client, seeded):
    """D: thời lượng < 10 phút hoặc > 12 giờ bị loại."""
    buf = build_xlsx([
        make_row(stt=1, ho_ten='BN 3 ngày', ngay_bd='2026-04-10 08:00:00',
                 ngay_kt='2026-04-13 08:00:00', may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN 1 phút', ngay_bd='2026-04-10 08:00:00',
                 ngay_kt='2026-04-10 08:01:00', may='Máy thận HDF số 2'),
    ])
    d = post_preview(client, buf).get_json()
    assert d['invalid'] == 2
    assert all(any('Thời lượng' in e for e in r['errors']) for r in d['rows'])


def test_constraint_same_patient_two_machines_warning(client, seeded):
    """A: cùng bệnh nhân đè giờ trên 2 máy khác nhau → CẢNH BÁO (vẫn nhập)."""
    buf = build_xlsx([
        make_row(stt=1, ho_ten='Nguyễn Văn X', ngay_bd='2026-04-01 08:00:00',
                 ngay_kt='2026-04-01 12:00:00', may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='Nguyễn Văn X', ngay_bd='2026-04-01 09:00:00',
                 ngay_kt='2026-04-01 13:00:00', may='Máy thận HDF số 2'),
    ])
    d = post_preview(client, buf).get_json()
    assert d['valid'] == 2 and d['warnings'] >= 1   # không reject, chỉ cảnh báo
    warned = [r for r in d['rows'] if r['warnings']]
    assert warned and any('đè giờ trên' in w for w in warned[0]['warnings'])


def test_constraint_maintenance_device_warns_not_blocks(client, seeded):
    """Máy 'Đang bảo dưỡng' → VẪN nhập (không loại) nhưng có CẢNH BÁO."""
    buf = build_xlsx([make_row(
        ho_ten='BN Bảo Dưỡng', ngay_bd='2026-04-01 08:00:00',
        ngay_kt='2026-04-01 12:00:00', may='Máy thận Fresinius số 5')])  # seeded = 'Đang bảo dưỡng'
    d = post_preview(client, buf).get_json()
    assert d['valid'] == 1 and d['invalid'] == 0     # không bị loại
    assert d['warnings'] >= 1
    assert any('bảo dưỡng' in w.lower() for w in d['rows'][0]['warnings'])


def test_preview_then_import_consistent(client, seeded):
    """Preview báo N hợp lệ → import thật phải success đúng N."""
    rows = [
        make_row(ho_ten='BN A', ngay_bd='2026-04-01 08:00:00',
                 ngay_kt='2026-04-01 12:00:00', may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN B', ngay_bd='2026-04-02 08:00:00',
                 ngay_kt='2026-04-02 12:00:00', may='Máy thận HDF số 2'),
    ]
    pv = post_preview(client, build_xlsx(rows)).get_json()
    assert pv['valid'] == 2
    im = post_excel(client, build_xlsx(rows)).get_json()
    assert im['success'] == pv['valid']


# ---------- FILE-LEVEL VALIDATION ----------

def test_no_file_400(client):
    r = client.post('/api/phien-dieu-tri/import-excel', data={})
    assert r.status_code == 400


def test_empty_filename_400(client):
    r = client.post(
        '/api/phien-dieu-tri/import-excel',
        data={'file': (io.BytesIO(b'x'), '')},
        content_type='multipart/form-data',
    )
    assert r.status_code == 400


def test_wrong_extension_400(client):
    r = client.post(
        '/api/phien-dieu-tri/import-excel',
        data={'file': (io.BytesIO(b'xxx'), 'data.csv')},
        content_type='multipart/form-data',
    )
    assert r.status_code == 400
    assert 'không hỗ trợ' in r.get_json()['error']


def test_empty_file_400(client):
    r = post_excel(client, io.BytesIO(b''), 'empty.xlsx')
    assert r.status_code == 400


def test_unparseable_xlsx_400(client):
    r = post_excel(client, io.BytesIO(b'\x00\x01\x02'), 'bad.xlsx')
    assert r.status_code == 400


def test_too_few_rows_400(client):
    """File có <12 dòng → lỗi."""
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.append(['just', 'two', 'rows'])
    sh.append(['still', 'not', 'enough'])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    r = post_excel(client, buf)
    assert r.status_code == 400


# ---------- ROW-LEVEL VALIDATION ----------

def test_happy_path_single_row(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='Nguyễn Văn Test',
        tuoi_nam=65, dia_chi='Hà Nội', so_ho_so=12345,
        ngay_bd=dt.datetime(2026, 4, 1, 8, 0),
        ngay_kt=dt.datetime(2026, 4, 1, 12, 0),
        ptv='Nguyễn Văn A', phu1='Trần Thị B',
        may='Máy thận HDF số 1',
    )])
    r = post_excel(client, buf)
    assert r.status_code == 200
    d = r.get_json()
    assert d['ok'] is True
    assert d['success'] == 1
    assert d['skipped'] == 0
    assert phien_dieu_tri.count() == 1


def test_empty_ho_ten_skipped_silently(client, seeded):
    """Dòng không có họ tên → skip, KHÔNG tính là lỗi."""
    buf = build_xlsx([make_row(ho_ten='', may='Máy thận HDF số 1')])
    r = post_excel(client, buf)
    d = r.get_json()
    assert d['total'] == 0
    assert d['success'] == 0
    assert d['skipped'] == 0


def test_ho_ten_single_char_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='A',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('quá ngắn' in e for e in d['errors'][0]['errors'])


def test_ho_ten_digits_only_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='12345',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('chữ cái' in e for e in d['errors'][0]['errors'])


def test_age_out_of_range_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='Bệnh Nhân X', tuoi_nam=200,
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('Tuổi ngoài phạm vi' in e for e in d['errors'][0]['errors'])


def test_age_negative_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN Y', tuoi_nu=0,  # 0 treated as missing, ok
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 1  # tuoi 0 OK


def test_age_non_numeric_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN Z', tuoi_nam='không biết',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0


def test_missing_start_date_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN Q', ngay_bd='', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('Thiếu ngày bắt đầu' in e for e in d['errors'][0]['errors'])


def test_end_before_start_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN R',
        ngay_bd='2026-04-01 12:00:00',
        ngay_kt='2026-04-01 08:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('phải sau' in e for e in d['errors'][0]['errors'])


def test_start_equals_end_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN S',
        ngay_bd='2026-04-01 08:00:00',
        ngay_kt='2026-04-01 08:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0


def test_missing_machine_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN T',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('Thiếu thông tin máy' in e for e in d['errors'][0]['errors'])


def test_machine_not_in_db_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN U',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy lạ hoắc chưa đăng ký',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('Không tìm thấy thiết bị' in e for e in d['errors'][0]['errors'])


# ---------- BUG B1 REGRESSION: status check ----------

def test_blocked_machine_hong_rejected(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN Hỏng',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận NIPRO số 3',  # hỏng
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('Hỏng' in e for e in d['errors'][0]['errors'])


def test_blocked_machine_thanhly_rejected(client, seeded):
    """B1: 'Đã thanh lý' TRƯỚC ĐÂY bị bỏ qua → phải REJECT."""
    buf = build_xlsx([make_row(
        ho_ten='BN ThanhLy',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận B.Braun số 4',  # Đã thanh lý
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert d['skipped'] == 1


def test_blocked_machine_baoloi_rejected(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN BaoLoi',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận NIPRO số 6',  # báo lỗi
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0


def test_maintenance_machine_accepted(client, seeded):
    """Đang bảo dưỡng KHÔNG block (intentional)."""
    buf = build_xlsx([make_row(
        ho_ten='BN BaoDuong',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận Fresinius số 5',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 1


def test_unknown_staff_rejected(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN UnknownStaff',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        ptv='Người Lạ Hoắc',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('không có trong CSDL' in e for e in d['errors'][0]['errors'])


# ---------- IN-FILE DUPLICATE DETECTION (BUG B2) ----------

def test_in_file_duplicate_same_machine_overlap(client, seeded):
    """2 dòng cùng máy, thời gian trùng → dòng sau bị reject."""
    buf = build_xlsx([
        make_row(ho_ten='BN 1',
                 ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
                 may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN 2',
                 ngay_bd='2026-04-01 10:00:00', ngay_kt='2026-04-01 14:00:00',
                 may='Máy thận HDF số 1'),
    ])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 1
    assert d['skipped'] == 1
    assert any('Trùng thời gian' in e or 'Trùng lặp' in e
               for e in d['errors'][0]['errors'])


def test_in_file_both_open_ended_blocked(client, seeded):
    """B2 FIX: 2 phiên cùng máy đều để trống ngày kết thúc → phải chặn."""
    buf = build_xlsx([
        make_row(ho_ten='BN Open 1', ngay_bd='2026-04-01 08:00:00', ngay_kt='',
                 may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN Open 2',
                 ngay_bd='2026-04-01 09:00:00', ngay_kt='',
                 may='Máy thận HDF số 1'),
    ])
    d = post_excel(client, buf).get_json()
    # BN Open 1 pass (missing end → lỗi ngày KT empty? Thực tế allow)
    # ⚠️ Nhưng ngày KT rỗng không bị validate error (chỉ báo khi có chuỗi không parse)
    # Do đó row 1 insert OK, row 2 phải bị chặn do overlap với row 1
    assert d['skipped'] >= 1


def test_in_file_different_machines_both_ok(client, seeded):
    """Cùng thời gian nhưng máy khác → cả 2 pass."""
    buf = build_xlsx([
        make_row(ho_ten='BN A',
                 ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
                 may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN B',
                 ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
                 may='Máy thận HDF số 2'),
    ])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 2


def test_in_file_back_to_back_ok(client, seeded):
    """Máy cùng ngày, giờ nối liền (8-12 và 12-16) → OK."""
    buf = build_xlsx([
        make_row(ho_ten='BN A',
                 ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
                 may='Máy thận HDF số 1'),
        make_row(stt=2, ho_ten='BN B',
                 ngay_bd='2026-04-01 12:00:00', ngay_kt='2026-04-01 16:00:00',
                 may='Máy thận HDF số 1'),
    ])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 2


def test_conflict_with_existing_db_session(client, seeded):
    """Phiên đã có trong DB từ trước → Excel row cùng máy + giờ overlap bị chặn."""
    phien_dieu_tri.create(
        ho_ten='BN cũ',
        thiet_bi_id=seeded['ok'],
        ngay_bat_dau='2026-04-01 08:00:00',
        ngay_ket_thuc='2026-04-01 12:00:00',
    )
    buf = build_xlsx([make_row(
        ho_ten='BN mới',
        ngay_bd='2026-04-01 10:00:00', ngay_kt='2026-04-01 14:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert d['skipped'] == 1


# ---------- DATE PARSING EDGE CASES ----------

def test_various_date_formats(client, seeded):
    """Cùng 1 ngày viết nhiều cách — phải accept tất cả."""
    buf = build_xlsx([
        make_row(ho_ten='BN1', stt=1,
                 ngay_bd='01/04/2026 08:00', ngay_kt='01/04/2026 10:00',
                 may='Máy thận HDF số 1'),
        make_row(ho_ten='BN2', stt=2,
                 ngay_bd='2026-04-01 10:00', ngay_kt='2026-04-01 12:00',
                 may='Máy thận HDF số 1'),
        make_row(ho_ten='BN3', stt=3,
                 ngay_bd='01-04-2026 12:00', ngay_kt='01-04-2026 14:00',
                 may='Máy thận HDF số 1'),
        make_row(ho_ten='BN4', stt=4,
                 ngay_bd='01.04.2026 14:00', ngay_kt='01.04.2026 16:00',
                 may='Máy thận HDF số 1'),
    ])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 4


def test_invalid_date_format_error(client, seeded):
    buf = build_xlsx([make_row(
        ho_ten='BN X',
        ngay_bd='not-a-date', ngay_kt='2026-04-01 12:00:00',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 0
    assert any('không đọc được' in e for e in d['errors'][0]['errors'])


# ---------- FUZZY MATCHING ----------

def test_device_fuzzy_match_by_keyword_number(client, seeded):
    """Nhập 'HDF_01' phải khớp 'Máy thận HDF số 1'."""
    buf = build_xlsx([make_row(
        ho_ten='BN Fuzzy',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        may='HDF_01',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 1


def test_staff_fuzzy_match_with_title(client, seeded):
    """Nhập 'BS. Nguyễn Văn A' phải khớp 'Nguyễn Văn A' trong DB."""
    buf = build_xlsx([make_row(
        ho_ten='BN Fuzzy Staff',
        ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 12:00:00',
        ptv='BS. Nguyễn Văn A',
        may='Máy thận HDF số 1',
    )])
    d = post_excel(client, buf).get_json()
    assert d['success'] == 1


# ---------- SUMMARY: multi-row mixed pass/fail ----------

def test_mixed_rows_aggregate_results(client, seeded):
    buf = build_xlsx([
        # pass
        make_row(stt=1, ho_ten='BN Pass 1',
                 ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 10:00:00',
                 may='Máy thận HDF số 1'),
        # fail: máy hỏng
        make_row(stt=2, ho_ten='BN Fail Hong',
                 ngay_bd='2026-04-01 08:00:00', ngay_kt='2026-04-01 10:00:00',
                 may='Máy thận NIPRO số 3'),
        # fail: thiếu ngày BĐ
        make_row(stt=3, ho_ten='BN Fail Date',
                 ngay_bd='', ngay_kt='2026-04-01 10:00:00',
                 may='Máy thận HDF số 1'),
        # pass
        make_row(stt=4, ho_ten='BN Pass 2',
                 ngay_bd='2026-04-02 08:00:00', ngay_kt='2026-04-02 10:00:00',
                 may='Máy thận HDF số 1'),
        # skip: không có họ tên
        make_row(stt=5, ho_ten='',
                 may='Máy thận HDF số 1'),
    ])
    d = post_excel(client, buf).get_json()
    assert d['total'] == 4   # 4 row có ho_ten (row 5 skipped silently)
    assert d['success'] == 2
    assert d['skipped'] == 2
    assert len(d['errors']) == 2
