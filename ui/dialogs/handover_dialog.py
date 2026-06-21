# -*- coding: utf-8 -*-
"""
Dialog thêm/sửa phiếu bàn giao.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QDateEdit, QTextEdit, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_outline
from database.queries import thiet_bi, nhan_vien


class HandoverDialog(QDialog):
    """Dialog thêm/sửa phiếu bàn giao."""

    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.result_data = None
        self._setup_ui()
        if data:
            self._populate(data)

    def _setup_ui(self):
        c = COLORS
        self.setWindowTitle("Sửa bàn giao" if self.data else "Thêm bàn giao")
        self.setMinimumWidth(480)
        self.setStyleSheet(f"QDialog {{ background-color: {c['bg_dark']}; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("✏️ Sửa bàn giao" if self.data else "➕ Thêm bàn giao mới")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {c['accent_red']}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.cb_thiet_bi = QComboBox()
        self.cb_thiet_bi.addItem("-- Chọn thiết bị --", None)
        for tb in thiet_bi.get_all():
            self.cb_thiet_bi.addItem(tb["ten_thiet_bi"], tb["id"])
        form.addRow("Thiết bị *:", self.cb_thiet_bi)

        self.cb_nguoi_giao = QComboBox()
        self.cb_nguoi_giao.addItem("-- Người giao --", None)
        for nv in nhan_vien.get_all():
            self.cb_nguoi_giao.addItem(
                f"{nv['ho_ten']} ({nv['chuc_vu_trinh_do']})", nv["id"]
            )
        form.addRow("Người giao:", self.cb_nguoi_giao)

        self.cb_nguoi_nhan = QComboBox()
        self.cb_nguoi_nhan.addItem("-- Người nhận --", None)
        for nv in nhan_vien.get_all():
            self.cb_nguoi_nhan.addItem(
                f"{nv['ho_ten']} ({nv['chuc_vu_trinh_do']})", nv["id"]
            )
        form.addRow("Người nhận:", self.cb_nguoi_nhan)

        self.date_bg = QDateEdit()
        self.date_bg.setDate(QDate.currentDate())
        self.date_bg.setCalendarPopup(True)
        form.addRow("Ngày bàn giao:", self.date_bg)

        self.txt_ghi_chu = QTextEdit()
        self.txt_ghi_chu.setMaximumHeight(80)
        self.txt_ghi_chu.setPlaceholderText("Ghi chú...")
        form.addRow("Ghi chú:", self.txt_ghi_chu)

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
        idx = self.cb_thiet_bi.findData(data.get("thiet_bi_id"))
        if idx >= 0:
            self.cb_thiet_bi.setCurrentIndex(idx)
        idx = self.cb_nguoi_giao.findData(data.get("nguoi_giao_id"))
        if idx >= 0:
            self.cb_nguoi_giao.setCurrentIndex(idx)
        idx = self.cb_nguoi_nhan.findData(data.get("nguoi_nhan_id"))
        if idx >= 0:
            self.cb_nguoi_nhan.setCurrentIndex(idx)
        if data.get("ngay_ban_giao"):
            self.date_bg.setDate(QDate.fromString(data["ngay_ban_giao"], "yyyy-MM-dd"))
        self.txt_ghi_chu.setText(data.get("ghi_chu") or "")

    def _save(self):
        if not self.cb_thiet_bi.currentData():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn thiết bị bàn giao.")
            self.cb_thiet_bi.setFocus()
            return
        self.result_data = {
            "thiet_bi_id": self.cb_thiet_bi.currentData(),
            "nguoi_giao_id": self.cb_nguoi_giao.currentData(),
            "nguoi_nhan_id": self.cb_nguoi_nhan.currentData(),
            "ngay_ban_giao": self.date_bg.date().toString("yyyy-MM-dd"),
            "ghi_chu": self.txt_ghi_chu.toPlainText().strip(),
        }
        self.accept()
