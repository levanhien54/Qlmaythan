/* Sessions Page */

async function renderSessions(el) {
    const devOpts = await loadDeviceOptions();
    const staff = await api('/api/nhan-vien');
    const ptvOpts = staff.map(s=>`<option value="${s.id}">${s.ho_ten}</option>`).join('');
    const today = todayLocal();
    el.innerHTML = `
        <h1 class="page-title">📋 Lịch sử hoạt động</h1>
        <div class="toolbar">
            <input type="search" id="sesSearch" placeholder="🔍 Tìm tên BN, SHS..." oninput="filterSessions()">
            <select id="sesDev" onchange="filterSessions()"><option value="">Tất cả máy</option>${devOpts}</select>
            <select id="sesPtv" onchange="filterSessions()"><option value="">Tất cả PTV</option>${ptvOpts}</select>
            <input type="date" id="sesDateFrom" value="${today}" onchange="filterSessions()" oninput="filterSessions()" title="Từ ngày">
            <input type="date" id="sesDateTo" value="${today}" onchange="filterSessions()" oninput="filterSessions()" title="Đến ngày">
            <div class="spacer"></div>
            <button class="btn btn-success" onclick="$('#excelFileInput').click()">📥 Nhập Excel</button>
            <input type="file" id="excelFileInput" accept=".xls,.xlsx" style="display:none" onchange="importExcelSessions(this)">
            <button class="btn btn-primary" onclick="addSession()">➕ Thêm hoạt động</button>
        </div>
        <div class="table-wrapper" id="sesTableWrap">
            <table><thead><tr><th>STT</th><th>Họ tên</th><th>Tuổi</th><th>Địa chỉ</th><th>Số HS</th><th>Ngày BĐ</th><th>Ngày KT</th><th>PTV chính</th><th>Phụ 1</th><th>Máy</th><th>Thao tác</th></tr></thead>
            <tbody id="sesBody"></tbody></table>
        </div>
        <div class="table-footer" id="sesCount"></div>`;
    filterSessions();
}

async function filterSessions() {
    destroyScrolls();
    const search = $('#sesSearch')?.value || '';
    const tb = $('#sesDev')?.value || '';
    const ptv = $('#sesPtv')?.value || '';
    const dateFrom = $('#sesDateFrom')?.value || '';
    const dateTo = $('#sesDateTo')?.value || '';
    let base = `/api/phien-dieu-tri?search=${encodeURIComponent(search)}`;
    if (tb) base += `&thiet_bi_id=${tb}`;
    if (ptv) base += `&ptv_chinh_id=${ptv}`;
    if (dateFrom) base += `&from_date=${dateFrom}`;
    if (dateTo) base += `&to_date=${dateTo}`;
    const scr = new InfiniteScroll('#sesTableWrap', '#sesBody', '#sesCount',
        (offset, limit) => api(`${base}&limit=${limit}&offset=${offset}`),
        (r, i) => `<tr>
            <td>${i+1}</td><td>${esc(r.ho_ten)}</td><td>${r.tuoi||''}</td>
            <td title="${esc(r.dia_chi)}">${esc((r.dia_chi||'').substring(0,25))}</td>
            <td>${esc(r.so_ho_so)}</td>
            <td>${esc((r.ngay_bat_dau||'').substring(0,16))}</td>
            <td>${esc((r.ngay_ket_thuc||'').substring(0,16))}</td>
            <td>${esc(r.ptv_chinh_ten)}</td><td>${esc(r.phu_1_ten)}</td>
            <td>${esc(r.may_thuc_hien)}</td>
            <td class="actions"><button class="btn btn-edit" aria-label="Sửa" title="Sửa" onclick="editSession(${r.id})">✏️</button>
            <button class="btn btn-danger" aria-label="Xóa" title="Xóa" onclick="deleteSession(${r.id})">🗑️</button></td>
        </tr>`,
        'hoạt động'
    );
    registerScroll(scr);
    await scr.loadFirst();
}

