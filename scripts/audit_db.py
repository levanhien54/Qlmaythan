import sys
sys.stdout.reconfigure(encoding='utf-8')
from database.connection import db

print("=== DATA INTEGRITY AUDIT ===\n")

# Totals
total_tb = db.fetch_one('SELECT COUNT(*) as c FROM thiet_bi')['c']
total_pdt = db.fetch_one('SELECT COUNT(*) as c FROM phien_dieu_tri')['c']
total_bg = db.fetch_one('SELECT COUNT(*) as c FROM ban_giao')['c']
total_bd = db.fetch_one('SELECT COUNT(*) as c FROM bao_duong')['c']
total_nv = db.fetch_one('SELECT COUNT(*) as c FROM nhan_vien')['c']
print(f"Totals: {total_tb} thiet_bi, {total_pdt} phien_dieu_tri, {total_bg} ban_giao, {total_bd} bao_duong, {total_nv} nhan_vien\n")

# 1. FK integrity
r1 = db.fetch_one('SELECT COUNT(*) as c FROM phien_dieu_tri WHERE thiet_bi_id IS NULL')
print(f"[1] phien_dieu_tri WITHOUT thiet_bi_id: {r1['c']}")

r1c = db.fetch_one('SELECT COUNT(*) as c FROM phien_dieu_tri WHERE thiet_bi_id IS NOT NULL AND thiet_bi_id NOT IN (SELECT id FROM thiet_bi)')
print(f"[2] phien_dieu_tri with INVALID thiet_bi_id: {r1c['c']}")

r1d = db.fetch_one('SELECT COUNT(*) as c FROM phien_dieu_tri WHERE ptv_chinh_id IS NOT NULL AND ptv_chinh_id NOT IN (SELECT id FROM nhan_vien)')
print(f"[3] phien_dieu_tri with INVALID ptv_chinh_id: {r1d['c']}")

r2 = db.fetch_one('SELECT COUNT(*) as c FROM ban_giao WHERE thiet_bi_id NOT IN (SELECT id FROM thiet_bi)')
print(f"[4] ban_giao with INVALID thiet_bi_id: {r2['c']}")

r3 = db.fetch_one('SELECT COUNT(*) as c FROM bao_duong WHERE thiet_bi_id NOT IN (SELECT id FROM thiet_bi)')
print(f"[5] bao_duong with INVALID thiet_bi_id: {r3['c']}")

r4 = db.fetch_one('SELECT COUNT(*) as c FROM thiet_bi WHERE nguoi_quan_ly_id IS NOT NULL AND nguoi_quan_ly_id NOT IN (SELECT id FROM nhan_vien)')
print(f"[6] thiet_bi with INVALID nguoi_quan_ly_id: {r4['c']}")

# Unmapped may_thuc_hien — dùng ĐÚNG logic find_device của bộ import (không
# phải LIKE '%...%' ngây thơ, vốn cho dương tính giả / verdict sai lệch).
print("\n=== UNMAPPED may_thuc_hien (theo logic find_device thật) ===")
from matching import find_device
_devs = db.fetch_all("SELECT id, ten_thiet_bi, tinh_trang FROM thiet_bi")
device_list = [(d['id'], d['ten_thiet_bi'],
                d['ten_thiet_bi'].lower().replace(' ', ''),
                d.get('tinh_trang', '')) for d in _devs]
unmapped = db.fetch_all("SELECT DISTINCT p.may_thuc_hien FROM phien_dieu_tri p WHERE p.thiet_bi_id IS NULL AND p.may_thuc_hien IS NOT NULL AND p.may_thuc_hien != ''")
for u in unmapped:
    name = u['may_thuc_hien']
    did, ten, _tt = find_device(name, device_list)
    status = f"MAP -> id={did} ({ten})" if did else "KHONG khop / mo ho (can ghi ro hang+so)"
    print(f"  '{name}' -> {status}")

# Date formats
print("\n=== DATE FORMAT CHECK ===")
r5 = db.fetch_all("SELECT ngay_bat_dau FROM phien_dieu_tri LIMIT 2")
for r in r5:
    print(f"  PDT ngay_bat_dau: {r['ngay_bat_dau']}")
r6 = db.fetch_all("SELECT ngay_ban_giao FROM ban_giao LIMIT 2")
for r in r6:
    print(f"  BG ngay_ban_giao: {r['ngay_ban_giao']}")
r7 = db.fetch_all("SELECT ngay_thuc_hien FROM bao_duong LIMIT 2")
for r in r7:
    print(f"  BD ngay_thuc_hien: {r['ngay_thuc_hien']}")
