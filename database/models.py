# -*- coding: utf-8 -*-
"""
Định nghĩa và tạo các bảng SQLite.
"""
from database.connection import db


def create_all_tables():
    """Tạo tất cả các bảng nếu chưa tồn tại."""

    # 1. Bảng Nhân viên
    db.execute("""
        CREATE TABLE IF NOT EXISTS nhan_vien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ho_ten TEXT NOT NULL,
            chuc_vu_trinh_do TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Bảng Thiết bị
    db.execute("""
        CREATE TABLE IF NOT EXISTS thiet_bi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_thiet_bi TEXT NOT NULL,
            model TEXT DEFAULT '',
            hang_san_xuat TEXT DEFAULT '',
            nuoc_san_xuat TEXT DEFAULT '',
            so_may TEXT DEFAULT '',
            nam_su_dung INTEGER DEFAULT 0,
            tinh_trang TEXT DEFAULT 'Hoạt động bình thường',
            tan_suat_su_dung INTEGER DEFAULT 0,
            nguoi_quan_ly_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nguoi_quan_ly_id) REFERENCES nhan_vien(id)
                ON DELETE SET NULL
        )
    """)

    # 3. Bảng Bảo dưỡng / Sửa chữa
    db.execute("""
        CREATE TABLE IF NOT EXISTS bao_duong (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thiet_bi_id INTEGER NOT NULL,
            nguoi_thuc_hien_id INTEGER,
            loai TEXT NOT NULL DEFAULT 'Bảo dưỡng định kỳ',
            ngay_thuc_hien DATE,
            ngay_du_kien_tiep_theo DATE,
            mo_ta TEXT DEFAULT '',
            chi_phi REAL DEFAULT 0,
            trang_thai TEXT DEFAULT 'Chờ xử lý',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thiet_bi_id) REFERENCES thiet_bi(id)
                ON DELETE CASCADE,
            FOREIGN KEY (nguoi_thuc_hien_id) REFERENCES nhan_vien(id)
                ON DELETE SET NULL
        )
    """)

    # 4. Bảng Phiên điều trị
    db.execute("""
        CREATE TABLE IF NOT EXISTS phien_dieu_tri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thiet_bi_id INTEGER,
            may_thuc_hien TEXT DEFAULT '',
            ho_ten TEXT NOT NULL,
            tuoi INTEGER DEFAULT 0,
            dia_chi TEXT DEFAULT '',
            so_ho_so TEXT DEFAULT '',
            ngay_bat_dau TIMESTAMP,
            ngay_ket_thuc TIMESTAMP,
            ptv_chinh_id INTEGER,
            phu_1_id INTEGER,
            ghi_chu TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thiet_bi_id) REFERENCES thiet_bi(id)
                ON DELETE SET NULL,
            FOREIGN KEY (ptv_chinh_id) REFERENCES nhan_vien(id)
                ON DELETE SET NULL,
            FOREIGN KEY (phu_1_id) REFERENCES nhan_vien(id)
                ON DELETE SET NULL
        )
    """)

    # 5. Bảng Bàn giao
    db.execute("""
        CREATE TABLE IF NOT EXISTS ban_giao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thiet_bi_id INTEGER NOT NULL,
            nguoi_giao_id INTEGER,
            nguoi_nhan_id INTEGER,
            ngay_ban_giao DATE,
            trang_thai TEXT DEFAULT 'Đã bàn giao',
            ghi_chu TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (thiet_bi_id) REFERENCES thiet_bi(id)
                ON DELETE CASCADE,
            FOREIGN KEY (nguoi_giao_id) REFERENCES nhan_vien(id)
                ON DELETE SET NULL,
            FOREIGN KEY (nguoi_nhan_id) REFERENCES nhan_vien(id)
                ON DELETE SET NULL
        )
    """)

    # Migration: add trang_thai if missing
    try:
        db.execute("ALTER TABLE ban_giao ADD COLUMN trang_thai TEXT DEFAULT 'Đã bàn giao'")
    except Exception:
        pass  # column already exists

    # UNIQUE INDEX chống race condition concurrent import.
    # Nếu DB còn duplicate cũ, CREATE UNIQUE INDEX sẽ fail — cần chạy
    # scripts/cleanup_duplicates.py --apply trước khi migration này chạy được.
    try:
        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_phien_tb_bd
            ON phien_dieu_tri(thiet_bi_id, ngay_bat_dau)
        """)
    except Exception as e:
        print(f"[DB] ⚠️  Không tạo được UNIQUE INDEX (có thể còn duplicate): {e}")
        print("[DB]    Chạy: python scripts/cleanup_duplicates.py --apply")

    print("[DB] All tables created successfully.")
