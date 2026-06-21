# -*- coding: utf-8 -*-
"""
Cấu hình ứng dụng Quản lý Máy Chạy Thận
"""
import os

# === Đường dẫn ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ql_may_than.db")

# === Sao lưu & log ===
BACKUP_DIR = os.path.join(DATA_DIR, "backups")   # bản sao lưu DB (chứa dữ liệu BN → gitignore)
BACKUP_KEEP = 10                                  # giữ N bản sao lưu gần nhất
LOG_PATH = os.path.join(DATA_DIR, "app.log")      # log lỗi (có thể chứa dữ liệu BN → gitignore)

# === File Excel nguồn ===
EXCEL_THIET_BI = os.path.join(BASE_DIR, "Bảng tính không có tiêu đề.xlsx")
EXCEL_PHIEN_DT = os.path.join(BASE_DIR, "011.3.xls")

# === Ứng dụng ===
APP_NAME = "Quản lý Máy Chạy Thận"
APP_VERSION = "1.0.0"
WINDOW_MIN_WIDTH = 1280
WINDOW_MIN_HEIGHT = 800

# === Tình trạng thiết bị ===
TINH_TRANG = {
    "binh_thuong": "Hoạt động bình thường",
    "bao_loi": "Báo lỗi",
    "hong": "Hỏng",
    "bao_duong": "Đang bảo dưỡng",
    "thanh_ly": "Đã thanh lý",
}

# === Loại bảo dưỡng ===
LOAI_BAO_DUONG = [
    "Bảo dưỡng định kỳ",
    "Sửa chữa",
    "Thay thế linh kiện",
    "Báo máy lỗi",
    "Máy hỏng",
    "Thanh lý",
    "Trả máy",
]

# === Trạng thái bảo dưỡng ===
TRANG_THAI_BAO_DUONG = [
    "Hoàn thành",
    "Đang xử lý",
    "Chờ xử lý",
]

# === Chức vụ nhân viên ===
CHUC_VU = [
    "Bác sĩ",
    "Thạc sĩ Bác sĩ",
    "Tiến sĩ Bác sĩ",
    "Kỹ thuật viên",
    "Điều dưỡng",
    "Kỹ sư vật tư",
    "Khác",
]

# === Tần suất sử dụng ===
TAN_SUAT = {
    0: "Không sử dụng",
    1: "Thấp (1 ca/ngày)",
    2: "Trung bình (2 ca/ngày)",
    3: "Cao (3 ca/ngày)",
}

# Tạo thư mục data nếu chưa có
os.makedirs(DATA_DIR, exist_ok=True)
