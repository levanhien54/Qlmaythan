/* Handover Page */

async function renderHandover(el) {
    const devOpts = await loadDeviceOptions();
    const staff = await api('/api/nhan-vien');
    const staffFilter = staff.map(s=>`<option value="${s.id}">${s.ho_ten}</option>`).join('');
    const today = todayLocal();
    el.innerHTML = `
        <h1 class="page-title">📋 Bàn giao Thiết bị</h1>
        <div class="toolbar">
            <select id="hoDev" onchange="filterHandover()"><option value="">Tất cả TB</option>${devOpts}</select>
            <select id="hoStaff" onchange="filterHandover()"><option value="">Tất cả NV</option>${staffFilter}</select>
            <input type="date" id="hoDateFrom" value="${today}" onchange="filterHandover()" oninput="filterHandover()" title="Từ ngày">
            <input type="date" id="hoDateTo" value="${today}" onchange="filterHandover()" oninput="filterHandover()" title="Đến ngày">
            <div class="spacer"></div>
            <button class="btn" style="background:var(--accent-orange);color:#fff" onclick="exportHandoverPDF()">📄 Xuất PDF</button>
            <button class="btn btn-success" onclick="batchHandover()">📦 Bàn giao hàng loạt</button>
            <button class="btn btn-primary" onclick="addHandover()">➕ Thêm bàn giao</button>
        </div>
        <div class="table-wrapper" id="hoTableWrap">
            <table><thead><tr>
                <th>STT</th><th>Thiết bị</th><th>Người giao</th><th>Người nhận</th>
                <th>Ngày</th><th>Trạng thái</th><th>Tần suất</th><th>Ghi chú</th><th>Thao tác</th>
            </tr></thead>
            <tbody id="hoBody"></tbody></table>
        </div>
        <div class="table-footer" id="hoCount"></div>`;
    filterHandover();
}

// Track handover stats across pages
let _hoStats = { total: 0, active: 0, totalSessions: 0, devices: new Set() };

async function filterHandover() {
    destroyScrolls();
    _hoStats = { total: 0, active: 0, totalSessions: 0, devices: new Set() };
    let base = '/api/ban-giao?';
    const tb = $('#hoDev')?.value;
    const nv = $('#hoStaff')?.value;
    const dateFrom = $('#hoDateFrom')?.value || '';
    const dateTo = $('#hoDateTo')?.value || '';
    if (tb) base += `thiet_bi_id=${tb}&`;
    if (nv) base += `nhan_vien_id=${nv}&`;
    if (dateFrom) base += `from_date=${dateFrom}&`;
    if (dateTo) base += `to_date=${dateTo}&`;
    const scr = new InfiniteScroll('#hoTableWrap', '#hoBody', '#hoCount',
        (offset, limit) => api(`${base}limit=${limit}&offset=${offset}`),
        (r, i) => {
            _hoStats.total++;
            if (r.thiet_bi_id && !_hoStats.devices.has(r.thiet_bi_id)) {
                _hoStats.devices.add(r.thiet_bi_id);
                if ((r.tinh_trang_may || '').includes('hoạt động') || (r.tinh_trang_may || '').includes('bình thường')) {
                    _hoStats.active++;
                }
                _hoStats.totalSessions += (r.tan_suat || 0);
            }
            return `<tr>
            <td>${i+1}</td><td>${esc(r.ten_thiet_bi)}</td>
            <td>${esc(r.nguoi_giao_ten)}</td><td>${esc(r.nguoi_nhan_ten)}</td>
            <td>${esc(r.ngay_ban_giao)}</td>
            <td>${statusBadge(r.tinh_trang_may||'')}</td>
            <td style="text-align:center;font-weight:600">${r.tan_suat||0}</td>
            <td title="${esc(r.ghi_chu)}">${esc((r.ghi_chu||'').substring(0,40))}</td>
            <td class="actions"><button class="btn btn-edit" aria-label="Sửa" title="Sửa" onclick="editHandover(${r.id})">✏️</button>
            <button class="btn btn-danger" aria-label="Xóa" title="Xóa" onclick="deleteHandover(${r.id})">🗑️</button></td>
        </tr>`;
        },
        'phiếu'
    );
    // Override footer to show rich stats
    scr._updateCount = function() {
        if (this.countEl) {
            this.countEl.innerHTML = `Hiển thị: <b>${_hoStats.total}</b> thiết bị${this.hasMore ? '' : ' (hết)'} &nbsp;|&nbsp; Máy hoạt động: <b>${_hoStats.active}</b> &nbsp;|&nbsp; Tổng tần suất: <b>${_hoStats.totalSessions}</b>`;
        }
    };
    registerScroll(scr);
    await scr.loadFirst();
}

