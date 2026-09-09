const VD=[{k:'有真实产品',d:'官网能看到可用的应用、文档、合约或代码',c:'var(--v0)',bg:'var(--v0bg)'},
 {k:'普通/正常',d:'站点存在且与简介一致，但只是常规 meme、藏品或落地页',c:'var(--v1)',bg:'var(--v1bg)'},
 {k:'空洞',d:'即将上线、模板站、空壳或链接已失效',c:'var(--v2)',bg:'var(--v2bg)'},
 {k:'骗局信号',d:'冒用品牌、保证收益、伪造数据或连钱包领奖',c:'var(--v3)',bg:'var(--v3bg)'}];
const SS=['正常','JS 空壳','403/404','域名失败','5xx'];
const MT=['相符','部分','不符','无法核实'];
const TOK=['未发币','已发币','地址不存在','疑似已发'];
const SRCLBL={bio:'简介',site:'官网',tweet:'推文'};
const CV=[{t:'—',d:'简介与官网都没有出现合约地址'},
 {t:'符号一致',d:'链上 symbol() 与简介自称的代币符号一致'},
 {t:'合约存在',d:'地址在链上是一个可读的代币合约'},
 {t:'合约存在(非代币)',d:'地址有合约代码但不是标准 ERC-20'},
 {t:'符号不符',d:'链上 symbol() 与简介自称的符号对不上'},
 {t:'在其他链',d:'地址不在 Robinhood 链，而在 Base / 以太坊 / BSC'},
 {t:'是钱包非合约',d:'地址有交易记录但没有合约代码'},
 {t:'链上不存在',d:'八条链都查不到，地址从未被使用'}];
const CATS=DATA.cats;
function weekOf(dt){const d=new Date(dt.replace(' ','T')+':00');const wd=(d.getDay()+6)%7;
 const m=new Date(d.getFullYear(),d.getMonth(),d.getDate()-wd);
 return m.getFullYear()+'-'+String(m.getMonth()+1).padStart(2,'0')+'-'+String(m.getDate()).padStart(2,'0');}
const R=DATA.rows.map(r=>({u:r[0],n:r[1],g:r[2],d:r[3],fo:r[4],site:r[5],ss:r[6],vd:r[7],mt:r[8],
 cat:CATS[r[9]],ci:r[9],su:r[10],no:r[11],tok:r[12],cv:r[13],ca:r[14],sym:r[15],own:r[16],ch:r[17],ren:r[18],age:r[19],src:r[20]||'',twc:r[21]===1,wk:weekOf(r[3])}));
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let fv=null,fc=null,fw=null,page=0,sortK='vd',sortD=1;
const PER=150,$=id=>document.getElementById(id);

const counts=[0,0,0,0]; R.forEach(r=>counts[r.vd]++);
(function coverage(){
 const el=document.getElementById('cover'); if(!el)return;
 const none=R.filter(r=>r.tok===0), read=none.filter(r=>r.twc).length;
 const pct=Math.round(read/Math.max(1,none.length)*100);
 el.innerHTML='标为未发币的 <b>'+none.length+'</b> 个账号里，已逐条读过推文的有 <b>'+read+'</b> 个（'+pct+'%）。'
  +'剩下 <b>'+(none.length-read)+'</b> 个的推文还没读完，它们的“未发币”可能不准，正在后台按每小时约 200 个补齐。'
  +'下面的快捷视角默认只算已读的那部分。';
 const bar=document.getElementById('coverbar'); if(bar) bar.style.width=pct+'%';
})();
$('vbar').innerHTML=VD.map((v,i)=>`<button data-v="${i}" style="flex:${counts[i]};background:${v.c}" title="${v.k} ${counts[i]}" aria-label="${v.k} ${counts[i]} 个"><\/button>`).join('');
$('vlegend').innerHTML=VD.map((v,i)=>`<div><div class="k"><span class="dot" style="background:${v.c}"><\/span>${v.k}<\/div><div class="n" style="color:${v.c}">${counts[i]}<\/div><div class="d">${v.d}<\/div><\/div>`).join('');
const byCat=CATS.map((c,i)=>{const m=[0,0,0,0];let t=0;R.forEach(r=>{if(r.ci===i){m[r.vd]++;t++}});return{c,i,m,t}}).sort((a,b)=>b.t-a.t);
$('cats').innerHTML=byCat.map(x=>`<button class="crow" data-c="${x.i}"><span class="cn">${esc(x.c)}<\/span>
 <span class="mini">${x.m.map((n,j)=>n?`<i style="flex:${n};background:${VD[j].c}" title="${VD[j].k} ${n}"><\/i>`:'').join('')}<\/span>
 <span class="ct">${x.t}<\/span><\/button>`).join('');

