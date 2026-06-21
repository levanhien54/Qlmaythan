# -*- coding: utf-8 -*-
"""
Pure matching helpers dùng cho Excel import.
Tách khỏi server.py để test unit được.
"""
import re
import datetime as _datetime
import unicodedata


def _norm(s: str) -> str:
    """Lowercase + strip + NFC normalize — dùng so sánh chuỗi Tiếng Việt
    có nguồn từ Mac (NFD) vs Windows (NFC)."""
    if s is None:
        return ''
    return unicodedata.normalize('NFC', str(s)).lower().strip()


def _extract_numbers(s: str) -> set:
    """Trả về tập các số nguyên xuất hiện trong chuỗi (vd 'số 10' → {10}).
    Dùng để so khớp số máy CHÍNH XÁC, tránh substring 'số 1' ⊂ 'số 10'."""
    return {int(n) for n in re.findall(r'\d+', s)}


def _word_substring(small: str, big: str) -> bool:
    """True nếu `small` nằm trong `big` ở RANH GIỚI TỪ (đầu/cuối chuỗi hoặc cạnh
    dấu cách). Tránh 'lê văn a' khớp nhầm 'lê văn an' (token cuối 'a' ≠ 'an')."""
    if not small or not big:
        return False
    if small == big:
        return True
    i = big.find(small)
    while i != -1:
        before = i == 0 or big[i - 1] == ' '
        after = i + len(small) == len(big) or big[i + len(small)] == ' '
        if before and after:
            return True
        i = big.find(small, i + 1)
    return False


DATE_FORMATS = [
    # Việt Nam style: dd/mm/yyyy
    '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y',
    # ISO-like: yyyy-mm-dd (space và T separator)
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
    # Dashes dd-mm-yyyy
    '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%d-%m-%Y',
    # Dots dd.mm.yyyy
    '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%d.%m.%Y',
    # Slashes yyyy/mm/dd (ít phổ biến)
    '%Y/%m/%d %H:%M:%S', '%Y/%m/%d',
]

# Trạng thái máy không cho phép nhập phiên — substring match (lowercase).
BLOCKED_DEVICE_STATES = ('hỏng', 'thanh lý', 'báo lỗi')

# Ngưỡng tối thiểu để coi một SỐ Excel là serial NGÀY. parse_excel_datetime chỉ
# chạy trên cột ngày (BĐ/KT) nên số trong cột này nên là serial. ~1990-01-01
# (serial 32874) đủ bao mọi hồ sơ điều trị thực tế mà vẫn loại số nhỏ vô nghĩa.
# Trước đây ngưỡng 40000 (~2009) làm RỚT âm thầm mọi ngày trước 2009.
_MIN_EXCEL_DATE_SERIAL = 32874


# Layout mặc định file 011.3.xls (BV BN Số 2).
DEFAULT_COLUMN_LAYOUT = {
    'stt': 0, 'ho_ten': 1,
    'tuoi_nam': 2, 'tuoi_nu': 3,
    'dia_chi': 4, 'so_ho_so': 5,
    'ngay_bat_dau': 8, 'ngay_ket_thuc': 9,
    'ptv_chinh': 18, 'phu_1': 19,
    'ghi_chu': 25, 'may': 28,
}

# Từ khóa tìm trong header (lowercase, substring match).
# Ưu tiên pattern cụ thể hơn trước.
_COLUMN_PATTERNS = [
    # (logical_name, [patterns])
    ('ho_ten',       ['họ và tên', 'họ tên', 'tên bệnh nhân', 'tên bn']),
    ('tuoi_nam',     ['nam']),
    ('tuoi_nu',      ['nữ']),
    ('dia_chi',      ['địa chỉ']),
    ('so_ho_so',     ['số hồ sơ', 'mã hồ sơ', 'mã hs']),
    ('ngay_bat_dau', ['ngày bắt đầu', 'giờ bắt đầu', 'bắt đầu', 'bđ']),
    ('ngay_ket_thuc',['ngày kết thúc', 'giờ kết thúc', 'kết thúc', 'kt']),
    ('ptv_chinh',    ['ptv chính', 'kỹ thuật chính', 'kỹ thuật viên chính']),
    ('phu_1',        ['phụ 1', 'ktv phụ 1']),
    ('ghi_chu',      ['ghi chú', 'chú thích']),
    ('may',          ['máy thực hiện', 'máy sử dụng', 'thiết bị']),
    ('stt',          ['stt', 'số tt', 'số thứ tự']),
]


