/* Dashboard Page */

// Map status keys from API to filter values for the Devices page
const STATUS_FILTER_MAP = {
    'Hoạt động': 'Hoạt động bình thường',
    'Báo lỗi': 'Báo lỗi',
    'Hỏng': 'Hỏng',
};

function goToDevices(filter, type) {
    // type: 'status' | 'search'
    navigate('devices');
    // Wait for DOM to render then apply filter
    setTimeout(() => {
        if (type === 'status' && $('#devStatus')) {
            // Try to match the filter value to a select option
            const sel = $('#devStatus');
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].value === filter || sel.options[i].text === filter) {
                    sel.selectedIndex = i;
                    break;
                }
            }
            filterDevices();
        } else if (type === 'search' && $('#devSearch')) {
            $('#devSearch').value = filter;
            filterDevices();
        }
    }, 300);
}

async function renderDashboard(el) {
    const d = await api('/api/dashboard');
    const maxUsage = Math.max(...Object.values(d.usage), 1);
    const maxStatus = Math.max(...Object.values(d.status), 1);

    el.innerHTML = `
        <h1 class="page-title">📊 Dashboard — Tổng quan hệ thống</h1>
        <div class="stats-grid">
            <div class="stat-card blue clickable" onclick="goToDevices('','status')"><span class="stat-icon">🖥️</span><div class="stat-info"><div class="stat-value">${d.total}</div><div class="stat-label">Tổng thiết bị</div></div></div>
            <div class="stat-card green clickable" onclick="goToDevices('Hoạt động bình thường','status')"><span class="stat-icon">✅</span><div class="stat-info"><div class="stat-value">${d.active}</div><div class="stat-label">Hoạt động</div></div></div>
            <div class="stat-card red clickable" onclick="goToDevices('Báo lỗi','status')"><span class="stat-icon">⚠️</span><div class="stat-info"><div class="stat-value">${d.error}</div><div class="stat-label">Báo lỗi / Hỏng</div></div></div>
            <div class="stat-card yellow clickable" onclick="navigate('sessions')"><span class="stat-icon">📋</span><div class="stat-info"><div class="stat-value">${d.sessions_today}</div><div class="stat-label">Tần xuất HĐ hôm nay</div></div></div>
        </div>
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">Tình trạng thiết bị</div>
                ${(() => {
                    const order = ['Hoạt động', 'Báo lỗi', 'Hỏng', 'Đang bảo dưỡng', 'Đã thanh lý'];
                    const colorMap = {'Báo lỗi':'#ffc107','Hỏng':'#e94560','Hoạt động':'#1a73e8','Đang bảo dưỡng':'#9c27b0','Đã thanh lý':'#888'};
                    const sorted = Object.entries(d.status).sort((a,b) => {
                        const ai = order.indexOf(a[0]), bi = order.indexOf(b[0]);
                        return (ai===-1?99:ai) - (bi===-1?99:bi);
                    });
                    return sorted.map(([k,v]) => {
                        const c = colorMap[k] || '#00c853';
                        return `<div class="bar-row clickable" onclick="goToDevices('${STATUS_FILTER_MAP[k]||k}','status')">
                            <div class="bar-label">${k}</div>
                            <div class="bar-track"><div class="bar-fill" style="width:${(v/maxStatus)*100}%;background:${c}">${v}</div></div>
                        </div>`;
                    }).join('');
                })()}
            </div>
            <div class="chart-card">
                <div class="chart-title">Tần suất sử dụng</div>
                ${Object.entries(d.usage).map(([k,v], i) => `
                    <div class="bar-row clickable" onclick="goToDevices('','status')">
                        <div class="bar-label">${k}</div>
                        <div class="bar-track"><div class="bar-fill" style="width:${(v/maxUsage)*100}%;background:${barColors(i)}">${v}</div></div>
                    </div>
                `).join('')}
            </div>
        </div>
        <div class="alert-card">
            <div class="chart-title">🔔 Cảnh báo</div>
            ${d.alerts.length ? d.alerts.map(a => {
                let onclick = '';
                if (a.type === 'error') onclick = `onclick="goToDevices('Hỏng','status')"`;
                else if (a.type === 'warning') onclick = `onclick="goToDevices('Báo lỗi','status')"`;
                else onclick = `onclick="navigate('maintenance')"`;
                return `<div class="alert-item ${a.type} clickable" ${onclick}>
                    ${a.type==='error'?'🔴':a.type==='warning'?'🟡':'🔵'} ${esc(a.msg)}
                </div>`;
            }).join('') : '<div style="color:var(--text-muted);padding:8px">✅ Không có cảnh báo.</div>'}
        </div>
    `;
}
