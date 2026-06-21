# -*- coding: utf-8 -*-
"""
Flask REST API server for Machine Management System.
"""
import sys, io, os
if sys.platform == 'win32':
    if getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from database.models import create_all_tables
from database.queries import thiet_bi, nhan_vien, bao_duong, phien_dieu_tri, ban_giao
from config import TAN_SUAT, LOAI_BAO_DUONG, TRANG_THAI_BAO_DUONG, CHUC_VU
from excel_import import parse_workbook, import_sessions, preview_sessions, ExcelParseError

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)

# ---------- Serve Frontend ----------
@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

# ---------- API: Dashboard ----------
@app.route('/api/dashboard')
def api_dashboard():
    total = thiet_bi.count()
    status = thiet_bi.count_by_tinh_trang()
    active = status.get('Hoạt động', 0)
    error = status.get('Báo lỗi', 0) + status.get('Hỏng', 0)
    sessions_today = phien_dieu_tri.count_today()
    usage = thiet_bi.count_by_tan_suat()
    usage_named = {TAN_SUAT.get(int(k), f"Muc {k}"): v for k, v in usage.items()}
    upcoming = bao_duong.get_upcoming(7)
    broken = [r for r in thiet_bi.get_all() if 'hỏng' in (r.get('tinh_trang','').lower())]
    error_list = [r for r in thiet_bi.get_all() if 'lỗi' in (r.get('tinh_trang','').lower())]
    alerts = []
    if broken:
        alerts.append({'type':'error','msg':f"{len(broken)} thiết bị đã hỏng: " + ", ".join(r['ten_thiet_bi'] for r in broken[:5])})
    if error_list:
        alerts.append({'type':'warning','msg':f"{len(error_list)} thiết bị báo lỗi: " + ", ".join(r['ten_thiet_bi'] for r in error_list[:5])})
    if upcoming:
        alerts.append({'type':'info','msg':f"{len(upcoming)} phiếu bảo dưỡng sắp đến hạn (7 ngày)"})
    unmatched = phien_dieu_tri.count_unmatched()
    if unmatched:
        alerts.append({'type':'warning',
                       'msg':f"{unmatched} phiên chưa gán máy (tên thiết bị không khớp khi import) — không vào thống kê theo máy"})
    return jsonify({
        'total': total, 'active': active, 'error': error,
        'sessions_today': sessions_today,
        'status': status, 'usage': usage_named, 'alerts': alerts
    })

