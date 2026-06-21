# -*- coding: utf-8 -*-
"""
Cửa sổ chính của ứng dụng.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QStatusBar, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from config import APP_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from ui.styles import COLORS, get_main_stylesheet
from ui.components.sidebar import Sidebar
from ui.pages.dashboard_page import DashboardPage
from ui.pages.devices_page import DevicesPage
from ui.pages.staff_page import StaffPage
from ui.pages.maintenance_page import MaintenancePage
from ui.pages.handover_page import HandoverPage
from ui.pages.sessions_page import SessionsPage
from ui.pages.statistics_page import StatisticsPage


class MainWindow(QMainWindow):
    """Cửa sổ chính với sidebar + stacked pages."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.showMaximized()

        # Apply stylesheet
        self.setStyleSheet(get_main_stylesheet())

        self._setup_ui()
        self._setup_status_bar()

        # Load initial data
        self._on_page_changed(0)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.sidebar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")

        self.page_dashboard = DashboardPage()
        self.page_devices = DevicesPage()
        self.page_staff = StaffPage()
        self.page_maintenance = MaintenancePage()
        self.page_handover = HandoverPage()
        self.page_sessions = SessionsPage()
        self.page_statistics = StatisticsPage()

        self.pages = [
            self.page_dashboard,
            self.page_devices,
            self.page_staff,
            self.page_maintenance,
            self.page_handover,
            self.page_sessions,
            self.page_statistics,
        ]

        for page in self.pages:
            self.stack.addWidget(page)

        layout.addWidget(self.stack)

    def _setup_status_bar(self):
        c = COLORS
        status_bar = QStatusBar()
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {c['bg_dark']};
                color: {c['text_muted']};
                border-top: 1px solid {c['border']};
                padding: 4px 12px;
                font-size: 11px;
            }}
        """)

        from config import DB_PATH
        self.status_db = QLabel(f"📁 DB: {DB_PATH}")
        self.status_db.setStyleSheet(f"color: {c['text_muted']}; background: transparent;")
        status_bar.addWidget(self.status_db)

        status_bar.addPermanentWidget(
            QLabel(f"⚕️ {APP_NAME} v1.0.0")
        )
        self.setStatusBar(status_bar)

    def _on_page_changed(self, index: int):
        """Khi chuyển trang, refresh dữ liệu."""
        self.stack.setCurrentIndex(index)
        page = self.pages[index]
        if hasattr(page, "refresh_data"):
            page.refresh_data()
