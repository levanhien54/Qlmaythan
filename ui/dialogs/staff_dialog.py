# -*- coding: utf-8 -*-
"""
Dialog thêm/sửa nhân viên.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_outline
from config import CHUC_VU


class StaffDialog(QDialog):
    """Dialog thêm/sửa nhân viên."""

    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.result_data = None
        self._setup_ui()
        if data:
            self._populate(data)

    def _setup_ui(self):
        c = COLORS
        self.setWindowTitle("Sửa nhân viên" if self.data else "Thêm nhân viên")
        self.setMinimumWidth(420)
        self.setStyleSheet(f"QDialog {{ background-color: {c['bg_dark']}; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("✏️ Sửa nhân viên" if self.data else "➕ Thêm nhân viên mới")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {c['accent_red']}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_ten = QLineEdit()
        self.txt_ten.setPlaceholderText("Họ và tên")
        form.addRow("Họ và tên *:", self.txt_ten)

        self.cb_chuc_vu = QComboBox()
        for cv in CHUC_VU:
            self.cb_chuc_vu.addItem(cv)
        form.addRow("Chức vụ/Trình độ:", self.cb_chuc_vu)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.setStyleSheet(btn_outline())
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Lưu")
        btn_save.setStyleSheet(btn_primary())
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _populate(self, data: dict):
        self.txt_ten.setText(data.get("ho_ten", ""))
        cv = data.get("chuc_vu_trinh_do", "")
        idx = self.cb_chuc_vu.findText(cv)
        if idx >= 0:
            self.cb_chuc_vu.setCurrentIndex(idx)

    def _save(self):
        if not self.txt_ten.text().strip():
            self.txt_ten.setFocus()
            return
        self.result_data = {
            "ho_ten": self.txt_ten.text().strip(),
            "chuc_vu_trinh_do": self.cb_chuc_vu.currentText(),
        }
        self.accept()