# ---------- API: Thiet Bi ----------
@app.route('/api/thiet-bi')
def api_thiet_bi_list():
    search = request.args.get('search', '')
    tinh_trang = request.args.get('tinh_trang', '')
    model = request.args.get('model', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    limit = request.args.get('limit', 0, type=int)
    offset = request.args.get('offset', 0, type=int)
    rows = thiet_bi.get_all(search=search, tinh_trang=tinh_trang, model=model,
                            from_date=from_date, to_date=to_date,
                            limit=limit, offset=offset)
    return jsonify(rows)

@app.route('/api/thiet-bi/<int:id>')
def api_thiet_bi_get(id):
    row = thiet_bi.get_by_id(id)
    return jsonify(row) if row else ('', 404)

@app.route('/api/thiet-bi', methods=['POST'])
def api_thiet_bi_create():
    data = request.json
    new_id = thiet_bi.create(**data)
    return jsonify({'id': new_id}), 201

@app.route('/api/thiet-bi/<int:id>', methods=['PUT'])
def api_thiet_bi_update(id):
    data = request.json
    thiet_bi.update(id, **data)
    return jsonify({'ok': True})

@app.route('/api/thiet-bi/<int:id>', methods=['DELETE'])
def api_thiet_bi_delete(id):
    try:
        thiet_bi.delete(id)
    except thiet_bi.DeviceHasHistoryError as e:
        return jsonify({'error': str(e)}), 409
    return jsonify({'ok': True})

@app.route('/api/thiet-bi/models')
def api_thiet_bi_models():
    return jsonify(thiet_bi.get_models())

# ---------- API: Nhan Vien ----------
@app.route('/api/nhan-vien')
def api_nhan_vien_list():
    search = request.args.get('search', '')
    chuc_vu = request.args.get('chuc_vu', '')
    limit = request.args.get('limit', 0, type=int)
    offset = request.args.get('offset', 0, type=int)
    return jsonify(nhan_vien.get_all(search=search, chuc_vu=chuc_vu, limit=limit, offset=offset))

@app.route('/api/nhan-vien/<int:id>')
def api_nhan_vien_get(id):
    row = nhan_vien.get_by_id(id)
    return jsonify(row) if row else ('', 404)

@app.route('/api/nhan-vien', methods=['POST'])
def api_nhan_vien_create():
    data = request.json
    new_id = nhan_vien.create(**data)
    return jsonify({'id': new_id}), 201

@app.route('/api/nhan-vien/<int:id>', methods=['PUT'])
def api_nhan_vien_update(id):
    data = request.json
    nhan_vien.update(id, **data)
    return jsonify({'ok': True})

@app.route('/api/nhan-vien/<int:id>', methods=['DELETE'])
def api_nhan_vien_delete(id):
    try:
        nhan_vien.delete(id)
    except nhan_vien.StaffReferencedError as e:
        return jsonify({'error': str(e)}), 409
    return jsonify({'ok': True})

# ---------- API: Bao Duong ----------
@app.route('/api/bao-duong')
def api_bao_duong_list():
    tb_id = request.args.get('thiet_bi_id', type=int)
    loai = request.args.get('loai', '')
    trang_thai = request.args.get('trang_thai', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    limit = request.args.get('limit', 0, type=int)
    offset = request.args.get('offset', 0, type=int)
    return jsonify(bao_duong.get_all(
        thiet_bi_id=tb_id, loai=loai, trang_thai=trang_thai,
        from_date=from_date, to_date=to_date,
        limit=limit, offset=offset
    ))

@app.route('/api/bao-duong/<int:id>')
def api_bao_duong_get(id):
    row = bao_duong.get_by_id(id)
    return jsonify(row) if row else ('', 404)

@app.route('/api/bao-duong', methods=['POST'])
def api_bao_duong_create():
    data = request.json
    new_id = bao_duong.create(**data)
    return jsonify({'id': new_id}), 201

@app.route('/api/bao-duong/<int:id>', methods=['PUT'])
def api_bao_duong_update(id):
    data = request.json
    bao_duong.update(id, **data)
    return jsonify({'ok': True})

@app.route('/api/bao-duong/<int:id>', methods=['DELETE'])
def api_bao_duong_delete(id):
    bao_duong.delete(id)
    return jsonify({'ok': True})

@app.route('/api/bao-duong/upcoming')
def api_bao_duong_upcoming():
    return jsonify(bao_duong.get_upcoming(7))

# ---------- API: Phien Dieu Tri ----------
@app.route('/api/phien-dieu-tri')
def api_phien_dt_list():
    search = request.args.get('search', '')
    tb_id = request.args.get('thiet_bi_id', type=int)
    ptv_id = request.args.get('ptv_chinh_id', type=int)
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    limit = request.args.get('limit', 0, type=int)
    offset = request.args.get('offset', 0, type=int)
    return jsonify(phien_dieu_tri.get_all(
        search=search, thiet_bi_id=tb_id, ptv_chinh_id=ptv_id,
        from_date=from_date, to_date=to_date,
        limit=limit, offset=offset
    ))

@app.route('/api/phien-dieu-tri/<int:id>')
def api_phien_dt_get(id):
    row = phien_dieu_tri.get_by_id(id)
    return jsonify(row) if row else ('', 404)

def _validate_session_payload(data):
    """Validate chung cho POST/PUT phien_dieu_tri.
    Trả về (error_message, status_code) nếu sai, None nếu OK."""
    ho_ten = (data.get('ho_ten') or '').strip()
    if len(ho_ten) < 2:
        return 'Họ tên bệnh nhân phải ≥ 2 ký tự', 400
    bd = data.get('ngay_bat_dau')
    if not bd:
        return 'Thiếu ngày bắt đầu', 400
    kt = data.get('ngay_ket_thuc')
    if kt and kt <= bd:
        return f'Ngày kết thúc ({kt}) phải sau ngày bắt đầu ({bd})', 400
    # tuoi có thể đến dạng chuỗi từ client → ép kiểu an toàn, tránh TypeError
    # khi so sánh str < int (gây 500) và để chuỗi ngoài phạm vi vẫn bị bắt.
    tuoi_raw = data.get('tuoi', 0)
    if tuoi_raw not in (None, '', 0, '0'):
        try:
            tuoi = int(float(str(tuoi_raw).strip()))
        except (ValueError, TypeError):
            return f'Tuổi không hợp lệ: {tuoi_raw}', 400
        if tuoi < 0 or tuoi > 120:
            return f'Tuổi ngoài phạm vi (1-120): {tuoi}', 400
    return None


@app.route('/api/phien-dieu-tri', methods=['POST'])
def api_phien_dt_create():
    data = request.json
    err = _validate_session_payload(data)
    if err:
        return jsonify({'error': err[0]}), err[1]
    # Check time overlap on same device
    tb_id = data.get('thiet_bi_id')
    bd = data.get('ngay_bat_dau')
    kt = data.get('ngay_ket_thuc')
    if tb_id and bd:
        conflict = phien_dieu_tri.check_time_overlap(tb_id, bd, kt)
        if conflict:
            return jsonify({
                'error': (f"Trùng khung giờ: Máy đang có phiên của "
                          f"\"{conflict['ho_ten']}\" "
                          f"từ {conflict['ngay_bat_dau']} "
                          f"đến {conflict['ngay_ket_thuc'] or '(chưa kết thúc)'}. "
                          f"Không thể tạo phiên trùng thời gian trên cùng 1 máy.")
            }), 409
    new_id = phien_dieu_tri.create(**data)
    return jsonify({'id': new_id}), 201

@app.route('/api/phien-dieu-tri/<int:id>', methods=['PUT'])
def api_phien_dt_update(id):
    data = request.json
    err = _validate_session_payload(data)
    if err:
        return jsonify({'error': err[0]}), err[1]
    # Check time overlap on same device (exclude self)
    tb_id = data.get('thiet_bi_id')
    bd = data.get('ngay_bat_dau')
    kt = data.get('ngay_ket_thuc')
    if tb_id and bd:
        conflict = phien_dieu_tri.check_time_overlap(tb_id, bd, kt, exclude_id=id)
        if conflict:
            return jsonify({
                'error': (f"Trùng khung giờ: Máy đang có phiên của "
                          f"\"{conflict['ho_ten']}\" "
                          f"từ {conflict['ngay_bat_dau']} "
                          f"đến {conflict['ngay_ket_thuc'] or '(chưa kết thúc)'}. "
                          f"Không thể lưu phiên trùng thời gian trên cùng 1 máy.")
            }), 409
    phien_dieu_tri.update(id, **data)
    return jsonify({'ok': True})

@app.route('/api/phien-dieu-tri/<int:id>', methods=['DELETE'])
def api_phien_dt_delete(id):
    phien_dieu_tri.delete(id)
    return jsonify({'ok': True})

@app.route('/api/phien-dieu-tri/stats')
def api_phien_dt_stats():
    return jsonify({
        'per_machine': phien_dieu_tri.sessions_per_machine(),
        'per_day': phien_dieu_tri.sessions_per_day(),
        'total': phien_dieu_tri.count(),
    })

# ---------- API: Ban Giao ----------
@app.route('/api/ban-giao')
def api_ban_giao_list():
    tb_id = request.args.get('thiet_bi_id', type=int)
    nv_id = request.args.get('nhan_vien_id', type=int)
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    limit = request.args.get('limit', 0, type=int)
    offset = request.args.get('offset', 0, type=int)
    return jsonify(ban_giao.get_all(
        thiet_bi_id=tb_id, nhan_vien_id=nv_id,
        from_date=from_date, to_date=to_date,
        limit=limit, offset=offset
    ))

@app.route('/api/ban-giao/<int:id>')
def api_ban_giao_get(id):
    row = ban_giao.get_by_id(id)
    return jsonify(row) if row else ('', 404)

@app.route('/api/ban-giao', methods=['POST'])
def api_ban_giao_create():
    data = request.json
    # Check duplicate: same device + same date
    tb_id = data.get('thiet_bi_id')
    ngay = data.get('ngay_ban_giao')
    if tb_id and ngay:
        dups = ban_giao.check_duplicates([tb_id], ngay)
        if dups:
            return jsonify({
                'error': f"Thiết bị '{dups[0]['ten_thiet_bi']}' đã có bàn giao ngày {ngay}"
            }), 409
    new_id = ban_giao.create(**data)
    return jsonify({'id': new_id}), 201

@app.route('/api/ban-giao/<int:id>', methods=['PUT'])
def api_ban_giao_update(id):
    data = request.json
    # Check duplicate on update (exclude self)
    tb_id = data.get('thiet_bi_id')
    ngay = data.get('ngay_ban_giao')
    if tb_id and ngay:
        dups = ban_giao.check_duplicates([tb_id], ngay, exclude_id=id)
        if dups:
            return jsonify({
                'error': f"Thiết bị '{dups[0]['ten_thiet_bi']}' đã có bàn giao ngày {ngay}"
            }), 409
    ban_giao.update(id, **data)
    return jsonify({'ok': True})

@app.route('/api/ban-giao/<int:id>', methods=['DELETE'])
def api_ban_giao_delete(id):
    ban_giao.delete(id)
    return jsonify({'ok': True})

@app.route('/api/ban-giao/batch', methods=['POST'])
def api_ban_giao_batch():
    """Create handover records for multiple devices at once."""
    data = request.json
    device_ids = data.get('device_ids', [])
    nguoi_giao_id = data.get('nguoi_giao_id')
    nguoi_nhan_id = data.get('nguoi_nhan_id')
    ngay_ban_giao = data.get('ngay_ban_giao')
    trang_thai = data.get('trang_thai', 'Đã bàn giao')
    ghi_chu = data.get('ghi_chu', '')

    # Check duplicates
    skipped = []
    if ngay_ban_giao and device_ids:
        dups = ban_giao.check_duplicates(device_ids, ngay_ban_giao)
        dup_ids = {d['thiet_bi_id'] for d in dups}
        skipped = [d['ten_thiet_bi'] for d in dups]
        device_ids = [tid for tid in device_ids if tid not in dup_ids]

    # Tạo cả lô trong MỘT giao dịch (nguyên tử) — lỗi giữa chừng sẽ rollback
    # toàn bộ thay vì để lại 'nửa lô'.
    import sqlite3
    try:
        created = ban_giao.create_batch(
            device_ids,
            nguoi_giao_id=nguoi_giao_id,
            nguoi_nhan_id=nguoi_nhan_id,
            ngay_ban_giao=ngay_ban_giao,
            trang_thai=trang_thai,
            ghi_chu=ghi_chu,
        )
    except sqlite3.IntegrityError:
        return jsonify({
            'ok': False,
            'error': 'Dữ liệu tham chiếu không hợp lệ (thiết bị hoặc nhân viên không tồn tại). '
                     'Không có phiếu nào được tạo.'
        }), 400
    return jsonify({
        'ok': True,
        'count': len(created), 'ids': created,
        'skipped': skipped, 'skipped_count': len(skipped)
    }), 201

@app.route('/api/ban-giao/export-pdf')
def api_ban_giao_export_pdf():
    """Export handover data as PDF with date range filter."""
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    # Fetch data
    rows = ban_giao.get_all(from_date=from_date, to_date=to_date)

    # Generate PDF
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Register Vietnamese font
    font_path = os.path.join('C:/Windows/Fonts', 'arial.ttf')
    font_bold_path = os.path.join('C:/Windows/Fonts', 'arialbd.ttf')
    if 'ArialVN' not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont('ArialVN', font_path))
            pdfmetrics.registerFont(TTFont('ArialVN-Bold', font_bold_path))
        except Exception:
            # Fallback: alias 'ArialVN' sang font built-in Helvetica để KHÔNG lỗi
            # 500 trên máy không có Arial (vd Linux). Tiếng Việt có thể thiếu dấu,
            # nhưng PDF vẫn tạo được thay vì crash khi doc.build() gặp font lạ.
            from reportlab.pdfbase.pdfmetrics import Font as _StdFont
            pdfmetrics.registerFont(_StdFont('ArialVN', 'Helvetica', 'WinAnsiEncoding'))
            pdfmetrics.registerFont(_StdFont('ArialVN-Bold', 'Helvetica-Bold', 'WinAnsiEncoding'))
        # Khai báo HỌ font để reportlab map được normal/bold (nếu thiếu sẽ lỗi
        # "Can't map determine family/bold/italic" khi dùng style in đậm).
        pdfmetrics.registerFontFamily(
            'ArialVN', normal='ArialVN', bold='ArialVN-Bold',
            italic='ArialVN', boldItalic='ArialVN-Bold',
        )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            topMargin=15*mm, bottomMargin=10*mm,
                            leftMargin=12*mm, rightMargin=12*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('VNTitle', fontName='ArialVN-Bold', fontSize=14, alignment=1, spaceAfter=4)
    sub_style = ParagraphStyle('VNSub', fontName='ArialVN', fontSize=10, alignment=1, spaceAfter=2)
    header_style = ParagraphStyle('VNHeader', fontName='ArialVN-Bold', fontSize=11, alignment=1, spaceAfter=8)
    cell_style = ParagraphStyle('VNCell', fontName='ArialVN', fontSize=8, leading=10)
    cell_bold = ParagraphStyle('VNCellBold', fontName='ArialVN-Bold', fontSize=8, leading=10, alignment=1)

    elements = []

    # Header
    elements.append(Paragraph("BỆNH VIỆN ĐA KHOA BẮC NINH SỐ 2", title_style))
    elements.append(Paragraph("Khoa Thận nhân tạo - Lọc máu", sub_style))
    elements.append(Spacer(1, 6*mm))

    # Title
    date_range_text = ""
    if from_date and to_date:
        date_range_text = f" ({from_date} → {to_date})"
    elif from_date:
        date_range_text = f" (từ {from_date})"
    elif to_date:
        date_range_text = f" (đến {to_date})"
    elements.append(Paragraph(f"BIÊN BẢN BÀN GIAO THIẾT BỊ{date_range_text}", header_style))
    elements.append(Spacer(1, 3*mm))

    # Table header
    headers = ['STT', 'Thiết bị', 'Trạng thái máy', 'Người giao', 'Người nhận', 'Ngày BG', 'Tần suất', 'Ghi chú']
    header_row = [Paragraph(h, cell_bold) for h in headers]

    # Table data
    table_data = [header_row]
    for i, r in enumerate(rows):
        # `or ''`: cột join có thể NULL (vd chưa có người giao/nhận) → Paragraph(None)
        # làm reportlab crash 500. Quy mọi giá trị về chuỗi an toàn.
        table_data.append([
            Paragraph(str(i+1), cell_style),
            Paragraph(r.get('ten_thiet_bi') or '', cell_style),
            Paragraph(r.get('tinh_trang_may') or '', cell_style),
            Paragraph(r.get('nguoi_giao_ten') or '', cell_style),
            Paragraph(r.get('nguoi_nhan_ten') or '', cell_style),
            Paragraph(r.get('ngay_ban_giao') or '', cell_style),
            Paragraph(str(r.get('tan_suat') or 0), cell_style),
            Paragraph(r.get('ghi_chu') or '', cell_style),
        ])

    col_widths = [25, 130, 90, 90, 90, 65, 45, 200]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ArialVN'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e6b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (5, 0), (6, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)

    # Footer with signatures
    elements.append(Spacer(1, 12*mm))
    sign_style = ParagraphStyle('VNSign', fontName='ArialVN-Bold', fontSize=10, alignment=1)
    sign_data = [
        [Paragraph("NGƯỜI GIAO", sign_style), Paragraph("", sign_style), Paragraph("NGƯỜI NHẬN", sign_style)],
        [Paragraph("(Ký, ghi rõ họ tên)", ParagraphStyle('VNSignSub', fontName='ArialVN', fontSize=8, alignment=1, textColor=colors.grey)),
         Paragraph("", cell_style),
         Paragraph("(Ký, ghi rõ họ tên)", ParagraphStyle('VNSignSub2', fontName='ArialVN', fontSize=8, alignment=1, textColor=colors.grey))],
    ]
    sign_tbl = Table(sign_data, colWidths=[200, 300, 200])
    sign_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sign_tbl)

    doc.build(elements)
    buf.seek(0)

    filename = f"ban_giao_{from_date or 'all'}_{to_date or 'all'}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)