// creation-time histogram
const HIST=DATA.hist, maxW=Math.max(...HIST.map(h=>h[1]+h[2]+h[3]+h[4]));
$('hist').innerHTML=HIST.map(h=>{const tot=h[1]+h[2]+h[3]+h[4];
 const hp=Math.max(3,Math.round(tot/maxW*100));
 return `<button class="hcol" data-w="${h[0]}" title="${h[0]} 当周新建 ${tot} 个 · 有真实产品 ${h[1]} · 骗局信号 ${h[4]}" aria-label="${h[0]} 当周 ${tot} 个账号" style="height:${hp}%">`
 +[1,2,3,4].map(i=>h[i]?`<i style="flex:${h[i]};background:${VD[i-1].c}"><\/i>`:'').join('')+'<\/button>'}).join('');
$('hax').innerHTML=HIST.map((h,i)=>`<span>${i%2===0?h[0].slice(5).replace('-','/'):''}<\/span>`).join('');
$('hnote').textContent='最早 '+HIST[0][0]+'，最晚 '+HIST[HIST.length-1][0]+' 当周；8 月最后一周新建 '+(HIST[12][1]+HIST[12][2]+HIST[12][3]+HIST[12][4])+' 个，是整段时间里最密集的一周。';


/* ---------- 隐藏（本机） / 剔除（记入名单） ---------- */
const HKEY='rh.hidden.v1', DKEY='rh.dropped.v1', RKEY='rh.restored.v1', DOC='research/excluded';
let hidden=new Set(), dropped=new Map();      // username -> {r:reason, t:isoDate, by:who}
// the repo's data/excluded.json, baked in at build time — everyone sees the same baseline
const SHARED=new Map(Object.entries((typeof SHARED_EXCLUDED!=='undefined'&&SHARED_EXCLUDED.items)||{}));
const isShared=u=>SHARED.has(u);
let dbRef=null, dbReady=false, saveTimer=null;
function lsGet(k){try{const v=localStorage.getItem(k);return v?JSON.parse(v):null}catch(e){return null}}
function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
(function loadLocal(){
  const h=lsGet(HKEY); if(Array.isArray(h)) hidden=new Set(h);
  const d=lsGet(DKEY); if(d&&typeof d==='object') dropped=new Map(Object.entries(d));
  const restored=lsGet(RKEY)||[];              // shared entries this viewer put back
  const back=new Set(restored);
  SHARED.forEach((v,k)=>{ if(!dropped.has(k)&&!back.has(k)) dropped.set(k,{...v,shared:true}); });
})();
function dropObj(){const o={};dropped.forEach((v,k)=>{if(!v.shared)o[k]=v});return o}
function sharedRestored(){const a=[];SHARED.forEach((v,k)=>{if(!dropped.has(k))a.push(k)});return a}
function persist(){
  lsSet(HKEY,[...hidden]); lsSet(DKEY,dropObj()); lsSet(RKEY,sharedRestored());
  if(!dbReady||!dbRef) return;
  clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>{
    dbRef.doc(DOC).set({items:dropObj(),updatedAt:new Date().toISOString()})
      .then(()=>setDbStatus('ok'))
      .catch(e=>setDbStatus('err',e&&e.code));
  },500);
}
function setDbStatus(kind,code){
  const el=$('dbst'); if(!el) return;
  if(kind==='ok') el.textContent='名单存储：已同步到云端';
  else if(kind==='local') el.textContent='名单：团队 '+SHARED.size+' 条（仓库） + 本机改动';
  else if(kind==='saving') el.textContent='名单存储：保存中…';
  else el.textContent='名单存储：云端写入失败（'+(code||'未知')+'），已留在本机';
}
setDbStatus('local');
if(window.claude&&typeof window.claude.use==='function'){
  window.claude.use('db').then(db=>{
    if(!db){setDbStatus('local');return}
    dbRef=db; dbReady=true;
    let firstSync=true;
    db.doc(DOC).onSnapshot(snap=>{
      const it=snap.exists?((snap.data()||{}).items):null;
      if(it&&typeof it==='object'){
        const server=new Map(Object.entries(it));
        if(firstSync){
          // first delivery: local entries made before the store loaded are additions
          let added=false;
          dropped.forEach((v,k)=>{if(!server.has(k)){server.set(k,v);added=true}});
          dropped=server; lsSet(DKEY,dropObj());
          if(added) persist();
        } else {
          dropped=server; lsSet(DKEY,dropObj());   // server is authoritative afterwards
        }
        render();
      } else if(firstSync && dropped.size){ persist(); }
      firstSync=false;
      setDbStatus('ok');
    },e=>setDbStatus('err',e&&e.code));
  }).catch(()=>setDbStatus('local'));
}
/* toast */
let toastTimer=null;
function toast(msg,actions){
  const old=document.querySelector('.toast'); if(old)old.remove();
  clearTimeout(toastTimer);
  const t=document.createElement('div'); t.className='toast'; t.setAttribute('role','status');
  t.innerHTML='<span>'+esc(msg)+'<\/span>';
  (actions||[]).forEach(a=>{const b=document.createElement('button');b.textContent=a.label;
    b.onclick=()=>{a.fn();t.remove()};t.appendChild(b)});
  const c=document.createElement('button'); c.className='cls'; c.textContent='×'; c.title='关闭';
  c.onclick=()=>t.remove(); t.appendChild(c);
  document.body.appendChild(t);
  toastTimer=setTimeout(()=>t.remove(),7000);
}
function hideOne(u,name){
  hidden.add(u); persist(); render();
  toast('已隐藏 '+name+'（仅本机）',[{label:'撤销',fn:()=>{hidden.delete(u);persist();render()}}]);
}
function dropOne(u,name,reason){
  dropped.set(u,{r:reason||'',t:new Date().toISOString().slice(0,10)}); persist(); render();
  toast('已剔除 '+name,[
    {label:'撤销',fn:()=>{dropped.delete(u);persist();render()}},
    {label:'加原因',fn:()=>openManage(u)}
  ]);
}