async function addSession() {
    const devData = await loadDeviceData(true);
    const staffData = await loadStaffData();
    openModal('➕ Thêm hoạt động', `
        <div class="form-group"><label>Họ tên BN *</label><input id="f_ten" placeholder="Họ và tên"></div>
        <div class="form-group"><label>Tuổi</label><input type="number" id="f_tuoi" value="0" min="0" max="120"></div>
        <div class="form-group"><label>Địa chỉ</label><input id="f_dc"></div>
        <div class="form-group"><label>Số hồ sơ</label><input id="f_shs"></div>
        <div class="form-group"><label>Ngày bắt đầu</label><div style="display:flex;gap:8px"><input type="date" id="f_bd_d" style="flex:1"><input type="text" id="f_bd_t" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Ngày kết thúc</label><div style="display:flex;gap:8px"><input type="date" id="f_kt_d" style="flex:1"><input type="text" id="f_kt_t" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Máy thực hiện</label>${searchSelect('s_may', devData, '🔍 Tìm máy...')}</div>
        <div class="form-group"><label>PTV chính</label>${searchSelect('s_ptv', staffData, '🔍 Tìm PTV chính...')}</div>
        <div class="form-group"><label>Phụ 1</label>${searchSelect('s_phu', staffData, '🔍 Tìm phụ 1...')}</div>
        <div class="form-group"><label>Ghi chú</label><textarea id="f_gc"></textarea></div>
    `, async () => {
        if (!$('#f_ten').value.trim()) return toast('Nhập tên BN', true);
        const mayVal = ssVal('s_may');
        const mayLabel = mayVal ? $(`#ssi_s_may`)?.value || '' : '';
        const bd = $('#f_bd_d').value && $('#f_bd_t').value ? `${$('#f_bd_d').value} ${$('#f_bd_t').value}:00` : null;
        const kt = $('#f_kt_d').value && $('#f_kt_t').value ? `${$('#f_kt_d').value} ${$('#f_kt_t').value}:00` : null;
        try {
            await api('/api/phien-dieu-tri', { method:'POST', body: JSON.stringify({
                ho_ten: $('#f_ten').value.trim(), tuoi: parseInt($('#f_tuoi').value)||0,
                dia_chi: $('#f_dc').value, so_ho_so: $('#f_shs').value,
                ngay_bat_dau: bd, ngay_ket_thuc: kt,
                thiet_bi_id: mayVal ? parseInt(mayVal) : null, may_thuc_hien: mayLabel,
                ptv_chinh_id: ssVal('s_ptv') ? parseInt(ssVal('s_ptv')) : null,
                phu_1_id: ssVal('s_phu') ? parseInt(ssVal('s_phu')) : null,
                ghi_chu: $('#f_gc').value
            })});
            closeModal(); toast('Đã thêm!'); filterSessions();
        } catch(e) { toast(e.message, true); }
    });
}

async function editSession(id) {
    const r = await api(`/api/phien-dieu-tri/${id}`);
    const devData = await loadDeviceData(true);
    const staffData = await loadStaffData();
    const bd_d = r.ngay_bat_dau ? r.ngay_bat_dau.substring(0,10) : '';
    const bd_t = r.ngay_bat_dau ? r.ngay_bat_dau.substring(11,16) : '';
    const kt_d = r.ngay_ket_thuc ? r.ngay_ket_thuc.substring(0,10) : '';
    const kt_t = r.ngay_ket_thuc ? r.ngay_ket_thuc.substring(11,16) : '';
    openModal('✏️ Sửa hoạt động', `
        <div class="form-group"><label>Họ tên</label><input id="f_ten" value="${esc(r.ho_ten)}"></div>
        <div class="form-group"><label>Tuổi</label><input type="number" id="f_tuoi" value="${r.tuoi||0}"></div>
        <div class="form-group"><label>Địa chỉ</label><input id="f_dc" value="${esc(r.dia_chi)}"></div>
        <div class="form-group"><label>Số HS</label><input id="f_shs" value="${esc(r.so_ho_so)}"></div>
        <div class="form-group"><label>Ngày BĐ</label><div style="display:flex;gap:8px"><input type="date" id="f_bd_d" value="${bd_d}" style="flex:1"><input type="text" id="f_bd_t" value="${bd_t}" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Ngày KT</label><div style="display:flex;gap:8px"><input type="date" id="f_kt_d" value="${kt_d}" style="flex:1"><input type="text" id="f_kt_t" value="${kt_t}" placeholder="HH:MM" maxlength="5" style="flex:1;text-align:center"></div></div>
        <div class="form-group"><label>Máy</label>${searchSelect('s_may', devData, '🔍 Tìm máy...', r.thiet_bi_id)}</div>
        <div class="form-group"><label>PTV chính</label>${searchSelect('s_ptv', staffData, '🔍 Tìm PTV chính...', r.ptv_chinh_id)}</div>
        <div class="form-group"><label>Phụ 1</label>${searchSelect('s_phu', staffData, '🔍 Tìm phụ 1...', r.phu_1_id)}</div>
        <div class="form-group"><label>Ghi chú</label><textarea id="f_gc">${esc(r.ghi_chu)}</textarea></div>
    `, async () => {
        const mayVal = ssVal('s_may');
        const mayLabel = mayVal ? $(`#ssi_s_may`)?.value || '' : '';
        const bd = $('#f_bd_d').value && $('#f_bd_t').value ? `${$('#f_bd_d').value} ${$('#f_bd_t').value}:00` : null;
        const kt = $('#f_kt_d').value && $('#f_kt_t').value ? `${$('#f_kt_d').value} ${$('#f_kt_t').value}:00` : null;
        try {
            await api(`/api/phien-dieu-tri/${id}`, { method:'PUT', body: JSON.stringify({
                ho_ten: $('#f_ten').value.trim(), tuoi: parseInt($('#f_tuoi').value)||0,
                dia_chi: $('#f_dc').value, so_ho_so: $('#f_shs').value,
                ngay_bat_dau: bd, ngay_ket_thuc: kt,
                thiet_bi_id: mayVal ? parseInt(mayVal) : null,
                may_thuc_hien: mayLabel,
                ptv_chinh_id: ssVal('s_ptv') ? parseInt(ssVal('s_ptv')) : null,
                phu_1_id: ssVal('s_phu') ? parseInt(ssVal('s_phu')) : null,
                ghi_chu: $('#f_gc').value
            })});
            closeModal(); toast('Đã cập nhật!'); filterSessions();
        } catch(e) { toast(e.message, true); }
    });
}

