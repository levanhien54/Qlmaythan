/* Settings Page — Chỉ quản lý Thiết bị (Nhân viên đã tách sang staff.js) */

async function renderSettings(el) {
    el.innerHTML = `
        <h1 class="page-title">⚙️ Cài đặt — Quản lý Thiết bị</h1>
        <div id="settDeviceSection" style="display:flex;flex-direction:column;flex:1;min-height:0">
            <div class="toolbar">
                <input type="search" id="settDevSearch" placeholder="🔍 Tìm thiết bị..." oninput="filterSettDevices()">
                <select id="settDevStatus" onchange="filterSettDevices()">
                    <option value="">Tất cả trạng thái</option>
                    <option>Hoạt động bình thường</option>
                    <option>Báo lỗi</option>
                    <option>Hỏng</option>
                    <option>Đang bảo dưỡng</option>
                    <option>Đã thanh lý</option>
                </select>
                <div class="spacer"></div>
                <button class="btn btn-primary" onclick="addSettDevice()">➕ Thêm thiết bị</button>
            </div>
            <div class="table-wrapper" id="settDevTableWrap">
                <table><thead><tr>
                    <th>STT</th><th>Tên thiết bị</th><th>Model</th><th>Hãng SX</th>
                    <th>Số máy</th><th>Năm SĐ</th><th>Người QL</th><th>Tình trạng</th><th>Thao tác</th>
                </tr></thead>
                <tbody id="settDevBody"></tbody></table>
            </div>
            <div class="table-footer" id="settDevCount"></div>
        </div>
    `;
    filterSettDevices();
}

// ========== Device CRUD (Settings) ==========
async function filterSettDevices() {
    destroyScrolls();
    const search = $('#settDevSearch')?.value || '';
    const status = $('#settDevStatus')?.value || '';
    const base = `/api/thiet-bi?search=${encodeURIComponent(search)}&tinh_trang=${encodeURIComponent(status)}`;
    const scr = new InfiniteScroll('#settDevTableWrap', '#settDevBody', '#settDevCount',
        (offset, limit) => api(`${base}&limit=${limit}&offset=${offset}`),
        (r, i) => `<tr>
            <td>${i+1}</td>
            <td>${esc(r.ten_thiet_bi)}</td><td>${esc(r.model)}</td><td>${esc(r.hang_san_xuat)}</td>
            <td>${esc(r.so_may)}</td><td>${r.nam_su_dung||''}</td><td>${esc(r.nguoi_quan_ly_ten)}</td>
            <td>${statusBadge(r.tinh_trang)}</td>
            <td class="actions">
                <button class="btn btn-edit" aria-label="Sửa" title="Sửa" onclick="editSettDevice(${r.id})">✏️</button>
                <button class="btn btn-danger" aria-label="Xóa" title="Xóa" onclick="deleteSettDevice(${r.id})">🗑️</button>
            </td>
        </tr>`,
        'thiết bị'
    );
    registerScroll(scr);
    await scr.loadFirst();
}