# ---------- API: Config ----------
@app.route('/api/config')
def api_config():
    return jsonify({
        'tan_suat': TAN_SUAT,
        'loai_bao_duong': LOAI_BAO_DUONG,
        'trang_thai_bao_duong': TRANG_THAI_BAO_DUONG,
        'chuc_vu': CHUC_VU,
    })

# ---------- API: Statistics ----------
@app.route('/api/statistics')
def api_statistics():
    total_cost = bao_duong.total_chi_phi()
    sessions = phien_dieu_tri.sessions_per_machine()
    total_devices = thiet_bi.count()
    status = thiet_bi.count_by_tinh_trang()
    active = status.get('Hoạt động', 0)
    rate = int((active / total_devices) * 100) if total_devices > 0 else 0
    all_devices = thiet_bi.get_all()
    # SỐ PHIÊN THỰC TẾ theo máy (so_phien), KHÔNG phải mã tần suất 0-3 (vô nghĩa
    # khi vẽ cột). Khóa = tên đầy đủ (frontend tự cắt khi hiển thị) tránh trùng khóa.
    usage_data = {d['ten_thiet_bi']: d.get('so_phien', 0) for d in all_devices}
    usage_sorted = dict(sorted(usage_data.items(), key=lambda x: x[1], reverse=True))
    return jsonify({
        'total_cost': total_cost,
        'top_machine': sessions[0] if sessions else None,
        'active_rate': rate,
        'usage_per_device': usage_sorted,
        'sessions_per_machine': sessions[:20],
    })


