#!/usr/bin/env python3
"""把本地 Markdown 详解写入 Notion 页面（转成原生 block）。

用法:
    python3 md2notion.py <page_id> <file.md> [--dry]

支持的 Markdown 子集:
    # / ## / ###       → heading_1/2/3
    - / *              → bulleted_list_item
    1. 2. ...          → numbered_list_item
    > ...              → quote
    ```lang ... ```    → code
    | a | b |          → table（含表头）
    $$ ... $$          → equation（display）
    $...$              → equation（inline rich_text）
    **bold** / `code`  → 对应 annotation
    <details>...</details> → 去标签留文本

凭证: ~/.mcp-servers/secrets.env 的 NOTION_TOKEN
"""
import os
import re
import sys
import json
import time
import urllib.request

API = 'https://api.notion.com/v1'
VER = '2022-06-28'


def load_token():
    p = os.path.expanduser('~/.mcp-servers/secrets.env')
    for line in open(p):
        line = line.strip()
        if line.startswith('NOTION_TOKEN'):
            v = line.split('=', 1)[1]
            return v.split(' #')[0].strip().strip('"').strip("'")
    raise SystemExit('NOTION_TOKEN not found')


TOKEN = load_token()


def post(path, payload, method='POST'):
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + TOKEN,
                 'Content-Type': 'application/json',
                 'Notion-Version': VER},
        method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def rt(text):
    return [{'type': 'text', 'text': {'content': text}}] if text else []


INLINE_RE = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\$[^$]+\$)')


def rich(text):
    """解析行内 **bold** / `code` / $math$ → rich_text 数组"""
    out = []
    text = text.replace('<details>', '').replace('</details>', '')
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            out.append({'type': 'text', 'text': {'content': part[2:-2]},
                        'annotations': {'bold': True}})
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            out.append({'type': 'text', 'text': {'content': part[1:-1]},
                        'annotations': {'code': True}})
        elif part.startswith('$') and part.endswith('$') and len(part) > 2:
            out.append({'type': 'equation', 'equation': {'expression': part[1:-1]}})
        else:
            out.append({'type': 'text', 'text': {'content': part}})
    return out or [{'type': 'text', 'text': {'content': ''}}]


def blk(kind, payload):
    return {'object': 'block', 'type': kind, kind: payload}


def para(text):
    return blk('paragraph', {'rich_text': rich(text)})


def heading(level, text):
    return blk(f'heading_{level}', {'rich_text': rich(text)})


def code_block(lang, code):
    return blk('code', {'rich_text': rt(code), 'language': lang or 'plain text'})


def table(rows):
    width = max(len(r) for r in rows)
    rows = [r + [''] * (width - len(r)) for r in rows]
    children = [blk('table_row', {'cells': [rich(c) for c in row]}) for row in rows]
    return blk('table', {'table_width': width, 'has_column_header': True,
                         'has_row_header': False, 'children': children})


def parse(md):
    lines = md.split('\n')
    blocks = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()

        if s.startswith('```'):                      # 代码块
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(code_block(lang, '\n'.join(buf)))
            continue

        if s.startswith('$$'):                        # display 公式
            if s.endswith('$$') and len(s) > 4:
                blocks.append(blk('equation', {'expression': s[2:-2]}))
                i += 1
                continue
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith('$$'):
                buf.append(lines[i].strip())
                i += 1
            i += 1
            blocks.append(blk('equation', {'expression': '\n'.join(buf)}))
            continue

        if s.startswith('|') and s.count('|') >= 2:    # 表格
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                blocks.append(table(rows))
            continue

        if not s or s == '---':
            i += 1
            continue

        m = re.match(r'^(#{1,3})\s+(.*)$', s)
        if m:
            blocks.append(heading(len(m.group(1)), m.group(2)))
            i += 1
            continue

        if s.startswith('- ') or s.startswith('* '):
            blocks.append(blk('bulleted_list_item', {'rich_text': rich(s[2:])}))
            i += 1
            continue

        m = re.match(r'^\d+\.\s+(.*)$', s)
        if m:
            blocks.append(blk('numbered_list_item', {'rich_text': rich(m.group(1))}))
            i += 1
            continue

        if s.startswith('> '):
            blocks.append(blk('quote', {'rich_text': rich(s[2:])}))
            i += 1
            continue

        blocks.append(para(s))
        i += 1
    return blocks


def main():
    page_id = sys.argv[1]
    md_file = sys.argv[2]
    blocks = parse(open(md_file).read())
    print(f'{len(blocks)} blocks parsed', file=sys.stderr)
    if '--dry' in sys.argv:
        print(json.dumps(blocks[:2], ensure_ascii=False, indent=2))
        return

    sent, BATCH = 0, 50
    for k in range(0, len(blocks), BATCH):
        chunk = blocks[k:k + BATCH]
        post(f'/blocks/{page_id}/children', {'children': chunk}, 'PATCH')
        sent += len(chunk)
        print(f'  {sent}/{len(blocks)}', file=sys.stderr)
        time.sleep(0.4)
    print(f'DONE {sent} blocks -> https://notion.so/{page_id.replace("-", "")}')


if __name__ == '__main__':
    main()

