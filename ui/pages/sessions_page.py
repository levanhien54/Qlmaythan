# -*- coding: utf-8 -*-
"""
Trang Phiên điều trị.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS, btn_primary, btn_success
from ui.components.data_table import DataTable
from ui.dialogs.session_dialog import SessionDialog
from database.queries import phien_dieu_tri, thiet_bi, nhan_vien


class SessionsPage(QWidget):
    """Trang phiên điều trị."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("💉 Phiên Điều trị")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        layout.addWidget(title)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm tên BN, số hồ sơ...")
        self.txt_search.setMinimumWidth(220)
        self.txt_search.textChanged.connect(self._filter)
        filter_layout.addWidget(self.txt_search)

        self.cb_thiet_bi = QComboBox()
        self.cb_thiet_bi.addItem("Tất cả máy", None)
        self.cb_thiet_bi.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_thiet_bi)

        self.cb_ptv = QComboBox()
        self.cb_ptv.addItem("Tất cả PTV", None)
        self.cb_ptv.currentIndexChanged.connect(self._filter)
        filter_layout.addWidget(self.cb_ptv)

        filter_layout.addStretch()

        btn_import = QPushButton("📥 Import Excel")
        btn_import.setStyleSheet(btn_success())
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self._import_excel)
        filter_layout.addWidget(btn_import)

        btn_add = QPushButton("➕ Thêm phiên")
        btn_add.setStyleSheet(btn_primary())
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add)
        filter_layout.addWidget(btn_add)

        layout.addLayout(filter_layout)

        self.table = DataTable([
            "STT", "Họ tên", "Tuổi", "Địa chỉ", "Số HS",
            "Ngày BĐ", "Ngày KT", "PTV chính", "Phụ 1",
            "Máy thực hiện", "Ghi chú"
        ])
        self.table.edit_clicked.connect(self._edit)
        self.table.delete_clicked.connect(self._delete)
        layout.addWidget(self.table)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        layout.addWidget(self.lbl_count)

    def refresh_data(self):
        self.cb_thiet_bi.clear()
        self.cb_thiet_bi.addItem("Tất cả máy", None)
        for tb in thiet_bi.get_all():
            self.cb_thiet_bi.addItem(tb["ten_thiet_bi"], tb["id"])

        self.cb_ptv.clear()
        self.cb_ptv.addItem("Tất cả PTV", None)
        for nv in nhan_vien.get_all():
            self.cb_ptv.addItem(nv["ho_ten"], nv["id"])

        self._filter()

    def _filter(self):
        search = self.txt_search.text().strip()
        tb_id = self.cb_thiet_bi.currentData() if self.cb_thiet_bi.currentIndex() > 0 else None
        ptv_id = self.cb_ptv.currentData() if self.cb_ptv.currentIndex() > 0 else None

        rows = phien_dieu_tri.get_all(
            search=search, thiet_bi_id=tb_id, ptv_chinh_id=ptv_id
        )
        display = []
        for i, r in enumerate(rows, 1):
            ngay_bd = str(r.get("ngay_bat_dau", ""))[:16] if r.get("ngay_bat_dau") else ""
            ngay_kt = str(r.get("ngay_ket_thuc", ""))[:16] if r.get("ngay_ket_thuc") else ""
            display.append({
                "id": r["id"],
                "stt": i,
                "ho_ten": r.get("ho_ten") or "",
                "tuoi": r.get("tuoi") if r.get("tuoi") is not None else "",
                "dia_chi": (r.get("dia_chi") or "")[:30],
                "so_hs": r.get("so_ho_so") or "",
                "ngay_bd": ngay_bd,
                "ngay_kt": ngay_kt,
                "ptv": r.get("ptv_chinh_ten") or "",
                "phu1": r.get("phu_1_ten") or "",
                "may": r.get("may_thuc_hien") or "",
                "ghi_chu": (r.get("ghi_chu") or "")[:30],
            })

        self.table.load_data(display, id_key="id", display_keys=[
            "stt", "ho_ten", "tuoi", "dia_chi", "so_hs",
            "ngay_bd", "ngay_kt", "ptv", "phu1", "may", "ghi_chu"
        ])
        self.lbl_count.setText(f"Tổng: {len(rows)} phiên")

    def _conflict_msg(self, d: dict, exclude_id: int = None) -> str:
        """Trả về thông báo nếu phiên trùng khung giờ trên cùng máy, None nếu OK.
        Khớp logic chặn trùng của web API (trước đây desktop bỏ sót)."""
        tb_id = d.get("thiet_bi_id")
        bd = d.get("ngay_bat_dau")
        if not (tb_id and bd):
            return None
        c = phien_dieu_tri.check_time_overlap(
            tb_id, bd, d.get("ngay_ket_thuc"), exclude_id=exclude_id
        )
        if c:
            return (f"Máy đang có phiên của \"{c['ho_ten']}\" từ "
                    f"{c['ngay_bat_dau']} đến {c['ngay_ket_thuc'] or '(chưa kết thúc)'}.\n"
                    f"Không thể lưu phiên trùng thời gian trên cùng 1 máy.")
        return None

    def _add(self):
        dlg = SessionDialog(parent=self)
        if dlg.exec() and dlg.result_data:
            conflict = self._conflict_msg(dlg.result_data)
            if conflict:
                QMessageBox.warning(self, "Trùng khung giờ", conflict)
                return
            try:
                phien_dieu_tri.create(**dlg.result_data)
            except phien_dieu_tri.DuplicateSessionError as e:
                QMessageBox.warning(self, "Trùng phiên", str(e))
                return
            self.refresh_data()

    def _edit(self, pdt_id: int):
        data = phien_dieu_tri.get_by_id(pdt_id)
        if not data:
            return
        dlg = SessionDialog(data=data, parent=self)
        if dlg.exec() and dlg.result_data:
            conflict = self._conflict_msg(dlg.result_data, exclude_id=pdt_id)
            if conflict:
                QMessageBox.warning(self, "Trùng khung giờ", conflict)
                return
            try:
                phien_dieu_tri.update(pdt_id, **dlg.result_data)
            except phien_dieu_tri.DuplicateSessionError as e:
                QMessageBox.warning(self, "Trùng phiên", str(e))
                return
            self.refresh_data()

    def _delete(self, pdt_id: int):
        reply = QMessageBox.question(
            self, "Xác nhận", "Bạn chắc chắn muốn xóa phiên này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            phien_dieu_tri.delete(pdt_id)
            self.refresh_data()

    def _import_excel(self):
        """Import phiên điều trị từ file Excel người dùng chọn.

        Dùng chung logic validation/matching với web API (excel_import.py) —
        nhập đúng FILE ĐƯỢC CHỌN (không phải file cứng trong config) và báo
        cáo kết quả thật (thành công / bị từ chối / chi tiết lỗi).
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file Excel", "",
            "Excel Files (*.xls *.xlsx)"
        )
        if not file_path:
            return
        try:
            from excel_import import import_from_path, ExcelParseError
            try:
                results = import_from_path(file_path)
            except ExcelParseError as e:
                QMessageBox.warning(self, "Lỗi", str(e))
                return

            self.refresh_data()

            # Tóm tắt kết quả
            lines = [
                f"✅ Thành công: {results['success']}/{results['total']} phiên",
            ]
            if results['skipped']:
                lines.append(f"❌ Bị từ chối: {results['skipped']} phiên")
            for e in results['errors'][:20]:
                errs = "; ".join(e.get('errors', []))
                lines.append(f"  • Dòng {e['row']} ({e['name']}): {errs}")
            if len(results['errors']) > 20:
                lines.append(f"  ... và {len(results['errors']) - 20} lỗi khác")

            msg = "\n".join(lines)
            if results['success'] and not results['skipped']:
                QMessageBox.information(self, "Hoàn tất", msg)
            else:
                QMessageBox.warning(self, "Hoàn tất (có lỗi)", msg)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Lỗi import: {e}")