# ---------- API: Import Excel ----------
@app.route('/api/phien-dieu-tri/import-excel', methods=['POST'])
def api_import_excel():
    """Import treatment sessions from Excel file (.xls/.xlsx) with strict validation."""
    import traceback

    try:
        # ===== FILE-LEVEL VALIDATION =====
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': 'Không tìm thấy file trong request'}), 400

        f = request.files['file']
        if not f.filename:
            return jsonify({'ok': False, 'error': 'Tên file rỗng'}), 400

        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in ('xls', 'xlsx'):
            return jsonify({'ok': False, 'error': f'Định dạng .{ext} không hỗ trợ. Chỉ chấp nhận .xls hoặc .xlsx'}), 400

        file_bytes = f.read()
        if not file_bytes:
            return jsonify({'ok': False, 'error': 'File rỗng (0 bytes)'}), 400

        if len(file_bytes) > 50 * 1024 * 1024:
            return jsonify({'ok': False, 'error': 'File quá lớn (>50MB)'}), 400

        # ===== PARSE EXCEL + IMPORT (logic dùng chung tại excel_import.py) =====
        try:
            rows_data, datemode = parse_workbook(file_bytes, ext)
        except ExcelParseError as e:
            return jsonify({'ok': False, 'error': str(e)}), 400

        results = import_sessions(rows_data, datemode)

        return jsonify({
            'ok': True,
            'success': results['success'],
            'total': results['total'],
            'skipped': results['skipped'],
            'errors': results['errors'][:100]
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': f'Lỗi hệ thống: {str(e)}',
            'trace': traceback.format_exc()
        }), 500