let preset='all';
const PRESETS={
 all:()=>true,
 gem:r=>r.tok===0&&r.vd===0&&r.twc,       // tweets read: the label is trustworthy
 gemall:r=>r.tok===0&&r.vd===0,
 pro:r=>r.vd===0,
 nocoin:r=>r.tok===0&&r.twc,
 nocoinall:r=>r.tok===0,
 scam:r=>r.vd===3,
 badca:r=>r.cv===4||r.cv===6||r.cv===7||r.tok===2
};
function cur(){
 const q=$('q').value.trim().toLowerCase(),fs=$('fs').value,fm=$('fm').value,ft=$('ft').value,fg=$('fv').value;
 const showDrop=$('showDropped').checked;
 return R.filter(r=>!hidden.has(r.u)&&(showDrop||!dropped.has(r.u))&&PRESETS[preset](r)&&(fv===null||r.vd===fv)&&(fc===null||r.ci===fc)&&(fw===null||r.wk===fw)
  &&(fs===''||r.ss===+fs)&&(fm===''||r.mt===+fm)&&(ft===''||(ft==='0c'?(r.tok===0&&r.twc):r.tok===+ft))&&(fg===''||r.g===1)
  &&(!q||(r.n+' @'+r.u+' '+r.su+' '+r.no+' '+r.site+' '+r.ca+' '+r.sym).toLowerCase().includes(q)));
}
function sorted(rows){
 const s=rows.slice();
 s.sort((a,b)=>{
  let x,y;
  if(sortK==='nm'){x=a.n.toLowerCase();y=b.n.toLowerCase()}
  else if(sortK==='su'){x=a.su;y=b.su}
  else if(sortK==='cat'){x=a.cat;y=b.cat}
  else{x=a[sortK];y=b[sortK]}
  if(x<y)return -sortD; if(x>y)return sortD;
  return b.fo-a.fo;
 });
 return s;
}
function render(){
 const rows=sorted(cur());
 const pages=Math.max(1,Math.ceil(rows.length/PER));
 if(page>=pages)page=pages-1;
 const slice=rows.slice(page*PER,page*PER+PER);
 $('cnt').textContent=rows.length.toLocaleString()+' / '+R.length.toLocaleString()+' 个账号';
 $('nHide').textContent=hidden.size; $('nDrop').textContent=dropped.size;
 $('unhideAll').disabled=hidden.size===0; $('manage').disabled=dropped.size===0;
 document.querySelectorAll('#presets button').forEach(b=>{
  const f=PRESETS[b.dataset.p], n=R.filter(r=>!hidden.has(r.u)&&!dropped.has(r.u)&&f(r)).length;
  const t=b.querySelector('b'); if(t)t.textContent=n;
 });
 $('empty').hidden=rows.length>0;
 $('tb').innerHTML=slice.map(r=>{
  const host=r.site?r.site.replace(/^https?:\/\//,'').replace(/\/$/,''):'';
  const cvi=CV[r.cv];
  let ca='<span class="ca">—<\/span>';
  if(r.ca){
   const short=r.ca.slice(0,6)+'…'+r.ca.slice(-4);
   const ex=r.ch?'':'https://robinscan.io/address/'+r.ca;
   ca=`<span class="ca">${ex?`<a href="${ex}" target="_blank" rel="noopener" title="${esc(r.ca)}">${short}<\/a>`:`<span title="${esc(r.ca)}">${short}<\/span>`}${r.sym?' <b style="color:var(--muted);font-weight:500">'+esc(r.sym)+'<\/b>':''}${r.ch?' <i style="font-style:normal;color:var(--v2)">'+esc(r.ch)+'<\/i>':''}<\/span>`;
  }
  const isDrop=dropped.has(r.u);
  return `<tr class="${isDrop?'dim':''}">
  <td class="act"><button class="h" data-u="${esc(r.u)}" title="隐藏（仅本机）" aria-label="隐藏 ${esc(r.n||r.u)}">◎<\/button><button class="x" data-u="${esc(r.u)}" title="${isDrop?'恢复':'剔除（记入名单）'}" aria-label="${isDrop?'恢复':'剔除'} ${esc(r.n||r.u)}">${isDrop?'↩':'✕'}<\/button><\/td>
  <td><span class="vp" style="color:${VD[r.vd].c};background:${VD[r.vd].bg}">${VD[r.vd].k}<\/span><\/td>
  <td class="nm"><a href="https://x.com/${esc(r.u)}" target="_blank" rel="noopener">${esc(r.n)||'@'+esc(r.u)}<\/a>${r.g?'<span class="gold">GOLD<\/span>':''}<span class="hd">@${esc(r.u)}<\/span><\/td>
  <td class="mono">${esc(r.cat)}<\/td>
  <td class="num">${r.fo.toLocaleString()}<\/td>
  <td class="dcell"><b>${esc(r.d.slice(0,10))}<\/b><span>${esc(r.d.slice(11))} · ${r.age} 天前<\/span><\/td>
  <td><span class="ss s${r.ss}">${SS[r.ss]}<\/span><\/td>
  <td><span class="mt m${r.mt}">${MT[r.mt]}<\/span><\/td>
  <td><span class="tok t${r.tok}">${TOK[r.tok]}<\/span><\/td>
  <td><span class="cv c${r.cv}" title="${esc(cvi.d)}">${cvi.t}<\/span><\/td>
  <td>${ca}<\/td>
  <td class="st">${host?`<a href="${esc(r.site)}" target="_blank" rel="noopener nofollow">${esc(host.length>30?host.slice(0,29)+'…':host)}<\/a>`:'<span>—<\/span>'}<\/td>
  <td class="su">${esc(r.su)}<\/td>
  <td class="no">${esc(r.no)}<\/td><\/tr>`}).join('');
 $('pg').innerHTML=pages>1?`<button id="pp" ${page===0?'disabled':''}>← 上一页<\/button>
  <span class="info">第 ${page+1} / ${pages} 页<\/span>
  <button id="pn" ${page>=pages-1?'disabled':''}>下一页 →<\/button>`:'';
 const jump=()=>window.scrollTo({top:document.querySelector('.tw').offsetTop-70,behavior:'smooth'});
 if(pages>1){$('pp').onclick=()=>{page--;render();jump()};$('pn').onclick=()=>{page++;render();jump()}}
 document.querySelectorAll('#vbar button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.v===fv)));
 document.querySelectorAll('.crow').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.c===fc)));
 document.querySelectorAll('.hcol').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.w===fw)));
 document.querySelectorAll('#presets button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.p===preset)));
 document.querySelectorAll('th[data-k]').forEach(th=>{const on=th.dataset.k===sortK;th.classList.toggle('on',on);th.classList.toggle('asc',on&&sortD===1)});
}
$('tb').onclick=e=>{
 const b=e.target.closest('button[data-u]'); if(!b)return;
 const u=b.dataset.u, row=R.find(x=>x.u===u); if(!row)return;
 const nm=row.n||('@'+row.u);
 if(b.classList.contains('h')) hideOne(u,nm);
 else if(dropped.has(u)){dropped.delete(u);persist();render();toast('已恢复 '+nm)}
 else dropOne(u,nm,'');
};
$('vbar').onclick=e=>{const b=e.target.closest('button');if(!b)return;const v=+b.dataset.v;fv=fv===v?null:v;page=0;render()};
$('hist').onclick=e=>{const b=e.target.closest('.hcol');if(!b)return;const w=b.dataset.w;fw=fw===w?null:w;page=0;render()};
$('cats').onclick=e=>{const b=e.target.closest('.crow');if(!b)return;const c=+b.dataset.c;fc=fc===c?null:c;page=0;render()};
$('presets').onclick=e=>{const b=e.target.closest('button');if(!b)return;preset=b.dataset.p;fv=null;fc=null;page=0;
 fw=null;
 if(preset==='gem'||preset==='nocoin'){sortK='d';sortD=-1;$('so').value='d-new'}
 render()};
