# -*- coding: utf-8 -*-
"""
Dialog thêm/sửa phiếu bảo dưỡng.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox,
    QTextEdit, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_outline
from config import LOAI_BAO_DUONG, TRANG_THAI_BAO_DUONG
from database.queries import thiet_bi, nhan_vien


class MaintenanceDialog(QDialog):
    """Dialog thêm/sửa phiếu bảo dưỡng."""

    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.result_data = None
        self._setup_ui()
        if data:
            self._populate(data)

    def _setup_ui(self):
        c = COLORS
        self.setWindowTitle("Sửa phiếu" if self.data else "Thêm phiếu bảo dưỡng")
        self.setMinimumWidth(520)
        self.setStyleSheet(f"QDialog {{ background-color: {c['bg_dark']}; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("✏️ Sửa phiếu" if self.data else "➕ Thêm phiếu bảo dưỡng")
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

        self.cb_loai = QComboBox()
        for loai in LOAI_BAO_DUONG:
            self.cb_loai.addItem(loai)
        form.addRow("Loại:", self.cb_loai)

        self.date_thuc_hien = QDateEdit()
        self.date_thuc_hien.setDate(QDate.currentDate())
        self.date_thuc_hien.setCalendarPopup(True)
        form.addRow("Ngày thực hiện:", self.date_thuc_hien)

        self.date_tiep_theo = QDateEdit()
        self.date_tiep_theo.setDate(QDate.currentDate().addMonths(6))
        self.date_tiep_theo.setCalendarPopup(True)
        form.addRow("Dự kiến tiếp theo:", self.date_tiep_theo)

        self.cb_nguoi_th = QComboBox()
        self.cb_nguoi_th.addItem("-- Chọn --", None)
        for nv in nhan_vien.get_all():
            self.cb_nguoi_th.addItem(
                f"{nv['ho_ten']} ({nv['chuc_vu_trinh_do']})", nv["id"]
            )
        form.addRow("Người thực hiện:", self.cb_nguoi_th)

        self.txt_mo_ta = QTextEdit()
        self.txt_mo_ta.setMaximumHeight(80)
        self.txt_mo_ta.setPlaceholderText("Mô tả công việc...")
        form.addRow("Mô tả:", self.txt_mo_ta)

        self.spin_chi_phi = QDoubleSpinBox()
        self.spin_chi_phi.setRange(0, 999999999)
        self.spin_chi_phi.setSuffix(" VNĐ")
        self.spin_chi_phi.setDecimals(0)
        form.addRow("Chi phí:", self.spin_chi_phi)

        self.cb_trang_thai = QComboBox()
        for tt in TRANG_THAI_BAO_DUONG:
            self.cb_trang_thai.addItem(tt)
        form.addRow("Trạng thái:", self.cb_trang_thai)

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

        idx = self.cb_loai.findText(data.get("loai", ""))
        if idx >= 0:
            self.cb_loai.setCurrentIndex(idx)

        if data.get("ngay_thuc_hien"):
            self.date_thuc_hien.setDate(QDate.fromString(data["ngay_thuc_hien"], "yyyy-MM-dd"))
        if data.get("ngay_du_kien_tiep_theo"):
            self.date_tiep_theo.setDate(QDate.fromString(data["ngay_du_kien_tiep_theo"], "yyyy-MM-dd"))

        idx = self.cb_nguoi_th.findData(data.get("nguoi_thuc_hien_id"))
        if idx >= 0:
            self.cb_nguoi_th.setCurrentIndex(idx)

        self.txt_mo_ta.setText(data.get("mo_ta", ""))
        self.spin_chi_phi.setValue(data.get("chi_phi", 0))

        idx = self.cb_trang_thai.findText(data.get("trang_thai", ""))
        if idx >= 0:
            self.cb_trang_thai.setCurrentIndex(idx)

    def _save(self):
        if not self.cb_thiet_bi.currentData():
            return
        self.result_data = {
            "thiet_bi_id": self.cb_thiet_bi.currentData(),
            "loai": self.cb_loai.currentText(),
            "ngay_thuc_hien": self.date_thuc_hien.date().toString("yyyy-MM-dd"),
            "ngay_du_kien_tiep_theo": self.date_tiep_theo.date().toString("yyyy-MM-dd"),
            "nguoi_thuc_hien_id": self.cb_nguoi_th.currentData(),
            "mo_ta": self.txt_mo_ta.toPlainText().strip(),
            "chi_phi": self.spin_chi_phi.value(),
            "trang_thai": self.cb_trang_thai.currentText(),
        }
        self.accept()
