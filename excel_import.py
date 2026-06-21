# -*- coding: utf-8 -*-
"""
Logic import phiên điều trị từ file Excel — DÙNG CHUNG cho:
  - Web API  (server.py  → POST /api/phien-dieu-tri/import-excel + /preview-excel)
  - Desktop UI (ui/pages/sessions_page.py → nút "Import Excel")

Tách khỏi server.py để không phải chạy Flask vẫn import được, và để cả hai
giao diện dùng đúng một bộ validation/matching (tránh lệch hành vi).

Quy trình tách 2 pha: _evaluate_row() validate + map 1 dòng (KHÔNG ghi DB) —
dùng cho cả preview (xem trước) lẫn import (ghi thật).
"""
import re
import datetime
from database.queries import nhan_vien, thiet_bi, phien_dieu_tri
from matching import (
    find_staff as _find_staff,
    find_device as _find_device,
    parse_excel_datetime,
    check_session_overlap,
    is_device_blocked,
    is_device_warning,
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


def _prepare(rows_data, datemode):
    """Chuẩn bị bối cảnh dùng chung cho cả import và preview: tìm header, build
    column mapping, preload DB, và các helper. existing_sessions được CHIA SẺ
    (mutable) để phát hiện trùng trong cùng file."""
    header_row = find_header_row(rows_data)
    col_map = build_column_mapping(rows_data, header_row)
    data_start = header_row + 2

    all_staff = nhan_vien.get_all()
    all_devices = thiet_bi.get_all()
    existing_sessions = phien_dieu_tri.get_all()

    device_list = []  # (id, ten, lowercase_nospace, tinh_trang)
    for d in all_devices:
        device_list.append((d['id'], d['ten_thiet_bi'],
                            d['ten_thiet_bi'].lower().replace(' ', ''),
                            d.get('tinh_trang', '')))

    def col(row, name, default=''):
        idx = col_map.get(name)
        if idx is None or idx >= len(row):
            return default
        return row[idx]

    return {
        'col': col,
        'data_start': data_start,
        'max_col_needed': max(col_map.values()) + 1,
        'existing_sessions': existing_sessions,
        'parse_datetime': lambda v: parse_excel_datetime(v, xls_datemode=datemode),
        'find_staff': lambda n: _find_staff(n, all_staff),
        'find_device': lambda n: _find_device(n, device_list),
        'check_duplicate': lambda tb, bd, kt: check_session_overlap(tb, bd, kt, existing_sessions),
    }


def _evaluate_row(row, ctx) -> dict:
    """Validate + map MỘT dòng (KHÔNG ghi DB). Trả record gồm các trường để
    insert, danh sách 'errors', và tên hiển thị (ptv/phụ) cho preview."""
    col = ctx['col']
    parse_datetime = ctx['parse_datetime']
    errors = []
    warnings = []

    ho_ten = safe_str(col(row, 'ho_ten'))

    # ── VALIDATE HỌ TÊN ──
    if len(ho_ten) < 2:
        errors.append(f'Họ tên quá ngắn: "{ho_ten}"')
    if not re.search(r'[a-zA-ZÀ-ỹ]', ho_ten):
        errors.append(f'Họ tên không chứa chữ cái: "{ho_ten}"')

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
        errors.append(f'Tuổi không hợp lệ: Nam="{tuoi_nam}" Nữ="{tuoi_nu}"')
    if tuoi != 0 and (tuoi < 1 or tuoi > 120):
        errors.append(f'Tuổi ngoài phạm vi (1-120): {tuoi}')

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
        errors.append(
            f'Ngày bắt đầu không đọc được: "{raw_bd}"' if raw_bd
            else 'Thiếu ngày bắt đầu'
        )
    if not ngay_ket_thuc:
        raw_kt = safe_str(col(row, 'ngay_ket_thuc'))
        if raw_kt:
            errors.append(f'Ngày kết thúc không đọc được: "{raw_kt}"')

    if ngay_bat_dau and ngay_ket_thuc and ngay_ket_thuc <= ngay_bat_dau:
        errors.append(f'Ngày KT ({ngay_ket_thuc}) phải sau ngày BĐ ({ngay_bat_dau})')

    # ── VALIDATE THIẾT BỊ (BẮT BUỘC) ──
    may_raw = safe_str(col(row, 'may'))
    thiet_bi_id, may_thuc_hien, may_status = ctx['find_device'](may_raw)
    if not may_raw:
        errors.append('Thiếu thông tin máy thực hiện (cột AC)')
    elif thiet_bi_id is None:
        errors.append(
            f'Không tìm thấy thiết bị "{may_raw}" trong CSDL. '
            f'Hãy thêm thiết bị trước khi nhập.'
        )
    elif is_device_blocked(may_status):
        errors.append(
            f'Máy "{may_thuc_hien}" đang ở trạng thái "{may_status}" — '
            f'không thể nhập phiên điều trị cho máy này.'
        )
    elif is_device_warning(may_status):
        warnings.append(
            f'Máy "{may_thuc_hien}" đang ở trạng thái "{may_status}" — '
            f'kiểm tra lại trước khi nhập phiên cho máy này.'
        )

    # ── VALIDATE PTV CHÍNH (NẾU CÓ) ──
    ptv_raw = safe_str(col(row, 'ptv_chinh'))
    ptv_chinh_id = None
    ptv_chinh_ten = ''
    if ptv_raw:
        ptv_result, ptv_name = ctx['find_staff'](ptv_raw)
        if ptv_result == -1:
            errors.append(
                f'PTV chính "{ptv_raw}" không có trong CSDL. Hãy thêm nhân viên trước.'
            )
        else:
            ptv_chinh_id = ptv_result
            ptv_chinh_ten = ptv_name

    # ── VALIDATE PHỤ 1 (NẾU CÓ) ──
    phu1_raw = safe_str(col(row, 'phu_1'))
    phu_1_id = None
    phu_1_ten = ''
    if phu1_raw:
        phu1_result, phu1_name = ctx['find_staff'](phu1_raw)
        if phu1_result == -1:
            errors.append(
                f'Phụ 1 "{phu1_raw}" không có trong CSDL. Hãy thêm nhân viên trước.'
            )
        else:
            phu_1_id = phu1_result
            phu_1_ten = phu1_name

    # ── CHECK TRÙNG LẶP (đè giờ cùng máy) ──
    if thiet_bi_id and ngay_bat_dau:
        dup_msg = ctx['check_duplicate'](thiet_bi_id, ngay_bat_dau, ngay_ket_thuc)
        if dup_msg:
            errors.append(dup_msg)

    # ── C: NGÀY PHI LÝ (chặn lỗi gõ năm; biên tuyệt đối → không phụ thuộc đồng hồ) ──
    if ngay_bat_dau:
        try:
            yr = int(ngay_bat_dau[:4])
            if yr < 2000 or yr > 2100:
                errors.append(f'Ngày bắt đầu bất thường: {ngay_bat_dau[:10]} (ngoài 2000–2100)')
        except (ValueError, TypeError):
            pass

    # ── D: THỜI LƯỢNG PHI LÝ (lọc máu ~4h; hợp lệ 10 phút – 12 giờ) ──
    if ngay_bat_dau and ngay_ket_thuc and ngay_ket_thuc > ngay_bat_dau:
        try:
            mins = (datetime.datetime.strptime(ngay_ket_thuc, '%Y-%m-%d %H:%M:%S')
                    - datetime.datetime.strptime(ngay_bat_dau, '%Y-%m-%d %H:%M:%S')
                    ).total_seconds() / 60
            if mins < 10 or mins > 12 * 60:
                errors.append(f'Thời lượng phiên bất thường: {mins:.0f} phút (hợp lệ 10 phút – 12 giờ)')
        except (ValueError, TypeError):
            pass

    # ── A (CẢNH BÁO): cùng bệnh nhân đè giờ trên MÁY KHÁC (1 người không thể ở 2 máy) ──
    if ho_ten and ngay_bat_dau:
        _nho = ho_ten.strip().lower()
        SENT = '9999-12-31 23:59:59'
        new_end = ngay_ket_thuc or SENT
        for s in ctx['existing_sessions']:
            if s.get('thiet_bi_id') == thiet_bi_id:
                continue  # cùng máy → đã do overlap-check xử lý
            if (s.get('ho_ten') or '').strip().lower() != _nho:
                continue
            s_start = s.get('ngay_bat_dau') or ''
            s_end = s.get('ngay_ket_thuc') or SENT
            if s_start and ngay_bat_dau < s_end and new_end > s_start:
                warnings.append(
                    f"Bệnh nhân '{ho_ten}' đè giờ trên MÁY KHÁC (từ {s_start}) "
                    f"— 1 người không thể ở 2 máy cùng lúc"
                )
                break

    ghi_chu = safe_str(col(row, 'ghi_chu'))

    return {
        'ho_ten': ho_ten, 'tuoi': tuoi, 'dia_chi': dia_chi, 'so_ho_so': so_ho_so,
        'ngay_bat_dau': ngay_bat_dau, 'ngay_ket_thuc': ngay_ket_thuc,
        'thiet_bi_id': thiet_bi_id, 'may_thuc_hien': may_thuc_hien,
        'ptv_chinh_id': ptv_chinh_id, 'ptv_chinh_ten': ptv_chinh_ten,
        'phu_1_id': phu_1_id, 'phu_1_ten': phu_1_ten,
        'ghi_chu': ghi_chu, 'errors': errors, 'warnings': warnings,
    }


def _iter_data_rows(rows_data, ctx):
    """Yield (row_num, row, ho_ten) cho từng dòng có họ tên (bỏ dòng trống)."""
    col = ctx['col']
    for idx in range(ctx['data_start'], len(rows_data)):
        row = rows_data[idx]
        while len(row) < ctx['max_col_needed']:
            row.append('')
        ho_ten = safe_str(col(row, 'ho_ten'))
        if not ho_ten:
            continue
        yield idx + 1, row, ho_ten


def import_sessions(rows_data, datemode: int = 0) -> dict:
    """Xử lý + CHÈN phiên điều trị từ rows_data đã parse.

    Trả về dict: {'success', 'errors', 'skipped', 'total'}.
    """
    ctx = _prepare(rows_data, datemode)
    results = {'success': 0, 'errors': [], 'skipped': 0, 'total': 0}

    for row_num, row, ho_ten in _iter_data_rows(rows_data, ctx):
        results['total'] += 1
        try:
            rec = _evaluate_row(row, ctx)
            if rec['errors']:
                results['errors'].append({'row': row_num, 'name': ho_ten, 'errors': rec['errors']})
                results['skipped'] += 1
                continue
            # Lưới an toàn cuối: kiểm tra trùng giờ với DB LIVE ngay trước khi ghi.
            # check_session_overlap (trong _evaluate_row) chỉ soi snapshot nạp 1 lần
            # lúc bắt đầu → bỏ sót phiên do tiến trình khác commit sau đó (import
            # đồng thời) gây double-book. SQLite không có ràng buộc overlap nên đây
            # là chốt chặn ở tầng app, dùng CHUNG check_time_overlap như API.
            if rec['thiet_bi_id'] and rec['ngay_bat_dau']:
                live = phien_dieu_tri.check_time_overlap(
                    rec['thiet_bi_id'], rec['ngay_bat_dau'], rec['ngay_ket_thuc'])
                if live:
                    results['errors'].append({'row': row_num, 'name': ho_ten, 'errors': [
                        f"Trùng thời gian (DB): máy đang có phiên của \"{live['ho_ten']}\" "
                        f"từ {live['ngay_bat_dau']} đến {live['ngay_ket_thuc'] or '(chưa kết thúc)'}"
                    ]})
                    results['skipped'] += 1
                    continue
            try:
                phien_dieu_tri.create(
                    ho_ten=rec['ho_ten'], tuoi=rec['tuoi'], dia_chi=rec['dia_chi'],
                    so_ho_so=rec['so_ho_so'], ngay_bat_dau=rec['ngay_bat_dau'],
                    ngay_ket_thuc=rec['ngay_ket_thuc'], thiet_bi_id=rec['thiet_bi_id'],
                    may_thuc_hien=rec['may_thuc_hien'], ptv_chinh_id=rec['ptv_chinh_id'],
                    phu_1_id=rec['phu_1_id'], ghi_chu=rec['ghi_chu'],
                )
                results['success'] += 1
            except phien_dieu_tri.DuplicateSessionError as e:
                results['errors'].append({'row': row_num, 'name': ho_ten,
                                          'errors': [f'Trùng lặp (race): {e}']})
                results['skipped'] += 1
                continue
            # Thêm vào danh sách để bắt trùng trong cùng file
            ctx['existing_sessions'].append({
                'thiet_bi_id': rec['thiet_bi_id'], 'ngay_bat_dau': rec['ngay_bat_dau'],
                'ngay_ket_thuc': rec['ngay_ket_thuc'], 'ho_ten': rec['ho_ten'],
            })
        except Exception as e:
            results['errors'].append({'row': row_num, 'name': ho_ten,
                                      'errors': [f'Lỗi hệ thống: {str(e)}']})
            results['skipped'] += 1

    return results


def preview_sessions(rows_data, datemode: int = 0, limit: int = 500) -> dict:
    """Như import_sessions nhưng KHÔNG ghi DB — trả KẾ HOẠCH để người dùng xem
    trước: mỗi dòng hợp lệ/lỗi, máy & PTV được map, lý do lỗi.

    Trả: {'total', 'valid', 'invalid', 'rows': [...]} (rows cắt tối đa `limit`).
    """
    ctx = _prepare(rows_data, datemode)
    out = {'total': 0, 'valid': 0, 'invalid': 0, 'warnings': 0, 'rows': []}

    for row_num, row, ho_ten in _iter_data_rows(rows_data, ctx):
        out['total'] += 1
        try:
            rec = _evaluate_row(row, ctx)
        except Exception as e:
            rec = {'ho_ten': ho_ten, 'errors': [f'Lỗi hệ thống: {str(e)}'], 'warnings': []}

        ok = not rec['errors']
        if rec.get('warnings'):
            out['warnings'] += 1
        if ok:
            out['valid'] += 1
            # Mô phỏng đã nhập để bắt trùng trong cùng file (giống import thật)
            ctx['existing_sessions'].append({
                'thiet_bi_id': rec.get('thiet_bi_id'),
                'ngay_bat_dau': rec.get('ngay_bat_dau'),
                'ngay_ket_thuc': rec.get('ngay_ket_thuc'),
                'ho_ten': ho_ten,
            })
        else:
            out['invalid'] += 1

        if len(out['rows']) < limit:
            out['rows'].append({
                'row': row_num,
                'ho_ten': rec.get('ho_ten', ho_ten),
                'status': 'ok' if ok else 'error',
                'errors': rec.get('errors', []),
                'warnings': rec.get('warnings', []),
                'may': rec.get('may_thuc_hien', ''),
                'ptv': rec.get('ptv_chinh_ten', ''),
                'ngay_bat_dau': rec.get('ngay_bat_dau'),
                'ngay_ket_thuc': rec.get('ngay_ket_thuc'),
            })

    return out


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
    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        raise ExcelParseError('File quá lớn (>50MB)')  # ngang với giới hạn web
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    if not file_bytes:
        raise ExcelParseError('File rỗng (0 bytes)')
    rows_data, datemode = parse_workbook(file_bytes, ext)
    return import_sessions(rows_data, datemode)
