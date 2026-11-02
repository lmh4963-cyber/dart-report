"""재무분석 HTML 대시보드 — 한 파일 (Pretendard, 정수 pt, 개조식). 5개년/10개년 전환, 분기·동종업체·거시지표 섹션은 데이터 있을 때만."""
from __future__ import annotations

import json
from datetime import date

from .peers import PEER_METRICS
from .quarter import bs_rows, quarter_rows

KEYS = ["revenue", "cogs", "gross", "sga", "op", "ni", "ni_owner", "assets", "liabilities", "equity", "cash_like", "borrowings", "net_debt",
        "inventories", "receivables", "ocf", "icf", "fcf_fin", "capex", "fcf", "dividends_paid", "eps",
        "gpm", "opm", "npm", "roe", "roa", "debt_ratio", "current_ratio", "equity_ratio", "rev_growth", "op_growth", "payout", "ocf_to_op"]

_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{--navy:#00338D;--lblue:#0091DA;--org:#ED7D31;--red:#C00000;--ink:#1a1a1a;--sub:#666;--line:#e3e6ea;--bg:#f6f7f9;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Pretendard,"Pretendard Variable",-apple-system,"맑은 고딕",sans-serif;font-size:11pt;line-height:1.5}
.wrap{max-width:1200px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:20pt;margin:0 0 4px;color:var(--navy)}
h2{font-size:14pt;margin:32px 0 12px;color:var(--navy);border-bottom:2px solid var(--navy);padding-bottom:4px;display:flex;justify-content:space-between;align-items:flex-end;gap:8px;flex-wrap:wrap}
h3{font-size:11pt;margin:0 0 6px}
.meta,.note{font-size:9pt;color:var(--sub)}
.note{margin:6px 0 0}
.est{display:inline-block;font-size:9pt;font-weight:700;color:var(--org);border:1px solid var(--org);border-radius:4px;padding:0 6px;margin-left:6px;vertical-align:middle}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-width:0}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(170px,100%),1fr));gap:12px}
.kpi .t{font-size:9pt;color:var(--sub)}
.kpi .v{font-size:20pt;font-weight:800;color:var(--navy);line-height:1.2}
.kpi .d{font-size:9pt;color:var(--sub)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(360px,100%),1fr));gap:12px}
.chart svg{width:100%;height:auto;max-height:260px;display:block}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:9pt;color:var(--sub);margin-bottom:4px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
ul.k{margin:0;padding-left:18px;font-size:10pt}
ul.k li{margin:2px 0}
table{border-collapse:collapse;width:100%;background:var(--card);font-size:10pt}
th{background:var(--navy);color:#fff;font-weight:700;font-size:10pt;padding:6px 8px;text-align:center;white-space:nowrap}
td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}
td.l{text-align:left}
tr.key td{background:#e6f3fb;font-weight:700}
tr.sec td{background:#f2f2f2;font-weight:700;text-align:left;color:var(--navy)}
td.main{background:#e6f3fb;font-weight:700}
.scroll{overflow-x:auto}
.up{color:var(--red)}.down{color:var(--navy)}
.seg{display:inline-flex;border:1px solid var(--navy);border-radius:6px;overflow:hidden}
.seg button{font:inherit;font-size:10pt;border:0;background:#fff;color:var(--navy);padding:4px 12px;cursor:pointer}
.seg button.on{background:var(--navy);color:#fff}
input[type=number]{width:90px;font:inherit;font-size:10pt;padding:3px 6px;border:1px solid #c9ced6;border-radius:4px;text-align:right}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
.row>div{flex:1 1 min(420px,100%);min-width:0}
</style>
</head>
<body>
<div class="wrap">
  <h1 id="ttl"></h1>
  <div class="meta" id="meta"></div>

  <h2>1. 핵심 지표 <span class="meta" id="kfy"></span></h2>
  <div class="kpi" id="kpi"></div>
  <div class="card" style="margin-top:12px"><h3>핵심 코멘트</h3><ul class="k" id="cmt"></ul></div>

  <h2><span>2. 재무 추이</span><span class="seg" id="seg"></span></h2>
  <div class="grid" id="charts"></div>
  <p class="note">단위 억원 · 비율 % · 현금흐름은 전체 재무제표 공시 연도만 표시 (요약 API 연도는 공백)</p>

  <h2>3. 재무 요약표</h2>
  <div class="scroll"><table id="tbl"></table></div>

  <section id="qsec"></section>
  <section id="psec"></section>
  <section id="msec"></section>

  <h2>출처 · 산식</h2>
  <ul class="k" id="src"></ul>
</div>
<script>
const D = __DATA__;
const C = {navy:"#00338D", lblue:"#0091DA", org:"#ED7D31", red:"#C00000", gray:"#9aa3ad"};
const $ = s => document.querySelector(s);
const nz = (v,d) => Math.abs(v)<0.5*Math.pow(10,-d)?0:v;
const f = (v,d=0) => v==null||isNaN(v) ? "-" : nz(v,d).toLocaleString("ko-KR",{minimumFractionDigits:d,maximumFractionDigits:d});
const eok = v => v==null ? null : v/1e8;
const pct = (v,d=1) => v==null ? "-" : f(v*100,d)+"%";
const sg = (v,d=1) => v==null ? "-" : (v>=0?"+":"")+f(v*100,d)+"%";
const pp = (v,d=1) => v==null ? "-" : (v>=0?"+":"")+f(v*100,d)+"%p";
const cls = v => v==null?"":v>0?"up":v<0?"down":"";
const esc = s => String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const Y = D.years, R = D.rows, last = Y[Y.length-1], prev = Y[Y.length-2];

$("#ttl").textContent = `${D.meta.corp_name} 재무분석 대시보드`;
document.title = `${D.meta.corp_name} 재무분석`;
$("#meta").textContent = `${D.meta.stock_code||"비상장"} · ${D.meta.market||""} · ${D.meta.fs_label} 기준 · FY${Y[0]}~FY${last} · 출처 OpenDART 사업보고서 · 생성일 ${D.generated}` + (D.offline ? " · 오프라인 픽스처" : "");
$("#kfy").textContent = `FY${last} · 전년 대비`;

// 1. KPI
const r = R[last]||{}, p = R[prev]||{};
const kpis = [
  ["매출액", f(eok(r.revenue))+"억", `전년 ${sg(r.rev_growth)} · CAGR ${sg(D.summary.rev_cagr)}`],
  ["영업이익", f(eok(r.op))+"억", `영업이익률 ${pct(r.opm)} (전년 ${pct(p.opm)})`],
  ["ROE", pct(r.roe), `ROA ${pct(r.roa)}`],
  [r.net_debt!=null&&r.net_debt<0 ? "순현금" : "순차입금", r.net_debt==null ? "-" : f(Math.abs(eok(r.net_debt)))+"억", `부채비율 ${pct(r.debt_ratio,0)} · 유동비율 ${pct(r.current_ratio,0)}`],
  ["FCF", r.fcf==null ? "-" : f(eok(r.fcf))+"억", `영업CF ${r.ocf==null?"-":f(eok(r.ocf))+"억"} · CAPEX ${r.capex==null?"-":f(eok(r.capex))+"억"}`],
];
$("#kpi").innerHTML = kpis.map(k=>`<div class="card"><div class="t">${k[0]}</div><div class="v">${k[1]}</div><div class="d">${k[2]}</div></div>`).join("");
$("#cmt").innerHTML = D.comments.map(c=>`<li>${esc(c)}</li>`).join("");

// 차트 공통
function axis(lo,hi){ if(lo===hi){lo-=1;hi+=1} const span=hi-lo, step=Math.pow(10,Math.floor(Math.log10(span/4))); const m=[1,2,2.5,5,10].find(m=>span/(m*step)<=5)*step; return {lo:Math.floor(lo/m)*m, hi:Math.ceil(hi/m)*m, step:m}; }
function svgChart(cats, series, o={}){
  const W=420,H=200,P={l:46,r:10,t:10,b:22}, n=cats.length, iw=W-P.l-P.r, ih=H-P.t-P.b;
  const all=series.flatMap(s=>s.values).filter(v=>v!=null);
  if(!all.length) return `<svg viewBox="0 0 ${W} ${H}"><text x="${W/2}" y="${H/2}" text-anchor="middle" font-size="12" fill="#999">데이터 없음</text></svg>`;
  const bars=o.type==="bar", ax=axis(Math.min(bars?0:Infinity,...all), Math.max(bars?0:-Infinity,...all));
  const ys=v=>P.t+ih*(1-(v-ax.lo)/(ax.hi-ax.lo)), bw=iw/n;
  let g="";
  for(let v=ax.lo; v<=ax.hi+1e-9; v+=ax.step) g+=`<line x1="${P.l}" x2="${W-P.r}" y1="${ys(v)}" y2="${ys(v)}" stroke="${Math.abs(v)<1e-9?"#b8bec6":"#eceef1"}"/><text x="${P.l-4}" y="${ys(v)+4}" font-size="10" text-anchor="end" fill="#888">${o.pct?f(v*100,0)+"%":f(v,0)}</text>`;
  const every=Math.ceil(n/10);
  cats.forEach((c,k)=>{ if(k%every===0||k===n-1) g+=`<text x="${P.l+bw*(k+.5)}" y="${H-6}" font-size="10" text-anchor="middle" fill="#888">${c}</text>`; });
  if(bars){
    const gw=bw*0.72, sw=gw/series.length;
    series.forEach((s,j)=>s.values.forEach((v,k)=>{ if(v==null) return; const x=P.l+bw*k+(bw-gw)/2+sw*j, y0=ys(0), y1=ys(v);
      g+=`<rect x="${x.toFixed(1)}" y="${Math.min(y0,y1).toFixed(1)}" width="${Math.max(sw-1,1).toFixed(1)}" height="${Math.max(Math.abs(y1-y0),0.5).toFixed(1)}" fill="${s.color}"><title>${s.name} ${cats[k]}: ${o.pct?pct(v):f(v)}</title></rect>`; }));
  } else {
    series.forEach(s=>{ let d="",pen=false; s.values.forEach((v,k)=>{ if(v==null){pen=false;return} const x=P.l+bw*(k+.5); d+=(pen?"L":"M")+x.toFixed(1)+","+ys(v).toFixed(1); pen=true; });
      g+=`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" ${s.dash?'stroke-dasharray="5 3"':''}/>`;
      s.values.forEach((v,k)=>{ if(v!=null) g+=`<circle cx="${P.l+bw*(k+.5)}" cy="${ys(v)}" r="2.5" fill="${s.color}"><title>${s.name} ${cats[k]}: ${o.pct?pct(v):f(v)}</title></circle>`; }); });
  }
  return `<svg viewBox="0 0 ${W} ${H}">${g}</svg>`;
}
const legend = ss => `<div class="legend">${ss.map(s=>`<span><i style="background:${s.color}"></i>${s.name}</span>`).join("")}</div>`;
function card(title, cats, series, o){ return `<div class="card chart"><h3>${title}</h3>${legend(series)}${svgChart(cats,series,o)}</div>`; }

// 2. 추이 (5/10개년)
const spans = [5,10].filter(n=>n<Y.length).concat([Y.length]).filter((v,i,a)=>a.indexOf(v)===i);
let span = Math.min(5, Y.length);
try { const s=+localStorage.getItem("dart_span"); if(spans.includes(s)) span=s; } catch(e){}
function drawCharts(){
  $("#seg").innerHTML = spans.length>1 ? spans.map(n=>`<button class="${n===span?"on":""}" data-n="${n}">${n}개년</button>`).join("") : "";
  document.querySelectorAll("#seg button").forEach(b=>b.onclick=()=>{ span=+b.dataset.n; try{localStorage.setItem("dart_span",span)}catch(e){} drawCharts(); drawTable(); });
  const ys=Y.slice(-span), cats=ys.map(y=>"'"+String(y).slice(2)), v=k=>ys.map(y=>R[y]?.[k]??null), ve=k=>v(k).map(eok);
  $("#charts").innerHTML = [
    card("매출액 · 영업이익 · 순이익 (억원)", cats, [{name:"매출액",color:C.navy,values:ve("revenue")},{name:"영업이익",color:C.lblue,values:ve("op")},{name:"당기순이익",color:C.org,values:ve("ni")}], {type:"bar"}),
    card("수익성 (%)", cats, [{name:"매출총이익률",color:C.navy,values:v("gpm")},{name:"영업이익률",color:C.lblue,values:v("opm")},{name:"순이익률",color:C.org,values:v("npm")}], {pct:true}),
    card("자본효율 (%)", cats, [{name:"ROE",color:C.navy,values:v("roe")},{name:"ROA",color:C.org,values:v("roa")}], {pct:true}),
    card("안정성 (%)", cats, [{name:"부채비율",color:C.red,values:v("debt_ratio")},{name:"유동비율",color:C.lblue,values:v("current_ratio")}], {pct:true}),
    card("현금흐름 (억원)", cats, [{name:"영업CF",color:C.navy,values:ve("ocf")},{name:"CAPEX",color:C.org,values:ve("capex")},{name:"FCF",color:C.lblue,values:ve("fcf")}], {type:"bar"}),
    card("재무구조 (억원)", cats, [{name:"자산총계",color:C.navy,values:ve("assets")},{name:"부채총계",color:C.red,values:ve("liabilities")},{name:"자본총계",color:C.lblue,values:ve("equity")}], {type:"bar"}),
  ].join("");
}

// 3. 요약표
const TROWS = [["손익",null],["매출액","revenue","amt",1],["매출원가","cogs","amt"],["매출총이익","gross","amt"],["영업이익","op","amt",1],["당기순이익","ni","amt",1],["매출 증가율","rev_growth","pct"],["영업이익률","opm","pct"],["순이익률","npm","pct"],
  ["재무상태",null],["자산총계","assets","amt",1],["부채총계","liabilities","amt"],["자본총계","equity","amt"],["순차입금(−=순현금)","net_debt","amt"],["부채비율","debt_ratio","pct0"],["유동비율","current_ratio","pct0"],["ROE","roe","pct"],
  ["현금흐름",null],["영업활동현금흐름","ocf","amt",1],["CAPEX","capex","amt"],["FCF","fcf","amt"],["배당금 지급","dividends_paid","amt"]];
function drawTable(){
  const ys=Y.slice(-span);
  $("#tbl").innerHTML = `<thead><tr><th>항목</th>${ys.map(y=>`<th>FY${y}</th>`).join("")}</tr></thead><tbody>` + TROWS.map(([l,k,t,key])=>{
    if(!k) return `<tr class="sec"><td colspan="${ys.length+1}">${l}</td></tr>`;
    return `<tr class="${key?"key":""}"><td class="l">${l}</td>${ys.map(y=>{const x=R[y]?.[k]; return `<td>${x==null?"-":t==="amt"?f(eok(x)):t==="pct0"?pct(x,0):pct(x)}</td>`}).join("")}</tr>`;
  }).join("") + "</tbody>";
}
drawCharts(); drawTable();

// 4. 분기
if(D.quarter){
  const q=D.quarter, yy=q.year;
  const vv=(r,v)=>r.kind==="amt"?f(eok(v),1):pct(v);
  const ch=(r,v)=>r.kind==="amt"?`<span class="${cls(v)}">${sg(v)}</span>`:`<span class="${cls(v)}">${pp(v)}</span>`;
  $("#qsec").innerHTML = `<h2>4. ${yy}년 ${q.label} 실적 <span class="meta">${q.fs_label} · 누적 ${q.months}개월 · 접수번호 ${q.rcept_no||"-"}</span></h2>
  <div class="row"><div style="flex:1.5 1 min(640px,100%)"><div class="scroll"><table><thead><tr><th>항목 (억원)</th><th>${yy} 누적</th><th>${yy-1} 누적</th><th>증감</th><th>${yy} 해당분기</th><th>${yy-1} 해당분기</th><th>증감</th></tr></thead><tbody>
  ${q.rows.map(r=>`<tr class="${["매출액","영업이익"].includes(r.label)?"key":""}"><td class="l">${r.label}</td><td>${vv(r,r.cum)}</td><td>${vv(r,r.cum_prev)}</td><td>${ch(r,r.cum_yoy)}</td><td>${r.q==null?"-":vv(r,r.q)}</td><td>${r.q_prev==null?"-":vv(r,r.q_prev)}</td><td>${r.q==null?"-":ch(r,r.q_yoy)}</td></tr>`).join("")}
  </tbody></table></div><p class="note">현금흐름은 누적만 공시 · 비율 증감 %p</p></div>
  <div><div class="scroll"><table><thead><tr><th>재무상태</th><th>${yy} ${q.label}말</th><th>${yy-1}말</th><th>증감</th></tr></thead><tbody>
  ${q.bs.map(r=>`<tr><td class="l">${r.label}</td><td>${r.kind==="amt"?f(eok(r.cur),1):pct(r.cur,0)}</td><td>${r.kind==="amt"?f(eok(r.prev),1):pct(r.prev,0)}</td><td>${r.kind==="amt"?f(eok(r.chg),1):pp(r.chg)}</td></tr>`).join("")}
  </tbody></table></div></div></div>
  <div class="grid" style="margin-top:12px">${card(`${q.label} 누적 vs 전년 동기 (억원)`, ["매출액","영업이익","순이익"], [{name:`${yy-1}`,color:C.gray,values:q.rows.slice(0,4).filter(r=>r.label!=="매출총이익").map(r=>eok(r.cum_prev))},{name:`${yy}`,color:C.navy,values:q.rows.slice(0,4).filter(r=>r.label!=="매출총이익").map(r=>eok(r.cum))}], {type:"bar"})}</div>`;
}

// 5. 동종업체
if(D.peers && D.peers.length>1){
  const P=D.peers, num=(m,v)=>m[2]==="amt"?f(eok(v)):m[2]==="pct"&&["debt_ratio","current_ratio"].includes(m[1])?pct(v,0):pct(v);
  const bar=(title,k,isPct)=>`<div class="card chart"><h3>${title}</h3>${svgChart(P.map(p=>p.name), [{name:title,color:C.lblue,values:P.map(p=>isPct?p.values[k]:eok(p.values[k]))}], {type:"bar",pct:isPct})}</div>`;
  $("#psec").innerHTML = `<h2>5. 동종업체 비교 <span class="meta">FY${P[0].fy} · 사용자 지정 비교군</span></h2>
  <div class="scroll"><table><thead><tr><th>항목</th>${P.map(p=>`<th>${esc(p.name)}<br><span style="font-weight:400;font-size:9pt">${p.stock_code||"비상장"} · ${p.fs_label}</span></th>`).join("")}</tr></thead><tbody>
  ${D.peer_metrics.map(m=>`<tr><td class="l">${m[0]}</td>${P.map(p=>`<td class="${p.main?"main":""}">${num(m,p.values[m[1]])}</td>`).join("")}</tr>`).join("")}
  </tbody></table></div><p class="note">파란 칸 = 분석 대상 · 매출 CAGR(2개년) = FY-2 → FY · 연결·별도 기준이 회사마다 다를 수 있음</p>
  <div class="grid" style="margin-top:12px">${bar("매출액 (억원)","revenue",false)}${bar("영업이익률","opm",true)}${bar("ROE","roe",true)}${bar("부채비율","debt_ratio",true)}</div>`;
}

// 6. 거시지표 연결
if(D.macro){
  const M=D.macro, ys=M.years;
  let coefs={}; try{coefs=JSON.parse(localStorage.getItem("dart_macro_coef")||"{}")}catch(e){}
  M.drivers.forEach(d=>{ if(coefs[d.key]==null) coefs[d.key]=d.coef; });
  const baseCogs=(ys.find(e=>e.year===M.base_year)||{}).cogs;
  function drawMacro(){
    let tot=0, any=false;
    const rows=M.drivers.map(d=>{ const v=d.delta==null?null:d.delta*(coefs[d.key]||0); if(v!=null){tot+=v;any=true}
      return `<tr><td class="l">${d.label}</td><td><input type="number" step="0.1" data-k="${d.key}" value="${coefs[d.key]}"></td><td>${f(d.delta,1)}</td><td class="${cls(v)}">${v==null?"-":f(v,1)}</td></tr>`}).join("");
    $("#mimp").innerHTML = rows + `<tr class="key"><td class="l">합계<span class="est">추정</span></td><td></td><td></td><td class="${cls(tot)}">${any?f(tot,1):"-"}</td></tr>` +
      (baseCogs&&any ? `<tr><td class="l">FY${M.base_year} 매출원가 대비</td><td></td><td></td><td>${pct(tot/eok(baseCogs),2)}</td></tr>` : "");
    document.querySelectorAll("#mimp input").forEach(el=>el.onchange=()=>{coefs[el.dataset.k]=parseFloat(el.value)||0; try{localStorage.setItem("dart_macro_coef",JSON.stringify(coefs))}catch(e){} drawMacro();});
  }
  const cats=ys.map(e=>"'"+String(e.year).slice(2));
  $("#msec").innerHTML = `<h2>6. 원가 × 거시지표 <span class="meta">${esc(M.file)} (macro_dash · 한국은행 ECOS)</span></h2>
  <div class="scroll"><table><thead><tr><th>항목</th>${ys.map(e=>`<th>FY${e.year}</th>`).join("")}</tr></thead><tbody>
  <tr class="key"><td class="l">매출원가 (억원)</td>${ys.map(e=>`<td>${f(eok(e.cogs))}</td>`).join("")}</tr>
  <tr class="key"><td class="l">매출원가율</td>${ys.map(e=>`<td>${pct(e.cogs_ratio)}</td>`).join("")}</tr>
  ${M.present.map(k=>`<tr><td class="l">${M.names[k]}</td>${ys.map(e=>{const m=e.macro[k]; return `<td>${m.avg==null?"-":f(m.avg,1)+(m.months<12?"*":"")}</td>`}).join("")}</tr>`).join("")}
  </tbody></table></div><p class="note">* 12개월 미만 평균 · 상관·회귀 분석 아님 (연도별 수치 병치)</p>
  <div class="row" style="margin-top:12px"><div>
    <h3>민감도 — FY${M.base_year??"-"} 연평균 vs 전년<span class="est">추정</span></h3>
    <div class="scroll"><table><thead><tr><th>동인</th><th>계수 (억원/단위·연)</th><th>전년비 변화(단위)</th><th>원가 영향 (억원)</th></tr></thead><tbody id="mimp"></tbody></table></div>
    <p class="note">계수 = 동인 1단위 ↑ 시 연간 원가 증가액 · 사용자 입력 (수입 비중·헤지 반영) · 브라우저에 저장</p>
  </div></div>
  <div class="grid" style="margin-top:12px">${card("매출원가율 (%)", cats, [{name:"매출원가율",color:C.navy,values:ys.map(e=>e.cogs_ratio)}], {pct:true})}${M.present.includes("usdkrw")?card("원/달러 연평균 (원)", cats, [{name:"원/달러",color:C.org,values:ys.map(e=>e.macro.usdkrw.avg)}], {}):""}</div>`;
  drawMacro();
}

// 출처
$("#src").innerHTML = [
  `재무: OpenDART 사업보고서 전체 재무제표(fnlttSinglAcntAll)·주요계정(fnlttSinglAcnt), ${D.meta.fs_label} 기준 · 접수번호 ${(D.meta.rcept_nos||[]).slice(0,6).join(", ")||"-"}`,
  D.quarter ? `분기: ${D.quarter.year}년 ${D.quarter.label}보고서 (접수번호 ${D.quarter.rcept_no||"-"})` : null,
  D.peers && D.peers.length>1 ? `동종업체: ${D.peers.filter(p=>!p.main).map(p=>p.name).join(", ")} — 사용자 지정, 사업보고서 주요계정` : null,
  D.macro ? `거시지표: ${D.macro.file} (macro_dash 출력, 한국은행 ECOS) — 원가 영향은 사용자 계수 기반 추정` : null,
  "ROE·ROA = 지배주주순이익 ÷ 평균 자본·자산 · 순차입금 = 차입금+사채 − 현금성자산 − 단기금융상품 · FCF = 영업CF − (유형+무형 취득)",
  "공시값 그대로 사용 · 추정 항목은 '추정' 표기 · 기업 판단·투자 권유 아님",
].filter(Boolean).map(t=>`<li>${esc(t)}</li>`).join("");
</script>
</body>
</html>
"""


def build_html(meta: dict, table: dict, comments: list[str], extras: dict, out_path: str, offline: bool = False) -> str:
    ys = table["summary"]["years"]
    data = {
        "meta": {k: meta.get(k) for k in ("corp_name", "stock_code", "market", "fs_label", "rcept_nos")},
        "years": ys,
        "rows": {y: {k: table["rows"][y].get(k) for k in KEYS} for y in ys},
        "summary": {k: v for k, v in table["summary"].items() if k != "years"},
        "comments": comments, "generated": date.today().isoformat(), "offline": offline,
        "quarter": None, "peers": extras.get("peers") or None, "macro": extras.get("macro") or None,
        "peer_metrics": PEER_METRICS,
    }
    q = extras.get("quarter")
    if q:
        data["quarter"] = {k: q[k] for k in ("year", "label", "months", "fs_label", "rcept_no")}
        data["quarter"]["rows"] = quarter_rows(q)
        data["quarter"]["bs"] = bs_rows(q)
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = _TEMPLATE.replace("__DATA__", payload).replace("__TITLE__", f"{meta.get('corp_name', '')} 재무분석")
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html)
    return out_path
