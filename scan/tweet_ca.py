import json,re,collections,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; D=ROOT/'data'
CA=re.compile(r'0x[a-fA-F0-9]{40}')
SOL=re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')
DEX=re.compile(r'(dexscreener\.com|dextools\.io|geckoterminal|pump\.fun|birdeye\.so|app\.uniswap\.org|jup\.ag)',re.I)
CAWORD=re.compile(r'\b(CA|C\.?A\.?|contract|合约|コントラクト)\b\s*[:：]?',re.I)
def is_addr(a):
    b=bytes.fromhex(a[2:]); return sum(1 for x in b if 32<=x<127)<16
rows=[]
if (D/'tweets/tweets.jsonl').exists():
    for l in open(D/'tweets/tweets.jsonl'):
        try: rows.append(json.loads(l))
        except: pass
res={}
for r in rows:
    u=r['u']
    if not r.get('ok'):
        res[u]={'st':r.get('e','err'),'ca':[],'dex':False,'n':0}
        continue
    cas=[];dex=False;caword=False;first_d=None
    for t in r.get('tw',[]):
        txt=(t.get('t') or '')+' '+(t.get('q') or '')
        for a in CA.findall(txt):
            a=a.lower()
            if is_addr(a) and a not in cas: cas.append(a)
        if DEX.search(txt): dex=True
        if CAWORD.search(txt): caword=True
    res[u]={'st':'ok','ca':cas,'dex':dex,'caword':caword,'n':r.get('n',0)}
json.dump(res,open(D/'tweet_ca.json','w'),ensure_ascii=False)
ok=[v for v in res.values() if v['st']=='ok']
print('accounts fetched:',len(res),'ok:',len(ok))
print('推文里出现合约地址:',sum(1 for v in ok if v['ca']))
print('推文里有DEX/交易链接:',sum(1 for v in ok if v['dex']))
print('推文提到CA/合约字样:',sum(1 for v in ok if v.get('caword')))
