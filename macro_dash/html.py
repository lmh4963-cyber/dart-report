"""의사결정 지원 대시보드 — HTML 한 파일 (Pretendard, 정수 pt, 개조식). 데이터는 페이지에 내장, 계수·룰 편집은 브라우저에서 즉시 재계산."""
from __future__ import annotations

import json

PALETTE = {"NAVY": "#00338D", "LBLUE": "#0091DA", "ORG": "#ED7D31", "RED": "#C00000"}

_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>거시지표 대시보드</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{--navy:#00338D;--lblue:#0091DA;--org:#ED7D31;--red:#C00000;--ink:#1a1a1a;--sub:#666;--line:#e3e6ea;--bg:#f6f7f9;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Pretendard,"Pretendard Variable",-apple-system,"맑은 고딕",sans-serif;font-size:11pt;line-height:1.5}
.wrap{max-width:1200px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:20pt;margin:0 0 4px;color:var(--navy)}
h2{font-size:14pt;margin:32px 0 12px;color:var(--navy);border-bottom:2px solid var(--navy);padding-bottom:4px}
.meta{font-size:9pt;color:var(--sub)}
.note{font-size:9pt;color:var(--sub);margin:6px 0 0}
.est{display:inline-block;font-size:9pt;font-weight:700;color:var(--org);border:1px solid var(--org);border-radius:4px;padding:0 6px;margin-left:6px;vertical-align:middle}
.sig{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.sig .t{font-size:10pt;color:var(--sub)}
.sig .s{font-size:20pt;font-weight:800;margin:2px 0}
.sig .d{font-size:9pt;color:var(--sub)}
.up{color:var(--red)}.down{color:var(--navy)}.flat{color:var(--lblue)}.na{color:var(--sub)}
.lamp{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:middle}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr));gap:12px}
.ch .hd{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.ch .nm{font-size:11pt;font-weight:700}
.ch .v{font-size:14pt;font-weight:800;color:var(--navy)}
.ch .cg{font-size:9pt;color:var(--sub)}
.ch svg{width:100%;height:150px;display:block;margin-top:6px}
table{border-collapse:collapse;width:100%;background:var(--card);font-size:10pt}
th{background:var(--navy);color:#fff;font-weight:700;font-size:10pt;padding:6px 8px;text-align:center;white-space:nowrap}
td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}
td.l{text-align:left}
tr.hl td{background:#e6f3fb;font-weight:700}
.scroll{overflow-x:auto}
input[type=number]{width:90px;font:inherit;font-size:10pt;padding:3px 6px;border:1px solid #c9ced6;border-radius:4px;text-align:right}
input.w{width:64px}
button{font:inherit;font-size:10pt;background:var(--navy);color:#fff;border:0;border-radius:6px;padding:6px 14px;cursor:pointer}
button.ghost{background:#fff;color:var(--navy);border:1px solid var(--navy)}
.row{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}
.row>div{flex:1 1 min(360px,100%);min-width:0}
ul.k{margin:6px 0 0;padding-left:18px;font-size:10pt}
a{color:var(--lblue)}
</style>
</head>
<body>
<div class="wrap">
  <h1>거시지표 대시보드 — 원자재·환율·금리 국면</h1>
  <div class="meta" id="meta"></div>
  <ul class="k">
    <li>목적: 가격 예측이 아닌 국면 판정·민감도 표시 → 구매·재고 의사결정 보조</li>
    <li>판정: 3개월 이동평균 vs 12개월 이동평균 (금리 ±__RT__%p, 환율·지수 ±__PT__% 초과 시 상승/하락)</li>
    <li>원가 영향·권장 커버리지는 사용자 입력 계수·룰 기반 <b>추정</b>치</li>
  </ul>

  <h2>1. 국면 신호등</h2>
  <div class="sig" id="sig"></div>

  <h2>2. 지표별 추이 (최근 __N__개월)</h2>
  <div class="grid" id="charts"></div>
  <p class="note">증감: 전월·전년 동월 대비 (금리는 %p, 그 외 %) · 점선: 12개월 이동평균</p>

  <h2>3. 민감도 시트<span class="est">추정</span></h2>
  <div class="row">
    <div>
      <div class="scroll"><table id="coefT"><thead><tr><th>동인</th><th>계수 (억원/단위)</th><th>전년비 변화(단위)</th><th>최근월 영향</th></tr></thead><tbody></tbody></table></div>
      <p class="note">계수 = "동인 1단위 ↑ 시 월 원가 증가액(억원)" · 사용자 입력 · 브라우저에 저장</p>
    </div>
    <div>
      <div class="scroll"><table id="impT"><thead></thead><tbody></tbody></table></div>
      <p class="note">월별 원가 영향(추정) = Σ 계수 × 전년 동월 대비 동인 변화 · 양수 = 원가 증가</p>
    </div>
  </div>

  <h2>4. 권장 재고 커버리지<span class="est">추정</span></h2>
  <div class="row">
    <div>
      <div class="scroll"><table id="covT"><thead><tr><th>변동성 하한(%)</th><th>상한(%)</th><th>커버리지(주)</th><th>비고</th></tr></thead><tbody></tbody></table></div>
      <p class="note">변동성 = 수입물가(원재료) 최근 12개월 월간 변화율 표준편차 · 룰은 예시 기준, 사용자 편집</p>
    </div>
    <div class="card">
      <div class="t" style="font-size:10pt;color:var(--sub)">현재 원자재 변동성</div>
      <div style="font-size:20pt;font-weight:800;color:var(--navy)" id="vol"></div>
      <div style="font-size:10pt;margin-top:6px">권장 커버리지 <b id="wk" style="font-size:14pt;color:var(--org)"></b><span class="est">추정</span></div>
      <div class="note" id="wkn"></div>
    </div>
  </div>

  <h2>5. 내보내기 · 출처</h2>
  <div class="row" style="align-items:center">
    <div style="flex:0 0 auto"><button onclick="dlCSV()">데이터 CSV 다운로드</button> <button class="ghost" onclick="resetInputs()">입력값 초기화</button></div>
    <div class="note" style="flex:1 1 auto">엑셀(맑은 고딕): 같은 폴더의 <b>__XLSX__</b> · 계수·룰 셀 수정 시 엑셀 수식으로 재계산</div>
  </div>
  <div class="scroll" style="margin-top:12px"><table id="srcT"><thead><tr><th>지표</th><th>통계표</th><th>항목</th><th>단위</th><th>최근 기준월</th></tr></thead><tbody></tbody></table></div>
  <p class="note" id="src"></p>
</div>
<script>
const D = __DATA__;
const C = {navy:"#00338D", lblue:"#0091DA", org:"#ED7D31", red:"#C00000"};
const LS = "macro_dash_inputs_v1";
const $ = s => document.querySelector(s);
const ymL = ym => ym ? ym.slice(0,4)+"."+ym.slice(4,6) : "-";
const f = (v,d=1) => v==null||isNaN(v) ? "-" : (Math.abs(v)<0.5*Math.pow(10,-d)?0:v).toLocaleString("ko-KR",{minimumFractionDigits:d,maximumFractionDigits:d});
const fc = (v,kind) => v==null ? "-" : (kind==="rate" ? (v>=0?"+":"")+f(v,2)+"%p" : (v>=0?"+":"")+f(v*100,1)+"%");
const cls = s => s==="상승"?"up":s==="하락"?"down":s==="안정"?"flat":"na";
const lampC = s => s==="상승"?C.red:s==="하락"?C.navy:s==="안정"?C.lblue:"#bbb";
const byKey = Object.fromEntries(D.indicators.map(i=>[i.key,i]));

$("#meta").textContent = `기준월 ${ymL(D.end)} · 생성일 ${D.generated} · 출처 ${D.source_label}` + (D.sample ? " · ※ 오프라인 예시 데이터 (실제값 아님)" : "");

// 1. 신호등
$("#sig").innerHTML = D.signals.map(s => {
  const i = byKey[s.key];
  const gap = s.gap==null ? "-" : (i.kind==="rate" ? (s.gap>=0?"+":"")+f(s.gap,2)+"%p" : (s.gap>=0?"+":"")+f(s.gap*100,1)+"%");
  return `<div class="card"><div class="t">${s.title} · ${s.name}</div>
    <div class="s ${cls(s.state)}"><span class="lamp" style="background:${lampC(s.state)}"></span>${s.state}</div>
    <div class="d">3M 평균 ${f(s.ma3,2)} vs 12M 평균 ${f(s.ma12,2)} (${gap})</div></div>`;
}).join("");

// 2. 차트 (단일 축)
function chart(i){
  const W=340,H=150,P={l:44,r:8,t:8,b:20};
  const vals=i.values, n=vals.length, xs=k=>P.l+(W-P.l-P.r)*k/Math.max(n-1,1);
  const ok=vals.filter(v=>v!=null); if(!ok.length) return `<svg viewBox="0 0 ${W} ${H}"><text x="10" y="70" font-size="12" fill="#999">데이터 없음</text></svg>`;
  let lo=Math.min(...ok), hi=Math.max(...ok); if(lo===hi){lo-=1;hi+=1} const pad=(hi-lo)*0.08; lo-=pad; hi+=pad;
  const ys=v=>P.t+(H-P.t-P.b)*(1-(v-lo)/(hi-lo));
  const path=arr=>{let d="",pen=false;arr.forEach((v,k)=>{if(v==null){pen=false;return}d+=(pen?"L":"M")+xs(k).toFixed(1)+","+ys(v).toFixed(1);pen=true});return d};
  const ma=vals.map((_,k)=>{if(k<11)return null;const w=vals.slice(k-11,k+1);return w.some(v=>v==null)?null:w.reduce((a,b)=>a+b,0)/12});
  const ticks=[lo+pad,(lo+hi)/2,hi-pad].map(v=>`<line x1="${P.l}" x2="${W-P.r}" y1="${ys(v)}" y2="${ys(v)}" stroke="#eceef1"/><text x="${P.l-4}" y="${ys(v)+4}" font-size="10" text-anchor="end" fill="#888">${f(v,i.kind==="rate"?2:0)}</text>`).join("");
  const xl=[[0,"start"],[Math.floor((n-1)/2),"middle"],[n-1,"end"]].map(([k,an])=>`<text x="${xs(k)}" y="${H-4}" font-size="10" text-anchor="${an}" fill="#888">${ymL(D.months[k])}</text>`).join("");
  const li=vals.map((v,k)=>v!=null?k:-1).filter(k=>k>=0).pop();
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${ticks}${xl}
    <path d="${path(ma)}" fill="none" stroke="${C.org}" stroke-width="1.5" stroke-dasharray="4 3"/>
    <path d="${path(vals)}" fill="none" stroke="${C.navy}" stroke-width="2"/>
    ${li!=null?`<circle cx="${xs(li)}" cy="${ys(vals[li])}" r="3" fill="${C.navy}"/>`:""}</svg>`;
}
$("#charts").innerHTML = D.indicators.map(i=>`<div class="card ch"><div class="hd"><span class="nm">${i.name} <span class="${cls(i.regime.state)}" style="font-size:9pt">● ${i.regime.state}</span></span><span class="v">${f(i.last,i.kind==="rate"?2:1)}<span class="cg"> ${i.unit||""}</span></span></div>
  <div class="cg">${ymL(i.last_ym)} · 전월 ${fc(i.mom,i.kind)} · 전년 ${fc(i.yoy,i.kind)}</div>${chart(i)}</div>`).join("");

// 저장된 입력
let saved={}; try{ saved=JSON.parse(localStorage.getItem(LS)||"{}") }catch(e){}
const coefs = Object.fromEntries(D.drivers.map(d=>[d.key, saved.coefs?.[d.key] ?? d.coef]));
let rules = saved.rules || D.coverage_rules.map(r=>({...r}));
const save=()=>{ try{ localStorage.setItem(LS, JSON.stringify({coefs, rules})) }catch(e){} };
function resetInputs(){ try{localStorage.removeItem(LS)}catch(e){} D.drivers.forEach(d=>coefs[d.key]=d.coef); rules=D.coverage_rules.map(r=>({...r})); drawCoef(); drawCov(); }

// 3. 민감도
function delta(key, ym, step){
  const i=byKey[key]; if(!i) return null; const k=D.months.indexOf(ym); if(k<12) return null;
  const a=i.values[k], b=i.values[k-12]; if(a==null||b==null) return null;
  return i.kind==="fx" ? (a-b)/step : (b? (a/b-1)*100/step : null);
}
const impMonths = D.months.slice(-12);
function drawCoef(){
  $("#coefT tbody").innerHTML = D.drivers.map(d=>{
    const last=impMonths[impMonths.length-1], dl=delta(d.key,last,d.step);
    return `<tr><td class="l">${d.label}</td><td><input type="number" step="0.1" data-k="${d.key}" value="${coefs[d.key]}"></td><td>${f(dl,1)}</td><td>${dl==null?"-":f(dl*coefs[d.key],1)+"억"}</td></tr>`}).join("");
  document.querySelectorAll("#coefT input").forEach(el=>el.oninput=()=>{coefs[el.dataset.k]=parseFloat(el.value)||0; save(); drawImp(); const tr=el.closest("tr"); const d=D.drivers.find(x=>x.key===el.dataset.k); const dl=delta(d.key,impMonths[impMonths.length-1],d.step); tr.cells[3].textContent=dl==null?"-":f(dl*coefs[d.key],1)+"억";});
  drawImp();
}
function drawImp(){
  $("#impT thead").innerHTML = `<tr><th>월</th>${D.drivers.map(d=>`<th>${byKey[d.key]?.name||d.key}</th>`).join("")}<th>합계(추정, 억원)</th></tr>`;
  $("#impT tbody").innerHTML = impMonths.map(ym=>{
    let tot=0, any=false;
    const cells=D.drivers.map(d=>{const dl=delta(d.key,ym,d.step); if(dl==null) return "<td>-</td>"; const v=dl*coefs[d.key]; tot+=v; any=true; return `<td>${f(v,1)}</td>`}).join("");
    return `<tr><td class="l">${ymL(ym)}</td>${cells}<td class="${any&&tot>0?"up":any&&tot<0?"down":""}"><b>${any?f(tot,1):"-"}</b></td></tr>`}).join("");
}
drawCoef();

// 4. 커버리지
function pick(v){ if(v==null) return null; return rules.find(r=>v>=r.lo && (r.hi==null||r.hi===""||v<r.hi)) || rules[rules.length-1]; }
function drawCov(){
  const cur=pick(D.volatility);
  $("#covT tbody").innerHTML = rules.map((r,k)=>`<tr class="${r===cur?"hl":""}"><td><input class="w" type="number" step="0.5" data-k="${k}" data-f="lo" value="${r.lo}"></td><td><input class="w" type="number" step="0.5" data-k="${k}" data-f="hi" value="${r.hi??""}"></td><td><input class="w" type="number" step="1" data-k="${k}" data-f="weeks" value="${r.weeks}"></td><td class="l">${r.note||""}</td></tr>`).join("");
  document.querySelectorAll("#covT input").forEach(el=>el.onchange=()=>{const r=rules[+el.dataset.k]; const v=el.value===""?null:parseFloat(el.value); r[el.dataset.f]=el.dataset.f==="weeks"?Math.round(v||0):v; save(); drawCov();});
  $("#vol").textContent = D.volatility==null ? "-" : f(D.volatility,1)+"%";
  $("#wk").textContent = cur ? cur.weeks+"주" : "-";
  $("#wkn").textContent = cur ? `${cur.note||""} · 구간 ${cur.lo}~${cur.hi??"∞"}%` : "변동성 산출 불가 (데이터 부족)";
}
drawCov();

// 5. 출처·CSV
$("#srcT tbody").innerHTML = D.indicators.map(i=>`<tr><td class="l">${i.name}</td><td class="l">${i.source?.stat||"-"} ${i.source?.stat_name||""}</td><td class="l">${(i.source?.items||[]).join(" · ")}</td><td class="l">${i.unit||""}</td><td>${ymL(i.last_ym)}</td></tr>`).join("");
$("#src").textContent = `출처: ${D.source_label} · 기준일 ${D.generated} · 원자재 외부 CSV: ${D.extra_label||"없음"}`;
function dlCSV(){
  const head=["월",...D.indicators.map(i=>i.name)];
  const rows=D.months.map((m,k)=>[m,...D.indicators.map(i=>i.values[k]??"")]);
  const csv="﻿"+[head,...rows].map(r=>r.join(",")).join("\n");
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"})); a.download=`거시지표_${D.end}.csv`; a.click();
}
</script>
</body>
</html>
"""


def build_html(dash: dict, out_path: str, xlsx_name: str) -> None:
    payload = json.dumps(dash, ensure_ascii=False).replace("</", "<\\/")
    th = dash["thresholds"]
    html = (_TEMPLATE.replace("__DATA__", payload).replace("__N__", str(len(dash["months"])))
            .replace("__XLSX__", xlsx_name).replace("__RT__", f"{th['rate']:.2f}").replace("__PT__", f"{th['index'] * 100:.0f}"))
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html)
