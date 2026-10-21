#!/usr/bin/env python3
"""把本地 Markdown 详解创建成 FlowUs 页面。

用法:
    python3 md2flowus.py <file.md> "<页面标题>" [--parent <page_id>]

依赖: ~/.local/bin/flowus（已登录，凭证在 ~/.flowus/credentials.json）
说明: FlowUs 的 CreatePageRequest 支持 `markdown` 字段直写正文
      （上限 4 MiB / 10000 blocks / 深度 32），故无需手工拼 block 树。
"""
import json
import os
import subprocess
import sys
import tempfile

FLOWUS = os.path.expanduser('~/.local/bin/flowus')


def title_prop(text):
    """FlowUs 的 title 属性需要带判别字段 type 与完整 RichText"""
    return {
        'type': 'title',
        'title': [{
            'type': 'text',
            'text': {'content': text},
            'annotations': {'bold': False, 'italic': False, 'strikethrough': False,
                            'underline': False, 'code': False},
            'plain_text': text,
            'href': None,
        }],
    }


def main():
    md_file, title = sys.argv[1], sys.argv[2]
    parent = None
    if '--parent' in sys.argv:
        parent = sys.argv[sys.argv.index('--parent') + 1]

    md = open(md_file).read()
    if len(md.encode()) > 4 * 1024 * 1024:
        raise SystemExit('markdown 超过 4 MiB 上限')

    body = {'properties': {'title': title_prop(title)}, 'markdown': md}
    if parent:
        body['parent'] = {'page_id': parent}

    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                     encoding='utf-8') as f:
        json.dump(body, f, ensure_ascii=False)
        path = f.name

    try:
        r = subprocess.run([FLOWUS, 'page', 'create', '--body', path, '--json'],
                           capture_output=True, text=True, timeout=180)
        out = r.stdout.strip()
        if not out:
            print('STDERR:', r.stderr[:800], file=sys.stderr)
            raise SystemExit('flowus 无输出')
        data = json.loads(out)
        if not data.get('ok'):
            print(json.dumps(data, ensure_ascii=False)[:800], file=sys.stderr)
            raise SystemExit('创建失败')
        pg = data['data']
        print(f"OK {pg.get('id')}  {pg.get('url')}")
    finally:
        os.unlink(path)


if __name__ == '__main__':
    main()
