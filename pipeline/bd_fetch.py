import os,sys,json,time,urllib.request,urllib.parse
TOK=open('/tmp/bd/tok').read().strip()
UA={'User-Agent':'pan.baidu.com'}
API='https://pan.baidu.com/rest/2.0/xpan/'
def _get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60))
def ls(d):
    out=[];start=0
    while True:
        q=urllib.parse.urlencode({'method':'list','dir':d,'access_token':TOK,'web':'1','start':start,'limit':1000})
        r=_get(API+'file?'+q)
        if r.get('errno'): return r
        out+=r.get('list',[])
        if len(r.get('list',[]))<1000: break
        start+=1000
    return out
def search(key,dir='/',recursion=1,num=100,page=1):
    q=urllib.parse.urlencode({'method':'search','key':key,'dir':dir,'recursion':recursion,'access_token':TOK,'web':'1','num':num,'page':page})
    return _get(API+'search?'+q)
def filemetas(fsids):
    q=urllib.parse.urlencode({'method':'filemetas','access_token':TOK,'fsids':json.dumps(fsids),'dlink':1,'thumb':0,'extra':0})
    return _get('https://pan.baidu.com/rest/2.0/xpan/multimedia?'+q)
def download(fsid,dest):
    r=filemetas([int(fsid)])
    if r.get('errno'): return ('meta_err',r)
    lst=r.get('list') or []
    if not lst: return ('no_list',r)
    d=lst[0].get('dlink')
    if not d: return ('no_dlink',lst[0])
    exp=lst[0].get('size',0)
    if os.path.exists(dest) and exp and os.path.getsize(dest)==exp: return ('cached',dest)
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    req=urllib.request.Request(d+'&access_token='+TOK,headers=UA)
    with urllib.request.urlopen(req,timeout=300) as resp, open(dest,'wb') as f:
        while True:
            b=resp.read(1<<20)
            if not b: break
            f.write(b)
    return ('ok',os.path.getsize(dest))
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='ls':
        r=ls(sys.argv[2])
        if isinstance(r,dict): print(r); sys.exit()
        for it in sorted(r,key=lambda x:(not x['isdir'],x['server_filename'])):
            print(('D' if it['isdir'] else 'F'), f"{it['size']:>12,}", it['path'])
    elif cmd=='search':
        key,dir=sys.argv[2],sys.argv[3]
        seen=set();allp=[]
        for pg in range(1,6):
            r=search(key,dir,1,100,pg)
            l=r.get('list') or []
            if not l: break
            for it in l:
                p=it.get('path')
                if p in seen: continue
                seen.add(p); allp.append(it)
            if len(l)<100: break
        for it in sorted(allp,key=lambda x:x.get('path','')):
            if it.get('isdir'): continue
            print(f"{it.get('size',0):>12,}", it.get('path'))
        print('--- total', len(allp),'entries', file=sys.stderr)
    elif cmd=='dl':
        print(download(sys.argv[2],sys.argv[3]))
