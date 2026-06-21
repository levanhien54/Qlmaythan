/* Devices Page */

async function renderDevices(el) {
    el.style.cssText = '';
    const today = todayLocal();
    el.innerHTML = `
        <h1 class="page-title">🖥️ Quản lý Thiết bị</h1>
        <div class="toolbar">
            <input type="search" id="devSearch" placeholder="🔍 Tìm tên, số máy..." oninput="filterDevices()">
            <select id="devStatus" onchange="filterDevices()">
                <option value="">Tất cả tình trạng</option>
                <option>Hoạt động bình thường</option><option>Báo lỗi</option><option>Hỏng</option><option>Đã thanh lý</option>
            </select>
            <input type="date" id="devDateFrom" value="${today}" onchange="filterDevices()" oninput="filterDevices()" title="Từ ngày">
            <input type="date" id="devDateTo" value="${today}" onchange="filterDevices()" oninput="filterDevices()" title="Đến ngày">
            <div class="spacer"></div>
        </div>
        <div class="table-wrapper" id="devTableWrap">
            <table><thead><tr>
                <th>STT</th><th>Tên thiết bị</th><th>Model</th><th>Hãng SX</th>
                <th>Số máy</th><th>Năm SĐ</th><th>Người QL</th><th>Tình trạng</th><th>Tần suất</th><th>Ghi chú</th>
            </tr></thead><tbody id="devBody"></tbody></table>
        </div>
        <div class="table-footer" id="devCount"></div>
    `;
    filterDevices();
}

// Track device stats across pages
let _devStats = { total: 0, active: 0, totalSessions: 0 };

async function filterDevices() {
    destroyScrolls();
    _devStats = { total: 0, active: 0, totalSessions: 0 };
    const search = $('#devSearch')?.value || '';
    const tinh_trang = $('#devStatus')?.value || '';
    const dateFrom = $('#devDateFrom')?.value || '';
    const dateTo = $('#devDateTo')?.value || '';
    let base = `/api/thiet-bi?search=${encodeURIComponent(search)}&tinh_trang=${encodeURIComponent(tinh_trang)}`;
    if (dateFrom) base += `&from_date=${dateFrom}`;
    if (dateTo) base += `&to_date=${dateTo}`;
    const scr = new InfiniteScroll('#devTableWrap', '#devBody', '#devCount',
        (offset, limit) => api(`${base}&limit=${limit}&offset=${offset}`),
        (r, i) => {
            _devStats.total++;
            if (r.so_phien > 0) _devStats.active++;
            _devStats.totalSessions += (r.so_phien || 0);
            return `<tr>
                <td>${i+1}</td>
                <td><a class="device-link clickable" tabindex="0" role="button" onclick="viewDevice(${r.id})">${esc(r.ten_thiet_bi)}</a></td>
                <td>${esc(r.model)}</td><td>${esc(r.hang_san_xuat)}</td>
                <td>${esc(r.so_may)}</td><td>${r.nam_su_dung||''}</td><td>${esc(r.nguoi_quan_ly_ten)}</td>
                <td>${statusBadge(r.tinh_trang)}</td><td>${r.so_phien||0}</td>
                <td title="${esc(r.ghi_chu)}">${esc((r.ghi_chu||'').substring(0,40))}</td>
            </tr>`;
        },
        'thiết bị'
    );
    // Override footer update to show rich stats
    scr._updateCount = function() {
        if (this.countEl) {
            this.countEl.innerHTML = `Hiển thị: <b>${_devStats.total}</b> thiết bị${this.hasMore ? '' : ' (hết)'} &nbsp;|&nbsp; Máy hoạt động: <b>${_devStats.active}</b> &nbsp;|&nbsp; Tổng tần suất: <b>${_devStats.totalSessions}</b>`;
        }
    };
    registerScroll(scr);
    await scr.loadFirst();
}

