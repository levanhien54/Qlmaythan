# -*- coding: utf-8 -*-
"""
Comprehensive test suite for:
  1. Excel import validation (all edge cases)
  2. Manual session entry via API

Run: python test_import.py
"""
import sys, io, os, json, time, requests, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 'http://localhost:5000'
RESULTS = {'passed': 0, 'failed': 0, 'tests': []}


def log(status, test_name, detail=''):
    icon = '✅' if status == 'PASS' else '❌'
    RESULTS['tests'].append({'status': status, 'name': test_name, 'detail': detail})
    if status == 'PASS':
        RESULTS['passed'] += 1
    else:
        RESULTS['failed'] += 1
    print(f"  {icon} {test_name}" + (f" — {detail}" if detail else ''))


def create_xls(rows, filename='test.xls'):
    """Create a .xls file with given rows. Rows 0-10 are header, 11+ is data."""
    import xlwt
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Sheet 1')
    headers_pre = [
        [''] * 29,
        ['SỞ Y TẾ BẮC NINH'] + [''] * 28,
        ['BỆNH VIỆN ĐA KHOA BẮC NINH SỐ 2'] + [''] * 28,
        ['Khoa Thận- Lọc Máu (Ngoại trú)'] + [''] * 28,
        [''] * 29,
        ['DANH SÁCH BỆNH NHÂN LÀM PHẪU THUẬT'] + [''] * 28,
        ['Từ ngày 11/03/2026 đến ngày 11/03/2026'] + [''] * 28,
        [''] * 29,
        [''] * 29,
        ['TT', 'Họ và tên', 'Tuổi', '', 'Địa chỉ', 'Số hồ sơ', 'Ngày vào viện', 'Ngày chỉ định',
         'Ngày bắt đầu', 'Ngày kết thúc', 'Chẩn Đoán trước TT', 'Chẩn Đoán sau TT',
         'Phương pháp', 'Phân loại', '', '', '', '', 'Số người', '', '', '', '', '', '', '', '', '', ''],
        ['', '', 'Nam', 'Nữ', '', '', '', '', '', '', '', '', '', 'I', 'II', 'III', 'ĐB', 'Chưa PL',
         'PTV chính', 'Phụ 1', 'Phụ 2', 'BS gây mê', 'Phụ mê', 'Tít dụng cụ', 'Giúp việc',
         'Ghi chú', 'Phân loại', 'Phòng thực hiện', 'Máy thực hiện'],
    ]
    for r_idx, row in enumerate(headers_pre):
        for c_idx, val in enumerate(row):
            ws.write(r_idx, c_idx, str(val))
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            ws.write(r_idx + 11, c_idx, val if val is not None else '')
    path = os.path.join(tempfile.gettempdir(), filename)
    wb.save(path)
    return path


def upload_excel(filepath):
    with open(filepath, 'rb') as f:
        res = requests.post(f'{BASE}/api/phien-dieu-tri/import-excel',
                            files={'file': (os.path.basename(filepath), f)})
    return res.status_code, res.json()


def api_post(path, data):
    res = requests.post(f'{BASE}{path}', json=data)
    return res.status_code, res.json()


def api_get(path):
    res = requests.get(f'{BASE}{path}')
    return res.status_code, res.json()


def make_row(stt, name, age_m, age_f, addr, shs, start, end, ptv, phu1, device):
    row = [''] * 29
    row[0] = stt; row[1] = name; row[2] = age_m; row[3] = age_f
    row[4] = addr; row[5] = shs; row[8] = start; row[9] = end
    row[18] = ptv; row[19] = phu1; row[28] = device
    return row