async function addHandover() {
    const devData = await loadDeviceData(true);
    const staffData = await loadStaffData();
    const today = todayLocal();
    openModal('➕ Thêm bàn giao', `
        <div class="form-group"><label>Thiết bị *</label>${searchSelect('h_tb', devData, '🔍 Tìm thiết bị...')}</div>
        <div class="form-group"><label>Người giao</label>${searchSelect('h_giao', staffData, '🔍 Tìm người giao...')}</div>
        <div class="form-group"><label>Người nhận</label>${searchSelect('h_nhan', staffData, '🔍 Tìm người nhận...')}</div>
        <div class="form-group"><label>Ngày bàn giao</label><input type="date" id="f_ngay" value="${today}"></div>
        <div class="form-group"><label>Trạng thái</label>
            <select id="f_tt"><option>Đã bàn giao</option><option>Đang chờ</option><option>Đã thu hồi</option></select>
        </div>
        <div class="form-group"><label>Ghi chú</label><textarea id="f_gc" placeholder="Ghi chú..."></textarea></div>
    `, async () => {
        if (!ssVal('h_tb')) return toast('Chọn thiết bị', true);
        try {
            await api('/api/ban-giao', { method:'POST', body: JSON.stringify({
                thiet_bi_id: parseInt(ssVal('h_tb')),
                nguoi_giao_id: ssVal('h_giao') ? parseInt(ssVal('h_giao')) : null,
                nguoi_nhan_id: ssVal('h_nhan') ? parseInt(ssVal('h_nhan')) : null,
                ngay_ban_giao: $('#f_ngay').value, trang_thai: $('#f_tt').value, ghi_chu: $('#f_gc').value
            })});
            closeModal(); toast('Đã thêm!'); filterHandover();
        } catch (e) {
            toast(e.message, true);
        }
    });
}

// ========== BATCH HANDOVER ==========
async function batchHandover() {
    const allDevices = await api('/api/thiet-bi');
    const devices = allDevices.filter(d => {
        const tt = (d.tinh_trang || '').toLowerCase();
        return !tt.includes('hỏng') && !tt.includes('thanh lý') && !tt.includes('báo lỗi');
    });
    const staffData = await loadStaffData();
    const today = todayLocal();

    const deviceListHTML = devices.map(d => `
        <label class="batch-item">
            <input type="checkbox" name="batch_dev" value="${d.id}">
            <span class="batch-name">${esc(d.ten_thiet_bi)}</span>
            <span class="batch-info">${esc(d.model)} — ${statusBadge(d.tinh_trang)}</span>
        </label>
    `).join('');

    openModal('📦 Bàn giao hàng loạt', `
        <div class="form-group">
            <label>Chọn thiết bị</label>
            <div style="margin-bottom:8px;display:flex;gap:8px">
                <button type="button" class="btn btn-sm" onclick="batchSelectAll(true)">☑️ Chọn tất cả</button>
                <button type="button" class="btn btn-sm" onclick="batchSelectAll(false)">⬜ Bỏ chọn tất cả</button>
            </div>
            <input type="search" id="batchDevSearch" placeholder="🔍 Tìm thiết bị..." oninput="batchFilterDevices()" style="margin-bottom:8px">
            <div class="batch-device-list" id="batchDevList">
                ${deviceListHTML}
            </div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:4px" id="batchSelectedCount">Đã chọn: 0 thiết bị</div>
        </div>
        <div class="form-group"><label>Người giao</label>${searchSelect('bh_giao', staffData, '🔍 Tìm người giao...')}</div>
        <div class="form-group"><label>Người nhận</label>${searchSelect('bh_nhan', staffData, '🔍 Tìm người nhận...')}</div>
        <div class="form-group"><label>Ngày bàn giao</label><input type="date" id="bh_ngay" value="${today}"></div>
        <div class="form-group"><label>Trạng thái</label>
            <select id="bh_tt"><option>Đã bàn giao</option><option>Đang chờ</option><option>Đã thu hồi</option></select>
        </div>
        <div class="form-group"><label>Ghi chú</label><textarea id="bh_gc" placeholder="Ghi chú chung..."></textarea></div>
    `, async () => {
        const checked = [...document.querySelectorAll('input[name="batch_dev"]:checked')].map(c => parseInt(c.value));
        if (!checked.length) return toast('Chưa chọn thiết bị nào!', true);

        try {
            const res = await api('/api/ban-giao/batch', { method:'POST', body: JSON.stringify({
                device_ids: checked,
                nguoi_giao_id: ssVal('bh_giao') ? parseInt(ssVal('bh_giao')) : null,
                nguoi_nhan_id: ssVal('bh_nhan') ? parseInt(ssVal('bh_nhan')) : null,
                ngay_ban_giao: $('#bh_ngay').value,
                trang_thai: $('#bh_tt').value,
                ghi_chu: $('#bh_gc').value
            })});
            closeModal();
            let msg = `Đã tạo ${res.count} phiếu bàn giao!`;
            if (res.skipped_count > 0) {
                msg += `\n⚠️ Bỏ qua ${res.skipped_count} thiết bị đã có bàn giao trong ngày:\n• ${res.skipped.join('\n• ')}`;
                toast(msg, true);
            } else {
                toast(msg);
            }
            filterHandover();
        } catch (e) {
            toast('Lỗi: ' + e.message, true);
        }
    });

    // Attach checkbox change listener for count + highlight
    document.querySelectorAll('input[name="batch_dev"]').forEach(cb => {
        cb.addEventListener('change', () => {
            cb.closest('.batch-item').classList.toggle('checked', cb.checked);
            updateBatchCount();
        });
    });
}

