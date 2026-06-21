# -*- coding: utf-8 -*-
"""
Trang Cài đặt — thông tin ứng dụng + Sao lưu / Khôi phục dữ liệu.
"""
import os
import sys
import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.styles import COLORS, btn_primary, btn_outline
from config import APP_NAME, APP_VERSION, DB_PATH, BACKUP_DIR
from database import backup
from database.queries import thiet_bi, nhan_vien, phien_dieu_tri, bao_duong, ban_giao


class SettingsPage(QWidget):
    """Cài đặt: thông tin + sao lưu/khôi phục."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _card(self) -> QFrame:
        c = COLORS
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background-color: {c['bg_card']}; border: 1px solid {c['border']};"
            f" border-radius: 12px; }}"
        )
        return f

    def _setup_ui(self):
        c = COLORS
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("⚙️ Cài đặt")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {c['text_primary']}; background: transparent;")
        layout.addWidget(title)

        # ── Thông tin ứng dụng ──
        info_card = self._card()
        il = QVBoxLayout(info_card)
        il.setContentsMargins(20, 16, 20, 16)
        h1 = QLabel("📋 Thông tin")
        h1.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        h1.setStyleSheet(f"color: {c['accent_blue_light']}; background: transparent;")
        il.addWidget(h1)
        self.info_label = QLabel()
        self.info_label.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        il.addWidget(self.info_label)
        layout.addWidget(info_card)

        # ── Sao lưu / Khôi phục ──
        bk_card = self._card()
        bl = QVBoxLayout(bk_card)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(10)
        h2 = QLabel("💾 Sao lưu & Khôi phục dữ liệu")
        h2.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        h2.setStyleSheet(f"color: {c['accent_blue_light']}; background: transparent;")
        bl.addWidget(h2)

        hint = QLabel("App tự sao lưu mỗi lần khởi động. Bạn có thể sao lưu thủ công "
                      "hoặc khôi phục từ một bản sao lưu bên dưới.")
        hint.setStyleSheet(f"color: {c['text_muted']}; background: transparent;")
        hint.setWordWrap(True)
        bl.addWidget(hint)

        btn_row = QHBoxLayout()
        self.btn_backup = QPushButton("💾 Sao lưu ngay")
        self.btn_backup.setStyleSheet(btn_primary())
        self.btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_backup.clicked.connect(self._backup_now)
        btn_row.addWidget(self.btn_backup)

        self.btn_open = QPushButton("📂 Mở thư mục sao lưu")
        self.btn_open.setStyleSheet(btn_outline())
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_folder)
        btn_row.addWidget(self.btn_open)
        btn_row.addStretch()
        bl.addLayout(btn_row)

        self.list = QListWidget()
        self.list.setStyleSheet(
            f"QListWidget {{ background-color: {c['bg_dark']}; color: {c['text_secondary']};"
            f" border: 1px solid {c['border']}; border-radius: 8px; }}"
            f" QListWidget::item:selected {{ background-color: {c['accent_blue']}; color: white; }}"
        )
        bl.addWidget(self.list)

        self.btn_restore = QPushButton("↩️ Khôi phục bản đã chọn")
        self.btn_restore.setStyleSheet(btn_outline())
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.clicked.connect(self._restore)
        bl.addWidget(self.btn_restore)

        layout.addWidget(bk_card)
        layout.addStretch()

    # ---------- data ----------
    def refresh_data(self):
        self.info_label.setText(
            f"{APP_NAME} — phiên bản {APP_VERSION}\n"
            f"CSDL: {DB_PATH}\n"
            f"Thiết bị: {thiet_bi.count()}   |   Nhân viên: {nhan_vien.count()}   |   "
            f"Phiên điều trị: {phien_dieu_tri.count()}   |   Bàn giao: {ban_giao.count()}   |   "
            f"Bảo dưỡng: {bao_duong.count()}"
        )
        self._load_backups()

    def _load_backups(self):
        self.list.clear()
        for b in backup.list_backups():
            dt = datetime.datetime.fromtimestamp(b['mtime']).strftime('%Y-%m-%d %H:%M:%S')
            item = QListWidgetItem(f"{b['name']}    —    {b['size'] // 1024} KB    —    {dt}")
            item.setData(Qt.ItemDataRole.UserRole, b['path'])
            self.list.addItem(item)
        if self.list.count() == 0:
            self.list.addItem(QListWidgetItem("(chưa có bản sao lưu nào)"))

    # ---------- actions ----------
    def _backup_now(self):
        try:
            dest = backup.backup_database()
            if dest:
                QMessageBox.information(self, "Sao lưu", f"Đã sao lưu:\n{dest}")
            else:
                QMessageBox.warning(self, "Sao lưu", "Chưa có CSDL để sao lưu.")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Sao lưu thất bại: {e}")
        self._load_backups()

    def _open_folder(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(BACKUP_DIR)  # noqa
        else:
            QMessageBox.information(self, "Thư mục sao lưu", BACKUP_DIR)

    def _restore(self):
        item = self.list.currentItem()
        path = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not path:
            QMessageBox.warning(self, "Khôi phục", "Hãy chọn một bản sao lưu trong danh sách.")
            return
        reply = QMessageBox.question(
            self, "Xác nhận khôi phục",
            "Khôi phục sẽ GHI ĐÈ dữ liệu hiện tại bằng bản sao lưu đã chọn.\n"
            "(Hiện trạng được sao lưu lại trước để an toàn.)\n\nTiếp tục?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            backup.restore_backup(path)
            QMessageBox.information(
                self, "Khôi phục",
                "Đã khôi phục dữ liệu. Vui lòng ĐÓNG và MỞ LẠI ứng dụng để nạp đầy đủ."
            )
            self.refresh_data()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Khôi phục thất bại: {e}")
