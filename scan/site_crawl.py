import json, re, subprocess, html, sys, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'data'
SRC = str(D / 'accounts_raw.json')      # {"projects":[{username,bio,website_urls,...}]}
OUT = str(D / 'site_crawl.jsonl')
social=re.compile(r'(t\.me/|linktr\.ee|x\.com|twitter\.com|discord|instagram|youtube|youtu\.be|tiktok|linkedin|facebook|medium\.com|bit\.ly|beacons|link\.bio|opensea\.io|dexscreener|dextools|magiceden|linkin|solo\.to|carrd\.co|telegram)',re.I)
d=json.load(open(SRC))
ps=d['projects']
done=set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: done.add(json.loads(l)['username'])
        except: pass
def pick(p):
    urls=p['website_urls']
    real=[u for u in urls if not social.search(u)]
    return (real or urls)[:2], bool(real)
def fetch(u):
    try:
        r=subprocess.run(['curl','-sSL','-m','25','--max-filesize','400000','-A','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36','-H','Accept-Language: en-US,en;q=0.9','-w','\n@@STATUS@@%{http_code}@@%{url_effective}@@%{size_download}',u],capture_output=True,timeout=40)
        out=r.stdout.decode('utf-8','ignore')
        body,_,tail=out.rpartition('\n@@STATUS@@')
        if not tail: return {'code':'000','final':u,'size':0,'err':r.stderr.decode()[:200],'body':''}
        code,final,size=tail.split('@@')[:3]
        return {'code':code,'final':final,'size':int(size or 0),'err':r.stderr.decode()[:200] if r.returncode else '','body':body}
    except Exception as e:
        return {'code':'000','final':u,'size':0,'err':str(e)[:200],'body':''}
def extract(body):
    t=re.search(r'<title[^>]*>(.*?)</title>',body,re.I|re.S)
    md=re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description|twitter:description)["\'][^>]+content=["\']([^"\']*)',body,re.I) or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:name|property)=["\'](?:description|og:description)',body,re.I)
    ogt=re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)',body,re.I)
    b=re.sub(r'<(script|style|noscript|svg)[^>]*>.*?</\1>','',body,flags=re.I|re.S)
    b=re.sub(r'<[^>]+>',' ',b); b=html.unescape(b); b=re.sub(r'\s+',' ',b).strip()
    low=body.lower()
    flags={k:bool(re.search(v,low)) for k,v in {
        'wallet':r'connect wallet|walletconnect|rainbowkit|wagmi|privy|metamask|web3modal|reown',
        'docs':r'docs\.|/docs|gitbook|documentation|whitepaper|litepaper',
        'github':r'github\.com/',
        'audit':r'audit',
        'presale':r'presale|pre-sale|private sale|whitelist|allowlist',
        'ca':r'0x[a-f0-9]{40}',
        'buy':r'buy now|dexscreener|dextools|uniswap\.org|geckoterminal',
        'coming_soon':r'coming soon|launching soon|stay tuned|countdown',
        'framework_shell':r'id="root"|id="__next"|id="app"',
        'template':r'framer\.com|webflow|wix\.com|squarespace|carrd|lovable|bolt\.new|v0\.dev',
    }.items()}
    return {'title':html.unescape(t.group(1)).strip()[:200] if t else '','og_title':html.unescape(ogt.group(1)).strip()[:200] if ogt else '','meta':html.unescape(md.group(1)).strip()[:500] if md else '','text':b[:3000],'text_len':len(b),'flags':flags}
def work(p):
    urls,has_real=pick(p)
    res=[]
    for u in urls:
        f=fetch(u)
        e=extract(f['body']) if f['body'] else {'title':'','og_title':'','meta':'','text':'','text_len':0,'flags':{}}
        res.append({'url':u,'code':f['code'],'final':f['final'],'size':f['size'],'err':f['err'],**e})
        if f['code'].startswith('2') and e['text_len']>200: break
    return {'username':p['username'],'name':p['name'],'verified':p['verification_type'],'created':p['created_at'][:10],'followers':p['followers_count'],'bio':p['bio'],'all_urls':p['website_urls'],'has_real_site':has_real,'fetched':res}
todo=[p for p in ps if p['username'] not in done]
print('todo',len(todo),'done',len(done),flush=True)
with open(OUT,'a') as f, ThreadPoolExecutor(24) as ex:
    for i,r in enumerate(ex.map(work,todo)):
        f.write(json.dumps(r,ensure_ascii=False)+'\n'); f.flush()
        if i%100==0: print(i,flush=True)
print('finished')