function batchSelectAll(selectAll) {
    document.querySelectorAll('input[name="batch_dev"]').forEach(cb => {
        const item = cb.closest('.batch-item');
        if (item.style.display !== 'none') {
            cb.checked = selectAll;
            item.classList.toggle('checked', selectAll);
        }
    });
    updateBatchCount();
}

function batchFilterDevices() {
    const q = $('#batchDevSearch')?.value.toLowerCase().trim() || '';
    document.querySelectorAll('#batchDevList .batch-item').forEach(item => {
        const name = item.querySelector('.batch-name').textContent.toLowerCase();
        item.style.display = name.includes(q) ? '' : 'none';
    });
}

function updateBatchCount() {
    const count = document.querySelectorAll('input[name="batch_dev"]:checked').length;
    const el = $('#batchSelectedCount');
    if (el) el.textContent = `Đã chọn: ${count} thiết bị`;
}

async function editHandover(id) {
    const r = await api(`/api/ban-giao/${id}`);
    const devData = await loadDeviceData();
    const staffData = await loadStaffData();
    openModal('✏️ Sửa bàn giao', `
        <div class="form-group"><label>Thiết bị</label>${searchSelect('h_tb', devData, '🔍 Tìm thiết bị...', r.thiet_bi_id)}</div>
        <div class="form-group"><label>Người giao</label>${searchSelect('h_giao', staffData, '🔍 Tìm người giao...', r.nguoi_giao_id)}</div>
        <div class="form-group"><label>Người nhận</label>${searchSelect('h_nhan', staffData, '🔍 Tìm người nhận...', r.nguoi_nhan_id)}</div>
        <div class="form-group"><label>Ngày</label><input type="date" id="f_ngay" value="${esc(r.ngay_ban_giao)}"></div>
        <div class="form-group"><label>Trạng thái</label>
            <select id="f_tt">
                <option ${(r.trang_thai||'')==='Đã bàn giao'?'selected':''}>Đã bàn giao</option>
                <option ${(r.trang_thai||'')==='Đang chờ'?'selected':''}>Đang chờ</option>
                <option ${(r.trang_thai||'')==='Đã thu hồi'?'selected':''}>Đã thu hồi</option>
            </select>
        </div>
        <div class="form-group"><label>Ghi chú</label><textarea id="f_gc">${esc(r.ghi_chu)}</textarea></div>
    `, async () => {
        try {
            await api(`/api/ban-giao/${id}`, { method:'PUT', body: JSON.stringify({
                thiet_bi_id: parseInt(ssVal('h_tb')),
                nguoi_giao_id: ssVal('h_giao') ? parseInt(ssVal('h_giao')) : null,
                nguoi_nhan_id: ssVal('h_nhan') ? parseInt(ssVal('h_nhan')) : null,
                ngay_ban_giao: $('#f_ngay').value, trang_thai: $('#f_tt').value, ghi_chu: $('#f_gc').value
            })});
            closeModal(); toast('Đã cập nhật!'); filterHandover();
        } catch (e) {
            toast(e.message, true);
        }
    });
}

async function deleteHandover(id) {
    if (!confirm('Xóa phiếu bàn giao?')) return;
    try {
        await api(`/api/ban-giao/${id}`, {method:'DELETE'});
        toast('Đã xóa!'); filterHandover();
    } catch (e) { toast(e.message, true); }
}

// ========== EXPORT PDF ==========
function exportHandoverPDF() {
    const today = todayLocal();
    const curFrom = $('#hoDateFrom')?.value || today;
    const curTo = $('#hoDateTo')?.value || today;
    openModal('📄 Xuất PDF Bàn giao', `
        <div class="form-group"><label>Từ ngày</label><input type="date" id="pdf_from" value="${curFrom}"></div>
        <div class="form-group"><label>Đến ngày</label><input type="date" id="pdf_to" value="${curTo}"></div>
        <p style="color:var(--text-muted);font-size:12px;margin-top:8px">
            📋 File PDF sẽ bao gồm tất cả bàn giao trong khoảng ngày đã chọn.<br>
            Bao gồm: Bảng dữ liệu + Phần ký tên Người giao / Người nhận.
        </p>
    `, async () => {
        const from = $('#pdf_from').value;
        const to = $('#pdf_to').value;
        if (!from || !to) return toast('Vui lòng chọn ngày!', true);
        closeModal();
        toast('Đang tạo PDF...');
        const url = `/api/ban-giao/export-pdf?from_date=${from}&to_date=${to}`;
        const a = document.createElement('a');
        a.href = url; a.download = `ban_giao_${from}_${to}.pdf`;
        document.body.appendChild(a); a.click(); a.remove();
    });
    // Change save button text
    setTimeout(() => { const btn = $('#modalSave'); if (btn) btn.textContent = '📥 Tải PDF'; }, 50);
}