@app.route('/api/phien-dieu-tri/preview-excel', methods=['POST'])
def api_preview_excel():
    """Xem trước import: parse + validate + map từng dòng nhưng KHÔNG ghi DB.
    Dùng để người dùng kiểm tra trước khi xác nhận nhập thật."""
    import traceback
    try:
        if 'file' not in request.files:
            return jsonify({'ok': False, 'error': 'Không tìm thấy file trong request'}), 400
        f = request.files['file']
        if not f.filename:
            return jsonify({'ok': False, 'error': 'Tên file rỗng'}), 400
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in ('xls', 'xlsx'):
            return jsonify({'ok': False, 'error': f'Định dạng .{ext} không hỗ trợ. Chỉ chấp nhận .xls hoặc .xlsx'}), 400
        file_bytes = f.read()
        if not file_bytes:
            return jsonify({'ok': False, 'error': 'File rỗng (0 bytes)'}), 400
        if len(file_bytes) > 50 * 1024 * 1024:
            return jsonify({'ok': False, 'error': 'File quá lớn (>50MB)'}), 400
        try:
            rows_data, datemode = parse_workbook(file_bytes, ext)
        except ExcelParseError as e:
            return jsonify({'ok': False, 'error': str(e)}), 400
        plan = preview_sessions(rows_data, datemode)
        return jsonify({'ok': True, **plan})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Lỗi hệ thống: {str(e)}',
                        'trace': traceback.format_exc()}), 500


if __name__ == '__main__':
    create_all_tables()
    try:
        from import_data import run_import
        run_import()
    except Exception as e:
        print(f"[Import] {e}")
    print("Server running at http://localhost:5000")
    # debug TẮT mặc định: debug=True bật Werkzeug debugger (nguy cơ RCE) trên app
    # quản lý dữ liệu y tế. Bật tạm khi dev bằng: set FLASK_DEBUG=1
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', port=5000)