# ============================================================
# PART 1: FILE-LEVEL VALIDATION
# ============================================================
def test_file_validation():
    print("\n" + "=" * 60)
    print("PART 1: FILE-LEVEL VALIDATION")
    print("=" * 60)

    # T1.1: No file
    res = requests.post(f'{BASE}/api/phien-dieu-tri/import-excel')
    d = res.json()
    log('PASS' if res.status_code == 400 else 'FAIL', 'T1.1 No file in request', d.get('error',''))

    # T1.2: Wrong type .txt
    tmp = os.path.join(tempfile.gettempdir(), 'test.txt')
    open(tmp,'w').write('hello')
    with open(tmp,'rb') as f:
        res = requests.post(f'{BASE}/api/phien-dieu-tri/import-excel', files={'file':('test.txt',f)})
    d = res.json()
    log('PASS' if res.status_code == 400 else 'FAIL', 'T1.2 Wrong type .txt', d.get('error',''))

    # T1.3: Wrong type .csv
    tmp = os.path.join(tempfile.gettempdir(), 'test.csv')
    open(tmp,'w').write('a,b')
    with open(tmp,'rb') as f:
        res = requests.post(f'{BASE}/api/phien-dieu-tri/import-excel', files={'file':('test.csv',f)})
    d = res.json()
    log('PASS' if res.status_code == 400 else 'FAIL', 'T1.3 Wrong type .csv', d.get('error',''))

    # T1.4: Empty xls (0 bytes)
    tmp = os.path.join(tempfile.gettempdir(), 'empty.xls')
    open(tmp,'wb').write(b'')
    with open(tmp,'rb') as f:
        res = requests.post(f'{BASE}/api/phien-dieu-tri/import-excel', files={'file':('empty.xls',f)})
    d = res.json()
    log('PASS' if res.status_code == 400 else 'FAIL', 'T1.4 Empty file 0 bytes', d.get('error',''))

    # T1.5: Corrupt xls
    tmp = os.path.join(tempfile.gettempdir(), 'corrupt.xls')
    open(tmp,'wb').write(b'\x00BADDATA\xFF')
    with open(tmp,'rb') as f:
        res = requests.post(f'{BASE}/api/phien-dieu-tri/import-excel', files={'file':('corrupt.xls',f)})
    d = res.json()
    log('PASS' if res.status_code == 400 else 'FAIL', 'T1.5 Corrupt file', d.get('error',''))

    # T1.6: Too few rows
    import xlwt
    wb = xlwt.Workbook(); ws = wb.add_sheet('S')
    for i in range(5): ws.write(i,0,f'R{i}')
    tmp = os.path.join(tempfile.gettempdir(), 'small.xls')
    wb.save(tmp)
    c, d = upload_excel(tmp)
    log('PASS' if c == 400 else 'FAIL', 'T1.6 Too few rows (<12)', d.get('error',''))


