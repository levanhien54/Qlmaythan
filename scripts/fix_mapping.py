"""Migration: map may_thuc_hien text to thiet_bi_id for orphaned phien_dieu_tri records."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
from database.connection import db


def _has_so(dev_name: str, num: int) -> bool:
    r"""True nếu dev_name chứa 'số <num>' với num là SỐ ĐỘC LẬP (so khớp chính xác).
    Tránh substring 'số 1' khớp nhầm 'số 10'/'số 11' → gán phiên sai máy.
    Cho phép số 0-đệm ('số 01' khớp num=1)."""
    return re.search(rf'số\s*0*{num}(?!\d)', dev_name) is not None

# Get all unmapped records with unique may_thuc_hien
unmapped = db.fetch_all("""
    SELECT DISTINCT may_thuc_hien 
    FROM phien_dieu_tri 
    WHERE thiet_bi_id IS NULL AND may_thuc_hien IS NOT NULL AND may_thuc_hien != ''
""")

# Get all devices
devices = db.fetch_all("SELECT id, ten_thiet_bi, so_may FROM thiet_bi")

# Build mapping: extract number from may_thuc_hien and match by device name pattern
total_updated = 0
for u in unmapped:
    mth = u['may_thuc_hien']
    matched_id = None
    
    # Try to extract a number from the may_thuc_hien
    # e.g. "Máy thận nhân tạo_F1" -> try to match "Fresinius số 1"
    # e.g. "Máy thận nhân tạo_Số 09" -> try to match "số 9"
    # e.g. "Máy thận nhân tạo_Nip 5" -> try Nip pattern
    # e.g. "Máy lọc máu HDF online_Số 02" -> HDF device
    
    for dev in devices:
        dev_name = dev['ten_thiet_bi'].lower()
        
        # Pattern: "F1" -> "fresinius số 1"
        f_match = re.search(r'_f(\d+)$', mth, re.IGNORECASE)
        if f_match:
            num = int(f_match.group(1))
            if 'fresinius' in dev_name and _has_so(dev_name, num):
                matched_id = dev['id']
                break

        # Pattern: "_Nip 5" -> Nipro
        nip_match = re.search(r'_nip\s*(\d+)$', mth, re.IGNORECASE)
        if nip_match:
            num = int(nip_match.group(1))
            if 'nipro' in dev_name and _has_so(dev_name, num):
                matched_id = dev['id']
                break

        # Pattern: "_Số 09" or "_Số 02" in "Máy thận nhân tạo" -> B.Braun
        so_match = re.search(r'thận nhân tạo_số\s*(\d+)', mth, re.IGNORECASE)
        if so_match:
            num = int(so_match.group(1))
            if 'b.braun' in dev_name and _has_so(dev_name, num):
                matched_id = dev['id']
                break

        # Pattern: "HDF online_Số 02"
        hdf_match = re.search(r'hdf.*_.*số\s*(\d+)', mth, re.IGNORECASE)
        if hdf_match:
            num = int(hdf_match.group(1))
            if 'hdf' in dev_name and _has_so(dev_name, num):
                matched_id = dev['id']
                break

        # Pattern: "HDF online_TTNLM_Số 03"
        hdf2_match = re.search(r'hdf.*_.*_.*số\s*(\d+)', mth, re.IGNORECASE)
        if hdf2_match:
            num = int(hdf2_match.group(1))
            if 'hdf' in dev_name and _has_so(dev_name, num):
                matched_id = dev['id']
                break
    
    if matched_id:
        count = db.fetch_one(
            "SELECT COUNT(*) as c FROM phien_dieu_tri WHERE thiet_bi_id IS NULL AND may_thuc_hien = ?",
            (mth,)
        )['c']
        db.execute(
            "UPDATE phien_dieu_tri SET thiet_bi_id = ? WHERE thiet_bi_id IS NULL AND may_thuc_hien = ?",
            (matched_id, mth)
        )
        total_updated += count
        print(f"  OK: '{mth}' -> device id={matched_id} ({count} records)")
    else:
        print(f"  SKIP: '{mth}' -> no match found")

# Final check
remaining = db.fetch_one('SELECT COUNT(*) as c FROM phien_dieu_tri WHERE thiet_bi_id IS NULL')
print(f"\nTotal updated: {total_updated}")
print(f"Remaining without thiet_bi_id: {remaining['c']}")
