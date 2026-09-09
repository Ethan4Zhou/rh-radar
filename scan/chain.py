import json,urllib.request,time,threading
from concurrent.futures import ThreadPoolExecutor
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
RPCS=["https://rpc.mainnet.chain.robinhood.com","https://robinhood-rpc.publicnode.com","https://rpc.ordofi.network"]
CANARY='0xb9972ca7188e511174947e3936a5315ac7073277'  # known contract, must always return code
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; D=ROOT/'data'
raw=json.load(open(D/'ca_raw.json'))
def is_addr_like(a):
    b=bytes.fromhex(a[2:]); return sum(1 for x in b if 32<=x<127) < 16
addrs=sorted({a for v in raw.values() for a in v['bio_ca']+v['site_ca'] if is_addr_like(a)})
print('addresses to verify:',len(addrs))
SEL={'name':'0x06fdde03','symbol':'0x95d89b41','decimals':'0x313ce567','totalSupply':'0x18160ddd','owner':'0x8da5cb5b'}
lock=threading.Lock(); stats={'req':0,'retry':0,'canary_fail':0}
def post(url,payload,timeout=45):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read())
def send(batch):
    """Send batch, verify every id came back with a 'result' key. Return dict id->result or None."""
    for attempt in range(5):
        url=RPCS[attempt % len(RPCS)]
        try:
            with lock: stats['req']+=1
            res=post(url,batch)
            if not isinstance(res,list): raise ValueError('not a list')
            by={}
            for x in res:
                if isinstance(x,dict) and 'id' in x and 'result' in x and x['result'] is not None:
                    by[x['id']]=x['result']
            missing=[b for b in batch if b['id'] not in by]
            if not missing: return by
            # retry only the missing ones, individually
            with lock: stats['retry']+=len(missing)
            for b in missing:
                for u2 in RPCS:
                    try:
                        r2=post(u2,[b],30)
                        if isinstance(r2,list) and r2 and 'result' in r2[0] and r2[0]['result'] is not None:
                            by[b['id']]=r2[0]['result']; break
                    except Exception: time.sleep(0.5)
            if all(b['id'] in by for b in batch): return by
            return by  # partial; caller marks unknowns
        except Exception:
            time.sleep(1.0*(attempt+1))
    return None
def dec_str(h):
    if not h or h=='0x': return None
    try: b=bytes.fromhex(h[2:])
    except Exception: return None
    if len(b)>=64:
        try:
            if int.from_bytes(b[:32],'big')==32:
                ln=int.from_bytes(b[32:64],'big')
                if 0<ln<=256 and len(b)>=64+ln:
                    s=b[64:64+ln].decode('utf-8','replace').strip('\x00').strip()
                    return s or None
        except Exception: pass
    if len(b)==32:
        s=b.rstrip(b'\x00').decode('utf-8','replace').strip()
        return s or None
    return None
def dec_int(h):
    try: return int(h,16)
    except Exception: return None
def work(group):
    batch=[];meta=[]
    def add(m,p,tag):
        batch.append({'jsonrpc':'2.0','id':len(batch),'method':m,'params':p}); meta.append(tag)
    for a in group:
        add('eth_getCode',[a,'latest'],(a,'code'))
        for k,s in SEL.items(): add('eth_call',[{'to':a,'data':s},'latest'],(a,k))
        add('eth_getTransactionCount',[a,'latest'],(a,'nonce'))
        add('eth_getBalance',[a,'latest'],(a,'bal'))
    add('eth_getCode',[CANARY,'latest'],('__canary__','code'))
    by=send(batch)
    d={a:{'ok':False} for a in group}
    if by is None: return d
    canary_id=len(batch)-1
    if not (by.get(canary_id) and by[canary_id]!='0x'):
        with lock: stats['canary_fail']+=1
        return d
    for i,(a,k) in enumerate(meta):
        if a=='__canary__': continue
        v=by.get(i)
        if v is None: continue
        e=d[a]
        if k=='code': e['has_code']=(v!='0x'); e['code_len']=(len(v)-2)//2; e['ok']=True
        elif k in ('name','symbol'): e[k]=dec_str(v)
        elif k=='decimals': e['decimals']=dec_int(v)
        elif k=='totalSupply': e['supply']=dec_int(v)
        elif k=='owner':
            iv=dec_int(v); e['owner']=('0x%040x'%iv) if iv is not None else None
        elif k=='nonce': e['nonce']=dec_int(v)
        elif k=='bal': e['bal']=dec_int(v)
    return d
out={}
groups=[addrs[i:i+15] for i in range(0,len(addrs),15)]
done=0
with ThreadPoolExecutor(5) as ex:
    for d in ex.map(work,groups):
        out.update(d); done+=len(d)
        if done%300<15: print(done,stats,flush=True)
bad=[a for a,v in out.items() if not v.get('ok')]
print('unresolved after retries:',len(bad))
if bad:
    for a in bad:
        d=work([a]); out.update(d)
    print('still unresolved:',sum(1 for a,v in out.items() if not v.get('ok')))
json.dump(out,open(D/'onchain.json','w'))
hc=sum(1 for v in out.values() if v.get('has_code')); tok=sum(1 for v in out.values() if v.get('symbol'))
print('TOTAL',len(out),'has_code',hc,'with symbol',tok,'stats',stats)
