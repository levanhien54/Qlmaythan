# -*- coding: utf-8 -*-
"""
Stat card widget cho Dashboard.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.styles import COLORS


class StatCard(QFrame):
    """Card hiển thị thống kê với icon, giá trị, nhãn."""

    def __init__(self, icon: str, value: str, label: str,
                 color: str = None, parent=None):
        super().__init__(parent)
        self._color = color or COLORS["accent_blue_light"]
        self._setup_ui(icon, value, label)

    def _setup_ui(self, icon: str, value: str, label: str):
        c = COLORS
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
                border-left: 4px solid {self._color};
            }}
        """)
        self.setFixedHeight(110)
        self.setMinimumWidth(200)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 28))
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setFixedWidth(50)
        layout.addWidget(icon_label)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        value_label.setStyleSheet(f"""
            color: {self._color};
            background: transparent;
        """)
        text_layout.addWidget(value_label)
        self._value_label = value_label

        desc_label = QLabel(label)
        desc_label.setFont(QFont("Segoe UI", 11))
        desc_label.setStyleSheet(f"""
            color: {c['text_secondary']};
            background: transparent;
        """)
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)
        layout.addStretch()

    def update_value(self, value: str):
        """Cập nhật giá trị hiển thị."""
        self._value_label.setText(str(value))
