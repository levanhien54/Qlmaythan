# -*- coding: utf-8 -*-
"""
Dark Modern Theme cho ứng dụng PyQt6.
"""

# === Color Palette ===
COLORS = {
    "bg_darkest": "#0f0f23",
    "bg_dark": "#1a1a2e",
    "bg_medium": "#16213e",
    "bg_card": "#1e2a4a",
    "bg_hover": "#253255",
    "bg_input": "#0d1b2a",
    "border": "#2a3a5c",
    "border_focus": "#e94560",
    "text_primary": "#e0e0e0",
    "text_secondary": "#8892b0",
    "text_muted": "#5a6785",
    "accent_red": "#e94560",
    "accent_red_hover": "#ff6b81",
    "accent_blue": "#0f3460",
    "accent_blue_light": "#1a73e8",
    "accent_green": "#00c853",
    "accent_yellow": "#ffc107",
    "accent_orange": "#ff9800",
    "accent_purple": "#9c27b0",
    "status_ok": "#00e676",
    "status_error": "#ff1744",
    "status_warning": "#ffab00",
    "scrollbar_bg": "#1a1a2e",
    "scrollbar_handle": "#2a3a5c",
}


def get_main_stylesheet() -> str:
    """Trả về QSS stylesheet chính cho toàn bộ ứng dụng."""
    c = COLORS
    return f"""
    /* === GLOBAL === */
    QWidget {{
        background-color: {c['bg_darkest']};
        color: {c['text_primary']};
        font-family: 'Segoe UI', 'Arial', sans-serif;
        font-size: 13px;
    }}

    /* === SCROLL BAR === */
    QScrollBar:vertical {{
        background: {c['scrollbar_bg']};
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['scrollbar_handle']};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['border']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {c['scrollbar_bg']};
        height: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['scrollbar_handle']};
        min-width: 30px;
        border-radius: 4px;
    }}

    /* === LINE EDIT === */
    QLineEdit {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {c['text_primary']};
        font-size: 13px;
        selection-background-color: {c['accent_blue']};
    }}
    QLineEdit:focus {{
        border-color: {c['border_focus']};
    }}
    QLineEdit::placeholder {{
        color: {c['text_muted']};
    }}

    /* === COMBO BOX === */
    QComboBox {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {c['text_primary']};
        min-width: 120px;
    }}
    QComboBox:focus {{
        border-color: {c['border_focus']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {c['text_secondary']};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent_blue']};
        color: {c['text_primary']};
        padding: 4px;
    }}

    /* === SPIN BOX === */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {c['text_primary']};
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['border_focus']};
    }}

    /* === DATE EDIT === */
    QDateEdit, QDateTimeEdit {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {c['text_primary']};
    }}
    QDateEdit:focus, QDateTimeEdit:focus {{
        border-color: {c['border_focus']};
    }}
    QDateEdit::drop-down, QDateTimeEdit::drop-down {{
        border: none;
        width: 24px;
    }}

    /* === TEXT EDIT === */
    QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
        color: {c['text_primary']};
    }}
    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c['border_focus']};
    }}

    /* === PUSH BUTTON === */
    QPushButton {{
        background-color: {c['accent_blue']};
        color: {c['text_primary']};
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-weight: bold;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {c['accent_blue_light']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_medium']};
    }}
    QPushButton:disabled {{
        background-color: {c['border']};
        color: {c['text_muted']};
    }}

    /* === TABLE === */
    QTableWidget {{
        background-color: {c['bg_dark']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        gridline-color: {c['border']};
        selection-background-color: {c['accent_blue']};
        alternate-background-color: {c['bg_medium']};
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {c['accent_blue']};
    }}
    QHeaderView::section {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        padding: 10px 12px;
        border: none;
        border-bottom: 2px solid {c['accent_red']};
        font-weight: bold;
        font-size: 12px;
    }}

    /* === TAB WIDGET === */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background: {c['bg_dark']};
    }}
    QTabBar::tab {{
        background: {c['bg_medium']};
        color: {c['text_secondary']};
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }}
    QTabBar::tab:selected {{
        background: {c['accent_red']};
        color: white;
    }}

    /* === GROUP BOX === */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 18px;
        font-weight: bold;
        color: {c['text_primary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}

    /* === LABEL === */
    QLabel {{
        background: transparent;
        color: {c['text_primary']};
    }}

    /* === DIALOG === */
    QDialog {{
        background-color: {c['bg_dark']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}

    /* === MESSAGE BOX === */
    QMessageBox {{
        background-color: {c['bg_dark']};
    }}
    QMessageBox QLabel {{
        color: {c['text_primary']};
    }}

    /* === TOOLTIP === */
    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        padding: 4px 8px;
        border-radius: 4px;
    }}
    """


# === Button style helpers ===
def btn_primary() -> str:
    c = COLORS
    return f"""
        QPushButton {{
            background-color: {c['accent_red']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {c['accent_red_hover']};
        }}
    """


def btn_success() -> str:
    c = COLORS
    return f"""
        QPushButton {{
            background-color: {c['accent_green']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #00e57a;
        }}
    """


def btn_danger() -> str:
    c = COLORS
    return f"""
        QPushButton {{
            background-color: {c['status_error']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #ff4569;
        }}
    """


def btn_outline() -> str:
    c = COLORS
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 20px;
        }}
        QPushButton:hover {{
            border-color: {c['accent_red']};
            color: {c['accent_red']};
        }}
    """
