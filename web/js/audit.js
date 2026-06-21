/* Nhật ký & Khôi phục (audit log) */

const _AUDIT_ACTION = { create: 'Tạo', update: 'Sửa', delete: 'Xóa', restore: 'Khôi phục' };
const _AUDIT_ENTITY = {
    thiet_bi: 'Thiết bị', nhan_vien: 'Nhân viên', phien_dieu_tri: 'Phiên ĐT',
    bao_duong: 'Bảo dưỡng', ban_giao: 'Bàn giao',
};

function _auditSummary(r) {
    const d = r.data_obj || {};
    return d.ho_ten || d.ten_thiet_bi || d.may_thuc_hien || d.loai || d.ngay_ban_giao || '';
}

async function renderAudit(el) {
    el.innerHTML = `
        <h1 class="page-title">🗒️ Nhật ký & Khôi phục</h1>
        <div class="toolbar">
            <select id="auEntity" onchange="filterAudit()">
                <option value="">Tất cả bảng</option>
                <option value="thiet_bi">Thiết bị</option>
                <option value="nhan_vien">Nhân viên</option>
                <option value="phien_dieu_tri">Phiên điều trị</option>
                <option value="bao_duong">Bảo dưỡng</option>
                <option value="ban_giao">Bàn giao</option>
            </select>
            <select id="auAction" onchange="filterAudit()">
                <option value="">Tất cả hành động</option>
                <option value="delete">Đã xóa (khôi phục được)</option>
                <option value="create">Tạo</option>
                <option value="update">Sửa</option>
                <option value="restore">Khôi phục</option>
            </select>
            <div class="spacer"></div>
        </div>
        <div class="table-wrapper" style="flex:1;min-height:0">
            <table><thead><tr>
                <th>Thời gian</th><th>Hành động</th><th>Bảng</th><th>ID</th><th>Tóm tắt</th><th>Thao tác</th>
            </tr></thead><tbody id="auBody"></tbody></table>
        </div>
        <div class="table-footer" id="auCount"></div>`;
    filterAudit();
}

async function filterAudit() {
    const entity = $('#auEntity')?.value || '';
    const action = $('#auAction')?.value || '';
    let url = '/api/audit?limit=200';
    if (entity) url += `&entity=${entity}`;
    if (action) url += `&action=${action}`;
    let rows;
    try { rows = await api(url); } catch (e) { return toast(e.message, true); }
    const body = $('#auBody');
    if (!body) return;
    body.innerHTML = rows.map(r => {
        const canRestore = r.action === 'delete';
        const btn = canRestore
            ? `<button class="btn btn-edit" title="Khôi phục" onclick="restoreAudit(${r.id})">↩️ Khôi phục</button>`
            : '';
        return `<tr>
            <td>${esc((r.ts || '').substring(0, 19))}</td>
            <td>${esc(_AUDIT_ACTION[r.action] || r.action)}</td>
            <td>${esc(_AUDIT_ENTITY[r.entity] || r.entity)}</td>
            <td>${r.entity_id ?? ''}</td>
            <td>${esc(_auditSummary(r))}</td>
            <td class="actions">${btn}</td>
        </tr>`;
    }).join('');
    $('#auCount').textContent = `Hiển thị: ${rows.length} mục`;
}

async function restoreAudit(id) {
    if (!confirm('Khôi phục bản ghi đã xóa này?')) return;
    try {
        await api(`/api/audit/${id}/restore`, { method: 'POST' });
        toast('Đã khôi phục!');
        filterAudit();
    } catch (e) { toast(e.message, true); }
}
