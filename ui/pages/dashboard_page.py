# -*- coding: utf-8 -*-
"""
Dashboard tổng quan.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QColor
from ui.styles import COLORS
from ui.components.stat_card import StatCard
from database.queries import thiet_bi, phien_dieu_tri, bao_duong


class SimpleChart(QFrame):
    """Biểu đồ bar đơn giản."""

    def __init__(self, title: str, data: dict, parent=None):
        super().__init__(parent)
        self._title = title
        self._data = data
        self.setMinimumHeight(250)
        self.setMinimumWidth(350)
        c = COLORS
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """)

    def set_data(self, data: dict):
        self._data = data
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 20
        chart_x = margin + 100
        chart_y = margin + 30
        chart_w = w - chart_x - margin
        chart_h = h - chart_y - margin - 20

        # Title
        painter.setPen(QColor(COLORS["text_primary"]))
        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        painter.drawText(margin, margin + 15, self._title)

        if not self._data:
            painter.end()
            return

        max_val = max(self._data.values()) if self._data else 1
        bar_height = min(30, max(15, chart_h // max(len(self._data), 1) - 4))
        colors = ["#e94560", "#1a73e8", "#00c853", "#ffc107", "#9c27b0", "#ff9800"]

        for i, (label, value) in enumerate(self._data.items()):
            y = chart_y + i * (bar_height + 6)
            if y + bar_height > h - margin:
                break

            # Label
            painter.setPen(QColor(COLORS["text_secondary"]))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(margin, y + bar_height - 3, str(label))

            # Bar
            bar_w = int((value / max_val) * chart_w) if max_val > 0 else 0
            color = QColor(colors[i % len(colors)])
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(chart_x, y, max(bar_w, 2), bar_height, 4, 4)

            # Value
            painter.setPen(QColor(COLORS["text_primary"]))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(chart_x + bar_w + 6, y + bar_height - 3, str(value))

        painter.end()


class DashboardPage(QWidget):
    """Trang Dashboard tổng quan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("📊 Dashboard — Tổng quan hệ thống")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        layout.addWidget(title)

        # Stat Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_total = StatCard("🖥️", "0", "Tổng thiết bị",
                                   COLORS["accent_blue_light"])
        self.card_active = StatCard("✅", "0", "Hoạt động",
                                    COLORS["accent_green"])
        self.card_error = StatCard("⚠️", "0", "Báo lỗi / Hỏng",
                                   COLORS["accent_red"])
        self.card_sessions = StatCard("💉", "0", "Phiên hôm nay",
                                      COLORS["accent_yellow"])

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_active)
        cards_layout.addWidget(self.card_error)
        cards_layout.addWidget(self.card_sessions)
        layout.addLayout(cards_layout)

        # Charts
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        self.chart_status = SimpleChart("Tình trạng thiết bị", {})
        self.chart_usage = SimpleChart("Tần suất sử dụng", {})

        charts_layout.addWidget(self.chart_status)
        charts_layout.addWidget(self.chart_usage)
        layout.addLayout(charts_layout)

        # Alerts
        self.alerts_frame = QFrame()
        c = COLORS
        self.alerts_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg_card']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """)
        alerts_layout = QVBoxLayout(self.alerts_frame)
        alerts_layout.setContentsMargins(16, 16, 16, 16)

        alerts_title = QLabel("🔔 Cảnh báo")
        alerts_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        alerts_title.setStyleSheet(f"color: {c['accent_yellow']}; background: transparent;")
        alerts_layout.addWidget(alerts_title)

        self.alerts_content = QLabel("Đang tải...")
        self.alerts_content.setStyleSheet(f"color: {c['text_secondary']}; background: transparent;")
        self.alerts_content.setWordWrap(True)
        alerts_layout.addWidget(self.alerts_content)

        layout.addWidget(self.alerts_frame)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """Cập nhật dữ liệu dashboard."""
        # Stats
        total = thiet_bi.count()
        status_count = thiet_bi.count_by_tinh_trang()
        active = status_count.get("Hoạt động", 0)
        error = status_count.get("Báo lỗi", 0) + status_count.get("Hỏng", 0)
        sessions = phien_dieu_tri.count_today()

        self.card_total.update_value(str(total))
        self.card_active.update_value(str(active))
        self.card_error.update_value(str(error))
        self.card_sessions.update_value(str(sessions))

        # Charts
        self.chart_status.set_data(status_count)

        usage = thiet_bi.count_by_tan_suat()
        from config import TAN_SUAT
        usage_named = {TAN_SUAT.get(k, f"Mức {k}"): v for k, v in usage.items()}
        self.chart_usage.set_data(usage_named)

        # Alerts
        upcoming = bao_duong.get_upcoming(7)
        broken = [r for r in thiet_bi.get_all() if "hỏng" in (r.get("tinh_trang", "").lower())]
        error_machines = [r for r in thiet_bi.get_all() if "lỗi" in (r.get("tinh_trang", "").lower())]

        alerts = []
        if broken:
            alerts.append(f"🔴 {len(broken)} thiết bị đã hỏng: " +
                         ", ".join(r["ten_thiet_bi"] for r in broken[:5]))
        if error_machines:
            alerts.append(f"🟡 {len(error_machines)} thiết bị báo lỗi: " +
                         ", ".join(r["ten_thiet_bi"] for r in error_machines[:5]))
        if upcoming:
            alerts.append(f"🔧 {len(upcoming)} phiếu bảo dưỡng sắp đến hạn (7 ngày)")

        self.alerts_content.setText("\n\n".join(alerts) if alerts else "✅ Không có cảnh báo.")
