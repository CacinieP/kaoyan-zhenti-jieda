#!/usr/bin/env python3
"""递归盘点网盘某目录下的 PDF，并输出文本型/扫描型判定表。

用法:
    python3 survey_pdf.py '/08-考研考证/.../数学一真题'
输出: 每行 TSV  size  pages  chars  verdict  filename
verdict: TEXT(可抽文本) / SCAN(图片型,需读图) / EMPTY(0页或损坏)
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bd_fetch as bd


def walk(path):
    """递归列目录，返回所有 .pdf 条目"""
    out, stack = [], [path]
    while stack:
        d = stack.pop()
        items = bd.ls(d)
        if isinstance(items, dict):
            print('ERR', d, items, file=sys.stderr)
            continue
        for it in items:
            if it.get('isdir'):
                stack.append(it['path'])
            elif it['server_filename'].lower().endswith('.pdf'):
                out.append(it)
    return out


def probe(local):
    """返回 (pages, chars, verdict)"""
    try:
        import pymupdf
        doc = pymupdf.open(local)
        pages = len(doc)
        chars = sum(len(p.get_text()) for p in doc)
        if pages == 0:
            return 0, 0, 'EMPTY'
        per = chars / pages
        return pages, chars, ('TEXT' if per >= 200 else 'SCAN')
    except Exception:
        return -1, -1, 'EMPTY'


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1].rstrip('/')
    rows = walk(root)
    print(f'# 目录 {root} 共 {len(rows)} 个 PDF', file=sys.stderr)
    for it in sorted(rows, key=lambda x: x['path']):
        print(f"{it['size']:>10}\t{it['fs_id']}\t{it['path']}")
