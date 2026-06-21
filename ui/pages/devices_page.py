# -*- coding: utf-8 -*-
"""
Trang Quản lý Thiết bị.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_outline
from ui.components.data_table import DataTable
from ui.dialogs.device_dialog import DeviceDialog
from database.queries import thiet_bi
from config import TAN_SUAT, TINH_TRANG


class DevicesPage(QWidget):
    """Trang quản lý thiết bị."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("🖥️ Quản lý Thiết bị")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        layout.addWidget(title)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm kiếm tên, số máy...")
        self.txt_search.setMinimumWidth(250)
        self.txt_search.textChanged.connect(self._filter)
        filter_layout.addWidget(self.txt_search)

        self.cb_tinh_trang = QComboBox()
        self.cb_tinh_trang.addItem("Tất cả tình trạng")
        for _label in TINH_TRANG.values():
            self.cb_tinh_trang.addItem(_label)
        self.cb_tinh_trang.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_tinh_trang)

        self.cb_model = QComboBox()
        self.cb_model.addItem("Tất cả Model")
        self.cb_model.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_model)

        filter_layout.addStretch()

        btn_add = QPushButton("➕ Thêm thiết bị")
        btn_add.setStyleSheet(btn_primary())
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add)
        filter_layout.addWidget(btn_add)

        layout.addLayout(filter_layout)

        # Table
        self.table = DataTable([
            "STT", "Tên thiết bị", "Model", "Hãng SX",
            "Số máy", "Năm SĐ", "Người QL", "Tình trạng", "Tần suất"
        ])
        self.table.edit_clicked.connect(self._edit)
        self.table.delete_clicked.connect(self._delete)
        layout.addWidget(self.table)

        # Count
        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        layout.addWidget(self.lbl_count)

    def refresh_data(self):
        """Tải lại dữ liệu."""
        models = thiet_bi.get_models()
        self.cb_model.clear()
        self.cb_model.addItem("Tất cả Model")
        for m in models:
            self.cb_model.addItem(m)
        self._filter()

    def _filter(self):
        search = self.txt_search.text().strip()
        tinh_trang = ""
        if self.cb_tinh_trang.currentIndex() > 0:
            tinh_trang = self.cb_tinh_trang.currentText()
        model = ""
        if self.cb_model.currentIndex() > 0:
            model = self.cb_model.currentText()

        rows = thiet_bi.get_all(search=search, tinh_trang=tinh_trang, model=model)
        display = []
        for i, r in enumerate(rows, 1):
            display.append({
                "id": r["id"],
                "stt": i,
                "ten_thiet_bi": r["ten_thiet_bi"],
                "model": r["model"],
                "hang_san_xuat": r["hang_san_xuat"],
                "so_may": r["so_may"],
                "nam_su_dung": r["nam_su_dung"],
                "nguoi_ql": r.get("nguoi_quan_ly_ten", ""),
                "tinh_trang": r["tinh_trang"],
                "tan_suat": TAN_SUAT.get(r["tan_suat_su_dung"], str(r["tan_suat_su_dung"])),
            })

        self.table.load_data(display, id_key="id", display_keys=[
            "stt", "ten_thiet_bi", "model", "hang_san_xuat",
            "so_may", "nam_su_dung", "nguoi_ql", "tinh_trang", "tan_suat"
        ])

        # Status badges
        for i, r in enumerate(display):
            self.table.set_status_badge(i, 7, r["tinh_trang"])

        self.lbl_count.setText(f"Tổng: {len(rows)} thiết bị")

    def _add(self):
        dlg = DeviceDialog(parent=self)
        if dlg.exec() and dlg.result_data:
            thiet_bi.create(**dlg.result_data)
            self.refresh_data()

    def _edit(self, tb_id: int):
        data = thiet_bi.get_by_id(tb_id)
        if not data:
            return
        dlg = DeviceDialog(data=data, parent=self)
        if dlg.exec() and dlg.result_data:
            thiet_bi.update(tb_id, **dlg.result_data)
            self.refresh_data()

    def _delete(self, tb_id: int):
        reply = QMessageBox.question(
            self, "Xác nhận", "Bạn chắc chắn muốn xóa thiết bị này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                thiet_bi.delete(tb_id)
            except thiet_bi.DeviceHasHistoryError as e:
                QMessageBox.warning(self, "Không thể xóa", str(e))
                return
            self.refresh_data()
