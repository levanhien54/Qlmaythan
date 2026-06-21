/* Statistics Page */

async function renderStatistics(el) {
    const stats = await api('/api/statistics');
    const maxUsage = Math.max(...Object.values(stats.usage_per_device), 1);
    const maxSes = stats.sessions_per_machine.length ? Math.max(...stats.sessions_per_machine.map(s=>s.so_phien), 1) : 1;

    el.innerHTML = `
        <h1 class="page-title">📈 Thống kê & Báo cáo</h1>
        <div class="summary-grid">
            <div class="summary-card"><div class="sc-label">💰 Tổng chi phí bảo dưỡng</div><div class="sc-value">${stats.total_cost.toLocaleString()} VNĐ</div></div>
            <div class="summary-card"><div class="sc-label">🏆 Máy dùng nhiều nhất</div><div class="sc-value">${stats.top_machine ? esc(stats.top_machine.may_thuc_hien)+' ('+stats.top_machine.so_phien+' lần)' : '-'}</div></div>
            <div class="summary-card"><div class="sc-label">📊 Tỷ lệ hoạt động</div><div class="sc-value">${stats.active_rate}%</div></div>
        </div>
        <div class="chart-card" style="margin-bottom:20px">
            <div class="chart-title">Tần suất sử dụng theo máy (0-3)</div>
            ${Object.entries(stats.usage_per_device).slice(0,25).map(([k,v],i) => `
                <div class="bar-row">
                    <div class="bar-label" style="width:200px" title="${esc(k)}">${esc(k.length>25?k.substring(0,23)+'...':k)}</div>
                    <div class="bar-track"><div class="bar-fill" style="width:${Math.max((v/3)*100,5)}%;background:${barColors(i)}">${v}</div></div>
                </div>
            `).join('')}
        </div>
        <div class="chart-card">
            <div class="chart-title">Tần suất theo máy (Top 20)</div>
            ${stats.sessions_per_machine.slice(0,20).map((s,i) => `
                <div class="bar-row">
                    <div class="bar-label" style="width:200px" title="${esc(s.may_thuc_hien)}">${esc(s.may_thuc_hien.length>25?s.may_thuc_hien.substring(0,23)+'...':s.may_thuc_hien)}</div>
                    <div class="bar-track"><div class="bar-fill" style="width:${(s.so_phien/maxSes)*100}%;background:${barColors(i)}">${s.so_phien}</div></div>
                </div>
            `).join('')}
        </div>
    `;
}
