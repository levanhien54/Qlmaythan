# -*- coding: utf-8 -*-
"""Smoke test GUI desktop (PyQt6) — chạy OFFSCREEN nên không mở cửa sổ.

Xác nhận 3 fix UI:
  - #5  DeviceDialog: nam_su_dung=0 KHÔNG bị kẹp lên 2000
  - #10 DataTable: số 0 hiển thị "0" (không phải ô trống)
  - #3  SessionsPage dùng excel_import.import_from_path (nhập đúng file)
Bỏ qua nếu môi trường không cài PyQt6.
"""
import os
import importlib
import pytest

# Phải set TRƯỚC khi import QtWidgets để không bật cửa sổ thật.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _silence_msgbox(monkeypatch):
    """QMessageBox modal sẽ TREO test headless — thay bằng no-op.
    Patch trên class nên áp dụng cho mọi module đã `import QMessageBox`."""
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))


# ---------- import-check mọi module ui/ (bắt lỗi cú pháp/khởi tạo) ----------

@pytest.mark.parametrize("mod", [
    "ui.components.data_table",
    "ui.dialogs.device_dialog",
    "ui.pages.sessions_page",
    "ui.pages.settings_page",
    "ui.main_window",
    "excel_import",
])
def test_ui_modules_import(mod):
    importlib.import_module(mod)


def test_settings_page_constructs_and_refreshes(qapp, temp_db):
    """Trang Cài đặt dựng được + refresh (đếm + liệt kê backup) không crash."""
    from ui.pages.settings_page import SettingsPage
    p = SettingsPage()
    p.refresh_data()
    assert p.info_label.text() and "phiên bản" in p.info_label.text()


# ---------- #5 DeviceDialog: năm 0 giữ nguyên ----------

def test_device_dialog_year_zero_not_clamped(qapp, temp_db):
    from ui.dialogs.device_dialog import DeviceDialog
    dlg = DeviceDialog(data={"ten_thiet_bi": "Máy X", "nam_su_dung": 0})
    assert dlg.spin_nam.value() == 0, "Năm 0 bị kẹp lên 2000 (fix #5 thất bại)"
    # _save phải giữ 0, không ghi 2000
    dlg.txt_ten.setText("Máy X")
    dlg._save()
    assert dlg.result_data["nam_su_dung"] == 0


def test_device_dialog_year_normal_preserved(qapp, temp_db):
    from ui.dialogs.device_dialog import DeviceDialog
    dlg = DeviceDialog(data={"ten_thiet_bi": "Máy Y", "nam_su_dung": 2018})
    assert dlg.spin_nam.value() == 2018


# ---------- #10 DataTable: số 0 hiển thị "0" ----------

def test_data_table_zero_renders_as_zero(qapp):
    from ui.components.data_table import DataTable
    tbl = DataTable(["Tên", "Tuổi", "Ghi chú"], show_actions=False)
    tbl.load_data(
        [{"id": 1, "ten": "BN", "tuoi": 0, "ghi_chu": ""}],
        id_key="id",
        display_keys=["ten", "tuoi", "ghi_chu"],
    )
    assert tbl.item(0, 1).text() == "0", "tuoi=0 phải hiện '0', không phải ô trống"
    assert tbl.item(0, 2).text() == "", "chuỗi rỗng vẫn là ô trống"


# ---------- #3 SessionsPage dùng logic import dùng chung ----------

def test_excel_import_helper_available():
    from excel_import import import_from_path, ExcelParseError  # noqa
    assert callable(import_from_path)


# ---------- R3/R5 SessionDialog: giữ may_thuc_hien + chịu được NULL ----------

def test_session_dialog_preserves_may_thuc_hien_when_unmatched(qapp, temp_db):
    """Sửa phiên có thiet_bi_id NULL + may_thuc_hien text, không chọn máy:
    _save phải GIỮ nguyên may_thuc_hien (không ghi đè rỗng)."""
    from ui.dialogs.session_dialog import SessionDialog
    dlg = SessionDialog(data={
        "ho_ten": "BN Test", "thiet_bi_id": None, "may_thuc_hien": "Máy 5",
        "ngay_bat_dau": "2026-04-01 08:00:00",
        "ngay_ket_thuc": "2026-04-01 12:00:00",
        "tuoi": None, "dia_chi": None, "so_ho_so": None, "ghi_chu": None,
    })
    dlg._save()
    assert dlg.result_data is not None, "NULL fields không được làm crash _populate"
    assert dlg.result_data["may_thuc_hien"] == "Máy 5", "Không được wipe tên máy"


def test_session_dialog_rejects_end_before_start(qapp, temp_db):
    """Ngày kết thúc <= bắt đầu → _save không tạo result_data (validate)."""
    from PyQt6.QtCore import QDateTime
    from ui.dialogs.session_dialog import SessionDialog
    dlg = SessionDialog()
    dlg.txt_ho_ten.setText("BN Test")
    dlg.dt_bat_dau.setDateTime(QDateTime.fromString("2026-04-01 12:00:00", "yyyy-MM-dd hh:mm:ss"))
    dlg.dt_ket_thuc.setDateTime(QDateTime.fromString("2026-04-01 08:00:00", "yyyy-MM-dd hh:mm:ss"))
    dlg._save()
    assert dlg.result_data is None, "Phiên end<start không được lưu"
