/* ================================================
   Quản lý Máy Chạy Thận — Utils & Shared Functions
   ================================================ */

const API = '';
let currentPage = 'dashboard';
let currentModalSave = null;
let cachedConfig = null;

// ========== HTML ESCAPE (chống XSS) ==========
// Mọi dữ liệu người dùng/nhập từ Excel (tên BN, ghi chú, tên máy...) phải đi qua
// esc() trước khi chèn vào innerHTML hoặc value="..." để tránh chèn mã/HTML.
function esc(v) {
    if (v === null || v === undefined) return '';
    return String(v)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Cắt giữa chuỗi, GIỮ phần đuôi (vd "...số 8") — tên máy phân biệt nhau ở cuối.
function midTrunc(s, max = 26) {
    s = String(s || '');
    if (s.length <= max) return s;
    const head = Math.ceil((max - 1) / 2), tail = Math.floor((max - 1) / 2);
    return s.slice(0, head) + '…' + s.slice(-tail);
}

// Local date helper (avoids UTC offset issue with toISOString)
function todayLocal() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

/**
 * Auto-format time input: 2030→20:30, 830→08:30, 9→09:00
 * Validates HH:MM (00:00–23:59), shows red border on error.
 */
function initTimeInput(el) {
    if (!el) return;
    el.addEventListener('input', () => {
        // Strip everything except digits and colon
        let v = el.value.replace(/[^\d:]/g, '');
        el.value = v;
    });
    el.addEventListener('blur', () => {
        let raw = el.value.replace(/[^\d:]/g, '');
        if (!raw) { el.style.borderColor = ''; return; }

        let h, m;
        if (raw.includes(':')) {
            // Already has colon: split
            const p = raw.split(':');
            h = parseInt(p[0]) || 0;
            m = parseInt(p[1]) || 0;
        } else {
            // Pure digits: 2030→20:30, 830→08:30, 30→00:30, 9→09:00
            const digits = raw.replace(/\D/g, '');
            if (digits.length >= 3) {
                m = parseInt(digits.slice(-2));
                h = parseInt(digits.slice(0, -2));
            } else if (digits.length === 2) {
                // "08" → 08:00, "20" → 20:00
                h = parseInt(digits);
                m = 0;
            } else {
                // single digit "9" → 09:00
                h = parseInt(digits);
                m = 0;
            }
        }

        // Validate
        if (h < 0 || h > 23 || m < 0 || m > 59 || isNaN(h) || isNaN(m)) {
            el.style.borderColor = '#ff4444';
            toast('Giờ không hợp lệ! Nhập HH:MM (00:00 – 23:59)', true);
            return;
        }

        el.value = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
        el.style.borderColor = '';
    });
}

// ========== API ==========
async function api(path, options = {}) {
    const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        let msg = `API error: ${res.status}`;
        try { const j = await res.json(); if (j.error) msg = j.error; } catch(e) {}
        throw new Error(msg);
    }
    return res.json();
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

// ========== TOAST ==========
function toast(msg, isError = false) {
    const el = document.createElement('div');
    el.className = `toast${isError ? ' error' : ''}`;
    el.textContent = msg;
    $('#toastContainer').appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

// ========== STATUS BADGE ==========
// Kèm BIỂU TƯỢNG hình dạng (không chỉ màu) để phân biệt trạng thái khi in
// trắng-đen / người mù màu. Glyph unicode nên không cần font icon.
function statusBadge(text) {
    if (!text) return '';
    const t = text.toLowerCase();
    let cls = 'badge-info', icon = '•';
    if (t.includes('bình thường') || t.includes('hoạt động')) { cls = 'badge-ok'; icon = '✓'; }
    else if (t.includes('hỏng')) { cls = 'badge-error'; icon = '✕'; }
    else if (t.includes('lỗi') || t.includes('nghỉ')) { cls = 'badge-warning'; icon = '⚠'; }
    else if (t.includes('hoàn thành') || t.includes('bàn giao')) { cls = 'badge-done'; icon = '✓'; }
    else if (t.includes('thu hồi')) { cls = 'badge-warning'; icon = '↩'; }
    else if (t.includes('đang')) { cls = 'badge-progress'; icon = '⟳'; }
    else if (t.includes('chờ')) { cls = 'badge-pending'; icon = '⏳'; }
    return `<span class="badge ${cls}"><span aria-hidden="true">${icon}</span> ${esc(text)}</span>`;
}

// ========== INFO MODAL (chỉ hiển thị, không có nút Lưu) ==========
function showInfoModal(title, bodyHTML) {
    $('#modalTitle').textContent = title;
    $('#modalBody').innerHTML = bodyHTML;
    currentModalSave = null;
    const f = document.querySelector('#modal .modal-footer');
    if (f) f.style.display = 'none';   // ẩn Hủy/Lưu cho hộp thoại thông tin
    $('#modalOverlay').classList.add('open');
}

// ========== CHART COLORS ==========
function barColors(i) {
    const colors = ['#e94560','#1a73e8','#00c853','#ffc107','#9c27b0','#ff9800','#00bcd4','#8bc34a'];
    return colors[i % colors.length];
}

// ========== MODAL ==========
function openModal(title, bodyHTML, saveFn) {
    $('#modalTitle').textContent = title;
    $('#modalBody').innerHTML = bodyHTML;
    currentModalSave = saveFn;
    $('#modalSave').textContent = '💾 Lưu';
    const _f = document.querySelector('#modal .modal-footer');
    if (_f) _f.style.display = '';   // khôi phục footer (showInfoModal có thể đã ẩn)
    $('#modalOverlay').classList.add('open');
    // Auto-init time inputs (HH:MM text fields)
    $$('#modalBody input[placeholder="HH:MM"]').forEach(el => initTimeInput(el));
    // Enter → next field (or save on last field)
    const fields = [...$$('#modalBody input, #modalBody select, #modalBody textarea')];
    fields.forEach((el, i) => {
        el.addEventListener('keydown', e => {
            if (e.key === 'Enter' && el.tagName !== 'TEXTAREA') {
                e.preventDefault();
                el.blur(); // trigger auto-format on time inputs
                if (i < fields.length - 1) {
                    fields[i + 1].focus();
                } else {
                    saveModal();
                }
            }
        });
    });
}

function closeModal() {
    $('#modalOverlay').classList.remove('open');
    currentModalSave = null;
    // Khôi phục footer (showInfoModal có thể đã ẩn) — tránh modal form sau mất nút Lưu.
    const f = document.querySelector('#modal .modal-footer');
    if (f) f.style.display = '';
}

function saveModal() {
    if (currentModalSave) currentModalSave();
}

// ========== CONFIG ==========
async function getConfig() {
    if (!cachedConfig) cachedConfig = await api('/api/config');
    return cachedConfig;
}

// ========== LOAD OPTIONS ==========
async function loadStaffOptions() {
    const staff = await api('/api/nhan-vien');
    return staff.map(s => `<option value="${s.id}">${s.ho_ten} (${s.chuc_vu_trinh_do})</option>`).join('');
}

async function loadDeviceOptions(filterInactive = false) {
    const devices = await api('/api/thiet-bi');
    const filtered = filterInactive
        ? devices.filter(d => {
            const tt = (d.tinh_trang || '').toLowerCase();
            return !tt.includes('hỏng') && !tt.includes('thanh lý') && !tt.includes('báo lỗi');
          })
        : devices;
    return filtered.map(d => `<option value="${d.id}">${d.ten_thiet_bi}</option>`).join('');
}

// ========== LOAD RAW DATA ==========
async function loadStaffData() {
    const staff = await api('/api/nhan-vien');
    return staff.map(s => ({ value: String(s.id), label: `${s.ho_ten} (${s.chuc_vu_trinh_do})` }));
}

async function loadDeviceData(filterInactive = false) {
    const devices = await api('/api/thiet-bi');
    const filtered = filterInactive
        ? devices.filter(d => {
            const tt = (d.tinh_trang || '').toLowerCase();
            return !tt.includes('hỏng') && !tt.includes('thanh lý') && !tt.includes('báo lỗi');
          })
        : devices;
    return filtered.map(d => ({ value: String(d.id), label: d.ten_thiet_bi }));
}

// ========== SEARCHABLE SELECT ==========
/**
 * Generate a searchable select (combobox + search hybrid).
 * @param {string} id - Unique ID for this component
 * @param {Array<{value:string, label:string}>} items - Options
 * @param {string} placeholder - Placeholder text
 * @param {string} [selectedVal] - Pre-selected value
 * @returns {string} HTML string
 */
function searchSelect(id, items, placeholder = '-- Tìm và chọn --', selectedVal = '') {
    const selectedItem = items.find(i => i.value === String(selectedVal));
    const displayText = selectedItem ? selectedItem.label : '';
    return `
        <div class="ss-wrapper" id="ss_${id}" onmouseleave="ssClose('${id}')">
            <input type="text" class="ss-input" id="ssi_${id}"
                placeholder="${esc(placeholder)}"
                value="${esc(displayText)}"
                autocomplete="off"
                onfocus="ssOpen('${id}')"
                oninput="ssFilter('${id}')"
                onkeydown="ssKeydown(event,'${id}')"
            >
            <input type="hidden" id="ssv_${id}" value="${esc(selectedVal)}">
            <div class="ss-clear ${selectedVal ? 'visible' : ''}" id="ssc_${id}" onclick="ssClear('${id}')">✕</div>
            <div class="ss-dropdown" id="ssd_${id}">
                ${items.map(i => `<div class="ss-option" data-value="${esc(i.value)}" onclick="ssPick('${id}',this.dataset.value,this.textContent)">${esc(i.label)}</div>`).join('')}
                <div class="ss-empty" style="display:none">Không tìm thấy</div>
            </div>
        </div>
    `;
}

function ssOpen(id) {
    // Close all other dropdowns first
    $$('.ss-dropdown.open').forEach(d => d.classList.remove('open'));
    const dd = $(`#ssd_${id}`);
    if (dd) dd.classList.add('open');
    // Select input text for easy replacement
    const inp = $(`#ssi_${id}`);
    if (inp) inp.select();
    // Clear highlight
    _ssHighlightIdx[id] = -1;
    if (dd) dd.querySelectorAll('.ss-option').forEach(o => o.classList.remove('ss-highlight'));
}

function ssFilter(id) {
    const inp = $(`#ssi_${id}`);
    const dd = $(`#ssd_${id}`);
    if (!inp || !dd) return;
    const q = inp.value.toLowerCase().trim();
    let found = 0;
    dd.querySelectorAll('.ss-option').forEach(opt => {
        const match = opt.textContent.toLowerCase().includes(q);
        opt.style.display = match ? '' : 'none';
        opt.classList.remove('ss-highlight');
        if (match) found++;
    });
    const empty = dd.querySelector('.ss-empty');
    if (empty) empty.style.display = found ? 'none' : 'block';
    dd.classList.add('open');
    // Clear selection if user edits
    $(`#ssv_${id}`).value = '';
    const clr = $(`#ssc_${id}`);
    if (clr) clr.classList.remove('visible');
    _ssHighlightIdx[id] = -1;
}

// Track highlighted index per searchable select
let _ssHighlightIdx = {};

function ssKeydown(e, id) {
    const dd = $(`#ssd_${id}`);
    if (!dd) return;
    const visibleOpts = [...dd.querySelectorAll('.ss-option')].filter(o => o.style.display !== 'none');
    if (!visibleOpts.length) return;

    let idx = _ssHighlightIdx[id] ?? -1;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        idx = Math.min(idx + 1, visibleOpts.length - 1);
        _ssHighlightIdx[id] = idx;
        _ssUpdateHighlight(visibleOpts, idx);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        idx = Math.max(idx - 1, 0);
        _ssHighlightIdx[id] = idx;
        _ssUpdateHighlight(visibleOpts, idx);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (idx >= 0 && idx < visibleOpts.length) {
            const opt = visibleOpts[idx];
            ssPick(id, opt.dataset.value, opt.textContent);
        }
    } else if (e.key === 'Escape') {
        dd.classList.remove('open');
        _ssHighlightIdx[id] = -1;
    }
}

function _ssUpdateHighlight(opts, idx) {
    opts.forEach((o, i) => {
        o.classList.toggle('ss-highlight', i === idx);
        if (i === idx) o.scrollIntoView({ block: 'nearest' });
    });
}

function ssPick(id, value, label) {
    const inp = $(`#ssi_${id}`);
    const hidden = $(`#ssv_${id}`);
    const dd = $(`#ssd_${id}`);
    const clr = $(`#ssc_${id}`);
    if (inp) inp.value = label;
    if (hidden) hidden.value = value;
    if (dd) dd.classList.remove('open');
    if (clr) clr.classList.add('visible');
    _ssHighlightIdx[id] = -1;
}

function ssClear(id) {
    const inp = $(`#ssi_${id}`);
    const hidden = $(`#ssv_${id}`);
    const clr = $(`#ssc_${id}`);
    if (inp) { inp.value = ''; inp.focus(); }
    if (hidden) hidden.value = '';
    if (clr) clr.classList.remove('visible');
    ssFilter(id);
}

/** Close a specific searchable select dropdown (used on mouseleave) */
function ssClose(id) {
    const dd = $(`#ssd_${id}`);
    if (!dd || !dd.classList.contains('open')) return;
    dd.classList.remove('open');
    // Restore input text to selected value
    const inp = $(`#ssi_${id}`);
    const hidden = $(`#ssv_${id}`);
    if (inp && hidden && hidden.value) {
        const selected = dd.querySelector(`.ss-option[data-value="${hidden.value}"]`);
        if (selected) inp.value = selected.textContent;
    } else if (inp && hidden && !hidden.value) {
        inp.value = '';
    }
    dd.querySelectorAll('.ss-option').forEach(o => o.classList.remove('ss-highlight'));
    _ssHighlightIdx[id] = -1;
}

/** Get the selected value of a searchable select */
function ssVal(id) {
    const el = $(`#ssv_${id}`);
    return el ? el.value : '';
}

// A11y: phần tử .clickable (thẻ card/hàng/cảnh báo) kích hoạt bằng Enter/Space
// như nút thật. Cần kèm tabindex="0" role="button" trên phần tử đó.
document.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ')
        && e.target.classList && e.target.classList.contains('clickable')) {
        e.preventDefault();
        e.target.click();
    }
});

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.ss-wrapper')) {
        $$('.ss-dropdown.open').forEach(d => {
            d.classList.remove('open');
            // Restore input text to selected value if user didn't pick
            const wrapper = d.closest('.ss-wrapper');
            if (wrapper) {
                const inp = wrapper.querySelector('.ss-input');
                const hidden = wrapper.querySelector('input[type="hidden"]');
                if (inp && hidden && hidden.value) {
                    const selected = d.querySelector(`.ss-option[data-value="${hidden.value}"]`);
                    if (selected) inp.value = selected.textContent;
                } else if (inp && hidden && !hidden.value) {
                    inp.value = '';
                }
            }
            d.querySelectorAll('.ss-option').forEach(o => o.classList.remove('ss-highlight'));
        });
    }
});

