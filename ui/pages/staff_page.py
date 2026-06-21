# -*- coding: utf-8 -*-
"""
Trang Quản lý Nhân viên.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary
from ui.components.data_table import DataTable
from ui.dialogs.staff_dialog import StaffDialog
from database.queries import nhan_vien
from config import CHUC_VU


class StaffPage(QWidget):
    """Trang quản lý nhân viên."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("👥 Quản lý Nhân viên")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        layout.addWidget(title)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm theo tên...")
        self.txt_search.setMinimumWidth(250)
        self.txt_search.textChanged.connect(self._filter)
        filter_layout.addWidget(self.txt_search)

        self.cb_chuc_vu = QComboBox()
        self.cb_chuc_vu.addItem("Tất cả chức vụ")
        for cv in CHUC_VU:
            self.cb_chuc_vu.addItem(cv)
        self.cb_chuc_vu.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_chuc_vu)

        filter_layout.addStretch()

        btn_add = QPushButton("➕ Thêm nhân viên")
        btn_add.setStyleSheet(btn_primary())
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add)
        filter_layout.addWidget(btn_add)

        layout.addLayout(filter_layout)

        self.table = DataTable(["STT", "Họ và tên", "Chức vụ / Trình độ"])
        self.table.edit_clicked.connect(self._edit)
        self.table.delete_clicked.connect(self._delete)
        layout.addWidget(self.table)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        layout.addWidget(self.lbl_count)

    def refresh_data(self):
        self._filter()

    def _filter(self):
        search = self.txt_search.text().strip()
        chuc_vu = ""
        if self.cb_chuc_vu.currentIndex() > 0:
            chuc_vu = self.cb_chuc_vu.currentText()

        rows = nhan_vien.get_all(search=search, chuc_vu=chuc_vu)
        display = []
        for i, r in enumerate(rows, 1):
            display.append({
                "id": r["id"],
                "stt": i,
                "ho_ten": r["ho_ten"],
                "chuc_vu_trinh_do": r["chuc_vu_trinh_do"],
            })

        self.table.load_data(display, id_key="id",
                            display_keys=["stt", "ho_ten", "chuc_vu_trinh_do"])
        self.lbl_count.setText(f"Tổng: {len(rows)} nhân viên")

    def _add(self):
        dlg = StaffDialog(parent=self)
        if dlg.exec() and dlg.result_data:
            nhan_vien.create(**dlg.result_data)
            self.refresh_data()

    def _edit(self, nv_id: int):
        data = nhan_vien.get_by_id(nv_id)
        if not data:
            return
        dlg = StaffDialog(data=data, parent=self)
        if dlg.exec() and dlg.result_data:
            nhan_vien.update(nv_id, **dlg.result_data)
            self.refresh_data()

    def _delete(self, nv_id: int):
        reply = QMessageBox.question(
            self, "Xác nhận", "Bạn chắc chắn muốn xóa nhân viên này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                nhan_vien.delete(nv_id)
            except nhan_vien.StaffReferencedError as e:
                QMessageBox.warning(self, "Không thể xóa", str(e))
                return
            self.refresh_data()
