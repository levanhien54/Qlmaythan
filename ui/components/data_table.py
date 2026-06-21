# -*- coding: utf-8 -*-
"""
Reusable data table widget.
"""
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from ui.styles import COLORS, btn_outline


class DataTable(QTableWidget):
    """Bảng dữ liệu tái sử dụng với các nút hành động."""

    edit_clicked = pyqtSignal(int)   # row_id
    delete_clicked = pyqtSignal(int)  # row_id

    def __init__(self, columns: list[str], show_actions: bool = True,
                 parent=None):
        super().__init__(parent)
        self._columns = columns
        self._show_actions = show_actions
        self._row_ids = []
        self._setup_ui()

    def _setup_ui(self):
        c = COLORS

        all_cols = list(self._columns)
        if self._show_actions:
            all_cols.append("Thao tác")

        self.setColumnCount(len(all_cols))
        self.setHorizontalHeaderLabels(all_cols)

        # Cấu hình
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        # Header
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        for i in range(len(all_cols) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        if self._show_actions:
            header.setSectionResizeMode(
                len(all_cols) - 1, QHeaderView.ResizeMode.Fixed
            )
            self.setColumnWidth(len(all_cols) - 1, 140)

    def load_data(self, rows: list[dict], id_key: str = "id",
                  display_keys: list[str] = None):
        """Nạp dữ liệu vào bảng.

        Args:
            rows: Danh sách dict dữ liệu.
            id_key: Key cho ID dòng.
            display_keys: Các key cần hiển thị. Nếu None, dùng thứ tự columns.
        """
        self.setRowCount(0)
        self._row_ids = []

        for row_data in rows:
            row_idx = self.rowCount()
            self.insertRow(row_idx)

            row_id = row_data.get(id_key, row_idx)
            self._row_ids.append(row_id)

            # Điền dữ liệu
            if display_keys:
                for col, key in enumerate(display_keys):
                    value = row_data.get(key, "")
                    # None/'' → ô trống; nhưng số 0 (tuổi, năm, tần suất) phải hiện "0".
                    item = QTableWidgetItem("" if value is None or value == "" else str(value))
                    self.setItem(row_idx, col, item)
            else:
                keys = [k for k in row_data if k != id_key]
                for col, key in enumerate(keys[:len(self._columns)]):
                    value = row_data.get(key, "")
                    item = QTableWidgetItem("" if value is None or value == "" else str(value))
                    self.setItem(row_idx, col, item)

            # Nút hành động
            if self._show_actions:
                self._add_action_buttons(row_idx, row_id)

        self.resizeColumnsToContents()
        if self._show_actions:
            self.setColumnWidth(self.columnCount() - 1, 140)

    def _add_action_buttons(self, row_idx: int, row_id: int):
        """Thêm nút Sửa/Xóa vào dòng."""
        c = COLORS
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(32, 28)
        btn_edit.setToolTip("Sửa")
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['accent_blue']};
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {c['accent_blue_light']};
            }}
        """)
        btn_edit.clicked.connect(lambda: self.edit_clicked.emit(row_id))
        layout.addWidget(btn_edit)

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(32, 28)
        btn_del.setToolTip("Xóa")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['status_error']};
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #ff4569;
            }}
        """)
        btn_del.clicked.connect(lambda: self.delete_clicked.emit(row_id))
        layout.addWidget(btn_del)

        layout.addStretch()
        self.setCellWidget(row_idx, self.columnCount() - 1, widget)

    def set_status_badge(self, row: int, col: int, text: str):
        """Thay thế cell bằng badge màu theo trạng thái."""
        c = COLORS
        text_lower = text.lower() if text else ""

        if "bình thường" in text_lower or "hoạt động" in text_lower:
            bg = c["status_ok"]
            fg = "#000"
        elif "hỏng" in text_lower:
            bg = c["status_error"]
            fg = "#fff"
        elif "lỗi" in text_lower or "nghỉ" in text_lower:
            bg = c["status_warning"]
            fg = "#000"
        elif "hoàn thành" in text_lower:
            bg = c["status_ok"]
            fg = "#000"
        elif "đang" in text_lower:
            bg = c["accent_yellow"]
            fg = "#000"
        elif "chờ" in text_lower:
            bg = c["accent_orange"]
            fg = "#000"
        else:
            bg = c["accent_blue"]
            fg = "#fff"

        label_widget = QWidget()
        layout = QHBoxLayout(label_widget)
        layout.setContentsMargins(4, 2, 4, 2)

        from PyQt6.QtWidgets import QLabel
        badge = QLabel(text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(badge)
        self.setCellWidget(row, col, label_widget)
