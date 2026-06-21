# -*- coding: utf-8 -*-
"""Tests cho sao lưu DB (database.backup)."""
import os
import sqlite3
import pytest

from database.backup import backup_database, list_backups, restore_backup


def _make_db(path, rows=3):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    c.executemany("INSERT INTO t (v) VALUES (?)", [(f"r{i}",) for i in range(rows)])
    c.commit()
    c.close()


def test_list_backups(tmp_path):
    db = str(tmp_path / "s.db"); _make_db(db)
    bdir = str(tmp_path / "b")
    backup_database(db, bdir); backup_database(db, bdir)
    lst = list_backups(bdir)
    assert len(lst) == 2
    assert all({'path', 'name', 'size', 'mtime'} <= set(x) for x in lst)


def test_restore_backup_replaces_db(tmp_path):
    """Khôi phục bản 3-dòng đè lên DB 4-dòng → còn 3 dòng (+ tự backup hiện trạng)."""
    db = str(tmp_path / "live.db"); _make_db(db, rows=3)
    bdir = str(tmp_path / "b")
    dest = backup_database(db, bdir, keep=10)           # snapshot 3 dòng
    c = sqlite3.connect(db); c.execute("INSERT INTO t (v) VALUES ('x')"); c.commit(); c.close()
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM t").fetchone()[0] == 4

    restore_backup(dest, db_path=db, backups_dir=bdir)
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM t").fetchone()[0] == 3
    # đã tự sao lưu hiện trạng (4 dòng) trước khi ghi đè → có thêm bản backup
    assert len(list_backups(bdir)) >= 2


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
