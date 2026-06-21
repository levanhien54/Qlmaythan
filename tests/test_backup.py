# -*- coding: utf-8 -*-
"""Tests cho sao lưu DB (database.backup)."""
import os
import sqlite3
import pytest

from database.backup import backup_database


def _make_db(path, rows=3):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    c.executemany("INSERT INTO t (v) VALUES (?)", [(f"r{i}",) for i in range(rows)])
    c.commit()
    c.close()


def test_backup_creates_valid_copy(tmp_path):
    db = tmp_path / "src.db"
    _make_db(str(db), rows=5)
    bdir = tmp_path / "backups"
    dest = backup_database(str(db), str(bdir), keep=10)
    assert dest and os.path.exists(dest)
    # Bản sao lưu phải đọc được và đủ dữ liệu
    c = sqlite3.connect(dest)
    n = c.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    c.close()
    assert n == 5


def test_backup_none_when_db_missing(tmp_path):
    assert backup_database(str(tmp_path / "nope.db"), str(tmp_path / "b"), keep=5) is None


def test_backup_rotation_keeps_n(tmp_path):
    db = tmp_path / "src.db"
    _make_db(str(db))
    bdir = tmp_path / "backups"
    for _ in range(5):
        backup_database(str(db), str(bdir), keep=3)
    files = [f for f in os.listdir(bdir) if f.endswith(".db")]
    assert len(files) == 3, f"Phải giữ đúng 3 bản, có {len(files)}"


def test_backup_wal_safe(tmp_path):
    """Sao lưu được kể cả khi DB đang mở ở chế độ WAL (có ghi chưa checkpoint)."""
    db = tmp_path / "src.db"
    c = sqlite3.connect(str(db))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    c.execute("INSERT INTO t (v) VALUES ('a')")
    c.commit()
    # Giữ connection MỞ (mô phỏng app đang chạy) khi sao lưu
    dest = backup_database(str(db), str(tmp_path / "b"), keep=5)
    c.close()
    assert dest and os.path.exists(dest)
    c2 = sqlite3.connect(dest)
    assert c2.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    c2.close()
