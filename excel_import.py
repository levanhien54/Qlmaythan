# -*- coding: utf-8 -*-
"""
Logic import phiên điều trị từ file Excel — DÙNG CHUNG cho:
  - Web API  (server.py  → POST /api/phien-dieu-tri/import-excel)
  - Desktop UI (ui/pages/sessions_page.py → nút "Import Excel")

Tách khỏi server.py để không phải chạy Flask vẫn import được, và để cả hai
giao diện dùng đúng một bộ validation/matching (tránh lệch hành vi).
"""
import re
from database.queries import nhan_vien, thiet_bi, phien_dieu_tri
from matching import (
    find_staff as _find_staff,
    find_device as _find_device,
    parse_excel_datetime,
    check_session_overlap,
    is_device_blocked,
    safe_str,
    find_header_row,
    build_column_mapping,
)


class ExcelParseError(Exception):
    """Không đọc được workbook hoặc file không đủ dòng (caller map → 400)."""


def parse_workbook(file_bytes: bytes, ext: str):
    """Đọc bytes Excel → (rows_data, datemode).

    ext: 'xls' hoặc 'xlsx'. Raise ExcelParseError nếu không đọc được.
    """
    rows_data = []
    datemode = 0
    try:
        if ext == 'xls':
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_bytes)
            sh = wb.sheet_by_index(0)
            for i in range(sh.nrows):
                rows_data.append([sh.cell_value(i, j) for j in range(sh.ncols)])
            # Windows=0, Mac=1
            datemode = getattr(wb, 'datemode', 0) or 0
        else:
            import openpyxl, io as sio
            wb = openpyxl.load_workbook(sio.BytesIO(file_bytes), data_only=True)
            sh = wb.active
            for row in sh.iter_rows(values_only=True):
                rows_data.append(list(row))
    except Exception as e:
        raise ExcelParseError(f'Không thể đọc file Excel: {str(e)}') from e

    if len(rows_data) < 12:
        raise ExcelParseError(
            f'File chỉ có {len(rows_data)} dòng, cần ít nhất 12 dòng (header + data)'
        )
    return rows_data, datemode


