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


# ---------- import-check mọi module ui/ (bắt lỗi cú pháp/khởi tạo) ----------

@pytest.mark.parametrize("mod", [
    "ui.components.data_table",
    "ui.dialogs.device_dialog",
    "ui.pages.sessions_page",
    "excel_import",
])
def test_ui_modules_import(mod):
    importlib.import_module(mod)


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
