"""거시지표 의사결정 대시보드 — 참고 양식(docs/DASHBOARD_STYLE.md) · dashkit 공통 CSS/JS.
구성: 상단 · 국면 신호등(레일) · 슬라이서 · 지표별 추이 · 원가 민감도(추정) · 재고 커버리지(추정) · 요약 · 데이터 표 · 출처."""
from __future__ import annotations

from dashkit import page

BODY = r"""
<header class="top"><div class="top-in">
  <div class="ident"><h1>거시지표 대시보드</h1><span class="ticker" id="tick"></span><span class="cos">원자재 · 환율 · 금리 국면 · 구매·재고 의사결정 보조</span></div>
  <div class="top-note"><span id="asof"></span><button class="tbtn" id="themeBtn" type="button">다크 모드</button></div>
</div></header>
<main class="wrap">
  <h2 class="sec">국면 신호등<small>3개월 vs 12개월 이동평균 · 가격 예측 아님</small></h2>
  <p class="seclead" id="lead"></p>
  <div class="rail" id="rail"></div>

  <h2 class="sec">지표별 추이<small>그룹·기간을 고르면 아래 차트와 표가 함께 바뀜</small></h2>
  <section class="slicer">
    <div class="srow"><span class="sname">지표 그룹</span><div class="chips" id="grpChips"></div></div>
    <div class="srow"><span class="sname">표시 기간</span><div class="seg" id="spanSeg"></div>
      <span class="sname" style="margin-left:12px">기준선</span><div class="seg" id="maSeg"></div>
      <div class="sright"><button class="tbtn" id="resetBtn" type="button">초기화</button></div></div>
    <div class="srow foot" id="slFoot"></div>
  </section>
  <div class="grid g3" id="charts"></div>

  <h2 class="sec">원가 민감도<span class="est">추정</span><small>계수 입력 → 월별 원가 영향 · 전년 동월 대비</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">계수 입력</h3><span class="p-unit">억원 / 단위</span></div>
      <div class="p-sub">계수 = 동인 1단위 ↑ 시 월 원가 증가액 · 사용자 입력 · 브라우저 저장</div>
      <div class="tbl-wrap"><table id="coefT"></table></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">월별 원가 영향</h3><span class="p-unit">억원 · 추정</span></div>
      <div class="p-sub">Σ 계수 × 전년 동월 대비 동인 변화 · 양수 = 원가 증가</div><div id="impL"></div><div class="chart" id="impC"></div></section>
    <section class="panel wide"><div class="p-head"><h3 class="p-title">원가 영향 내역</h3><span class="p-unit">억원 · 추정</span></div><div class="p-sub">최근 12개월 · 동인별</div><div class="tbl-wrap"><table id="impT"></table></div></section>
  </div>

  <h2 class="sec">권장 재고 커버리지<span class="est">추정</span><small>원자재 변동성 구간별 룰 · 사용자 편집</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">변동성 구간 룰</h3><span class="p-unit">% · 주</span></div>
      <div class="p-sub">변동성 = 수입물가(원재료) 최근 12개월 월간 변화율 표준편차 · 예시 기준, 회사 리드타임·보관비용에 맞게 수정</div>
      <div class="tbl-wrap"><table id="covT"></table></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">현재 판정</h3><span class="p-unit" id="covYm"></span></div><div class="p-sub">현재 변동성이 속한 구간</div>
      <div class="k-label">원자재 변동성</div><div class="k-val" id="vol" style="font-size:44px"></div>
      <div class="k-label" style="margin-top:18px">권장 커버리지<span class="est">추정</span></div><div class="k-val" id="wk" style="color:var(--accent)"></div>
      <div class="k-sub" id="wkn"></div><div class="chart" id="volC" style="margin-top:12px"></div></section>
  </div>

  <h2 class="sec">요약<small>최근월 국면 사실 정리 · 판단·권유 아님</small></h2>
  <div class="reads" id="reads"></div>

  <h2 class="sec" id="tblTitle">데이터 표</h2>
  <section class="slicer"><div class="srow"><span class="sname">표 설정</span><div class="seg" id="tblSeg"></div>
    <div class="sright"><button class="tbtn" id="csvBtn" type="button">CSV 다운로드</button><button class="tbtn" id="copyBtn" type="button">표 복사</button></div></div>
    <div class="srow foot" id="xlsxNote"></div></section>
  <div class="tbl-wrap"><table id="tbl"></table></div>

  <footer class="notes"><h4>데이터 출처 · 기준</h4><ol id="notes"></ol></footer>
</main>
"""

