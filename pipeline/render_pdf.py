#!/usr/bin/env python3
"""判断 PDF 是文本型还是扫描型，并把页面渲染成 PNG 供逐页读图转录。

用法:
    python3 render_pdf.py <pdf> [--dpi 140] [--pages 1-13] [--outdir DIR]

为什么需要读图：
    数学/408 真题里的公式在 PDF 文本层中会被打散（积分号变 \\uf0f2、
    分式与上下限丢失、上下标被拆成多行）。按《生产规范》「公式符号必须
    逐项对照、不能用模型猜测代替原讲解」，公式题面必须回到页面图像确认。
"""
import sys, os, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--dpi', type=int, default=140)
    ap.add_argument('--pages', default='')
    ap.add_argument('--outdir', default='')
    a = ap.parse_args()

    import pymupdf
    doc = pymupdf.open(a.pdf)
    total = len(doc)
    chars = sum(len(p.get_text()) for p in doc)
    per = chars / max(total, 1)
    verdict = 'TEXT' if per >= 200 else 'SCAN'
    print(f'pages={total} chars={chars} chars/pg={per:.0f} verdict={verdict}')

    outdir = a.outdir or os.path.join('/tmp', 'pdfimg', os.path.splitext(os.path.basename(a.pdf))[0])
    os.makedirs(outdir, exist_ok=True)

    if a.pages:
        s, _, e = a.pages.partition('-')
        lo, hi = int(s), int(e or s)
    else:
        lo, hi = 1, total
    for i in range(lo - 1, min(hi, total)):
        pix = doc[i].get_pixmap(dpi=a.dpi)
        out = os.path.join(outdir, f'p{i+1}.png')
        pix.save(out)
        print(f'{out}\t{pix.width}x{pix.height}')


if __name__ == '__main__':
    main()