def import_sessions(rows_data, datemode: int = 0) -> dict:
    """Xử lý + chèn phiên điều trị từ rows_data đã parse.

    Trả về dict: {'success', 'errors', 'skipped', 'total'} (errors đã cắt 100 dòng
    bởi caller nếu cần — ở đây trả full).
    """
    # ===== FIND HEADER + BUILD COLUMN MAPPING =====
    header_row = find_header_row(rows_data)
    col_map = build_column_mapping(rows_data, header_row)
    data_start = header_row + 2

    # ===== PRE-LOAD DB =====
    all_staff = nhan_vien.get_all()
    all_devices = thiet_bi.get_all()
    existing_sessions = phien_dieu_tri.get_all()

    # Build lookup list for device matching
    device_list = []  # (id, ten, lowercase_nospace, tinh_trang)
    for d in all_devices:
        device_list.append((d['id'], d['ten_thiet_bi'],
                            d['ten_thiet_bi'].lower().replace(' ', ''),
                            d.get('tinh_trang', '')))

    def parse_datetime(v):
        return parse_excel_datetime(v, xls_datemode=datemode)

    def find_staff_strict(name_raw):
        return _find_staff(name_raw, all_staff)

    def find_device_strict(name_raw):
        return _find_device(name_raw, device_list)

    def check_duplicate(thiet_bi_id, ngay_bat_dau, ngay_ket_thuc, ho_ten):
        return check_session_overlap(
            thiet_bi_id, ngay_bat_dau, ngay_ket_thuc, existing_sessions,
        )

    results = {'success': 0, 'errors': [], 'skipped': 0, 'total': 0}

    def col(row, name, default=''):
        idx = col_map.get(name)
        if idx is None or idx >= len(row):
            return default
        return row[idx]

    max_col_needed = max(col_map.values()) + 1
    for idx in range(data_start, len(rows_data)):
        row = rows_data[idx]
        while len(row) < max_col_needed:
            row.append('')

        ho_ten = safe_str(col(row, 'ho_ten'))
        if not ho_ten:
            continue

        results['total'] += 1
        row_num = idx + 1
        errors_this_row = []

        try:
            # ── VALIDATE HỌ TÊN ──
            if len(ho_ten) < 2:
                errors_this_row.append(f'Họ tên quá ngắn: "{ho_ten}"')
            if not re.search(r'[a-zA-ZÀ-ỹ]', ho_ten):
                errors_this_row.append(f'Họ tên không chứa chữ cái: "{ho_ten}"')

            # ── VALIDATE TUỔI ──
            tuoi = 0
            tuoi_nam = col(row, 'tuoi_nam')
            tuoi_nu = col(row, 'tuoi_nu')
            try:
                if tuoi_nam and str(tuoi_nam).strip():
                    tuoi = int(float(str(tuoi_nam).strip()))
                elif tuoi_nu and str(tuoi_nu).strip():
                    tuoi = int(float(str(tuoi_nu).strip()))
            except Exception:
                errors_this_row.append(f'Tuổi không hợp lệ: Nam="{tuoi_nam}" Nữ="{tuoi_nu}"')
            if tuoi != 0 and (tuoi < 1 or tuoi > 120):
                errors_this_row.append(f'Tuổi ngoài phạm vi (1-120): {tuoi}')

            # ── ĐỊA CHỈ ──
            dia_chi = safe_str(col(row, 'dia_chi'))

            # ── SỐ HỒ SƠ ──
            so_ho_so = ''
            try:
                v = col(row, 'so_ho_so')
                if v:
                    so_ho_so = str(int(float(v))) if isinstance(v, (int, float)) else safe_str(v)
            except Exception:
                so_ho_so = safe_str(col(row, 'so_ho_so'))

            # ── VALIDATE NGÀY GIỜ ──
            ngay_bat_dau = parse_datetime(col(row, 'ngay_bat_dau'))
            ngay_ket_thuc = parse_datetime(col(row, 'ngay_ket_thuc'))

            if not ngay_bat_dau:
                raw_bd = safe_str(col(row, 'ngay_bat_dau'))
                errors_this_row.append(
                    f'Ngày bắt đầu không đọc được: "{raw_bd}"' if raw_bd
                    else 'Thiếu ngày bắt đầu'
                )
            if not ngay_ket_thuc:
                raw_kt = safe_str(col(row, 'ngay_ket_thuc'))
                if raw_kt:
                    errors_this_row.append(f'Ngày kết thúc không đọc được: "{raw_kt}"')

            if ngay_bat_dau and ngay_ket_thuc and ngay_ket_thuc <= ngay_bat_dau:
                errors_this_row.append(
                    f'Ngày KT ({ngay_ket_thuc}) phải sau ngày BĐ ({ngay_bat_dau})'
                )

            # ── VALIDATE THIẾT BỊ (BẮT BUỘC) ──
            may_raw = safe_str(col(row, 'may'))
            thiet_bi_id, may_thuc_hien, may_status = find_device_strict(may_raw)
            if not may_raw:
                errors_this_row.append('Thiếu thông tin máy thực hiện (cột AC)')
            elif thiet_bi_id is None:
                errors_this_row.append(
                    f'Không tìm thấy thiết bị "{may_raw}" trong CSDL. '
                    f'Hãy thêm thiết bị trước khi nhập.'
                )
            elif is_device_blocked(may_status):
                errors_this_row.append(
                    f'Máy "{may_thuc_hien}" đang ở trạng thái "{may_status}" — '
                    f'không thể nhập phiên điều trị cho máy này.'
                )

            # ── VALIDATE PTV CHÍNH (BẮT BUỘC NẾU CÓ) ──
            ptv_raw = safe_str(col(row, 'ptv_chinh'))
            ptv_chinh_id = None
            if ptv_raw:
                ptv_result, ptv_name = find_staff_strict(ptv_raw)
                if ptv_result == -1:
                    errors_this_row.append(
                        f'PTV chính "{ptv_raw}" không có trong CSDL. '
                        f'Hãy thêm nhân viên trước.'
                    )
                else:
                    ptv_chinh_id = ptv_result

            # ── VALIDATE PHỤ 1 (NẾU CÓ) ──
            phu1_raw = safe_str(col(row, 'phu_1'))
            phu_1_id = None
            if phu1_raw:
                phu1_result, phu1_name = find_staff_strict(phu1_raw)
                if phu1_result == -1:
                    errors_this_row.append(
                        f'Phụ 1 "{phu1_raw}" không có trong CSDL. '
                        f'Hãy thêm nhân viên trước.'
                    )
                else:
                    phu_1_id = phu1_result

            # ── CHECK TRÙNG LẶP ──
            if thiet_bi_id and ngay_bat_dau:
                dup_msg = check_duplicate(thiet_bi_id, ngay_bat_dau, ngay_ket_thuc, ho_ten)
                if dup_msg:
                    errors_this_row.append(dup_msg)

            # ── GHI CHÚ ──
            ghi_chu = safe_str(col(row, 'ghi_chu'))

            # ── QUYẾT ĐỊNH: CÓ LỖI → KHÔNG NHẬP ──
            if errors_this_row:
                results['errors'].append({
                    'row': row_num,
                    'name': ho_ten,
                    'errors': errors_this_row
                })
                results['skipped'] += 1
                continue

            # ── INSERT (chỉ khi pass tất cả validation) ──
            try:
                phien_dieu_tri.create(
                    ho_ten=ho_ten,
                    tuoi=tuoi,
                    dia_chi=dia_chi,
                    so_ho_so=so_ho_so,
                    ngay_bat_dau=ngay_bat_dau,
                    ngay_ket_thuc=ngay_ket_thuc,
                    thiet_bi_id=thiet_bi_id,
                    may_thuc_hien=may_thuc_hien,
                    ptv_chinh_id=ptv_chinh_id,
                    phu_1_id=phu_1_id,
                    ghi_chu=ghi_chu
                )
                results['success'] += 1
            except phien_dieu_tri.DuplicateSessionError as e:
                # Race condition — upload song song đã insert cùng phiên.
                results['errors'].append({
                    'row': row_num, 'name': ho_ten,
                    'errors': [f'Trùng lặp (race): {e}']
                })
                results['skipped'] += 1
                continue

            # Add to existing list to detect duplicates within same file
            existing_sessions.append({
                'thiet_bi_id': thiet_bi_id,
                'ngay_bat_dau': ngay_bat_dau,
                'ngay_ket_thuc': ngay_ket_thuc,
                'ho_ten': ho_ten
            })

        except Exception as e:
            results['errors'].append({
                'row': row_num,
                'name': ho_ten,
                'errors': [f'Lỗi hệ thống: {str(e)}']
            })
            results['skipped'] += 1

    return results


def import_from_path(file_path: str) -> dict:
    """Đọc file Excel theo đường dẫn rồi import. Dùng cho Desktop UI.

    Trả về results dict. Raise ExcelParseError nếu file lỗi/đuôi sai.
    """
    import os
    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
    if ext not in ('xls', 'xlsx'):
        raise ExcelParseError(f'Định dạng .{ext} không hỗ trợ. Chỉ chấp nhận .xls hoặc .xlsx')
    if not os.path.exists(file_path):
        raise ExcelParseError(f'File không tồn tại: {file_path}')
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    if not file_bytes:
        raise ExcelParseError('File rỗng (0 bytes)')
    rows_data, datemode = parse_workbook(file_bytes, ext)
    return import_sessions(rows_data, datemode)
