/* ================================================
   Quản lý Máy Chạy Thận — Main Router
   All page modules loaded via separate script tags.
   ================================================ */

// ========== NAVIGATION ==========
function navigate(page) {
    currentPage = page;
    $$('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.page === page));
    renderPage(page);
}

async function renderPage(page) {
    destroyScrolls();
    const main = $('#mainContent');
    // Dashboard needs overflow-y auto (no table-wrapper), other pages use flex with table-wrapper scroll
    main.style.overflowY = page === 'dashboard' ? 'auto' : 'hidden';
    main.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted)">Đang tải...</div>';
    try {
        switch (page) {
            case 'dashboard': await renderDashboard(main); break;
            case 'devices': await renderDevices(main); break;
            case 'settings': await renderSettings(main); break;
            case 'maintenance': await renderMaintenance(main); break;
            case 'handover': await renderHandover(main); break;
            case 'sessions': await renderSessions(main); break;
            case 'staff': await renderStaff(main); break;
            case 'statistics': await renderStatistics(main); break;
            case 'audit': await renderAudit(main); break;
        }
    } catch (e) {
        main.innerHTML = `<div style="color:var(--status-error);padding:40px;">Lỗi: ${e.message}</div>`;
    }
}

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
    navigate('dashboard');
});