async function deleteSession(id) {
    if (!confirm('Xóa phiên này?')) return;
    try {
        await api(`/api/phien-dieu-tri/${id}`, {method:'DELETE'});
        toast('Đã xóa!'); filterSessions();
    } catch (e) { toast(e.message, true); }
}

// ========== IMPORT EXCEL ==========
async function importExcelSessions(inputEl) {
    const file = inputEl.files[0];
    if (!file) return;
    inputEl.value = ''; // reset for next upload

    const ext = file.name.split('.').pop().toLowerCase();
    if (!['xls', 'xlsx'].includes(ext)) {
        return toast('Chỉ chấp nhận file .xls hoặc .xlsx', true);
    }

    toast('⏳ Đang kiểm tra và nhập dữ liệu từ Excel...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/api/phien-dieu-tri/import-excel', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (!data.ok && data.error) {
            toast(`❌ ${data.error}`, true);
            return;
        }

        // Hộp thoại kết quả chi tiết (modal trong app, không dùng al() chặn UI)
        if (data.skipped > 0 || (data.errors && data.errors.length > 0)) {
            const lines = [];
            lines.push(`Thành công: ${data.success}/${data.total} phiên`);
            if (data.skipped > 0) lines.push(`Bị từ chối: ${data.skipped} phiên`);
            lines.push('');
            if (data.errors && data.errors.length > 0) {
                lines.push(`Chi tiết lỗi (${data.errors.length} dòng):`);
                data.errors.slice(0, 50).forEach(e => {
                    lines.push(`• Dòng ${e.row} — ${e.name}:`);
                    (e.errors || [e.error]).forEach(err => lines.push(`    - ${err}`));
                });
                if (data.errors.length > 50) {
                    lines.push(`... và ${data.errors.length - 50} lỗi khác`);
                }
            }
            const body = `<div style="max-height:55vh;overflow:auto;white-space:pre-wrap;`
                + `font-size:13px;line-height:1.6">${esc(lines.join('\n'))}</div>`
                + `<div style="text-align:right;margin-top:14px">`
                + `<button class="btn btn-primary" onclick="closeModal()">Đóng</button></div>`;
            showInfoModal(`📊 Kết quả nhập: ${file.name}`, body);
        }

        if (data.success > 0) {
            toast(`✅ Đã nhập ${data.success}/${data.total} phiên thành công!`);
        } else if (data.total > 0) {
            toast(`❌ Không nhập được phiên nào (${data.skipped} lỗi)`, true);
        }

        filterSessions();
    } catch (e) {
        toast(`❌ Lỗi kết nối: ${e.message}`, true);
    }
}
