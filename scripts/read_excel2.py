# -*- coding: utf-8 -*-
import xlrd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

wb = xlrd.open_workbook(r'D:\QL may than\011.3.xls')
print('Sheets:', wb.sheet_names())

for sn in wb.sheet_names():
    ws = wb.sheet_by_name(sn)
    print(f'\n=== Sheet: {sn} ===')
    print(f'Rows: {ws.nrows}, Cols: {ws.ncols}')
    for r in range(min(80, ws.nrows)):
        row_data = [ws.cell_value(r, c) for c in range(ws.ncols)]
        print(row_data)
