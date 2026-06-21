# -*- coding: utf-8 -*-
"""
Trang Bảo dưỡng & Sửa chữa.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QDateEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary
from ui.components.data_table import DataTable
from ui.dialogs.maintenance_dialog import MaintenanceDialog
from database.queries import bao_duong, thiet_bi
from config import LOAI_BAO_DUONG, TRANG_THAI_BAO_DUONG


class MaintenancePage(QWidget):
    """Trang bảo dưỡng & sửa chữa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        c = COLORS
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("🔧 Bảo dưỡng & Sửa chữa")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {c['text_primary']}; background: transparent;")
        layout.addWidget(title)

        # Alert banner
        self.alert_banner = QFrame()
        self.alert_banner.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 171, 0, 0.15);
                border: 1px solid {c['accent_yellow']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        alert_layout = QHBoxLayout(self.alert_banner)
        self.alert_label = QLabel("⚠️ Đang kiểm tra...")
        self.alert_label.setStyleSheet(f"color: {c['accent_yellow']}; background: transparent;")
        alert_layout.addWidget(self.alert_label)
        layout.addWidget(self.alert_banner)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.cb_thiet_bi = QComboBox()
        self.cb_thiet_bi.addItem("Tất cả thiết bị", None)
        self.cb_thiet_bi.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_thiet_bi)

        self.cb_loai = QComboBox()
        self.cb_loai.addItem("Tất cả loại")
        for loai in LOAI_BAO_DUONG:
            self.cb_loai.addItem(loai)
        self.cb_loai.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_loai)

        self.cb_trang_thai = QComboBox()
        self.cb_trang_thai.addItem("Tất cả trạng thái")
        for tt in TRANG_THAI_BAO_DUONG:
            self.cb_trang_thai.addItem(tt)
        self.cb_trang_thai.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_trang_thai)

        filter_layout.addStretch()

        btn_add = QPushButton("➕ Thêm phiếu")
        btn_add.setStyleSheet(btn_primary())
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add)
        filter_layout.addWidget(btn_add)

        layout.addLayout(filter_layout)

        # Table
        self.table = DataTable([
            "STT", "Thiết bị", "Loại", "Ngày TH", "Người TH",
            "Mô tả", "Chi phí", "Trạng thái"
        ])
        self.table.edit_clicked.connect(self._edit)
        self.table.delete_clicked.connect(self._delete)
        layout.addWidget(self.table)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet(f"color: {c['text_muted']}; background: transparent;")
        layout.addWidget(self.lbl_count)

    def refresh_data(self):
        # Reload device dropdown
        self.cb_thiet_bi.clear()
        self.cb_thiet_bi.addItem("Tất cả thiết bị", None)
        for tb in thiet_bi.get_all():
            self.cb_thiet_bi.addItem(tb["ten_thiet_bi"], tb["id"])

        # Alerts
        upcoming = bao_duong.get_upcoming(7)
        if upcoming:
            self.alert_label.setText(
                f"⚠️ {len(upcoming)} thiết bị cần bảo dưỡng trong 7 ngày tới"
            )
            self.alert_banner.show()
        else:
            self.alert_banner.hide()

        self._filter()

    def _filter(self):
        tb_id = self.cb_thiet_bi.currentData() if self.cb_thiet_bi.currentIndex() > 0 else None
        loai = self.cb_loai.currentText() if self.cb_loai.currentIndex() > 0 else ""
        trang_thai = self.cb_trang_thai.currentText() if self.cb_trang_thai.currentIndex() > 0 else ""

        rows = bao_duong.get_all(thiet_bi_id=tb_id, loai=loai, trang_thai=trang_thai)
        display = []
        for i, r in enumerate(rows, 1):
            chi_phi = f"{r['chi_phi']:,.0f} VNĐ" if r.get("chi_phi") else ""
            display.append({
                "id": r["id"],
                "stt": i,
                "thiet_bi": r.get("ten_thiet_bi", ""),
                "loai": r.get("loai", ""),
                "ngay_th": r.get("ngay_thuc_hien") or "",
                "nguoi_th": r.get("nguoi_thuc_hien_ten") or "",
                "mo_ta": (r.get("mo_ta") or "")[:50],
                "chi_phi": chi_phi,
                "trang_thai": r.get("trang_thai", ""),
            })

        self.table.load_data(display, id_key="id", display_keys=[
            "stt", "thiet_bi", "loai", "ngay_th", "nguoi_th",
            "mo_ta", "chi_phi", "trang_thai"
        ])

        for i, r in enumerate(display):
            self.table.set_status_badge(i, 7, r["trang_thai"])

        self.lbl_count.setText(f"Tổng: {len(rows)} phiếu")

    def _add(self):
        dlg = MaintenanceDialog(parent=self)
        if dlg.exec() and dlg.result_data:
            bao_duong.create(**dlg.result_data)
            self.refresh_data()

    def _edit(self, bd_id: int):
        data = bao_duong.get_by_id(bd_id)
        if not data:
            return
        dlg = MaintenanceDialog(data=data, parent=self)
        if dlg.exec() and dlg.result_data:
            bao_duong.update(bd_id, **dlg.result_data)
            self.refresh_data()

    def _delete(self, bd_id: int):
        reply = QMessageBox.question(
            self, "Xác nhận", "Bạn chắc chắn muốn xóa phiếu này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            bao_duong.delete(bd_id)
            self.refresh_data()