async function addSettDevice() {
    const staffData = await loadStaffData();
    openModal('➕ Thêm thiết bị', `
        <div class="form-group"><label>Tên thiết bị *</label><input id="f_ten" placeholder="VD: Máy chạy thận Fresinius số 1"></div>
        <div class="form-group"><label>Model</label><input id="f_model" placeholder="VD: 4008S"></div>
        <div class="form-group"><label>Hãng sản xuất</label><input id="f_hang" placeholder="VD: Fresenius"></div>
        <div class="form-group"><label>Nước sản xuất</label><input id="f_nuoc" placeholder="VD: Đức"></div>
        <div class="form-group"><label>Số máy (Serial)</label><input id="f_so_may" placeholder="Serial number"></div>
        <div class="form-group"><label>Năm sử dụng</label><input type="number" id="f_nam" value="2025" min="2000" max="2035"></div>
        <div class="form-group"><label>Tình trạng</label>
            <select id="f_tinh_trang">
                <option>Hoạt động bình thường</option><option>Báo lỗi</option><option>Hỏng</option>
                <option>Đang bảo dưỡng</option><option>Đã thanh lý</option>
            </select>
        </div>
        <div class="form-group"><label>Người quản lý</label>${searchSelect('sd_ql', staffData, '🔍 Tìm nhân viên...')}</div>
    `, async () => {
        const ten = $('#f_ten')?.value?.trim();
        if (!ten) return toast('Vui lòng nhập tên thiết bị', true);
        await api('/api/thiet-bi', { method: 'POST', body: JSON.stringify({
            ten_thiet_bi: ten, model: $('#f_model').value.trim(),
            hang_san_xuat: $('#f_hang').value.trim(), nuoc_san_xuat: $('#f_nuoc').value.trim(),
            so_may: $('#f_so_may').value.trim(), nam_su_dung: parseInt($('#f_nam').value),
            tinh_trang: $('#f_tinh_trang').value,
            nguoi_quan_ly_id: ssVal('sd_ql') ? parseInt(ssVal('sd_ql')) : null
        })});
        closeModal(); toast('Đã thêm thiết bị!'); filterSettDevices();
    });
}

async function editSettDevice(id) {
    const r = await api(`/api/thiet-bi/${id}`);
    const staffData = await loadStaffData();
    openModal('✏️ Sửa thiết bị', `
        <div class="form-group"><label>Tên thiết bị *</label><input id="f_ten" value="${esc(r.ten_thiet_bi)}"></div>
        <div class="form-group"><label>Model</label><input id="f_model" value="${esc(r.model)}"></div>
        <div class="form-group"><label>Hãng SX</label><input id="f_hang" value="${esc(r.hang_san_xuat)}"></div>
        <div class="form-group"><label>Nước SX</label><input id="f_nuoc" value="${esc(r.nuoc_san_xuat)}"></div>
        <div class="form-group"><label>Số máy</label><input id="f_so_may" value="${esc(r.so_may)}"></div>
        <div class="form-group"><label>Năm SĐ</label><input type="number" id="f_nam" value="${r.nam_su_dung||2025}"></div>
        <div class="form-group"><label>Tình trạng</label>
            <select id="f_tinh_trang">
                ${['Hoạt động bình thường','Báo lỗi','Hỏng','Đang bảo dưỡng','Đã thanh lý']
                    .map(t=>`<option ${t===r.tinh_trang?'selected':''}>${t}</option>`).join('')}
            </select>
        </div>
        <div class="form-group"><label>Người QL</label>${searchSelect('sd_ql', staffData, '🔍 Tìm NV...', r.nguoi_quan_ly_id)}</div>
        <div class="form-group"><label>Ghi chú</label><textarea id="f_gc">${esc(r.ghi_chu)}</textarea></div>
    `, async () => {
        await api(`/api/thiet-bi/${id}`, { method: 'PUT', body: JSON.stringify({
            ten_thiet_bi: $('#f_ten').value.trim(), model: $('#f_model').value.trim(),
            hang_san_xuat: $('#f_hang').value.trim(), nuoc_san_xuat: $('#f_nuoc').value.trim(),
            so_may: $('#f_so_may').value.trim(), nam_su_dung: parseInt($('#f_nam').value),
            tinh_trang: $('#f_tinh_trang').value,
            nguoi_quan_ly_id: ssVal('sd_ql') ? parseInt(ssVal('sd_ql')) : null,
            ghi_chu: $('#f_gc').value
        })});
        closeModal(); toast('Đã cập nhật!'); filterSettDevices();
    });
}

async function deleteSettDevice(id) {
    if (!confirm('Xóa thiết bị này? Thao tác không thể hoàn tác.')) return;
    try {
        await api(`/api/thiet-bi/${id}`, {method:'DELETE'});
        toast('Đã xóa!'); filterSettDevices();
    } catch (e) { toast(e.message, true); }
}
