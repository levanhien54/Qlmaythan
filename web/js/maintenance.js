/* Maintenance Page */

async function renderMaintenance(el) {
    const cfg = await getConfig();
    const devOpts = await loadDeviceOptions();
    const today = todayLocal();
    el.innerHTML = `
        <h1 class="page-title">🔧 Lịch sử sửa chữa bảo dưỡng</h1>
        <div id="maintAlert"></div>
        <div class="toolbar">
            <select id="maintDev" onchange="filterMaint()"><option value="">Tất cả thiết bị</option>${devOpts}</select>
            <select id="maintType" onchange="filterMaint()"><option value="">Tất cả loại</option>${cfg.loai_bao_duong.map(l=>`<option>${l}</option>`).join('')}</select>
            <select id="maintStatus" onchange="filterMaint()"><option value="">Tất cả trạng thái</option>${cfg.trang_thai_bao_duong.map(t=>`<option>${t}</option>`).join('')}</select>
            <input type="date" id="maintDateFrom" value="${today}" onchange="filterMaint()" oninput="filterMaint()" title="Từ ngày">
            <input type="date" id="maintDateTo" value="${today}" onchange="filterMaint()" oninput="filterMaint()" title="Đến ngày">
            <div class="spacer"></div>
            <button class="btn btn-primary" onclick="addMaint()">➕ Thêm phiếu</button>
        </div>
        <div class="table-wrapper" id="maintTableWrap">
            <table><thead><tr><th>STT</th><th>Thiết bị</th><th>Loại</th><th>Ngày TH</th><th>Người TH</th><th>Mô tả</th><th>Trạng thái</th><th>Thao tác</th></tr></thead>
            <tbody id="maintBody"></tbody></table>
        </div>
        <div class="table-footer" id="maintCount"></div>`;
    const upcoming = await api('/api/bao-duong/upcoming');
    if (upcoming.length) {
        $('#maintAlert').innerHTML = `<div class="alert-item warning" style="margin-bottom:16px">⚠️ ${upcoming.length} thiết bị cần bảo dưỡng trong 7 ngày tới</div>`;
    }
    filterMaint();
}

async function filterMaint() {
    destroyScrolls();
    const tb = $('#maintDev')?.value || '';
    const loai = $('#maintType')?.value || '';
    const tt = $('#maintStatus')?.value || '';
    const dateFrom = $('#maintDateFrom')?.value || '';
    const dateTo = $('#maintDateTo')?.value || '';
    let base = '/api/bao-duong?';
    if (tb) base += `thiet_bi_id=${tb}&`;
    if (loai) base += `loai=${encodeURIComponent(loai)}&`;
    if (tt) base += `trang_thai=${encodeURIComponent(tt)}&`;
    if (dateFrom) base += `from_date=${dateFrom}&`;
    if (dateTo) base += `to_date=${dateTo}&`;
    const scr = new InfiniteScroll('#maintTableWrap', '#maintBody', '#maintCount',
        (offset, limit) => api(`${base}limit=${limit}&offset=${offset}`),
        (r, i) => `<tr>
            <td>${i+1}</td><td>${esc(r.ten_thiet_bi)}</td><td>${esc(r.loai)}</td>
            <td>${esc(r.ngay_thuc_hien)}</td><td>${esc(r.nguoi_thuc_hien_ten)}</td>
            <td title="${esc(r.mo_ta)}">${esc((r.mo_ta||'').substring(0,40))}</td>
            <td>${statusBadge(r.trang_thai)}</td>
            <td class="actions"><button class="btn btn-edit" onclick="editMaint(${r.id})">✏️</button>
            <button class="btn btn-danger" onclick="deleteMaint(${r.id})">🗑️</button></td>
        </tr>`,
        'phiếu'
    );
    registerScroll(scr);
    await scr.loadFirst();
}