document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
 const k=th.dataset.k;
 if(sortK===k)sortD=-sortD;else{sortK=k;sortD=(k==='fo'||k==='d')?-1:1}
 $('so').value=(k==='d')?(sortD===-1?'d-new':'d-old'):(k==='fo'?'fo':(k==='vd'?'vd':''));
 page=0;render()});
$('so').onchange=()=>{const v=$('so').value;
 if(v==='d-new'){sortK='d';sortD=-1}else if(v==='d-old'){sortK='d';sortD=1}
 else if(v==='fo'){sortK='fo';sortD=-1}else{sortK='vd';sortD=1}
 page=0;render()};
['q','fs','fm','ft','fv'].forEach(id=>$(id).addEventListener('input',()=>{page=0;render()}));
$('reset').onclick=()=>{fv=null;fc=null;fw=null;preset='all';page=0;
 ['q','fs','fm','ft','fv'].forEach(id=>$(id).value='');$('showDropped').checked=false;$('so').value='vd';sortK='vd';sortD=1;render()};
$('showDropped').onchange=()=>{page=0;render()};
$('unhideAll').onclick=()=>{const n=hidden.size;hidden.clear();persist();render();toast('已恢复 '+n+' 个隐藏项')};
$('dropFiltered').onclick=()=>{
 const rows=cur().filter(r=>!dropped.has(r.u));
 if(!rows.length){toast('当前筛选结果为空');return}
 if(!confirm('把当前筛选出的 '+rows.length+' 个项目全部剔除？\n可在“管理名单”里恢复。'))return;
 const today=new Date().toISOString().slice(0,10);
 rows.forEach(r=>dropped.set(r.u,{r:'批量剔除',t:today}));
 persist();render();
 toast('已剔除 '+rows.length+' 个项目',[{label:'撤销',fn:()=>{rows.forEach(r=>dropped.delete(r.u));persist();render()}}]);
};
const CHIPS=['已归零','已跑路','长期无进展','与主题无关','重复项目','已发币不看'];
function openManage(focusU){
 const mask=document.createElement('div'); mask.className='mask';
 const items=[...dropped.entries()].sort((a,b)=>(b[1].t||'').localeCompare(a[1].t||''));
 mask.innerHTML=`<div class="panel" role="dialog" aria-modal="true" aria-label="已剔除名单">
  <header><h3>已剔除名单<\/h3><span class="lbl" style="font-size:12px;color:var(--muted)">${items.length} 个项目 · 可随时恢复<\/span><button class="close" aria-label="关闭">×<\/button><\/header>
  <div class="body">${items.length?items.map(([u,v])=>{
    const r=R.find(x=>x.u===u)||{n:u,u};
    return `<div class="xrow" data-u="${esc(u)}">
     <div class="who"><a href="https://x.com/${esc(u)}" target="_blank" rel="noopener">${esc(r.n||u)}<\/a><span>@${esc(u)} · ${esc(v.t||'')}<\/span><\/div>
     <input value="${esc(v.r||'')}" placeholder="剔除原因（可留空）" aria-label="剔除原因">
     <button class="rs">恢复<\/button><\/div>`}).join(''):'<div class="pempty">名单是空的。<\/div>'}<\/div>
  <div class="foot"><button class="copy">复制名单<\/button><button class="clr">全部恢复<\/button>
   <span style="margin-left:auto;font-size:12px;color:var(--muted)">改动即时保存<\/span><\/div><\/div>`;
 document.body.appendChild(mask);
 const close=()=>{mask.remove();document.removeEventListener('keydown',onKey)};
 const onKey=e=>{if(e.key==='Escape')close()};
 document.addEventListener('keydown',onKey);
 mask.onclick=e=>{if(e.target===mask)close()};
 mask.querySelector('.close').onclick=close;
 mask.querySelectorAll('.xrow').forEach(row=>{
  const u=row.dataset.u;
  row.querySelector('input').oninput=e=>{const v=dropped.get(u)||{t:''};v.r=e.target.value.slice(0,80);dropped.set(u,v);persist()};
  row.querySelector('.rs').onclick=()=>{dropped.delete(u);persist();row.remove();render();
   if(!dropped.size){close();toast('名单已清空')}};
 });
 mask.querySelector('.clr').onclick=()=>{if(!confirm('恢复全部 '+dropped.size+' 个已剔除项目？\n团队名单里的项目只在本机恢复，仓库不受影响。'))return;
  const n=dropped.size;dropped.clear();persist();render();close();toast('已恢复 '+n+' 个项目')};
 mask.querySelector('.copy').onclick=()=>{
  const obj={}; dropped.forEach((v,k)=>{obj[k]={r:v.r||'',t:v.t||'',by:v.by||'me'}});
  const txt=JSON.stringify({items:obj},null,1);
  navigator.clipboard.writeText(txt).then(
   ()=>toast('已复制为 data/excluded.json 的格式，提交到仓库即可共享给团队'),
   ()=>toast('复制失败，请手动选取'));
 };
 if(focusU){const el=mask.querySelector('.xrow[data-u="'+focusU+'"] input');if(el){el.focus();el.select()}}
}
$('manage').onclick=()=>openManage();
const TOKN=['未发币','已发币','地址不存在','疑似已发'];
$('exportCsv').onclick=async()=>{
 const rows=sorted(cur());
 if(!rows.length){toast('当前列表为空，没有可导出的内容');return}
 const head=['项目','X账号','X主页','建号时间','粉丝','赛道','判定','官网状态','与简介','发币','合约核验','合约地址','代币符号','官网','做什么','核验依据'];
 const q=v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"';
 const body=rows.map(r=>[r.n,'@'+r.u,'https://x.com/'+r.u,r.d,r.fo,r.cat,VD[r.vd].k,SS[r.ss],MT[r.mt],
   TOKN[r.tok],CV[r.cv].t,r.ca,r.sym,r.site,r.su,r.no].map(q).join(','));
 const csv='﻿'+head.map(q).join(',')+'\n'+body.join('\n');
 const dl=(window.claude&&window.claude.use)?await window.claude.use('downloads').catch(()=>null):null;
 if(dl){
  try{ await dl.save({filename:'robinhood-chain-projects.csv',data:csv}); toast('已导出 '+rows.length+' 行'); }
  catch(e){ const c=e&&e.code;
   if(c==='declined') return;
   navigator.clipboard.writeText(csv).then(()=>toast('导出被拒绝，已改为复制到剪贴板'),()=>toast('导出失败：'+(c||'未知')));
  }
 } else {
  navigator.clipboard.writeText(csv).then(()=>toast('已复制 '+rows.length+' 行 CSV 到剪贴板'),()=>toast('无法导出，请手动选取表格'));
 }
};

render();
