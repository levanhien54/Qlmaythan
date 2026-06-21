# -*- coding: utf-8 -*-
"""
Sidebar navigation widget.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS


class SidebarButton(QPushButton):
    """Nút navigation trong sidebar."""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self.setFont(QFont("Segoe UI", 12))
        self._update_style()

    def set_active(self, active: bool):
        self._active = active
        self._update_style()

    def _update_style(self):
        c = COLORS
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['accent_red']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 16px;
                    font-weight: bold;
                    font-size: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c['text_secondary']};
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 16px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {c['bg_hover']};
                    color: {c['text_primary']};
                }}
            """)


class Sidebar(QWidget):
    """Sidebar navigation chính."""

    page_changed = pyqtSignal(int)

    MENU_ITEMS = [
        ("📊", "Dashboard"),
        ("🖥️", "Thiết bị"),
        ("👥", "Nhân viên"),
        ("🔧", "Bảo dưỡng"),
        ("📋", "Bàn giao"),
        ("💉", "Phiên ĐT"),
        ("📈", "Thống kê"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.buttons: list[SidebarButton] = []
        self._setup_ui()
        self.set_active_page(0)

    def _setup_ui(self):
        c = COLORS
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {c['bg_dark']},
                    stop: 1 {c['bg_medium']}
                );
                border-right: 1px solid {c['border']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(4)

        # Logo / Title
        title = QLabel("⚕️ QL Máy Thận")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"""
            color: {c['accent_red']};
            background: transparent;
            padding: 8px 0 20px 8px;
        """)
        layout.addWidget(title)

        # Menu items
        for i, (icon, text) in enumerate(self.MENU_ITEMS):
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            self.buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Version
        version = QLabel("v1.0.0")
        version.setStyleSheet(f"""
            color: {c['text_muted']};
            background: transparent;
            font-size: 11px;
            padding: 8px;
        """)
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

    def _on_click(self, index: int):
        self.set_active_page(index)
        self.page_changed.emit(index)

    def set_active_page(self, index: int):
        for i, btn in enumerate(self.buttons):
            btn.set_active(i == index)