// ========== INFINITE SCROLL ==========
const PAGE_SIZE = 50;

/**
 * Reusable infinite scroll manager.
 * @param {string} wrapperSel - CSS selector for the .table-wrapper
 * @param {string} tbodySel - CSS selector for the tbody
 * @param {string} countSel - CSS selector for the footer count div
 * @param {function(offset, limit): Promise<Array>} fetchFn - Async function returning rows
 * @param {function(row, index): string} renderRow - Function returning TR html
 */
class InfiniteScroll {
    constructor(wrapperSel, tbodySel, countSel, fetchFn, renderRow, label = 'dòng') {
        this.wrapper = $(wrapperSel);
        this.tbody = $(tbodySel);
        this.countEl = $(countSel);
        this.fetchFn = fetchFn;
        this.renderRow = renderRow;
        this.label = label;
        this.offset = 0;
        this.totalLoaded = 0;
        this.loading = false;
        this.hasMore = true;
        this._onScroll = this._handleScroll.bind(this);
        if (this.wrapper) {
            this.wrapper.addEventListener('scroll', this._onScroll);
        }
    }

    async loadFirst() {
        this.offset = 0;
        this.totalLoaded = 0;
        this.hasMore = true;
        if (this.tbody) this.tbody.innerHTML = '';
        await this._loadMore();
    }

