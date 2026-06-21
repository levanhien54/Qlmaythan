# Quản lý Máy Chạy Thận

Hệ thống quản lý thiết bị lọc máu (máy chạy thận) cho khoa Thận nhân tạo —
**Bệnh viện Đa khoa Bắc Ninh Số 2**. Quản lý thiết bị, nhân viên, phiên điều
trị, lịch sử bảo dưỡng/sửa chữa và bàn giao thiết bị.

> ⚠️ **Bảo mật dữ liệu y tế:** Repo này **không** chứa dữ liệu bệnh nhân thật
> (các file `*.xls`, `*.xlsx`, `*.db` đã bị `.gitignore`). Bạn phải tự cung cấp
> file dữ liệu của mình. Tuyệt đối **không commit** hồ sơ bệnh nhân lên repo công khai.

## Tính năng

- **Dashboard** — tổng quan: số thiết bị, hoạt động/lỗi/hỏng, phiên hôm nay, cảnh báo.
- **Thiết bị** — CRUD, lọc theo tình trạng/model, trang chi tiết (phiên + bảo dưỡng + bàn giao).
- **Nhân viên** — CRUD bác sĩ / KTV / điều dưỡng.
- **Phiên điều trị** — CRUD + **nhập từ Excel** (tự khớp tên máy & nhân viên, kiểm trùng khung giờ).
- **Bảo dưỡng & sửa chữa** — CRUD, cảnh báo phiếu sắp đến hạn (7 ngày).
- **Bàn giao** — CRUD, **bàn giao hàng loạt** (nguyên tử), **xuất PDF** biên bản có ký tên.
- **Thống kê** — chi phí bảo dưỡng, máy dùng nhiều nhất, tỷ lệ hoạt động, xuất Excel.

## Kiến trúc

Hai giao diện dùng **chung** tầng truy vấn `database/queries/` và logic nghiệp vụ:

```
┌─────────────────┐     ┌──────────────────────┐
│  Web UI (web/)  │     │ Desktop UI (ui/, PyQt6)│
│  HTML+JS fetch  │     │                       │
└────────┬────────┘     └───────────┬───────────┘
         │ REST JSON                │ gọi trực tiếp
┌────────▼────────┐                 │
│  server.py      │  Flask API      │
└────────┬────────┘                 │
         └──────────┬───────────────┘
            ┌────────▼─────────┐
            │ database/queries │  (thiet_bi, nhan_vien, phien_dieu_tri,
            │ matching.py      │   bao_duong, ban_giao)
            │ excel_import.py  │  ← logic nhập Excel dùng chung
            └────────┬─────────┘
                ┌────▼────┐
                │ SQLite  │  data/ql_may_than.db
                └─────────┘
```

- **Backend:** Flask + flask-cors
- **Desktop:** PyQt6
- **CSDL:** SQLite (WAL, `foreign_keys=ON`, per-thread connection)
- **Excel:** openpyxl (`.xlsx`) + xlrd (`.xls`)
- **PDF:** reportlab

## Cài đặt

```bash
git clone https://github.com/levanhien54/Qlmaythan.git
cd Qlmaythan
python -m pip install -r requirements.txt
```

### Cung cấp dữ liệu (tùy chọn — để import lần đầu)

Sửa đường dẫn trong [`config.py`](config.py) cho đúng file Excel của bạn:

```python
EXCEL_THIET_BI = ".../danh_sach_thiet_bi.xlsx"   # danh sách thiết bị
EXCEL_PHIEN_DT = ".../phien_dieu_tri.xls"        # phiên điều trị
```

Nếu không có file, app vẫn chạy với CSDL rỗng (thêm dữ liệu qua giao diện).

## Chạy ứng dụng

**Web** (mở http://localhost:5000):
```bash
python server.py
```
> `debug` TẮT mặc định. Bật khi phát triển: đặt biến môi trường `FLASK_DEBUG=1`.
> Không có xác thực — chỉ dùng trong mạng nội bộ tin cậy.

**Desktop:**
```bash
python main.py
```

## Kiểm thử

```bash
# Toàn bộ (266 test). Tắt cache nếu gặp lỗi quyền ghi .pytest_cache:
python -m pytest -p no:cacheprovider -q

# Test GUI (PyQt) chạy ẩn, không mở cửa sổ:
QT_QPA_PLATFORM=offscreen python -m pytest -p no:cacheprovider -q
```

Bộ test bao gồm: matching, import Excel e2e, queries, concurrency, audit, bảo mật
API (chống SQL injection / phân quyền cột), GUI headless, và **connectivity từng
màn hình** (UI ↔ backend).

## Cấu trúc thư mục

```
server.py            # Flask REST API
main.py              # Điểm vào desktop PyQt6
matching.py          # Khớp tên máy/nhân viên + parse ngày Excel
excel_import.py      # Logic nhập Excel (dùng chung web + desktop)
import_data.py       # Nhập dữ liệu khởi tạo từ Excel
config.py            # Cấu hình (đường dẫn, hằng số nghiệp vụ)
database/            # connection, models (schema), queries/
ui/                  # Desktop: pages/, dialogs/, components/
web/                 # Web: index.html, app.js, js/*.js, styles.css
scripts/             # Tiện ích audit & dọn dữ liệu (dry-run mặc định)
tests/               # pytest
```

## Sao lưu dữ liệu

- App **tự sao lưu DB** mỗi lần khởi động (web + desktop) vào `data/backups/`, giữ 10 bản gần nhất (dùng SQLite online-backup, an toàn cả khi đang ghi/WAL).
- Sao lưu thủ công / theo lịch: `python scripts/backup_db.py` (đặt vào Task Scheduler / cron để chạy hằng ngày).
- Thư mục `data/backups/` và `data/app.log` chứa dữ liệu BN → đã `.gitignore`.

## Ghi chú bảo mật

- Không commit dữ liệu bệnh nhân (`*.xls/*.xlsx/*.db` đã ignore).
- `update()` ở tầng query whitelist cột → chặn SQL injection / mass-assignment.
- Xóa thiết bị còn lịch sử / nhân viên đang được tham chiếu bị **chặn** để tránh mất dữ liệu.
- Đầu ra hiển thị trên web được escape HTML (chống XSS).