async function addMaint() {
    const cfg = await getConfig();
    const devData = await loadDeviceData();
    const staffData = await loadStaffData();
    const today = todayLocal();
    openModal('➕ Thêm phiếu bảo dưỡng', `
        <div class="form-group"><label>Thiết bị *</label>${searchSelect('m_tb', devData, '🔍 Tìm thiết bị...')}</div>
        <div class="form-group"><label>Loại</label><select id="f_loai">${cfg.loai_bao_duong.map(l=>`<option>${l}</option>`).join('')}</select></div>
        <div class="form-group"><label>Ngày thực hiện</label><div style="display:flex;gap:8px"><input type="date" id="f_ngay" value="${today}" style="flex:1"><input type="text" id="f_ngay_t" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Dự kiến tiếp theo</label><div style="display:flex;gap:8px"><input type="date" id="f_ngay2" style="flex:1"><input type="text" id="f_ngay2_t" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Người thực hiện</label>${searchSelect('m_nv', staffData, '🔍 Tìm nhân viên...')}</div>
        <div class="form-group"><label>Mô tả</label><textarea id="f_mota" placeholder="Mô tả công việc..."></textarea></div>
        <div class="form-group"><label>Trạng thái</label><select id="f_tt">${cfg.trang_thai_bao_duong.map(t=>`<option>${t}</option>`).join('')}</select></div>
    `, async () => {
        if (!ssVal('m_tb')) return toast('Chọn thiết bị', true);
        const ngay1 = $('#f_ngay').value && $('#f_ngay_t').value ? `${$('#f_ngay').value} ${$('#f_ngay_t').value}` : $('#f_ngay').value;
        const ngay2 = $('#f_ngay2').value && $('#f_ngay2_t').value ? `${$('#f_ngay2').value} ${$('#f_ngay2_t').value}` : ($('#f_ngay2').value||null);
        await api('/api/bao-duong', { method:'POST', body: JSON.stringify({
            thiet_bi_id: parseInt(ssVal('m_tb')), loai: $('#f_loai').value,
            ngay_thuc_hien: ngay1, ngay_du_kien_tiep_theo: ngay2,
            nguoi_thuc_hien_id: ssVal('m_nv') ? parseInt(ssVal('m_nv')) : null,
            mo_ta: $('#f_mota').value,
            trang_thai: $('#f_tt').value
        })});
        closeModal(); toast('Đã thêm!'); filterMaint();
    });
}

async function editMaint(id) {
    const r = await api(`/api/bao-duong/${id}`);
    const cfg = await getConfig();
    const devData = await loadDeviceData();
    const staffData = await loadStaffData();
    const ngay_d = r.ngay_thuc_hien ? r.ngay_thuc_hien.substring(0,10) : '';
    const ngay_t = r.ngay_thuc_hien && r.ngay_thuc_hien.length > 10 ? r.ngay_thuc_hien.substring(11,16) : '';
    const ngay2_d = r.ngay_du_kien_tiep_theo ? r.ngay_du_kien_tiep_theo.substring(0,10) : '';
    const ngay2_t = r.ngay_du_kien_tiep_theo && r.ngay_du_kien_tiep_theo.length > 10 ? r.ngay_du_kien_tiep_theo.substring(11,16) : '';
    openModal('✏️ Sửa phiếu', `
        <div class="form-group"><label>Thiết bị</label>${searchSelect('m_tb', devData, '🔍 Tìm thiết bị...', r.thiet_bi_id)}</div>
        <div class="form-group"><label>Loại</label><select id="f_loai">${cfg.loai_bao_duong.map(l=>`<option ${l===r.loai?'selected':''}>${l}</option>`).join('')}</select></div>
        <div class="form-group"><label>Ngày TH</label><div style="display:flex;gap:8px"><input type="date" id="f_ngay" value="${ngay_d}" style="flex:1"><input type="text" id="f_ngay_t" value="${ngay_t}" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Dự kiến TT</label><div style="display:flex;gap:8px"><input type="date" id="f_ngay2" value="${ngay2_d}" style="flex:1"><input type="text" id="f_ngay2_t" value="${ngay2_t}" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Người TH</label>${searchSelect('m_nv', staffData, '🔍 Tìm nhân viên...', r.nguoi_thuc_hien_id)}</div>
        <div class="form-group"><label>Mô tả</label><textarea id="f_mota">${esc(r.mo_ta)}</textarea></div>
        <div class="form-group"><label>Trạng thái</label><select id="f_tt">${cfg.trang_thai_bao_duong.map(t=>`<option ${t===r.trang_thai?'selected':''}>${t}</option>`).join('')}</select></div>
    `, async () => {
        const ngay1 = $('#f_ngay').value && $('#f_ngay_t').value ? `${$('#f_ngay').value} ${$('#f_ngay_t').value}` : $('#f_ngay').value;
        const ngay2 = $('#f_ngay2').value && $('#f_ngay2_t').value ? `${$('#f_ngay2').value} ${$('#f_ngay2_t').value}` : ($('#f_ngay2').value||null);
        await api(`/api/bao-duong/${id}`, { method:'PUT', body: JSON.stringify({
            thiet_bi_id: parseInt(ssVal('m_tb')), loai: $('#f_loai').value,
            ngay_thuc_hien: ngay1, ngay_du_kien_tiep_theo: ngay2,
            nguoi_thuc_hien_id: ssVal('m_nv') ? parseInt(ssVal('m_nv')):null,
            mo_ta: $('#f_mota').value,
            trang_thai: $('#f_tt').value
        })});
        closeModal(); toast('Đã cập nhật!'); filterMaint();
    });
}

async function deleteMaint(id) {
    if (!confirm('Xóa phiếu này?')) return;
    try {
        await api(`/api/bao-duong/${id}`, {method:'DELETE'});
        toast('Đã xóa!'); filterMaint();
    } catch (e) { toast(e.message, true); }
}
