import bd,os
LOG=open('/tmp/bd/bulk.log','a',buffering=1)
def log(*a): print(*a,file=LOG,flush=True)
dirs=[('/08-考研考证/301-03-历年真题与模考/来源-08-01 历年真题_2010-2025/数学一真题','math1'),
      ('/08-考研考证/408-02-教材讲义与真题/408考研真题及答案解析','c408')]
for d,tag in dirs:
    items=bd.ls(d)
    if isinstance(items,dict): log('ERR',d,items); continue
    for it in items:
        if it.get('isdir') or not it['server_filename'].lower().endswith('.pdf'): continue
        dest=f'/tmp/bd/corpus/{tag}/{it["server_filename"]}'
        try: log(tag,it['server_filename'],bd.download(it['fs_id'],dest))
        except Exception as e: log(tag,it['server_filename'],'FAIL',type(e).__name__,e)
log('BULKDONE')
