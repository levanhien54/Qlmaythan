/* Staff Page — CRUD nhân viên */

async function renderStaff(el) {
    const cfg = await getConfig();
    el.innerHTML = `
        <h1 class="page-title">👥 Quản lý Nhân viên</h1>
        <div class="toolbar">
            <input type="search" id="staffSearch" placeholder="🔍 Tìm theo tên..." oninput="filterStaff()">
            <select id="staffRole" onchange="filterStaff()">
                <option value="">Tất cả chức vụ</option>
                ${cfg.chuc_vu.map(c => `<option>${c}</option>`).join('')}
            </select>
            <div class="spacer"></div>
            <button class="btn btn-primary" onclick="addStaff()">➕ Thêm nhân viên</button>
        </div>
        <div class="table-wrapper" id="staffTableWrap">
            <table>
                <thead><tr>
                    <th>STT</th><th>Họ và tên</th><th>Chức vụ / Trình độ</th><th>Thao tác</th>
                </tr></thead>
                <tbody id="staffBody"></tbody>
            </table>
        </div>
        <div class="table-footer" id="staffCount"></div>
    `;
    filterStaff();
}

async function filterStaff() {
    destroyScrolls();
    const search = $('#staffSearch')?.value || '';
    const chuc_vu = $('#staffRole')?.value || '';
    const base = `/api/nhan-vien?search=${encodeURIComponent(search)}&chuc_vu=${encodeURIComponent(chuc_vu)}`;
    const scr = new InfiniteScroll('#staffTableWrap', '#staffBody', '#staffCount',
        (offset, limit) => api(`${base}&limit=${limit}&offset=${offset}`),
        (r, i) => `<tr>
            <td>${i+1}</td><td>${esc(r.ho_ten)}</td><td>${esc(r.chuc_vu_trinh_do)}</td>
            <td class="actions">
                <button class="btn btn-edit" onclick="editStaff(${r.id})">✏️</button>
                <button class="btn btn-danger" onclick="deleteStaff(${r.id})">🗑️</button>
            </td>
        </tr>`,
        'nhân viên'
    );
    registerScroll(scr);
    await scr.loadFirst();
}

async function addStaff() {
    const cfg = await getConfig();
    openModal('➕ Thêm nhân viên', `
        <div class="form-group"><label>Họ và tên *</label><input id="f_ten" placeholder="Họ và tên"></div>
        <div class="form-group"><label>Chức vụ / Trình độ</label>
            <select id="f_cv">${cfg.chuc_vu.map(c => `<option>${c}</option>`).join('')}</select>
        </div>
    `, async () => {
        if (!$('#f_ten').value.trim()) return toast('Vui lòng nhập tên', true);
        await api('/api/nhan-vien', { method: 'POST', body: JSON.stringify({
            ho_ten: $('#f_ten').value.trim(),
            chuc_vu_trinh_do: $('#f_cv').value,
        })});
        closeModal();
        toast('Đã thêm!');
        filterStaff();
    });
}

async function editStaff(id) {
    const r = await api(`/api/nhan-vien/${id}`);
    const cfg = await getConfig();
    openModal('✏️ Sửa nhân viên', `
        <div class="form-group"><label>Họ và tên *</label><input id="f_ten" value="${esc(r.ho_ten)}"></div>
        <div class="form-group"><label>Chức vụ</label>
            <select id="f_cv">${cfg.chuc_vu.map(c => `<option ${c===r.chuc_vu_trinh_do?'selected':''}>${c}</option>`).join('')}</select>
        </div>
    `, async () => {
        await api(`/api/nhan-vien/${id}`, { method: 'PUT', body: JSON.stringify({
            ho_ten: $('#f_ten').value.trim(),
            chuc_vu_trinh_do: $('#f_cv').value,
        })});
        closeModal();
        toast('Đã cập nhật!');
        filterStaff();
    });
}

async function deleteStaff(id) {
    if (!confirm('Xóa nhân viên này?')) return;
    try {
        await api(`/api/nhan-vien/${id}`, { method: 'DELETE' });
        toast('Đã xóa!');
        filterStaff();
    } catch (e) { toast(e.message, true); }
}
