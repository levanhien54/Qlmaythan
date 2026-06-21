# -*- coding: utf-8 -*-
"""
Dialog thêm/sửa phiên điều trị.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QDateTimeEdit,
    QTextEdit, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_outline
from database.queries import thiet_bi, nhan_vien


class SessionDialog(QDialog):
    """Dialog thêm/sửa phiên điều trị."""

    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.result_data = None
        self._setup_ui()
        if data:
            self._populate(data)

    def _setup_ui(self):
        c = COLORS
        self.setWindowTitle("Sửa phiên" if self.data else "Thêm phiên điều trị")
        self.setMinimumWidth(520)
        self.setStyleSheet(f"QDialog {{ background-color: {c['bg_dark']}; }}")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("✏️ Sửa phiên" if self.data else "➕ Thêm phiên điều trị")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {c['accent_red']}; background: transparent;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_ho_ten = QLineEdit()
        self.txt_ho_ten.setPlaceholderText("Họ và tên bệnh nhân")
        form.addRow("Họ và tên *:", self.txt_ho_ten)

        self.spin_tuoi = QSpinBox()
        self.spin_tuoi.setRange(0, 120)
        form.addRow("Tuổi:", self.spin_tuoi)

        self.txt_dia_chi = QLineEdit()
        form.addRow("Địa chỉ:", self.txt_dia_chi)

        self.txt_so_hs = QLineEdit()
        form.addRow("Số hồ sơ:", self.txt_so_hs)

        self.dt_bat_dau = QDateTimeEdit()
        self.dt_bat_dau.setDateTime(QDateTime.currentDateTime())
        self.dt_bat_dau.setCalendarPopup(True)
        form.addRow("Ngày bắt đầu:", self.dt_bat_dau)

        self.dt_ket_thuc = QDateTimeEdit()
        self.dt_ket_thuc.setDateTime(QDateTime.currentDateTime().addSecs(4 * 3600))
        self.dt_ket_thuc.setCalendarPopup(True)
        form.addRow("Ngày kết thúc:", self.dt_ket_thuc)

        self.cb_thiet_bi = QComboBox()
        self.cb_thiet_bi.addItem("-- Chọn máy --", None)
        for tb in thiet_bi.get_all():
            self.cb_thiet_bi.addItem(tb["ten_thiet_bi"], tb["id"])
        form.addRow("Máy thực hiện:", self.cb_thiet_bi)

        self.cb_ptv = QComboBox()
        self.cb_ptv.addItem("-- PTV chính --", None)
        for nv in nhan_vien.get_all():
            self.cb_ptv.addItem(f"{nv['ho_ten']} ({nv['chuc_vu_trinh_do']})", nv["id"])
        form.addRow("PTV chính:", self.cb_ptv)

        self.cb_phu1 = QComboBox()
        self.cb_phu1.addItem("-- Phụ 1 --", None)
        for nv in nhan_vien.get_all():
            self.cb_phu1.addItem(f"{nv['ho_ten']} ({nv['chuc_vu_trinh_do']})", nv["id"])
        form.addRow("Phụ 1:", self.cb_phu1)

        self.txt_ghi_chu = QTextEdit()
        self.txt_ghi_chu.setMaximumHeight(60)
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
        # Dùng `or default`: cột NULL trong DB trả None (key tồn tại) → setText(None)
        # / setValue(None) sẽ crash; `or` quy về giá trị mặc định an toàn.
        self.txt_ho_ten.setText(data.get("ho_ten") or "")
        self.spin_tuoi.setValue(data.get("tuoi") or 0)
        self.txt_dia_chi.setText(data.get("dia_chi") or "")
        self.txt_so_hs.setText(data.get("so_ho_so") or "")

        if data.get("ngay_bat_dau"):
            self.dt_bat_dau.setDateTime(
                QDateTime.fromString(data["ngay_bat_dau"], "yyyy-MM-dd hh:mm:ss")
            )
        if data.get("ngay_ket_thuc"):
            self.dt_ket_thuc.setDateTime(
                QDateTime.fromString(data["ngay_ket_thuc"], "yyyy-MM-dd hh:mm:ss")
            )

        idx = self.cb_thiet_bi.findData(data.get("thiet_bi_id"))
        if idx >= 0:
            self.cb_thiet_bi.setCurrentIndex(idx)
        idx = self.cb_ptv.findData(data.get("ptv_chinh_id"))
        if idx >= 0:
            self.cb_ptv.setCurrentIndex(idx)
        idx = self.cb_phu1.findData(data.get("phu_1_id"))
        if idx >= 0:
            self.cb_phu1.setCurrentIndex(idx)
        self.txt_ghi_chu.setText(data.get("ghi_chu") or "")

    def _save(self):
        if not self.txt_ho_ten.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập họ tên bệnh nhân.")
            self.txt_ho_ten.setFocus()
            return
        # Validate ngày: kết thúc phải sau bắt đầu (khớp ràng buộc của web API).
        bd = self.dt_bat_dau.dateTime()
        kt = self.dt_ket_thuc.dateTime()
        if kt <= bd:
            QMessageBox.warning(self, "Ngày không hợp lệ",
                                "Ngày kết thúc phải SAU ngày bắt đầu.")
            self.dt_ket_thuc.setFocus()
            return
        tb_id = self.cb_thiet_bi.currentData()
        # Khi KHÔNG chọn máy: GIỮ NGUYÊN may_thuc_hien gốc (vd phiên import chưa
        # map được thiết bị) thay vì ghi đè rỗng → tránh mất tên máy đã lưu.
        if tb_id:
            may_text = self.cb_thiet_bi.currentText()
        else:
            may_text = (self.data or {}).get("may_thuc_hien", "") or ""
        self.result_data = {
            "ho_ten": self.txt_ho_ten.text().strip(),
            "tuoi": self.spin_tuoi.value(),
            "dia_chi": self.txt_dia_chi.text().strip(),
            "so_ho_so": self.txt_so_hs.text().strip(),
            "ngay_bat_dau": self.dt_bat_dau.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
            "ngay_ket_thuc": self.dt_ket_thuc.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
            "thiet_bi_id": tb_id,
            "may_thuc_hien": may_text,
            "ptv_chinh_id": self.cb_ptv.currentData(),
            "phu_1_id": self.cb_phu1.currentData(),
            "ghi_chu": self.txt_ghi_chu.toPlainText().strip(),
        }
        self.accept()