# ============================================================
# PART 2: ROW-LEVEL VALIDATION
# ============================================================
def test_row_validation():
    print("\n" + "=" * 60)
    print("PART 2: ROW-LEVEL VALIDATION")
    print("=" * 60)

    _, staff_list = api_get('/api/nhan-vien')
    vs = staff_list[0]['ho_ten'] if staff_list else 'Unknown'

    rows = [
        # 0: VALID
        make_row(1,'Nguyễn Văn Test OK','45','','Bắc Ninh','99990001',
                 '15/03/2026 08:00:00','15/03/2026 12:00:00', vs,'','Máy thận nhân tạo_F1'),
        # 1: Short name
        make_row(2,'A','30','','HN','99990002',
                 '15/03/2026 13:00:00','15/03/2026 17:00:00', vs,'','Máy thận nhân tạo_F1'),
        # 2: Number-only name
        make_row(3,'12345','30','','HN','99990003',
                 '15/03/2026 13:00:00','15/03/2026 17:00:00', vs,'','Máy thận nhân tạo_F2'),
        # 3: Age negative
        make_row(4,'Trần Tuổi Âm','-5','','BN','99990004',
                 '15/03/2026 14:00:00','15/03/2026 18:00:00', vs,'','Máy thận nhân tạo_F3'),
        # 4: Age > 120
        make_row(5,'Phạm Tuổi Lớn','200','','BN','99990005',
                 '15/03/2026 14:00:00','15/03/2026 18:00:00', vs,'','Máy thận nhân tạo_F4'),
        # 5: Age text
        make_row(6,'Lê Tuổi Chữ','abc','','HN','99990006',
                 '15/03/2026 14:00:00','15/03/2026 18:00:00', vs,'','Máy thận nhân tạo_F5'),
        # 6: Bad date
        make_row(7,'Hoàng Ngày Sai','40','','HN','99990007',
                 'not-a-date','15/03/2026 18:00:00', vs,'','Máy thận nhân tạo_F6'),
        # 7: End < Start
        make_row(8,'Vũ Ngày Ngược','35','','HN','99990008',
                 '15/03/2026 18:00:00','15/03/2026 08:00:00', vs,'','Máy thận nhân tạo_F7'),
        # 8: Missing device
        make_row(9,'Đỗ Thiếu Máy','50','','HN','99990009',
                 '15/03/2026 20:00:00','15/03/2026 23:00:00', vs,'',''),
        # 9: Device not in DB
        make_row(10,'Bùi Máy Lạ','42','','HN','99990010',
                 '15/03/2026 20:00:00','15/03/2026 23:00:00', vs,'','Máy XYZ Phantom'),
        # 10: PTV not in DB
        make_row(11,'Đinh PTV Lạ','38','','HN','99990011',
                 '15/03/2026 20:00:00','15/03/2026 23:00:00','BS Giả Mạo XYZ999','','Máy thận nhân tạo_F10'),
        # 11: Phụ 1 not in DB
        make_row(12,'Mai Phụ Lạ','28','','HN','99990012',
                 '15/03/2026 21:00:00','15/03/2026 23:00:00', vs,'NV Giả Mạo 777','Máy thận nhân tạo_F11'),
        # 12: VALID #2
        make_row(13,'Trịnh OK Hai','','55','Hà Nội','99990013',
                 '16/03/2026 08:00:00','16/03/2026 12:00:00', vs,'','Máy thận nhân tạo_F2'),
        # 13: DUPLICATE same device+time as row 12
        make_row(14,'Ngô Trùng Lặp','40','','BN','99990014',
                 '16/03/2026 08:00:00','16/03/2026 12:00:00', vs,'','Máy thận nhân tạo_F2'),
        # 14: EMPTY ROW
        ['15'] + [''] * 28,
        # 15: MULTIPLE ERRORS
        make_row(16,'X','999','','','99990016',
                 '15/03/2026 20:00:00','15/03/2026 10:00:00','UnknownDoc999','','Máy Ghost'),
    ]

    filepath = create_xls(rows, 'test_validation.xls')
    c, data = upload_excel(filepath)
    errors = data.get('errors', [])

    print(f"\n  Result: success={data.get('success')}, total={data.get('total')}, "
          f"skipped={data.get('skipped')}, errors={len(errors)}")

    def find_err(keyword):
        return [e for e in errors if keyword in e.get('name', '')]

    # Check each case
    log('PASS' if data.get('success',0) >= 2 else 'FAIL',
        'T2.1 Valid rows accepted', f"success={data.get('success')}")

    e = find_err('A')
    # Name 'A' is exact match
    short = [x for x in errors if x.get('name') == 'A']
    log('PASS' if short else 'FAIL', 'T2.2 Short name (1 char) rejected',
        str(short[0].get('errors',[])) if short else '')

    num = [x for x in errors if x.get('name') == '12345']
    log('PASS' if num else 'FAIL', 'T2.3 Number-only name rejected',
        str(num[0].get('errors',[])) if num else '')

    log('PASS' if find_err('Tuổi Âm') else 'FAIL', 'T2.4 Negative age rejected',
        str(find_err('Tuổi Âm')[0].get('errors',[])) if find_err('Tuổi Âm') else '')

    log('PASS' if find_err('Tuổi Lớn') else 'FAIL', 'T2.5 Age > 120 rejected',
        str(find_err('Tuổi Lớn')[0].get('errors',[])) if find_err('Tuổi Lớn') else '')

    log('PASS' if find_err('Tuổi Chữ') else 'FAIL', 'T2.6 Age text rejected',
        str(find_err('Tuổi Chữ')[0].get('errors',[])) if find_err('Tuổi Chữ') else '')

    log('PASS' if find_err('Ngày Sai') else 'FAIL', 'T2.7 Bad date rejected',
        str(find_err('Ngày Sai')[0].get('errors',[])) if find_err('Ngày Sai') else '')

    log('PASS' if find_err('Ngày Ngược') else 'FAIL', 'T2.8 End < Start rejected',
        str(find_err('Ngày Ngược')[0].get('errors',[])) if find_err('Ngày Ngược') else '')

    log('PASS' if find_err('Thiếu Máy') else 'FAIL', 'T2.9 Missing device rejected',
        str(find_err('Thiếu Máy')[0].get('errors',[])) if find_err('Thiếu Máy') else '')

    log('PASS' if find_err('Máy Lạ') else 'FAIL', 'T2.10 Unknown device rejected',
        str(find_err('Máy Lạ')[0].get('errors',[])) if find_err('Máy Lạ') else '')

    log('PASS' if find_err('PTV Lạ') else 'FAIL', 'T2.11 PTV not in DB rejected',
        str(find_err('PTV Lạ')[0].get('errors',[])) if find_err('PTV Lạ') else '')

    log('PASS' if find_err('Phụ Lạ') else 'FAIL', 'T2.12 Phụ 1 not in DB rejected',
        str(find_err('Phụ Lạ')[0].get('errors',[])) if find_err('Phụ Lạ') else '')

    log('PASS' if find_err('Trùng Lặp') else 'FAIL', 'T2.13 Duplicate same device+time rejected',
        str(find_err('Trùng Lặp')[0].get('errors',[])) if find_err('Trùng Lặp') else '')

    multi = [x for x in errors if x.get('name') == 'X']
    log('PASS' if multi and len(multi[0].get('errors',[])) >= 3 else 'FAIL',
        'T2.14 Multiple errors per row',
        f"{len(multi[0].get('errors',[]))} errors" if multi else '')

    log('PASS' if data.get('total',0) < len(rows) else 'FAIL',
        'T2.15 Empty row skipped', f"total={data.get('total')} < rows={len(rows)}")


