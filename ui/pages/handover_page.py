# -*- coding: utf-8 -*-
"""
Trang Bàn giao Thiết bị.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary
from ui.components.data_table import DataTable
from ui.dialogs.handover_dialog import HandoverDialog
from database.queries import ban_giao, thiet_bi, nhan_vien


class HandoverPage(QWidget):
    """Trang bàn giao thiết bị."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("📋 Bàn giao Thiết bị")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        layout.addWidget(title)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.cb_thiet_bi = QComboBox()
        self.cb_thiet_bi.addItem("Tất cả thiết bị", None)
        self.cb_thiet_bi.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_thiet_bi)

        self.cb_nhan_vien = QComboBox()
        self.cb_nhan_vien.addItem("Tất cả nhân viên", None)
        self.cb_nhan_vien.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_nhan_vien)

        filter_layout.addStretch()

        btn_add = QPushButton("➕ Thêm bàn giao")
        btn_add.setStyleSheet(btn_primary())
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add)
        filter_layout.addWidget(btn_add)

        layout.addLayout(filter_layout)

        self.table = DataTable([
            "STT", "Thiết bị", "Người giao", "Người nhận",
            "Ngày bàn giao", "Ghi chú"
        ])
        self.table.edit_clicked.connect(self._edit)
        self.table.delete_clicked.connect(self._delete)
        layout.addWidget(self.table)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        layout.addWidget(self.lbl_count)

    def refresh_data(self):
        self.cb_thiet_bi.clear()
        self.cb_thiet_bi.addItem("Tất cả thiết bị", None)
        for tb in thiet_bi.get_all():
            self.cb_thiet_bi.addItem(tb["ten_thiet_bi"], tb["id"])

        self.cb_nhan_vien.clear()
        self.cb_nhan_vien.addItem("Tất cả nhân viên", None)
        for nv in nhan_vien.get_all():
            self.cb_nhan_vien.addItem(nv["ho_ten"], nv["id"])

        self._filter()

    def _filter(self):
        tb_id = self.cb_thiet_bi.currentData() if self.cb_thiet_bi.currentIndex() > 0 else None
        nv_id = self.cb_nhan_vien.currentData() if self.cb_nhan_vien.currentIndex() > 0 else None

        rows = ban_giao.get_all(thiet_bi_id=tb_id, nhan_vien_id=nv_id)
        display = []
        for i, r in enumerate(rows, 1):
            display.append({
                "id": r["id"],
                "stt": i,
                "thiet_bi": r.get("ten_thiet_bi", ""),
                "nguoi_giao": r.get("nguoi_giao_ten", ""),
                "nguoi_nhan": r.get("nguoi_nhan_ten", ""),
                "ngay": r.get("ngay_ban_giao", ""),
                "ghi_chu": r.get("ghi_chu", "")[:50],
            })

        self.table.load_data(display, id_key="id", display_keys=[
            "stt", "thiet_bi", "nguoi_giao", "nguoi_nhan", "ngay", "ghi_chu"
        ])
        self.lbl_count.setText(f"Tổng: {len(rows)} phiếu bàn giao")

    def _add(self):
        dlg = HandoverDialog(parent=self)
        if dlg.exec() and dlg.result_data:
            ban_giao.create(**dlg.result_data)
            self.refresh_data()

    def _edit(self, bg_id: int):
        data = ban_giao.get_by_id(bg_id)
        if not data:
            return
        dlg = HandoverDialog(data=data, parent=self)
        if dlg.exec() and dlg.result_data:
            ban_giao.update(bg_id, **dlg.result_data)
            self.refresh_data()

    def _delete(self, bg_id: int):
        reply = QMessageBox.question(
            self, "Xác nhận", "Bạn chắc chắn muốn xóa phiếu bàn giao này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ban_giao.delete(bg_id)
            self.refresh_data()