def find_header_row(rows_data, max_scan: int = 15, default: int = 9) -> int:
    """Tìm index của row chứa header. Heuristic: row có 'tt' hoặc 'họ và tên' hoặc
    'họ tên' (lowercase, normalized). Fallback default nếu không thấy."""
    for i in range(min(max_scan, len(rows_data))):
        row_vals = [_norm(v) for v in rows_data[i]]
        if any(v in ('tt', 'stt') for v in row_vals):
            return i
        if any('họ và tên' in v or 'họ tên' in v for v in row_vals if v):
            return i
    return default


def build_column_mapping(rows_data, header_idx: int) -> dict:
    """Quét header row + sub-header row (nếu có) để xây mapping logical_name → col_idx.
    Trả về dict có mọi key của DEFAULT_COLUMN_LAYOUT (fallback mặc định nếu header thiếu).

    Ví dụ file 011.3.xls: header row có 'Họ và tên', 'Tuổi' (merged),
    sub-header có 'Nam', 'Nữ', 'PTV chính', 'Phụ 1'.
    """
    mapping = dict(DEFAULT_COLUMN_LAYOUT)
    scan_rows = []
    if 0 <= header_idx < len(rows_data):
        scan_rows.append(rows_data[header_idx])
    if 0 <= header_idx + 1 < len(rows_data):
        scan_rows.append(rows_data[header_idx + 1])

    for row in scan_rows:
        for col_idx, val in enumerate(row):
            if val is None:
                continue
            norm_val = _norm(val)
            if not norm_val:
                continue
            for logical_name, patterns in _COLUMN_PATTERNS:
                for p in patterns:
                    if p == norm_val or p in norm_val:
                        mapping[logical_name] = col_idx
                        break
    return mapping


def validate_required_columns(mapping: dict, rows_data, header_idx: int) -> list:
    """Trả về list tên cột BẮT BUỘC nhưng chưa được detect đúng.
    (Header row text ở col mapping[name] phải match 1 pattern cho 'name'.)

    Chỉ báo khi mapping = default nhưng header row không có text tương ứng → ép detect.
    """
    required = ['ho_ten', 'ngay_bat_dau', 'may']
    missing = []
    if header_idx >= len(rows_data):
        return required
    header = rows_data[header_idx]
    sub = rows_data[header_idx + 1] if header_idx + 1 < len(rows_data) else []

    def col_text(col_idx):
        parts = []
        if col_idx < len(header) and header[col_idx]:
            parts.append(_norm(header[col_idx]))
        if col_idx < len(sub) and sub[col_idx]:
            parts.append(_norm(sub[col_idx]))
        return ' '.join(parts)

    pattern_map = {k: v for k, v in _COLUMN_PATTERNS}
    for name in required:
        txt = col_text(mapping.get(name, -1))
        patterns = pattern_map.get(name, [])
        if not any(p in txt for p in patterns):
            missing.append(name)
    return missing


def safe_str(v) -> str:
    """Trim + xoá newline; None → ''."""
    if v is None:
        return ''
    return str(v).strip().replace('\r\n', ' ').replace('\n', ' ')