# ============================================================
# PART 3: DUPLICATE RE-IMPORT
# ============================================================
def test_duplicate_reimport():
    print("\n" + "=" * 60)
    print("PART 3: DUPLICATE DETECTION (re-import)")
    print("=" * 60)

    _, staff_list = api_get('/api/nhan-vien')
    vs = staff_list[0]['ho_ten'] if staff_list else 'Unknown'

    rows = [make_row(1,'Nguyễn Reimport','50','','BN','88880001',
                     '20/03/2026 08:00:00','20/03/2026 12:00:00', vs,'','Máy thận nhân tạo_F20')]
    filepath = create_xls(rows, 'test_reimport.xls')

    c1, d1 = upload_excel(filepath)
    c2, d2 = upload_excel(filepath)
    print(f"  1st: success={d1.get('success')}, 2nd: success={d2.get('success')}")

    log('PASS' if d2.get('success',1) == 0 and d2.get('skipped',0) > 0 else 'FAIL',
        'T3.1 Re-import detected duplicate',
        str(d2.get('errors',[{}])[0].get('errors',[])) if d2.get('errors') else '')


# ============================================================
# PART 4: MANUAL API ENTRY
# ============================================================
def test_manual_entry():
    print("\n" + "=" * 60)
    print("PART 4: MANUAL ENTRY VIA API")
    print("=" * 60)

    _, staff_list = api_get('/api/nhan-vien')
    _, dev_list = api_get('/api/thiet-bi')
    sid = staff_list[0]['id'] if staff_list else None
    did = dev_list[0]['id'] if dev_list else None
    dname = dev_list[0]['ten_thiet_bi'] if dev_list else ''

    # T4.1: Valid
    c, d = api_post('/api/phien-dieu-tri', {
        'ho_ten':'Nguyễn Manual Test','tuoi':45,'dia_chi':'BN','so_ho_so':'77770001',
        'ngay_bat_dau':'2026-03-17 08:00:00','ngay_ket_thuc':'2026-03-17 12:00:00',
        'thiet_bi_id':did,'may_thuc_hien':dname,'ptv_chinh_id':sid,'ghi_chu':'Test'
    })
    log('PASS' if c in (200,201) else 'FAIL', 'T4.1 Valid manual entry', f'code={c}')

    # T4.2: Empty name
    c, d = api_post('/api/phien-dieu-tri', {'ho_ten':'','tuoi':30,'thiet_bi_id':did,'may_thuc_hien':'T'})
    log('PASS' if c >= 400 else 'FAIL', 'T4.2 Empty name', f'code={c} (manual allows empty — note)')

    # T4.3: Null device
    c, d = api_post('/api/phien-dieu-tri', {'ho_ten':'Test No Dev','tuoi':30})
    log('PASS' if c in (200,201) else 'FAIL', 'T4.3 Null device (allowed manual)', f'code={c}')

    # T4.4: GET session list
    c, d = api_get('/api/phien-dieu-tri')
    log('PASS' if c == 200 and isinstance(d, list) else 'FAIL', 'T4.4 GET sessions', f'{len(d)} sessions')

    # T4.5: DELETE test sessions
    c, sessions = api_get('/api/phien-dieu-tri')
    cleaned = 0
    for s in sessions:
        if 'Manual Test' in s.get('ho_ten','') or 'Test No Dev' in s.get('ho_ten',''):
            requests.delete(f"{BASE}/api/phien-dieu-tri/{s['id']}")
            cleaned += 1
    log('PASS' if cleaned > 0 else 'FAIL', 'T4.5 DELETE cleanup', f'deleted {cleaned}')