APP = r"""
const $ = id => document.getElementById(id);
const {num, pct, spct, spp, dir, esc} = K;
const IND = D.indicators, MON = D.months, by = Object.fromEntries(IND.map(i => [i.key, i]));
const GROUPS = [...new Set(IND.map(i => i.group))];
const GCOL = {"금리": "--c1", "환율": "--c3", "물가": "--c4", "경기": "--c2", "원자재(외부)": "--c5"};
const ym = s => s ? s.slice(0, 4) + "." + s.slice(4, 6) : "-";
const st0 = K.store.get("md_state", {});
let span = [12, 24, 36].includes(st0.span) ? Math.min(st0.span, MON.length) : MON.length;
let showMa = st0.ma !== false, tblMode = st0.tbl === "chg" ? "chg" : "val";
let grp = new Set((st0.grp || GROUPS).filter(g => GROUPS.includes(g))); if (!grp.size) grp = new Set(GROUPS);
const save = () => K.store.set("md_state", {span, ma: showMa, grp: [...grp], tbl: tblMode});
const valF = i => v => v == null ? "-" : num(v, i.kind === "rate" ? 2 : 1);
const chgF = (i, v) => v == null ? "-" : i.kind === "rate" ? (v > 0 ? "+" : "") + num(v, 2) + "%p" : spct(v);
const stCls = s => s === "상승" ? "st-up" : s === "하락" ? "st-down" : s === "안정" ? "st-flat" : "st-na";

/* 상단 */
$("tick").textContent = `기준월 ${ym(D.end)}`;
$("asof").textContent = `${D.source_label} · 생성 ${D.generated}` + (D.sample ? " · 예시 데이터 (실제값 아님)" : "");
$("lead").innerHTML = `판정: 3개월 이동평균이 12개월 이동평균 대비 금리 <b>±${num(D.thresholds.rate, 2)}%p</b>, 환율·지수 <b>±${num(D.thresholds.index * 100, 0)}%</b> 초과 시 상승·하락 · 원가 영향·커버리지는 사용자 입력 기반 <b>추정</b>`;
K.theme($("themeBtn"));

/* 레일 */
function renderRail(){
  const lamps = D.signals.map(s => `<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid var(--line-2)">
    <span style="font-size:13px;font-weight:600">${s.title}<span style="color:var(--ink-3);font-weight:500"> · ${esc(s.name)}</span></span><span class="lamp ${stCls(s.state)}" style="font-size:16px">${s.state}</span></div>`).join("");
  const cell = (key, label) => { const i = by[key]; if (!i) return ""; const s = i.regime.state;
    return `<div class="cell"><div class="k-label">${label} · ${ym(i.last_ym)}</div><div class="k-val">${valF(i)(i.last)}<span class="k-unit">${esc(i.unit || "")}</span></div>
      <div class="k-sub">전월 <span class="delta inv ${dir(i.mom)}">${chgF(i, i.mom)}</span> · 전년 <span class="delta inv ${dir(i.yoy)}">${chgF(i, i.yoy)}</span><br><span class="lamp ${stCls(s)}" style="font-size:12px">${s}</span></div>${K.spark(i.values, GCOL[i.group])}</div>`; };
  const cov = D.coverage;
  $("rail").innerHTML = `<div class="cell hero"><div class="k-label">국면 요약 · ${ym(D.end)}</div><div style="margin-top:10px">${lamps}</div>
      <div class="k-sub" style="margin-top:10px">원자재 변동성 <b>${D.volatility == null ? "-" : num(D.volatility, 1) + "%"}</b> → 권장 커버리지 <b>${cov ? cov.weeks + "주" : "-"}</b><span class="est">추정</span></div></div>` +
    cell("ktb3y", "국고채 3년") + cell("usdkrw", "원/달러") + cell("imp_raw", "수입물가(원재료)") + cell("bsi_mfg", "제조업 BSI");
}

/* 슬라이서 */
function renderSlicer(){
  K.chips($("grpChips"), GROUPS.map(g => ({id: g, label: `${g} ${IND.filter(i => i.group === g).length}`, color: GCOL[g] || "--c6"})), grp, s => { grp = s; save(); renderCharts(); renderTable(); });
  K.seg($("spanSeg"), [12, 24, 36].filter(n => n <= MON.length).map(n => [n, `${n}개월`]), span, v => { span = v; save(); renderCharts(); renderTable(); });
  K.seg($("maSeg"), [[true, "12M 이동평균"], [false, "숨김"]], showMa, v => { showMa = v; save(); renderCharts(); });
  $("slFoot").textContent = `기준월 ${ym(D.end)} · 증감은 전월·전년 동월 대비 (금리 %p, 그 외 %) · 단일 축 · 점선 = 12개월 이동평균`;
}
$("resetBtn").onclick = () => { span = MON.length; showMa = true; grp = new Set(GROUPS); save(); renderSlicer(); renderCharts(); renderTable(); };

/* 지표별 */
function ma12(vals){ return vals.map((_, k) => { if (k < 11) return null; const w = vals.slice(k - 11, k + 1); return w.some(v => v == null) ? null : w.reduce((a, b) => a + b, 0) / 12; }); }
function renderCharts(){
  const off = MON.length - span, ms = MON.slice(off), cats = ms.map(m => m.slice(2, 4) + "." + m.slice(4));
  const list = IND.filter(i => grp.has(i.group));
  $("charts").innerHTML = list.map(i => `<section class="panel"><div class="p-head"><h3 class="p-title">${esc(i.name)}</h3><span class="p-unit">${esc(i.unit || "")}</span></div>
    <div class="p-sub"><b>${valF(i)(i.last)}</b> · ${ym(i.last_ym)} · 전월 <span class="delta inv ${dir(i.mom)}">${chgF(i, i.mom)}</span> · 전년 <span class="delta inv ${dir(i.yoy)}">${chgF(i, i.yoy)}</span> · <span class="lamp ${stCls(i.regime.state)}" style="font-size:12px">${i.regime.state}</span></div>
    <div class="chart" id="ch_${i.key}"></div></section>`).join("");
  list.forEach(i => {
    const col = GCOL[i.group] || "--c6", m = ma12(i.values).slice(off);
    K.combo($("ch_" + i.key), {cats, h: 190, l: 44, zero: false, fmt: valF(i),
      series: [{name: i.name, color: col, type: "line", vals: i.values.slice(off)}].concat(showMa ? [{name: "12M 이동평균", color: "--ink-3", type: "line", dash: true, width: 1.6, vals: m}] : [])});
  });
}

/* 민감도 */
const coefs = Object.assign(Object.fromEntries(D.drivers.map(d => [d.key, d.coef])), K.store.get("md_coefs", {}));
const impMonths = MON.slice(-12);
function delta(key, m, step){
  const i = by[key]; if (!i) return null; const k = MON.indexOf(m); if (k < 12) return null;
  const a = i.values[k], b = i.values[k - 12]; if (a == null || b == null) return null;
  return i.kind === "fx" ? (a - b) / step : (b ? (a / b - 1) * 100 / step : null);
}
function renderSens(){
  const drv = D.drivers.filter(d => by[d.key]), last = impMonths[impMonths.length - 1];
  $("coefT").innerHTML = `<thead><tr><th class="lab">동인</th><th>계수</th><th>전년비 변화</th><th>${ym(last)} 영향</th></tr></thead><tbody>` + drv.map(d => {
    const dl = delta(d.key, last, d.step), x = dl == null ? null : dl * (coefs[d.key] || 0);
    return `<tr><td class="lab">${d.label}</td><td><input type="number" step="0.1" data-k="${d.key}" value="${coefs[d.key]}"></td><td>${num(dl, 1)}</td><td><span class="delta inv ${dir(x)}">${x == null ? "-" : num(x, 1)}</span></td></tr>`; }).join("") + "</tbody>";
  $("coefT").querySelectorAll("input").forEach(el => el.onchange = () => { coefs[el.dataset.k] = parseFloat(el.value) || 0; K.store.set("md_coefs", coefs); renderSens(); });
  const parts = drv.map(d => impMonths.map(m => { const dl = delta(d.key, m, d.step); return dl == null ? null : dl * (coefs[d.key] || 0); }));
  const tot = impMonths.map((_, j) => { const v = parts.map(p => p[j]).filter(x => x != null); return v.length ? v.reduce((a, b) => a + b, 0) : null; });
  const cols = ["--c3", "--c2", "--c5", "--c4"];
  const ser = drv.map((d, k) => ({name: by[d.key].name, color: cols[k % 4], vals: parts[k], noLegend: false})).concat([{name: "합계(추정)", color: "--c1", type: "line", vals: tot}]);
  $("impL").innerHTML = K.legend(ser);
  K.combo($("impC"), {cats: impMonths.map(m => m.slice(2, 4) + "." + m.slice(4)), series: ser, fmt: x => num(x, 1), slot: 12, h: 230});
  $("impT").innerHTML = `<thead><tr><th class="lab">월</th>${drv.map(d => `<th>${esc(by[d.key].name)}</th>`).join("")}<th>합계(추정)</th></tr></thead><tbody>` +
    impMonths.map((m, j) => `<tr><td class="lab">${ym(m)}</td>${parts.map(p => `<td>${p[j] == null ? "-" : num(p[j], 1)}</td>`).join("")}<td><span class="delta inv ${dir(tot[j])}"><b>${tot[j] == null ? "-" : num(tot[j], 1)}</b></span></td></tr>`).join("") + "</tbody>";
}

/* 커버리지 */
let rules = K.store.get("md_rules", null) || D.coverage_rules.map(r => ({...r}));
function pick(v){ if (v == null) return null; return rules.find(r => v >= r.lo && (r.hi == null || r.hi === "" || v < r.hi)) || rules[rules.length - 1]; }
function renderCov(){
  const cur = pick(D.volatility);
  $("covT").innerHTML = `<thead><tr><th>하한(%)</th><th>상한(%)</th><th>커버리지(주)</th><th class="lab">비고</th></tr></thead><tbody>` + rules.map((r, k) =>
    `<tr><td class="${r === cur ? "hl-key" : ""}"><input type="number" step="0.5" data-k="${k}" data-f="lo" value="${r.lo}"></td><td class="${r === cur ? "hl-key" : ""}"><input type="number" step="0.5" data-k="${k}" data-f="hi" value="${r.hi ?? ""}"></td>
     <td class="${r === cur ? "hl-key" : ""}"><input type="number" step="1" data-k="${k}" data-f="weeks" value="${r.weeks}"></td><td class="lab" style="font-weight:500">${esc(r.note || "")}</td></tr>`).join("") + "</tbody>";
  $("covT").querySelectorAll("input").forEach(el => el.onchange = () => { const r = rules[+el.dataset.k]; const v = el.value === "" ? null : parseFloat(el.value); r[el.dataset.f] = el.dataset.f === "weeks" ? Math.round(v || 0) : v; K.store.set("md_rules", rules); renderCov(); });
  $("covYm").textContent = `${ym(D.end)} 기준`;
  $("vol").innerHTML = D.volatility == null ? "-" : `${num(D.volatility, 1)}<span class="k-unit">%</span>`;
  $("wk").innerHTML = cur ? `${cur.weeks}<span class="k-unit">주</span>` : "-";
  $("wkn").textContent = cur ? `${cur.note || ""} · 구간 ${cur.lo}~${cur.hi ?? "∞"}%` : "변동성 산출 불가 (데이터 부족)";
  const raw = by.imp_raw;
  if (raw){ const ch = raw.values.map((v, k) => k && v != null && raw.values[k - 1] ? (v / raw.values[k - 1] - 1) : null);
    K.combo($("volC"), {cats: MON.map(m => m.slice(2, 4) + "." + m.slice(4)), series: [{name: "수입물가(원재료) 월간 변화율", color: "--c4", vals: ch}], fmt: x => spct(x), axisPct: true, h: 160, slot: 8}); }
}

/* 요약 */
function renderReads(){
  const F = s => `<span class="fig">${s}</span>`, card = (cls, t, list) => `<div class="read ${cls}"><h3>${t}</h3><ul>${(list.length ? list : ["해당 없음"]).map(x => `<li>${x}</li>`).join("")}</ul></div>`;
  const line = i => `${esc(i.name)} ${F(valF(i)(i.last) + (i.unit ? " " + esc(i.unit) : ""))} · 전년 ${chgF(i, i.yoy)}`;
  $("reads").innerHTML = card("warn", "상승 국면", IND.filter(i => i.regime.state === "상승").map(line)) + card("", "하락 국면", IND.filter(i => i.regime.state === "하락").map(line)) +
    card("note", "안정 · 판정불가", IND.filter(i => !["상승", "하락"].includes(i.regime.state)).map(i => line(i) + (i.regime.state === "판정불가" ? " · 판정불가" : "")));
}

/* 데이터 표 */
function renderTable(){
  K.seg($("tblSeg"), [["val", "값"], ["chg", "값 + 전월비"]], tblMode, v => { tblMode = v; save(); renderTable(); });
  const list = IND.filter(i => grp.has(i.group)), ms = MON.slice(MON.length - span).reverse(), both = tblMode === "chg";
  $("tblTitle").innerHTML = `데이터 표<small>${ym(ms[ms.length - 1])} — ${ym(ms[0])} · 최신순 · 표시 그룹만</small>`;
  $("tbl").innerHTML = `<thead><tr><th class="lab">월</th>${list.map(i => `<th${both ? ' colspan="2"' : ""}>${esc(i.name)}<br><span style="font-weight:500">${esc(i.unit || "")}</span></th>`).join("")}</tr></thead><tbody>` +
    ms.map(m => { const k = MON.indexOf(m); return `<tr><td class="lab">${ym(m)}</td>${list.map(i => { const v = i.values[k], p = i.values[k - 1];
      const c = v == null || p == null ? null : i.kind === "rate" ? v - p : (p ? v / p - 1 : null);
      return `<td>${valF(i)(v)}</td>` + (both ? `<td class="d ${dir(c)}">${c == null ? "" : chgF(i, c)}</td>` : ""); }).join("")}</tr>`; }).join("") + "</tbody>";
}
$("copyBtn").onclick = () => K.copyTable($("tbl"), $("copyBtn"));
$("csvBtn").onclick = () => {
  const csv = "﻿" + [["월", ...IND.map(i => `${i.name}(${i.unit || ""})`)], ...MON.map((m, k) => [m.slice(0, 4) + "-" + m.slice(4), ...IND.map(i => i.values[k] ?? "")])].map(r => r.join(",")).join("\n");
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"})); a.download = `거시지표_${D.end}.csv`; a.click();
};
$("xlsxNote").textContent = `엑셀(맑은 고딕): 같은 폴더의 ${D.xlsx_name} · 민감도·커버리지 노란 셀 수정 시 엑셀 수식으로 재계산`;

/* 출처 */
$("notes").innerHTML = IND.map(i => `${i.name}: ${(i.source || {}).stat || "-"} ${(i.source || {}).stat_name || ""} · ${((i.source || {}).items || []).join(" · ")} · ${i.unit || ""} · 최근 ${ym(i.last_ym)}`)
  .concat([`출처 ${D.source_label} · 기준일 ${D.generated}`, `원자재 외부 CSV: ${D.extra_label || "없음"}`, "국면 = 3개월 vs 12개월 이동평균 · 원가 영향·커버리지 = 사용자 입력 기반 추정 · 판단·권유 아님"])
  .map(t => `<li>${esc(t)}</li>`).join("");

function renderAll(){ renderRail(); renderSlicer(); renderCharts(); renderSens(); renderCov(); renderReads(); renderTable(); }
renderAll();
K.onResize(() => { renderCharts(); renderSens(); renderCov(); });
"""


def build_html(dash: dict, out_path: str, xlsx_name: str) -> None:
    data = {**dash, "xlsx_name": xlsx_name}
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(page(f"거시지표 대시보드 {dash['end'][:4]}.{dash['end'][4:]}", BODY, data, APP))