// ========== DEVICE DETAIL VIEW ==========
async function viewDevice(id) {
    const main = $('#mainContent');
    main.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted)">Đang tải...</div>';

    try {
        const [dev, sessions, maintenance, handovers] = await Promise.all([
            api(`/api/thiet-bi/${id}`),
            api(`/api/phien-dieu-tri?thiet_bi_id=${id}`),
            api(`/api/bao-duong?thiet_bi_id=${id}`),
            api(`/api/ban-giao?thiet_bi_id=${id}`),
        ]);

        const tsMap = {0:'Không sử dụng',1:'Thấp (1 ca/ngày)',2:'Trung bình (2 ca/ngày)',3:'Cao (3 ca/ngày)'};

        main.style.cssText = 'display:block; overflow-y:auto; height:100%;';
        main.innerHTML = `
            <div class="detail-header">
                <button class="btn btn-outline" onclick="navigate('devices')">← Quay lại</button>
                <h1 class="page-title" style="margin-bottom:0;margin-left:12px">🖥️ ${esc(dev.ten_thiet_bi)}</h1>
            </div>
            <div class="detail-info-grid">
                <div class="detail-info-card">
                    <div class="info-row"><span class="info-label">Model:</span><span>${esc(dev.model) || '—'}</span></div>
                    <div class="info-row"><span class="info-label">Hãng SX:</span><span>${esc(dev.hang_san_xuat) || '—'}</span></div>
                    <div class="info-row"><span class="info-label">Số máy:</span><span>${esc(dev.so_may) || '—'}</span></div>
                </div>
                <div class="detail-info-card">
                    <div class="info-row"><span class="info-label">Năm SĐ:</span><span>${dev.nam_su_dung || '—'}</span></div>
                    <div class="info-row"><span class="info-label">Tần suất:</span><span>${tsMap[dev.tan_suat_su_dung] || '—'}</span></div>
                    <div class="info-row"><span class="info-label">Người QL:</span><span>${esc(dev.nguoi_quan_ly_ten) || '—'}</span></div>
                </div>
                <div class="detail-info-card">
                    <div class="info-row"><span class="info-label">Tình trạng:</span>${statusBadge(dev.tinh_trang)}</div>
                    <div class="info-row"><span class="info-label">Tần suất:</span><span class="detail-count">${sessions.length}</span></div>
                    <div class="info-row"><span class="info-label">Số lần BD:</span><span class="detail-count">${maintenance.length}</span></div>
                </div>
            </div>
            <div class="detail-section">
                <h2 class="detail-section-title">📋 Lịch sử hoạt động <span class="detail-badge">${sessions.length}</span></h2>
                ${sessions.length ? `<div class="table-wrapper"><table><thead><tr>
                    <th>STT</th><th>Họ tên BN</th><th>Tuổi</th><th>Số HS</th><th>Ngày BĐ</th><th>Ngày KT</th><th>PTV chính</th><th>Phụ 1</th><th>Ghi chú</th>
                </tr></thead><tbody>${sessions.map((s,i) => `<tr>
                    <td>${i+1}</td><td>${esc(s.ho_ten)}</td><td>${s.tuoi||''}</td><td>${esc(s.so_ho_so)}</td>
                    <td>${esc((s.ngay_bat_dau||'').substring(0,16))}</td><td>${esc((s.ngay_ket_thuc||'').substring(0,16))}</td>
                    <td>${esc(s.ptv_chinh_ten)}</td><td>${esc(s.phu_1_ten)}</td>
                    <td title="${esc(s.ghi_chu)}">${esc((s.ghi_chu||'').substring(0,30))}</td>
                </tr>`).join('')}</tbody></table></div>` : '<div class="detail-empty">Chưa có hoạt động nào.</div>'}
            </div>
            <div class="detail-grid-2col">
                <div class="detail-section">
                    <h2 class="detail-section-title">🔧 Bảo dưỡng & sửa chữa <span class="detail-badge">${maintenance.length}</span></h2>
                    ${maintenance.length ? `<div class="table-wrapper"><table><thead><tr>
                        <th>STT</th><th>Loại</th><th>Ngày TH</th><th>Người TH</th><th>Trạng thái</th>
                    </tr></thead><tbody>${maintenance.map((m,i) => `<tr>
                        <td>${i+1}</td><td>${esc(m.loai)}</td><td>${esc(m.ngay_thuc_hien)}</td><td>${esc(m.nguoi_thuc_hien_ten)}</td>
                        <td>${statusBadge(m.trang_thai)}</td>
                    </tr>`).join('')}</tbody></table></div>` : '<div class="detail-empty">Chưa có lịch sử bảo dưỡng.</div>'}
                </div>
                <div class="detail-section">
                    <h2 class="detail-section-title">📋 Lịch sử bàn giao <span class="detail-badge">${handovers.length}</span></h2>
                    ${handovers.length ? `<div class="table-wrapper"><table><thead><tr>
                        <th>STT</th><th>Người giao</th><th>Người nhận</th><th>Ngày</th><th>Ghi chú</th>
                    </tr></thead><tbody>${handovers.map((h,i) => `<tr>
                        <td>${i+1}</td><td>${esc(h.nguoi_giao_ten)}</td><td>${esc(h.nguoi_nhan_ten)}</td>
                        <td>${esc(h.ngay_ban_giao)}</td><td title="${esc(h.ghi_chu)}">${esc((h.ghi_chu||'').substring(0,30))}</td>
                    </tr>`).join('')}</tbody></table></div>` : '<div class="detail-empty">Chưa có lịch sử bàn giao.</div>'}
                </div>
            </div>
        `;
    } catch(e) {
        main.innerHTML = `<div style="color:var(--status-error);padding:40px;">Lỗi: ${e.message}</div>`;
    }
}