def parse_excel_datetime(v, xls_datemode: int = 0):
    """Parse giá trị ngày/giờ từ Excel về chuỗi ISO 'YYYY-MM-DD HH:MM:SS'.

    Hỗ trợ: datetime object, date object, chuỗi nhiều format, Excel serial number.
    xls_datemode: 0 = Windows (1900), 1 = Mac (1904).
    Trả None nếu không parse được.
    """
    if v is None or v == '':
        return None

    if isinstance(v, _datetime.datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(v, _datetime.date):
        return v.strftime('%Y-%m-%d') + ' 00:00:00'

    # Excel serial number trước khi fall-through sang chuỗi. Loại bool (vì
    # isinstance(True, int) == True) và số quá nhỏ; xldate_as_tuple sẽ tự loại
    # serial ngoài phạm vi hợp lệ.
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= _MIN_EXCEL_DATE_SERIAL:
        try:
            import xlrd
            t = xlrd.xldate_as_tuple(v, xls_datemode)
            return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
        except Exception:
            return None

    s = safe_str(v)
    if not s:
        return None
    # Strip ISO timezone designator Z (coi là UTC, lưu như naive).
    if s.endswith('Z'):
        s = s[:-1]
    for fmt in DATE_FORMATS:
        try:
            return _datetime.datetime.strptime(s, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return None


def is_device_blocked(status) -> bool:
    """True nếu trạng thái máy nằm trong nhóm chặn (hỏng/thanh lý/báo lỗi).
    So bằng substring — 'Đã thanh lý' cũng match 'thanh lý'.
    """
    if not status:
        return False
    lo = str(status).lower()
    return any(tok in lo for tok in BLOCKED_DEVICE_STATES)


def check_session_overlap(thiet_bi_id, ngay_bat_dau, ngay_ket_thuc,
                           existing_sessions: list):
    """Kiểm tra trùng giờ trong danh sách phiên đã có (thường trong cùng 1 file Excel).

    Phiên mở (ngay_ket_thuc=None) coi như chạy đến vô cực — chặn mọi phiên sau đó
    trên cùng máy.

    Trả về chuỗi mô tả lỗi nếu trùng, None nếu không.
    """
    if not thiet_bi_id or not ngay_bat_dau:
        return None

    SENTINEL_END = '9999-12-31 23:59:59'
    new_end = ngay_ket_thuc or SENTINEL_END

    for s in existing_sessions:
        if s.get('thiet_bi_id') != thiet_bi_id:
            continue
        s_start = s.get('ngay_bat_dau') or ''
        s_end = s.get('ngay_ket_thuc') or SENTINEL_END
        if not s_start:
            continue

        if s_start == ngay_bat_dau:
            return (f"Trùng lặp: Máy đã có phiên lúc {ngay_bat_dau} "
                    f"(BN: {s.get('ho_ten', '?')})")

        if ngay_bat_dau < s_end and new_end > s_start:
            return (f"Trùng thời gian: Máy đang dùng từ {s_start} đến "
                    f"{s.get('ngay_ket_thuc') or '(chưa kết thúc)'} "
                    f"(BN: {s.get('ho_ten', '?')})")
    return None


def strip_title(name: str) -> str:
    """Bỏ các tiền tố chức danh để so khớp tên nhân viên. Đã NFC-normalize."""
    # Prefix dài đứng trước prefix ngắn — tránh 'bs' ăn trước 'bscki'.
    return re.sub(
        r'^(ths\.?bs\.?|bsckii\.?|bscki\.?|ths\.?|bs\.?|ts\.?|cn\.?)\s*',
        '',
        _norm(name),
    ).strip()


def find_staff(name_raw, all_staff: list):
    """Tìm nhân viên theo tên.

    Chiến lược ưu tiên an toàn:
      1. Exact match (lowercase) — luôn thắng.
      2. Exact match sau khi strip_title (VD 'BS. X' → 'X' exact).
      3. Substring match — CHỈ trả về khi DUY NHẤT 1 người khớp. Nếu ≥2
         người cùng match (ambiguous), trả về (-1, name) để ép user
         sửa dữ liệu gốc thay vì gán sai âm thầm.

    Trả về (id, matched_name) nếu thấy,
            (-1, name) nếu không thấy hoặc ambiguous,
            (None, None) nếu input rỗng.
    """
    if not name_raw or not str(name_raw).strip():
        return None, None
    name = str(name_raw).strip()
    name_lower = _norm(name)  # NFC-normalized
    name_stripped = strip_title(name)

    # 1. Exact match (NFC-normalized)
    staff_map = {_norm(s['ho_ten']): s['id'] for s in all_staff}
    if name_lower in staff_map:
        return staff_map[name_lower], name

    # 2. Exact sau strip_title ở 2 phía
    for s in all_staff:
        s_stripped = strip_title(s['ho_ten'])
        if name_stripped and s_stripped and name_stripped == s_stripped:
            return s['id'], s['ho_ten']

    # 3. Substring match — phải UNIQUE
    candidates = []
    for s in all_staff:
        s_lower = _norm(s['ho_ten'])
        s_stripped = strip_title(s['ho_ten'])
        if _word_substring(name_lower, s_lower) or _word_substring(s_lower, name_lower):
            candidates.append(s)
            continue
        if name_stripped and s_stripped and (
            _word_substring(name_stripped, s_stripped) or _word_substring(s_stripped, name_stripped)
        ):
            candidates.append(s)

    if len(candidates) == 1:
        return candidates[0]['id'], candidates[0]['ho_ten']

    return -1, name


def find_device(name_raw, device_list: list):
    """Tìm thiết bị theo tên.

    device_list: list các tuple (id, ten, ten_normalized, tinh_trang).

    Chiến lược ưu tiên an toàn:
      1. Full-name substring match (NFC + normalize whitespace). Nếu UNIQUE → OK.
      2. Tách số + keyword (hdf/nipro/braun/fresinius). Khớp UNIQUE → OK.
      3. Số đứng một mình (không keyword) → chỉ OK nếu duy nhất 1 máy cùng số.
    Ambiguous → trả (None, raw, None) để ép user ghi rõ hãng.

    Trả về (id, ten, tinh_trang) hoặc (None, raw, None).
    """
    if not name_raw or not str(name_raw).strip():
        return None, '', None
    raw = str(name_raw).strip()
    raw_norm_full = _norm(raw).replace('_', ' ')
    raw_norm_nospace = raw_norm_full.replace(' ', '')

    # 1. Full-name substring: chỉ trả khi UNIQUE
    full_candidates = []
    for did, dten, _dlow, dtt in device_list:
        dlow_nospace = _norm(dten).replace(' ', '')
        if dlow_nospace and (dlow_nospace in raw_norm_nospace or raw_norm_nospace in dlow_nospace):
            full_candidates.append((did, dten, dtt))
    if len(full_candidates) == 1:
        return full_candidates[0]
    # Nếu substring match nhiều, tiếp tục sang lọc bằng keyword/number

    # 2-3. Extract số + prefix hint (F=Fresinius, B=Braun — convention BV BN Số 2)
    m = re.search(r'[_\s]*(F|B|f|b|số|Số|so)\s*0*(\d+)\s*$', raw)
    prefix_hint = None
    if not m:
        m = re.search(r'[_\s]*0*(\d+)\s*$', raw)
        num = m.group(1) if m else None
    else:
        num = m.group(2)
        p = m.group(1).lower()
        if p == 'f':
            prefix_hint = 'fresinius'
        elif p == 'b':
            prefix_hint = 'braun'
        elif p in ('số', 'so'):
            # Convention BV BN Số 2: 'Số X' = B.Braun X (vs 'F X' = Fresinius)
            prefix_hint = 'braun'

    if not num:
        return None, raw, None

    raw_lower = _norm(raw)
    keyword = None
    if 'hdf' in raw_lower:
        keyword = 'hdf'
    elif 'nipro' in raw_lower or 'nip' in raw_lower:
        keyword = 'nipro'
    elif 'b.braun' in raw_lower or 'braun' in raw_lower:
        keyword = 'braun'
    elif 'fresinius' in raw_lower or 'fresenius' in raw_lower:
        keyword = 'fresinius'
    # Nếu không có keyword explicit, dùng prefix hint (F/B)
    if keyword is None and prefix_hint:
        keyword = prefix_hint

    try:
        num_int = int(num)
    except (TypeError, ValueError):
        num_int = None

    num_candidates = []
    for did, dten, _dlow, dtt in device_list:
        dten_lower = _norm(dten)
        # So khớp SỐ chính xác (so sánh số nguyên), không phải substring.
        # Tránh 'số 1' khớp nhầm 'số 10'/'số 11' → gán phiên sai máy.
        if num_int is None or num_int not in _extract_numbers(dten_lower):
            continue
        if keyword:
            if keyword in dten_lower:
                num_candidates.append((did, dten, dtt))
        else:
            num_candidates.append((did, dten, dtt))

    if len(num_candidates) == 1:
        return num_candidates[0]

    # Còn >1 ứng viên (cùng số + cùng keyword) → MƠ HỒ. KHÔNG đoán bừa (pick-first
    # cũ gán phiên sai máy âm thầm — nguy hiểm với hồ sơ y tế). Trả None để buộc
    # người dùng ghi rõ tên máy thay vì gán nhầm không cảnh báo.
    return None, raw, None
