import json,subprocess,os,sys,time,re,random
BIRD=_node_bin()
ENV=dict(os.environ); ENV["NODE_USE_ENV_PROXY"]="1"
ENV["PATH"]=str(Path(BIRD).parent)+":"+ENV.get("PATH","")
from pathlib import Path
import shutil

def _node_bin():
    """Find the node/bird install without hardcoding one machine's paths."""
    for c in (os.environ.get("BIRD_BIN"), shutil.which("bird")):
        if c and Path(c).exists():
            return str(Path(c).resolve())
    for p in sorted(Path.home().glob(".nvm/versions/node/*/bin/bird"), reverse=True):
        return str(p)
    return "bird"

ROOT=Path(__file__).resolve().parent.parent; D=ROOT/"data"
(D/"tweets").mkdir(parents=True, exist_ok=True)
OUT=str(D/"tweets/tweets.jsonl"); LOG=str(D/"tweets/progress.log")
COUNT="20"
LOCK = D / "tweets" / ".fetch.lock"

def acquire_lock():
    """Only one reader at a time — two would burn the same rate-limit budget twice."""
    try:
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        return True
    except FileExistsError:
        try:
            pid = int(open(LOCK).read().strip() or 0)
            os.kill(pid, 0)          # raises if the holder is gone
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            LOCK.unlink(missing_ok=True)
            return acquire_lock()

def release_lock():
    LOCK.unlink(missing_ok=True)

def log(m):
    line=time.strftime('%H:%M:%S')+' '+m
    print(line,flush=True)
    with open(LOG,'a') as f: f.write(line+'\n')
if not acquire_lock():
    print("another tweet reader holds the lock; exiting"); sys.exit(0)
import atexit; atexit.register(release_lock)

# resume: keep only successful + permanently-failed(user not found); retry rate/timeout
keep={}
if os.path.exists(OUT):
    for l in open(OUT):
        try:
            r=json.loads(l)
            if r['ok'] or r.get('e')=='notfound': keep[r['u']]=r
        except: pass
    with open(OUT,'w') as f:
        for r in keep.values(): f.write(json.dumps(r,ensure_ascii=False)+'\n')
users=json.load(open(D/'tweets/priority.json'))
todo=[u for u in users if u not in keep]
log(f"resume: have={len(keep)} todo={len(todo)}")
delay=5.0          # seconds between requests, adapts
MIN_D,MAX_D=3.5,14.0
consec_ok=0
MAX_ACCOUNTS=int(os.environ.get("MAX_ACCOUNTS","0")) or len(todo)
todo=todo[:MAX_ACCOUNTS]
log(f"this run will read up to {len(todo)} accounts")
f=open(OUT,'a')
i=0
while i<len(todo):
    u=todo[i]
    try:
        p=subprocess.run([BIRD,"user-tweets",u,"-n",COUNT,"--json","--timeout","45000","--no-color","--no-emoji"],
                         capture_output=True,env=ENV,timeout=120)
        out=p.stdout.decode('utf-8','ignore'); err=p.stderr.decode('utf-8','ignore')
        j=out.find('[')
        if j>=0:
            try:
                arr=json.loads(out[j:])
                rec={'u':u,'ok':True,'n':len(arr),
                     'tw':[{'t':x.get('text',''),'d':x.get('createdAt',''),'q':(x.get('quotedTweet') or {}).get('text','')} for x in arr]}
                f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush()
                i+=1; consec_ok+=1
                if consec_ok>=40 and delay>MIN_D:
                    delay=max(MIN_D,delay*0.85); consec_ok=0; log(f"speed up -> delay={delay:.1f}s")
                time.sleep(delay*random.uniform(0.85,1.15)); continue
            except Exception as e:
                f.write(json.dumps({'u':u,'ok':False,'e':'parse'},ensure_ascii=False)+'\n'); f.flush(); i+=1; continue
        if 'HTTP 429' in err or '429' in err:
            consec_ok=0
            delay=min(MAX_D,max(delay*1.35,6.0))
            log(f"429 on @{u} -> backoff, delay={delay:.1f}s, sleeping 300s")
            time.sleep(300); continue          # retry same user
        if 'not found' in err.lower() or 'suspend' in err.lower() or 'protected' in err.lower():
            f.write(json.dumps({'u':u,'ok':False,'e':'notfound','msg':err.strip()[-140:]},ensure_ascii=False)+'\n'); f.flush()
            i+=1; time.sleep(delay*0.5); continue
        f.write(json.dumps({'u':u,'ok':False,'e':'err','msg':err.strip()[-160:]},ensure_ascii=False)+'\n'); f.flush()
        i+=1; time.sleep(delay); continue
    except subprocess.TimeoutExpired:
        f.write(json.dumps({'u':u,'ok':False,'e':'timeout'},ensure_ascii=False)+'\n'); f.flush(); i+=1; time.sleep(delay); continue
    except Exception as e:
        log('EXC '+str(e)[:80]); time.sleep(10); continue
    finally:
        if i%100==0 and i>0: log(f"progress {i}/{len(todo)} delay={delay:.1f}s")
f.close(); log("FINISHED")