// ========== DEVICE CRUD ==========
async function addDevice() {
    const cfg = await getConfig();
    const staffData = await loadStaffData();
    const tsOpts = Object.entries(cfg.tan_suat).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');
    openModal('➕ Thêm thiết bị', `
        <div class="form-group"><label>Tên thiết bị *</label><input id="f_ten" placeholder="VD: Máy chạy thận Fresinius số 1"></div>
        <div class="form-group"><label>Model</label><input id="f_model" placeholder="VD: 4008S"></div>
        <div class="form-group"><label>Hãng/Nước SX</label><input id="f_hang" placeholder="VD: Đức"></div>
        <div class="form-group"><label>Số máy</label><input id="f_so_may" placeholder="Serial number"></div>
        <div class="form-group"><label>Năm SĐ</label><input type="number" id="f_nam" value="2025" min="2000" max="2030"></div>
        <div class="form-group"><label>Tình trạng</label><select id="f_tinh_trang"><option>Hoạt động bình thường</option><option>Báo lỗi</option><option>Hỏng</option><option>Đang bảo dưỡng</option><option>Đã thanh lý</option></select></div>
        <div class="form-group"><label>Tần suất</label><select id="f_tan_suat">${tsOpts}</select></div>
        <div class="form-group"><label>Người quản lý</label>${searchSelect('f_ql', staffData, '🔍 Tìm nhân viên...')}</div>
    `, async () => {
        if (!$('#f_ten').value.trim()) return toast('Vui lòng nhập tên thiết bị', true);
        await api('/api/thiet-bi', { method: 'POST', body: JSON.stringify({
            ten_thiet_bi: $('#f_ten').value.trim(), model: $('#f_model').value.trim(),
            hang_san_xuat: $('#f_hang').value.trim(), nuoc_san_xuat: $('#f_hang').value.trim(),
            so_may: $('#f_so_may').value.trim(), nam_su_dung: parseInt($('#f_nam').value),
            tinh_trang: $('#f_tinh_trang').value, tan_suat_su_dung: parseInt($('#f_tan_suat').value),
            nguoi_quan_ly_id: ssVal('f_ql') ? parseInt(ssVal('f_ql')) : null
        })});
        closeModal(); toast('Đã thêm thiết bị!'); filterDevices();
    });
}

async function editDevice(id) {
    const r = await api(`/api/thiet-bi/${id}`);
    const cfg = await getConfig();
    const staffData = await loadStaffData();
    const tsOpts = Object.entries(cfg.tan_suat).map(([k,v])=>`<option value="${k}" ${k==r.tan_suat_su_dung?'selected':''}>${v}</option>`).join('');
    openModal('✏️ Sửa thiết bị', `
        <div class="form-group"><label>Tên thiết bị *</label><input id="f_ten" value="${esc(r.ten_thiet_bi)}"></div>
        <div class="form-group"><label>Model</label><input id="f_model" value="${esc(r.model)}"></div>
        <div class="form-group"><label>Hãng SX</label><input id="f_hang" value="${esc(r.hang_san_xuat)}"></div>
        <div class="form-group"><label>Số máy</label><input id="f_so_may" value="${esc(r.so_may)}"></div>
        <div class="form-group"><label>Năm SĐ</label><input type="number" id="f_nam" value="${r.nam_su_dung||2025}"></div>
        <div class="form-group"><label>Tình trạng</label><select id="f_tinh_trang">
            ${['Hoạt động bình thường','Báo lỗi','Hỏng','Đang bảo dưỡng'].map(s=>`<option ${s===r.tinh_trang?'selected':''}>${s}</option>`).join('')}
        </select></div>
        <div class="form-group"><label>Tần suất</label><select id="f_tan_suat">${tsOpts}</select></div>
        <div class="form-group"><label>Người QL</label>${searchSelect('f_ql', staffData, '🔍 Tìm nhân viên...', r.nguoi_quan_ly_id)}</div>
    `, async () => {
        await api(`/api/thiet-bi/${id}`, { method: 'PUT', body: JSON.stringify({
            ten_thiet_bi: $('#f_ten').value.trim(), model: $('#f_model').value.trim(),
            hang_san_xuat: $('#f_hang').value.trim(), so_may: $('#f_so_may').value.trim(),
            nam_su_dung: parseInt($('#f_nam').value), tinh_trang: $('#f_tinh_trang').value,
            tan_suat_su_dung: parseInt($('#f_tan_suat').value),
            nguoi_quan_ly_id: ssVal('f_ql') ? parseInt(ssVal('f_ql')) : null
        })});
        closeModal(); toast('Đã cập nhật!'); filterDevices();
    });
}

async function deleteDevice(id) {
    if (!confirm('Xóa thiết bị này?')) return;
    try {
        await api(`/api/thiet-bi/${id}`, { method: 'DELETE' });
        toast('Đã xóa!'); filterDevices();
    } catch (e) { toast(e.message, true); }
}
