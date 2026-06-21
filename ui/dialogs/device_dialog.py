# -*- coding: utf-8 -*-
"""
Dialog thêm/sửa thiết bị.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_outline
from config import TINH_TRANG, TAN_SUAT
from database.queries import nhan_vien


class DeviceDialog(QDialog):
    """Dialog thêm/sửa thiết bị."""

    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.result_data = None
        self._setup_ui()
        if data:
            self._populate(data)

    def _setup_ui(self):
        c = COLORS
        self.setWindowTitle("Sửa thiết bị" if self.data else "Thêm thiết bị")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg_dark']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("✏️ Sửa thiết bị" if self.data else "➕ Thêm thiết bị mới")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {c['accent_red']}; background: transparent;")
        layout.addWidget(title)

        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_ten = QLineEdit()
        self.txt_ten.setPlaceholderText("VD: Máy chạy thận Fresinius số 1")
        form.addRow("Tên thiết bị *:", self.txt_ten)

        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("VD: 4008S")
        form.addRow("Model:", self.txt_model)

        self.txt_hang = QLineEdit()
        self.txt_hang.setPlaceholderText("VD: Đức")
        form.addRow("Hãng/Nước SX:", self.txt_hang)

        self.txt_so_may = QLineEdit()
        self.txt_so_may.setPlaceholderText("Serial number")
        form.addRow("Số máy:", self.txt_so_may)

        self.spin_nam = QSpinBox()
        # min=0 để giữ giá trị "chưa rõ" (nam_su_dung=0); range cũ 2000-2030 sẽ
        # KẸP 0 → 2000, làm hỏng dữ liệu năm chỉ khi mở rồi lưu lại.
        self.spin_nam.setRange(0, 2030)
        self.spin_nam.setSpecialValueText("(chưa rõ)")  # hiển thị khi value == 0
        self.spin_nam.setValue(2025)
        form.addRow("Năm đưa vào SĐ:", self.spin_nam)

        self.cb_tinh_trang = QComboBox()
        for val in TINH_TRANG.values():
            self.cb_tinh_trang.addItem(val)
        form.addRow("Tình trạng:", self.cb_tinh_trang)

        self.cb_tan_suat = QComboBox()
        for k, v in TAN_SUAT.items():
            self.cb_tan_suat.addItem(v, k)
        form.addRow("Tần suất SĐ:", self.cb_tan_suat)

        self.cb_nguoi_ql = QComboBox()
        self.cb_nguoi_ql.addItem("-- Chọn --", None)
        for nv in nhan_vien.get_all():
            self.cb_nguoi_ql.addItem(
                f"{nv['ho_ten']} ({nv['chuc_vu_trinh_do']})", nv["id"]
            )
        form.addRow("Người quản lý:", self.cb_nguoi_ql)

        layout.addLayout(form)

        # Buttons
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
        """Điền dữ liệu khi sửa."""
        # `or ""`: cột NULL trả None → setText(None) crash.
        self.txt_ten.setText(data.get("ten_thiet_bi") or "")
        self.txt_model.setText(data.get("model") or "")
        self.txt_hang.setText(data.get("hang_san_xuat") or "")
        self.txt_so_may.setText(data.get("so_may") or "")
        # 0 → "(chưa rõ)" nhờ specialValueText; không còn bị kẹp lên 2000.
        self.spin_nam.setValue(data.get("nam_su_dung") or 0)

        tinh_trang = data.get("tinh_trang", "")
        idx = self.cb_tinh_trang.findText(tinh_trang)
        if idx >= 0:
            self.cb_tinh_trang.setCurrentIndex(idx)

        tan_suat = data.get("tan_suat_su_dung", 0)
        idx = self.cb_tan_suat.findData(tan_suat)
        if idx >= 0:
            self.cb_tan_suat.setCurrentIndex(idx)

        nql_id = data.get("nguoi_quan_ly_id")
        if nql_id:
            idx = self.cb_nguoi_ql.findData(nql_id)
            if idx >= 0:
                self.cb_nguoi_ql.setCurrentIndex(idx)

    def _save(self):
        if not self.txt_ten.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên thiết bị.")
            self.txt_ten.setFocus()
            return

        self.result_data = {
            "ten_thiet_bi": self.txt_ten.text().strip(),
            "model": self.txt_model.text().strip(),
            "hang_san_xuat": self.txt_hang.text().strip(),
            "nuoc_san_xuat": self.txt_hang.text().strip(),
            "so_may": self.txt_so_may.text().strip(),
            "nam_su_dung": self.spin_nam.value(),
            "tinh_trang": self.cb_tinh_trang.currentText(),
            "tan_suat_su_dung": self.cb_tan_suat.currentData(),
            "nguoi_quan_ly_id": self.cb_nguoi_ql.currentData(),
        }
        self.accept()