# ============================================================
# PART 5: REAL FILE
# ============================================================
def test_real_file():
    print("\n" + "=" * 60)
    print("PART 5: REAL FILE (011.3.xls)")
    print("=" * 60)

    real_file = r'D:\QL may than\011.3.xls'
    if not os.path.exists(real_file):
        log('FAIL', 'T5.1 Real file exists', 'not found')
        return
    log('PASS', 'T5.1 Real file exists', real_file)

    c, d = upload_excel(real_file)
    print(f"  success={d.get('success')}, total={d.get('total')}, skipped={d.get('skipped')}")
    errors = d.get('errors', [])
    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors[:5]:
            for err in e.get('errors', []):
                print(f"    Row {e['row']} ({e['name']}): {err}")

    log('PASS' if d.get('ok') else 'FAIL', 'T5.2 Real file parsed',
        f"{d.get('success')}/{d.get('total')} imported, {d.get('skipped')} skipped")


# ============================================================
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  COMPREHENSIVE TEST SUITE — Session Import Validation")
    print("=" * 60)

    try:
        import xlwt
    except ImportError:
        os.system('pip install xlwt -q')
        import xlwt

    try:
        requests.get(f'{BASE}/', timeout=3)
    except:
        print("ERROR: Server not running at", BASE)
        sys.exit(1)

    test_file_validation()
    test_row_validation()
    test_duplicate_reimport()
    test_manual_entry()
    test_real_file()

    # SUMMARY
    total = RESULTS['passed'] + RESULTS['failed']
    pct = (RESULTS['passed'] / total * 100) if total else 0

    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"  ✅ Passed: {RESULTS['passed']}/{total}")
    print(f"  ❌ Failed: {RESULTS['failed']}/{total}")
    print(f"  📊 Score:  {pct:.1f}%\n")

    if RESULTS['failed'] > 0:
        print("  FAILED TESTS:")
        for t in RESULTS['tests']:
            if t['status'] == 'FAIL':
                print(f"    ❌ {t['name']}: {t['detail']}")
        print()
