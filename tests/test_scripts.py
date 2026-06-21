# -*- coding: utf-8 -*-
"""Integration tests cho scripts/ — bảo đảm cleanup + audit chạy đúng logic."""
import os
import sys
import importlib.util
import pytest

from database.queries import thiet_bi, nhan_vien, phien_dieu_tri


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_script(name):
    """Import 1 script từ scripts/ (không phải package)."""
    path = os.path.join(PROJECT_ROOT, 'scripts', name)
    spec = importlib.util.spec_from_file_location(name.replace('.py', ''), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ==========================================================
# AUDIT: find_exact_duplicates / find_overlapping_sessions
# ==========================================================

@pytest.fixture
def seeded_with_dups(temp_db, monkeypatch):
    """DB có 2 phiên duplicate + 1 phiên overlap + 1 phiên rác + 2 phiên sạch."""
    tb1 = thiet_bi.create(ten_thiet_bi='Máy A')
    tb2 = thiet_bi.create(ten_thiet_bi='Máy B')
    nv = nhan_vien.create(ho_ten='PTV', chuc_vu_trinh_do='KTV')

    # Drop UNIQUE index TRƯỚC để mô phỏng DB legacy chưa có constraint
    import database.queries.phien_dieu_tri as pdt_mod
    pdt_mod.db.execute("DROP INDEX IF EXISTS ux_phien_tb_bd")

    # 2 phiên SẠCH (không trùng)
    phien_dieu_tri.create(
        ho_ten='BN Sạch 1', thiet_bi_id=tb1,
        ngay_bat_dau='2026-04-01 08:00:00',
        ngay_ket_thuc='2026-04-01 12:00:00',
    )
    phien_dieu_tri.create(
        ho_ten='BN Sạch 2', thiet_bi_id=tb2,
        ngay_bat_dau='2026-04-01 08:00:00',
        ngay_ket_thuc='2026-04-01 12:00:00',
    )

    # Seed duplicate (mô phỏng DB production có dup từ thời trước khi có constraint)
    pdt_mod.db.execute("""
        INSERT INTO phien_dieu_tri (thiet_bi_id, ho_ten, ngay_bat_dau, ngay_ket_thuc)
        VALUES (?, 'BN Sạch 1 COPY', '2026-04-01 08:00:00', '2026-04-01 12:00:00')
    """, (tb1,))
    # Thêm 1 phiên overlap nữa (không cùng start — khác bản chất, SQLite không block)
    pdt_mod.db.execute("""
        INSERT INTO phien_dieu_tri (thiet_bi_id, ho_ten, ngay_bat_dau, ngay_ket_thuc)
        VALUES (?, 'BN Overlap', '2026-04-01 10:00:00', '2026-04-01 14:00:00')
    """, (tb1,))
    # Phiên rác
    pdt_mod.db.execute("""
        INSERT INTO phien_dieu_tri (thiet_bi_id, ho_ten, ngay_bat_dau)
        VALUES (?, '', NULL)
    """, (tb1,))
    return {'tb1': tb1, 'tb2': tb2}


def test_audit_duplicates_find_exact(seeded_with_dups):
    script = _load_script('audit_duplicates.py')
    dups = script.find_exact_duplicates()
    # 1 nhóm: (tb1, 2026-04-01 08:00:00) có 2 phiên (Sạch 1 + Copy)
    assert len(dups) == 1
    assert dups[0]['thiet_bi_id'] == seeded_with_dups['tb1']
    assert dups[0]['n'] == 2


def test_audit_duplicates_find_overlapping(seeded_with_dups):
    script = _load_script('audit_duplicates.py')
    overlaps = script.find_overlapping_sessions()
    # BN Sạch 1 (08-12) overlap với BN Overlap (10-14) trên tb1
    # + BN Sạch 1 COPY (08-12) overlap với BN Overlap (10-14) trên tb1
    assert len(overlaps) >= 1
    assert any(o['thiet_bi_id'] == seeded_with_dups['tb1'] for o in overlaps)


# ==========================================================
# CLEANUP: cleanup_duplicates.py
# ==========================================================

def test_cleanup_duplicates_find_groups(seeded_with_dups):
    script = _load_script('cleanup_duplicates.py')
    groups = script.find_dup_groups()
    assert len(groups) == 1
    g = groups[0]
    assert g['n'] == 2
    # keep_id = min(id), xóa phần còn lại
    ids = sorted(int(x) for x in g['all_ids'].split(','))
    assert g['keep_id'] == ids[0]


def test_cleanup_duplicates_apply_deletes_correct(seeded_with_dups, monkeypatch, tmp_path):
    script = _load_script('cleanup_duplicates.py')

    # Patch DB_PATH + backup dir cho script (avoid touching prod DB)
    import database.queries.phien_dieu_tri as pdt_mod
    monkeypatch.setattr(script, 'DB_PATH', ':memory:')
    monkeypatch.setattr(script, 'db', pdt_mod.db)
    monkeypatch.setattr(script, 'shutil', type('FakeShutil', (),
                                                 {'copy2': lambda a, b: None}))

    before = phien_dieu_tri.count()
    # Simulate --apply
    monkeypatch.setattr(sys, 'argv', ['cleanup_duplicates.py', '--apply'])
    script.main()
    after = phien_dieu_tri.count()
    assert after == before - 1   # 1 duplicate bị xóa


def test_cleanup_duplicates_dry_run_no_changes(seeded_with_dups, monkeypatch):
    script = _load_script('cleanup_duplicates.py')
    import database.queries.phien_dieu_tri as pdt_mod
    monkeypatch.setattr(script, 'db', pdt_mod.db)

    before = phien_dieu_tri.count()
    monkeypatch.setattr(sys, 'argv', ['cleanup_duplicates.py'])  # no --apply
    script.main()
    assert phien_dieu_tri.count() == before, 'Dry-run KHÔNG được xóa'


# ==========================================================
# CLEANUP: cleanup_garbage_sessions.py
# ==========================================================

def test_cleanup_garbage_find(seeded_with_dups):
    script = _load_script('cleanup_garbage_sessions.py')
    rows = script.find_garbage()
    # 1 phiên rác (ho_ten='', ngay_bat_dau=NULL)
    assert len(rows) == 1
    assert rows[0]['ho_ten'] == ''


def test_cleanup_garbage_apply(seeded_with_dups, monkeypatch):
    script = _load_script('cleanup_garbage_sessions.py')
    import database.queries.phien_dieu_tri as pdt_mod
    monkeypatch.setattr(script, 'db', pdt_mod.db)
    monkeypatch.setattr(script, 'shutil', type('FakeShutil', (),
                                                 {'copy2': lambda a, b: None}))

    before = phien_dieu_tri.count()
    monkeypatch.setattr(sys, 'argv', ['cleanup_garbage_sessions.py', '--apply'])
    script.main()
    assert phien_dieu_tri.count() == before - 1


# ==========================================================
# AUDIT: audit_data_quality.py
# ==========================================================

def test_audit_data_quality_runs_without_crash(seeded_with_dups, capsys):
    """Chạy full audit — không crash, có output expected sections."""
    script = _load_script('audit_data_quality.py')
    script.audit_staff_fragmentation()
    script.audit_orphan_sessions()
    script.audit_no_ptv()
    script.audit_age_outliers()
    script.audit_date_inversion()
    script.audit_session_duration()
    script.audit_orphan_fk()
    out = capsys.readouterr().out
    # Có ít nhất các section header
    assert 'STAFF FRAGMENTATION' in out
    assert 'ORPHAN' in out.upper() or 'PHIÊN' in out


def test_audit_orphan_sessions_detects_null_tb(temp_db, monkeypatch):
    """Chèn phiên thiet_bi_id=NULL → audit phải phát hiện."""
    nhan_vien.create(ho_ten='X', chuc_vu_trinh_do='KTV')
    import database.queries.phien_dieu_tri as pdt_mod
    pdt_mod.db.execute("""
        INSERT INTO phien_dieu_tri (ho_ten, ngay_bat_dau)
        VALUES ('BN Orphan', '2026-04-01 08:00:00')
    """)
    script = _load_script('audit_data_quality.py')
    rows = pdt_mod.db.fetch_all("""
        SELECT id FROM phien_dieu_tri
        WHERE thiet_bi_id IS NULL
    """)
    assert len(rows) == 1
