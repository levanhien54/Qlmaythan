# -*- coding: utf-8 -*-
import xlrd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

wb = xlrd.open_workbook(r'D:\QL may than\011.3.xls')
ws = wb.sheet_by_index(0)

# Find the header row (look for rows 5-12)
for r in range(4, 15):
    row_data = []
    for c in range(ws.ncols):
        val = ws.cell_value(r, c)
        if val:
            row_data.append(f'[Col{c}] {val}')
    if row_data:
        print(f'Row {r}: {row_data}')