    async _loadMore() {
        if (this.loading || !this.hasMore) return;
        this.loading = true;
        try {
            const rows = await this.fetchFn(this.offset, PAGE_SIZE);
            if (rows.length < PAGE_SIZE) this.hasMore = false;
            const startIdx = this.totalLoaded;
            const html = rows.map((r, i) => this.renderRow(r, startIdx + i)).join('');
            if (this.tbody) this.tbody.insertAdjacentHTML('beforeend', html);
            this.totalLoaded += rows.length;
            this.offset += rows.length;
            this._updateCount();
        } catch (e) {
            console.error('InfiniteScroll load error:', e);
        }
        this.loading = false;
    }

    _handleScroll() {
        if (!this.wrapper || !this.hasMore || this.loading) return;
        const { scrollTop, scrollHeight, clientHeight } = this.wrapper;
        // Load more when scrolled past 2/3
        if (scrollTop + clientHeight >= scrollHeight * 0.67) {
            this._loadMore();
        }
    }

    _updateCount() {
        if (this.countEl) {
            this.countEl.textContent = `Hiển thị: ${this.totalLoaded} ${this.label}` +
                (this.hasMore ? ' (cuộn để xem thêm...)' : ' (hết)');
        }
    }

    destroy() {
        if (this.wrapper) {
            this.wrapper.removeEventListener('scroll', this._onScroll);
        }
    }
}

// Global scroll instances (destroyed on page switch)
let _scrollInstances = [];
function registerScroll(s) { _scrollInstances.push(s); }
function destroyScrolls() { _scrollInstances.forEach(s => s.destroy()); _scrollInstances = []; }
