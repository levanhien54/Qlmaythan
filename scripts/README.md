# Dev scripts (one-off / manual)

Các script tay để debug, audit, sửa dữ liệu lẻ tẻ. **Không** dùng cho runtime.

| File | Mục đích |
|---|---|
| `read_excel1.py` / `read_excel2.py` | Đọc 2 file Excel nguồn ra stdout để khảo sát |
| `read_headers.py` | In header của Excel phiên điều trị |
| `audit_db.py` | Kiểm tra nhất quán dữ liệu SQLite |
| `fix_mapping.py` | Sửa ánh xạ tên máy/nhân viên lỗi lịch sử |
| `test_import.py` | Integration test gọi thẳng API (`localhost:5000`). Yêu cầu server đang chạy + `xlwt`. **Không** phải pytest — chạy `python scripts/test_import.py` |

Unit tests thực sự nằm ở [../tests/](../tests/) và chạy qua `pytest`.
