"""재무분석 HTML 대시보드 — 참고 양식(docs/DASHBOARD_STYLE.md) · dashkit 공통 CSS/JS.
구성: 상단 · 한눈에 보기 · 핵심 지표(슬라이서+레일) · 실적·성장성 · 재무 안정성 · 분기 · 동종업체 · 원가×거시 · 요약 · 재무표 · 출처.
공시값 그대로, 추정은 '추정' 배지."""
from __future__ import annotations

from datetime import date

from dashkit import page

from .peers import PEER_METRICS
from .quarter import bs_rows, quarter_rows

KEYS = ["revenue", "cogs", "gross", "sga", "op", "ni", "ni_owner", "assets", "liabilities", "equity", "cash_like", "borrowings", "net_debt",
        "inventories", "receivables", "ocf", "icf", "fcf_fin", "capex", "fcf", "dividends_paid", "eps",
        "gpm", "opm", "npm", "roe", "roa", "debt_ratio", "current_ratio", "equity_ratio", "rev_growth", "op_growth", "payout", "ocf_to_op", "net_debt_to_op"]

BODY = r"""
<header class="top"><div class="top-in">
  <div class="ident"><h1 id="ttl"></h1><span class="ticker" id="tick"></span><span class="cos" id="cos"></span></div>
  <div class="top-note"><span id="asof"></span><button class="tbtn" id="themeBtn" type="button">다크 모드</button></div>
</div></header>
<main class="wrap">
  <h2 class="sec">한눈에 보기<small>기업개요 · 자료 범위</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">기업 개요</h3><span class="p-unit">DART 기업개황</span></div><div class="p-sub" id="ovSub"></div><dl class="facts" id="facts"></dl></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">자료 범위</h3><span class="p-unit">출처 · 기준</span></div><div class="p-sub">각 자료의 출처·기준 시점·접수번호</div><div class="tbl-wrap"><table id="scope"></table></div></section>
  </div>

  <h2 class="sec">핵심 지표<small>기업·기간·단위를 고르면 아래 차트와 표가 함께 바뀜</small></h2>
  <section class="slicer">
    <div class="srow" id="rowCo"><span class="sname">표시 기업</span><div class="chips" id="coChips"></div></div>
    <div class="srow"><span class="sname">분석 기간</span><div class="seg" id="spanSeg"></div>
      <span class="sname" style="margin-left:12px">단위</span><div class="seg" id="unitSeg"></div>
      <div class="sright"><button class="tbtn" id="resetBtn" type="button">초기화</button></div></div>
    <div class="srow foot" id="slFoot"></div>
  </section>
  <div class="rail" id="rail"></div>
  <div class="cos-rail" id="coRail"></div>

  <h2 class="sec">실적 · 성장성<small id="growRange"></small></h2>
  <div class="grid" id="gGrow"></div>

  <h2 class="sec">재무 안정성<small>부채 · 유동성 · 차입 · 현금흐름 · 운전자본</small></h2>
  <div class="grid" id="gStab"></div>

  <div id="secQ"></div>
  <div id="secP"></div>
  <div id="secM"></div>

  <h2 class="sec">요약<small>공시 수치 기준 사실 정리 · 판단·권유 아님</small></h2>
  <div class="reads" id="reads"></div>

  <h2 class="sec" id="tblTitle">재무 요약표</h2>
  <section class="slicer"><div class="srow"><span class="sname">표 설정</span><div class="seg" id="tblSeg"></div><div class="sright"><button class="tbtn" id="copyBtn" type="button">표 복사</button></div></div></section>
  <div class="tbl-wrap"><table id="tbl"></table></div>

  <footer class="notes"><h4>데이터 출처 · 산식</h4><ol id="notes"></ol></footer>
</main>
"""

APP = r"""
const $ = id => document.getElementById(id);
const {num, pct, spct, spp, dir, esc} = K;
const CO = D.companies, MAIN = CO[0], ALLY = MAIN.years;
const S = K.store.get("dr_state_" + MAIN.id, {});
let span = [5, 10, ALLY.length].includes(S.span) && S.span <= ALLY.length ? S.span : Math.min(5, ALLY.length);
let unit = S.unit === "m" ? "m" : "e";
let sel = new Set((S.sel || CO.map(c => c.id)).filter(id => CO.some(c => c.id === id))); sel.add(MAIN.id);
let tblMode = S.tbl === "amt" ? "amt" : "both";
const save = () => K.store.set("dr_state_" + MAIN.id, {span, unit, sel: [...sel], tbl: tblMode});
const U = () => unit === "e" ? 1e8 : 1e6, uName = () => unit === "e" ? "억원" : "백만원";
const amt = (v, d = 0) => v == null ? "-" : num(v / U(), d);
const A = v => v == null ? null : v / U();
const Y = () => ALLY.slice(-span);
const cats = ys => ys.map(y => "'" + String(y).slice(2));
const R = (c, y) => (c.fy[y] || {});
const vis = () => CO.filter(c => sel.has(c.id));
const DEF = MAIN.color;

/* 상단 */
$("ttl").textContent = CO.length > 1 ? `${MAIN.name} · 동종 ${CO.length - 1}사 비교` : `${MAIN.name} 재무분석`;
document.title = $("ttl").textContent;
$("tick").textContent = `${D.meta.stock_code || "비상장"}${D.meta.market ? " · " + D.meta.market : ""}`;
$("cos").textContent = CO.length > 1 ? CO.map(c => c.name).join(" · ") : `${D.meta.fs_label} 기준`;
$("asof").textContent = `FY${ALLY[0]}–FY${ALLY[ALLY.length - 1]} · OpenDART · 생성 ${D.generated}${D.offline ? " · 오프라인 픽스처" : ""}`;
K.theme($("themeBtn"));

/* 한눈에 */
$("ovSub").textContent = `${D.meta.corp_name} · DART 기업개황 기준`;
$("facts").innerHTML = [["회사명", D.meta.corp_name], ["종목 · 시장", `${D.meta.stock_code || "비상장"} · ${D.meta.market || "-"}`], ["대표자", D.meta.ceo_nm], ["업종코드", D.meta.induty],
  ["설립일", D.meta.est_dt], ["결산월", D.meta.acc_mt], ["주소", D.meta.adres], ["홈페이지", D.meta.hm_url]]
  .map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v || "확인 불가")}</dd></div>`).join("");
const noCF = ALLY.filter(y => R(MAIN, y).ocf == null);
$("scope").innerHTML = `<thead><tr><th class="lab">구분</th><th class="lab">자료</th><th class="lab">기준</th></tr></thead><tbody>` + [
  ["연간 재무", `사업보고서 FY${ALLY[0]}–FY${ALLY[ALLY.length - 1]}`, `${D.meta.fs_label} · 접수 ${(D.meta.rcept_nos || []).length}건`],
  noCF.length ? ["현금흐름 공백", `FY${noCF[0]}–FY${noCF[noCF.length - 1]}`, "주요계정 API만 공시 → '-'"] : null,
  D.quarter ? ["분기·반기", `${D.quarter.year}년 ${D.quarter.label}보고서`, `접수 ${D.quarter.rcept_no || "-"}`] : ["분기·반기", "해당 없음", "최신 분·반기 미조회"],
  CO.length > 1 ? ["동종업체", CO.slice(1).map(c => c.name).join(", "), `FY${CO[1].fy_last} 사업보고서 · 사용자 지정`] : null,
  D.macro ? ["거시지표", D.macro.file, "macro_dash · 한국은행 ECOS"] : null,
].filter(Boolean).map(r => `<tr><td class="lab">${esc(r[0])}</td><td class="lab" style="font-weight:500">${esc(r[1])}</td><td class="lab" style="font-weight:500;color:var(--ink-3)">${esc(r[2])}</td></tr>`).join("") + "</tbody>";

/* 슬라이서 */
function renderSlicer(){
  $("rowCo").hidden = CO.length < 2;
  K.chips($("coChips"), CO.map(c => ({id: c.id, label: c.name + (c.main ? " (대상)" : ""), color: c.color})), sel, s => { sel = s; save(); renderAll(); }, MAIN.id);
  const spans = [...new Set([5, 10, ALLY.length].filter(n => n <= ALLY.length))];
  K.seg($("spanSeg"), spans.map(n => [n, n === ALLY.length && ![5, 10].includes(n) ? `전체 ${n}년` : `${n}개년`]), span, v => { span = v; save(); renderAll(); });
  K.seg($("unitSeg"), [["e", "억원"], ["m", "백만원"]], unit, v => { unit = v; save(); renderAll(); });
  $("slFoot").textContent = `기준 FY${ALLY[ALLY.length - 1]} · 금액 ${uName()} · 비율 % · 공시값 그대로 (추정·보정 없음)` + (CO.length > 1 ? " · 동종업체는 최근 3개년만" : "");
}
$("resetBtn").onclick = () => { span = Math.min(5, ALLY.length); unit = "e"; sel = new Set(CO.map(c => c.id)); tblMode = "both"; save(); renderAll(); };

/* 레일 */
function cell(label, val, u, sub, sparkVals, color, hero){
  return `<div class="cell${hero ? " hero" : ""}"><div class="k-label">${label}</div><div class="k-val">${val}<span class="k-unit">${u}</span></div><div class="k-sub">${sub}</div>${K.spark(sparkVals, color)}</div>`;
}
const dl = (v, f, inv) => v == null ? `<span class="delta flat">-</span>` : `<span class="delta ${inv ? "inv " : ""}${dir(v)}">${f(v)}</span>`;
function renderRail(){
  const ys = Y(), L = ys[ys.length - 1], r = R(MAIN, L), p = R(MAIN, L - 1), v = k => ys.map(y => R(MAIN, y)[k] ?? null);
  const cagr = (() => { const a = R(MAIN, ys[0]).revenue, b = r.revenue, n = ys.length - 1; return a > 0 && b > 0 && n > 0 ? Math.pow(b / a, 1 / n) - 1 : null; })();
  const nd = r.net_debt;
  $("rail").innerHTML = [
    cell(`매출액 · FY${L}`, amt(r.revenue), uName(), `전년비 ${dl(r.rev_growth, spct)} · ${ys.length - 1}년 CAGR <b>${spct(cagr)}</b>`, v("revenue"), "--s1", true),
    cell("영업이익", amt(r.op), uName(), `영업이익률 <b>${pct(r.opm)}</b> · 전년비 ${dl(r.opm != null && p.opm != null ? r.opm - p.opm : null, spp)}`, v("op"), "--s3"),
    cell("ROE", r.roe == null ? "-" : num(r.roe * 100, 1), "%", `ROA <b>${pct(r.roa)}</b> · 전년 ${pct(p.roe)}`, v("roe"), "--s2"),
    cell(nd != null && nd < 0 ? "순현금" : "순차입금", nd == null ? "-" : amt(Math.abs(nd)), uName(), `부채비율 <b>${pct(r.debt_ratio, 0)}</b> · 유동비율 <b>${pct(r.current_ratio, 0)}</b>`, v("net_debt").map(x => x == null ? null : -x), "--s2"),
    cell("FCF", amt(r.fcf), uName(), r.ocf == null ? "현금흐름 공시 없음" : `영업CF <b>${amt(r.ocf)}</b> · CAPEX <b>${amt(r.capex)}</b>`, v("fcf"), "--s4"),
  ].join("");
  $("coRail").hidden = vis().length < 2;
  $("coRail").innerHTML = vis().length < 2 ? "" : vis().map(c => {
    const y = c.fy_last, x = R(c, y), sp = c.years.map(yy => R(c, yy).revenue ?? null);
    return `<div class="cocard" style="--cc:${K.CSSV(c.color)}"><div class="nm">${esc(c.name)}</div><div class="ty">${esc(c.stock_code || "비상장")} · ${c.fs_label}${c.main ? " · 분석 대상" : ""}</div>
      <div class="v">${amt(x.revenue)}<small>${uName()}</small></div><div class="s">FY${y} 매출 · 전년비 ${dl(x.rev_growth, spct)}</div>
      <div class="s">영업이익률 <b>${pct(x.opm)}</b> · ROE <b>${pct(x.roe)}</b></div>${K.spark(sp, c.color)}</div>`;
  }).join("");
}

/* 패널 */
function panel(id, title, unitLbl, sub, wide, extra = ""){
  return `<section class="panel${wide ? " wide" : ""}"><div class="p-head"><h3 class="p-title">${title}</h3>${extra}<span class="p-unit">${unitLbl}</span></div><div class="p-sub">${sub}</div><div id="${id}L"></div><div class="chart" id="${id}"></div></section>`;
}
function draw(id, o){ $(id + "L").innerHTML = K.legend(o.series.filter(s => !s.noLegend)); K.combo($(id), o); }
const amtF = v => num(v), pF = v => pct(v);

function renderGrow(){
  const ys = Y(), c = cats(ys), v = k => ys.map(y => A(R(MAIN, y)[k])), vr = k => ys.map(y => R(MAIN, y)[k] ?? null);
  $("growRange").textContent = `FY${ys[0]} — FY${ys[ys.length - 1]}`;
  const multi = vis().length > 1;
  $("gGrow").innerHTML = [
    panel("cRev", "매출 규모", uName(), `${MAIN.name} 연간 매출액 · 막대 위 숫자 = 전년비 증감률`),
    panel("cIdx", "매출 성장 지수", `FY${ys[0]} = 100`, multi ? "각 사 기간 내 첫 해 매출 = 100 · 동종업체는 최근 3개년" : "기간 첫 해 매출 = 100"),
    panel("cOpm", "영업이익률 추이", "%", multi ? "표시 기업별 영업이익 ÷ 매출액" : "영업이익 ÷ 매출액"),
    panel("cMar", "이익률 비교", "%", "매출총이익률 · 영업이익률 · 순이익률 (매출총이익은 전체 재무제표 공시 연도만)"),
    panel("cPro", "영업이익 · 당기순이익", uName(), "금액 · 음수는 기준선 아래"),
    panel("cRoe", "자본 효율", "%", "ROE = 지배주주순이익 ÷ 평균 자본 · ROA = ÷ 평균 자산"),
  ].join("");
  const growth = vr("rev_growth");
  draw("cRev", {cats: c, series: [{name: "매출액", color: "--s1", vals: v("revenue")}], fmt: amtF, barLabels: (x, i) => growth[i] == null ? "" : spct(growth[i], 0), tipFoot: i => `전년비 ${spct(growth[i])}`});
  const idx = co => { const vals = ys.map(y => R(co, y).revenue ?? null); const b = vals.find(x => x != null && x > 0); return vals.map(x => x == null || !b ? null : x / b * 100); };
  draw("cIdx", {cats: c, series: vis().map(co => ({name: co.name, color: co.color, type: "line", vals: idx(co)})), fmt: x => num(x, 1), endLabels: true, zero: false});
  draw("cOpm", {cats: c, series: vis().map(co => ({name: co.name, color: co.color, type: "line", vals: ys.map(y => R(co, y).opm ?? null)})), fmt: pF, axisPct: true, endLabels: true, zero: false});
  draw("cMar", {cats: c, series: [{name: "매출총이익률", color: "--s1", type: "line", vals: vr("gpm")}, {name: "영업이익률", color: "--s3", type: "line", vals: vr("opm")}, {name: "순이익률", color: "--s2", type: "line", vals: vr("npm")}], fmt: pF, axisPct: true, zero: false});
  draw("cPro", {cats: c, series: [{name: "영업이익", color: "--s3", vals: v("op")}, {name: "당기순이익", color: "--s2", vals: v("ni")}], fmt: amtF});
  draw("cRoe", {cats: c, series: [{name: "ROE", color: "--s1", type: "line", vals: vr("roe")}, {name: "ROA", color: "--s4", type: "line", vals: vr("roa")}], fmt: pF, axisPct: true, zero: false});
}

function renderStab(){
  const ys = Y(), c = cats(ys), v = k => ys.map(y => A(R(MAIN, y)[k])), vr = k => ys.map(y => R(MAIN, y)[k] ?? null);
  const rows = [["부채비율", "debt_ratio", -1, x => pct(x, 0)], ["유동비율", "current_ratio", 1, x => pct(x, 0)], ["자기자본비율", "equity_ratio", 1, x => pct(x, 1)],
    ["순차입금 (−=순현금)", "net_debt", -1, x => amt(x)], ["순차입금 ÷ 영업이익", "net_debt_to_op", -1, x => x == null ? "-" : num(x, 2) + "배"], ["영업CF ÷ 영업이익", "ocf_to_op", 1, x => pct(x, 0)]];
  const tbl = `<div class="hl-legend"><span><i style="background:var(--hl-up)"></i>전년 대비 개선</span><span><i style="background:var(--hl-down)"></i>전년 대비 악화</span></div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">지표</th>${ys.map(y => `<th>FY${y}</th>`).join("")}</tr></thead><tbody>${rows.map(([l, k, good, f]) => `<tr><td class="lab">${l}</td>${ys.map(y => {
      const x = R(MAIN, y)[k], pv = R(MAIN, y - 1)[k]; let cl = "";
      if (x != null && pv != null && Math.abs(x - pv) > 1e-9) cl = (x - pv) * good > 0 ? "hl-up" : "hl-down";
      return `<td class="${cl}">${f(x)}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
  const wc = ys.filter(y => R(MAIN, y).dso != null);
  $("gStab").innerHTML = `<section class="panel wide"><div class="p-head"><h3 class="p-title">재무 안정성 지표</h3><span class="p-unit">${uName()} · %</span></div><div class="p-sub">칸 색 = 전년 대비 방향 (부채비율·순차입금은 낮을수록 개선)</div>${tbl}</section>` +
    panel("cDebt", "총차입금 · 현금성자산", uName(), "총차입금 = 단기차입금 + 유동성장기차입금 + 장기차입금 + 사채 · 현금성 = 현금 + 단기금융상품") +
    panel("cCf", "현금흐름", uName(), "영업CF · CAPEX(유형+무형 취득) · FCF = 영업CF − CAPEX" + (noCF.length ? ` · FY${noCF[0]}–FY${noCF[noCF.length - 1]}은 공시 범위 밖` : "")) +
    panel("cWc", "운전자본 회전기간", "일", wc.length ? "매출채권 ÷ 매출액 × 365 · 재고자산 ÷ 매출원가 × 365 (전체 재무제표 공시 연도만)" : "계산 가능한 연도 없음", true) +
    panel("cStr", "재무 구조", uName(), "자산총계 · 부채총계 · 자본총계 (기말)", true);
  draw("cDebt", {cats: c, series: [{name: "총차입금", color: "--s4", vals: v("borrowings")}, {name: "현금성자산", color: "--s2", vals: v("cash_like")}], fmt: amtF});
  draw("cCf", {cats: c, series: [{name: "영업CF", color: "--s1", vals: v("ocf")}, {name: "CAPEX", color: "--s4", vals: v("capex")}, {name: "FCF", color: "--s2", type: "line", vals: v("fcf")}], fmt: amtF});
  draw("cWc", {cats: c, series: [{name: "매출채권 회전일수", color: "--s3", vals: vr("dso")}, {name: "재고자산 회전일수", color: "--s1", vals: vr("invdays")}], fmt: x => num(x, 0) + "일", h: 220});
  draw("cStr", {cats: c, series: [{name: "자산총계", color: "--s1", vals: v("assets")}, {name: "부채총계", color: "--s4", vals: v("liabilities")}, {name: "자본총계", color: "--s2", vals: v("equity")}], fmt: amtF, h: 220});
}

/* 분기 */
function renderQ(){
  const q = D.quarter; if (!q){ $("secQ").innerHTML = ""; return; }
  const yy = q.year, va = (r, x) => r.kind === "amt" ? amt(x, 1) : pct(x), ch = (r, x) => x == null ? "-" : `<span class="delta ${dir(x)}">${r.kind === "amt" ? spct(x) : spp(x)}</span>`;
  $("secQ").innerHTML = `<h2 class="sec">${yy}년 ${q.label} 실적<small>${q.fs_label} · 누적 ${q.months}개월 · 접수번호 ${q.rcept_no || "-"}</small></h2><div class="grid">
    <section class="panel wide"><div class="p-head"><h3 class="p-title">손익 · 현금흐름</h3><span class="p-unit">${uName()}</span></div><div class="p-sub">누적 = 당기 누적(thstrm_add_amount) · 해당분기 = 3개월 · 현금흐름은 누적만 공시 · 비율 증감 %p</div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">항목</th><th>${yy} 누적</th><th>${yy - 1} 누적</th><th>증감</th><th>${yy} 해당분기</th><th>${yy - 1} 해당분기</th><th>증감</th></tr></thead><tbody>
    ${q.rows.map(r => `<tr class="${["매출액", "영업이익"].includes(r.label) ? "tot" : ""}"><td class="lab">${r.label}</td><td>${va(r, r.cum)}</td><td>${va(r, r.cum_prev)}</td><td>${ch(r, r.cum_yoy)}</td><td>${r.q == null ? "-" : va(r, r.q)}</td><td>${r.q_prev == null ? "-" : va(r, r.q_prev)}</td><td>${r.q == null ? "-" : ch(r, r.q_yoy)}</td></tr>`).join("")}
    </tbody></table></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">${q.label} 누적 vs 전년 동기</h3><span class="p-unit">${uName()}</span></div><div class="p-sub">매출액 · 영업이익 · 당기순이익</div><div id="cQL"></div><div class="chart" id="cQ"></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">재무상태</h3><span class="p-unit">${q.label}말 vs ${yy - 1}말</span></div><div class="p-sub">직전 사업연도말 대비 변동</div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">항목</th><th>${yy} ${q.label}말</th><th>${yy - 1}말</th><th>증감</th></tr></thead><tbody>
    ${q.bs.map(r => `<tr><td class="lab">${r.label}</td><td>${r.kind === "amt" ? amt(r.cur, 1) : pct(r.cur, 0)}</td><td>${r.kind === "amt" ? amt(r.prev, 1) : pct(r.prev, 0)}</td><td>${r.kind === "amt" ? amt(r.chg, 1) : spp(r.chg)}</td></tr>`).join("")}
    </tbody></table></div></section></div>`;
  const pick = ["매출액", "영업이익", "당기순이익"].map(l => q.rows.find(r => r.label === l));
  draw("cQ", {cats: ["매출액", "영업이익", "당기순이익"], series: [{name: `${yy - 1}`, color: "--ink-3", vals: pick.map(r => A(r.cum_prev))}, {name: `${yy}`, color: "--s1", vals: pick.map(r => A(r.cum))}], fmt: x => num(x, 1)});
}

/* 동종업체 */
function renderP(){
  if (CO.length < 2){ $("secP").innerHTML = ""; return; }
  const P = vis(), M = D.peer_metrics, fy = MAIN.fy_last;
  const fmtM = (m, v) => m[2] === "amt" ? amt(v) : ["debt_ratio", "current_ratio"].includes(m[1]) ? pct(v, 0) : pct(v);
  const lowGood = new Set(["debt_ratio"]);
  $("secP").innerHTML = `<h2 class="sec">동종업체 비교<small>FY${fy} · 사용자 지정 비교군 · 사업보고서 주요계정</small></h2><div class="grid">
    <section class="panel wide"><div class="p-head"><h3 class="p-title">${P.length}사 핵심 지표</h3><span class="p-unit">${uName()} · %</span></div><div class="p-sub">보라 칸 = 분석 대상 · 연두 = 표시 기업 중 최고 · 분홍 = 최저 (부채비율은 반대) · 매출 CAGR(2개년) = FY-2 → FY</div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">지표</th>${P.map(c => `<th>${esc(c.name)}</th>`).join("")}</tr></thead><tbody>
    ${M.map(m => { const vals = P.map(c => c.vals[m[1]]), ok = vals.filter(x => x != null), hi = Math.max(...ok), lo = Math.min(...ok), lg = lowGood.has(m[1]);
      return `<tr><td class="lab">${m[0]}</td>${P.map((c, i) => { const x = vals[i]; let cl = c.main ? "me" : ""; if (ok.length > 2 && x != null && m[2] === "pct"){ if (x === (lg ? lo : hi)) cl += " hl-up"; else if (x === (lg ? hi : lo)) cl += " hl-down"; }
        return `<td class="${cl}">${fmtM(m, x)}</td>`; }).join("")}</tr>`; }).join("")}
    </tbody></table></div></section>
    ${panel("pRev", "매출액", uName(), `FY${fy}`)}${panel("pOpm", "영업이익률", "%", `FY${fy}`)}${panel("pRoe", "ROE", "%", `FY${fy}`)}${panel("pDebt", "부채비율", "%", `FY${fy} · 낮을수록 부채 부담 작음`)}</div>`;
  const names = P.map(c => c.name);
  const one = (id, k, isP) => K.combo($(id), {cats: names, series: [{name: "", colors: P.map(c => c.color), vals: P.map(c => isP ? c.vals[k] : A(c.vals[k]))}], fmt: isP ? pF : amtF, axisPct: isP, slot: 44,
    barLabels: x => isP ? pct(x) : amt(x * U())});
  one("pRev", "revenue", false); one("pOpm", "opm", true); one("pRoe", "roe", true); one("pDebt", "debt_ratio", true);
}

/* 원가 × 거시 */
function renderM(){
  const Mx = D.macro; if (!Mx){ $("secM").innerHTML = ""; return; }
  const ys = Mx.years, c = cats(ys.map(e => e.year));
  const coefs = K.store.get("dr_macro_" + MAIN.id, {}); Mx.drivers.forEach(d => { if (coefs[d.key] == null) coefs[d.key] = d.coef; });
  const baseCogs = (ys.find(e => e.year === Mx.base_year) || {}).cogs;
  $("secM").innerHTML = `<h2 class="sec">원가 × 거시지표<small>${esc(Mx.file)} · macro_dash · 한국은행 ECOS</small></h2><div class="grid">
    <section class="panel wide"><div class="p-head"><h3 class="p-title">매출원가율 · 거시지표 연평균</h3><span class="p-unit">${uName()}</span></div><div class="p-sub">* = 12개월 미만 평균 · 상관·회귀 분석 아님 (연도별 수치 병치)</div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">항목</th>${ys.map(e => `<th>FY${e.year}</th>`).join("")}</tr></thead><tbody>
    <tr class="tot"><td class="lab">매출원가</td>${ys.map(e => `<td>${amt(e.cogs)}</td>`).join("")}</tr>
    <tr class="tot"><td class="lab">매출원가율</td>${ys.map(e => `<td>${pct(e.cogs_ratio)}</td>`).join("")}</tr>
    ${Mx.present.map(k => `<tr><td class="lab">${Mx.names[k]}</td>${ys.map(e => { const m = e.macro[k]; return `<td>${m.avg == null ? "-" : num(m.avg, 1) + (m.months < 12 ? "*" : "")}</td>`; }).join("")}</tr>`).join("")}
    </tbody></table></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">원가 민감도<span class="est">추정</span></h3><span class="p-unit">FY${Mx.base_year ?? "-"} vs 전년</span></div>
    <div class="p-sub">계수 = 동인 1단위 ↑ 시 연간 원가 증가액(억원, 표시 단위와 무관) · 사용자 입력 · 브라우저 저장</div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">동인</th><th>계수(억원)</th><th>전년비 변화</th><th>원가 영향(억원)</th></tr></thead><tbody id="mImp"></tbody></table></div></section>
    ${panel("mCogs", "매출원가율", "%", "매출원가 ÷ 매출액 (전체 재무제표 공시 연도만)")}</div>`;
  function imp(){
    let tot = 0, any = false;
    $("mImp").innerHTML = Mx.drivers.map(d => { const x = d.delta == null ? null : d.delta * (coefs[d.key] || 0); if (x != null){ tot += x; any = true; }
      return `<tr><td class="lab">${d.label}</td><td><input type="number" step="0.1" data-k="${d.key}" value="${coefs[d.key]}"></td><td>${num(d.delta, 1)}</td><td><span class="delta inv ${dir(x)}">${x == null ? "-" : num(x, 1)}</span></td></tr>`; }).join("") +
      `<tr class="tot"><td class="lab">합계<span class="est">추정</span></td><td></td><td></td><td>${any ? num(tot, 1) : "-"}</td></tr>` +
      (baseCogs && any ? `<tr><td class="lab">매출원가 대비</td><td></td><td></td><td>${pct(tot * 1e8 / baseCogs, 2)}</td></tr>` : "");
    $("mImp").querySelectorAll("input").forEach(el => el.onchange = () => { coefs[el.dataset.k] = parseFloat(el.value) || 0; K.store.set("dr_macro_" + MAIN.id, coefs); imp(); });
  }
  imp();
  draw("mCogs", {cats: c, series: [{name: "매출원가율", color: "--s1", type: "line", vals: ys.map(e => e.cogs_ratio)}], fmt: pF, axisPct: true, zero: false});
}

/* 요약 (사실 정리) */
function renderReads(){
  const ys = Y(), L = ys[ys.length - 1], r = R(MAIN, L), p = R(MAIN, L - 1), F = s => `<span class="fig">${s}</span>`;
  const good = [], warn = [], note = [];
  if (r.rev_growth != null) (r.rev_growth >= 0 ? good : warn).push(`FY${L} 매출 ${F(amt(r.revenue) + uName())}, 전년비 ${F(spct(r.rev_growth))}`);
  if (r.opm != null && p.opm != null) (Math.abs(r.opm - p.opm) < 5e-4 ? note : r.opm > p.opm ? good : warn).push(`영업이익률 ${F(pct(r.opm))} (전년 ${pct(p.opm)}, ${spp(r.opm - p.opm)})`);
  if (r.net_debt != null) (r.net_debt <= 0 ? good : (r.net_debt_to_op != null && r.net_debt_to_op > 3 ? warn : note)).push(r.net_debt <= 0 ? `순현금 ${F(amt(-r.net_debt) + uName())}` : `순차입금 ${F(amt(r.net_debt) + uName())} (영업이익의 ${num(r.net_debt_to_op, 1)}배)`);
  if (r.fcf != null) (r.fcf >= 0 ? good : warn).push(`FCF ${F(amt(r.fcf) + uName())} (영업CF ${amt(r.ocf)} − CAPEX ${amt(r.capex)})`);
  if (r.current_ratio != null && r.current_ratio < 1) warn.push(`유동비율 ${F(pct(r.current_ratio, 0))} — 100% 미만`);
  if (r.ocf_to_op != null) (r.ocf_to_op >= 0.8 ? good : warn).push(`영업CF ÷ 영업이익 ${F(pct(r.ocf_to_op, 0))}`);
  const q = D.quarter;
  if (q){ const op = q.rows.find(x => x.label === "영업이익"); if (op && op.cum_yoy != null) (op.cum_yoy >= 0 ? good : warn).push(`${q.year} ${q.label} 누적 영업이익 ${F(amt(op.cum) + uName())}, 전년 동기비 ${F(spct(op.cum_yoy))}`); }
  if (vis().length > 1){
    const others = vis().filter(c => !c.main), med = k => { const a = others.map(c => c.vals[k]).filter(x => x != null).sort((x, y) => x - y); return a.length ? (a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2) : null; };
    [["영업이익률", "opm"], ["ROE", "roe"]].forEach(([l, k]) => { const m = med(k), x = MAIN.vals[k]; if (m != null && x != null) (x >= m ? good : warn).push(`${l} ${F(pct(x))} — 비교군 중앙값 ${pct(m)}`); });
  }
  if (noCF.length) note.push(`FY${noCF[0]}–FY${noCF[noCF.length - 1]} 현금흐름은 요약 공시만 있어 공백`);
  note.push(`재무 기준 ${D.meta.fs_label} · 공시값 그대로`);
  if (D.macro) note.push(`원가 영향은 사용자 계수 기반 ${F("추정")}`);
  if (!q) note.push("최신 분·반기 실적 미포함");
  const card = (cls, t, list) => `<div class="read ${cls}"><h3>${t}</h3><ul>${(list.length ? list : ["해당 없음"]).map(x => `<li>${x}</li>`).join("")}</ul></div>`;
  $("reads").innerHTML = card("", "개선 · 양호", good) + card("warn", "점검", warn) + card("note", "참고", note);
}

/* 재무표 */
const TROWS = [["손익", null], ["매출액", "revenue", "amt", 1], ["매출원가", "cogs", "amt"], ["매출총이익", "gross", "amt"], ["판매비와관리비", "sga", "amt"], ["영업이익", "op", "amt", 1], ["당기순이익", "ni", "amt", 1], ["영업이익률", "opm", "pct"], ["순이익률", "npm", "pct"],
  ["재무상태", null], ["자산총계", "assets", "amt", 1], ["부채총계", "liabilities", "amt"], ["자본총계", "equity", "amt"], ["현금성자산", "cash_like", "amt"], ["총차입금", "borrowings", "amt"], ["순차입금(−=순현금)", "net_debt", "amt"], ["부채비율", "debt_ratio", "pct0"], ["유동비율", "current_ratio", "pct0"], ["ROE", "roe", "pct"],
  ["현금흐름", null], ["영업활동현금흐름", "ocf", "amt", 1], ["CAPEX", "capex", "amt"], ["FCF", "fcf", "amt"], ["배당금 지급", "dividends_paid", "amt"]];
function renderTable(){
  K.seg($("tblSeg"), [["both", "금액 + 전년비 증감률"], ["amt", "금액만"]], tblMode, v => { tblMode = v; save(); renderTable(); });
  const ys = Y(), both = tblMode === "both";
  $("tblTitle").innerHTML = `재무 요약표<small>FY${ys[0]} — FY${ys[ys.length - 1]} · ${uName()} · ${D.meta.fs_label}</small>`;
  const head = `<thead><tr><th class="lab">항목</th>${ys.map(y => `<th${both ? ' colspan="2"' : ""}>FY${y}</th>`).join("")}</tr></thead>`;
  const body = TROWS.map(([l, k, t, key]) => {
    if (!k) return `<tr class="grp"><td class="lab" colspan="${ys.length * (both ? 2 : 1) + 1}">${l}</td></tr>`;
    return `<tr class="${key ? "tot" : ""}"><td class="lab${key ? "" : " ind"}">${l}</td>${ys.map(y => {
      const x = R(MAIN, y)[k], pv = R(MAIN, y - 1)[k];
      const main = x == null ? "-" : t === "amt" ? amt(x) : t === "pct0" ? pct(x, 0) : pct(x);
      if (!both) return `<td>${main}</td>`;
      const d = t === "amt" ? (x != null && pv && pv > 0 ? x / pv - 1 : null) : (x != null && pv != null ? x - pv : null);
      return `<td>${main}</td><td class="d ${dir(d)}">${d == null ? "" : t === "amt" ? spct(d, 0) : spp(d, 1)}</td>`;
    }).join("")}</tr>`;
  }).join("");
  $("tbl").innerHTML = head + `<tbody>${body}</tbody>`;
}
$("copyBtn").onclick = () => K.copyTable($("tbl"), $("copyBtn"));

/* 출처 */
$("notes").innerHTML = [
  `OpenDART 사업보고서 전체 재무제표(fnlttSinglAcntAll)·주요계정(fnlttSinglAcnt) — ${D.meta.corp_name} ${D.meta.fs_label}, 접수번호 ${(D.meta.rcept_nos || []).join(", ") || "-"}`,
  D.quarter ? `OpenDART ${D.quarter.year}년 ${D.quarter.label}보고서 (접수번호 ${D.quarter.rcept_no || "-"})` : null,
  CO.length > 1 ? `동종업체 ${CO.slice(1).map(c => c.name).join(", ")} — OpenDART 사업보고서 주요계정, 비교군은 사용자 지정` : null,
  D.macro ? `거시지표 ${D.macro.file} — macro_dash 출력(한국은행 ECOS), 원가 영향은 사용자 계수 기반 추정` : null,
  "ROE·ROA = 지배주주순이익 ÷ 평균 자본·자산 · 순차입금 = 차입금 + 사채 − 현금 − 단기금융상품 · FCF = 영업CF − (유형 + 무형자산 취득)",
  "매출채권 회전일수 = 매출채권 ÷ 매출액 × 365 · 재고자산 회전일수 = 재고자산 ÷ 매출원가 × 365 (기말 잔액 기준)",
  `생성 ${D.generated} · dart-report · 공시값 그대로, 기업 판단·투자 권유 아님`,
].filter(Boolean).map(t => `<li>${esc(t)}</li>`).join("");

function renderAll(){ renderSlicer(); renderRail(); renderGrow(); renderStab(); renderQ(); renderP(); renderM(); renderReads(); renderTable(); }
renderAll();
K.onResize(() => { renderGrow(); renderStab(); renderQ(); renderP(); renderM(); });
"""


def _days(r: dict) -> dict:
    out = {}
    if r.get("receivables") is not None and r.get("revenue"):
        out["dso"] = r["receivables"] / r["revenue"] * 365
    if r.get("inventories") is not None and r.get("cogs"):
        out["invdays"] = r["inventories"] / r["cogs"] * 365
    return out


def build_html(meta: dict, table: dict, comments: list[str], extras: dict, out_path: str, offline: bool = False) -> str:
    ys = table["summary"]["years"]
    main = {
        "id": "main", "name": meta.get("corp_name"), "stock_code": meta.get("stock_code"), "fs_label": meta.get("fs_label"), "main": True,
        "color": "--c1", "years": ys, "fy_last": ys[-1],
        "fy": {y: {**{k: table["rows"][y].get(k) for k in KEYS}, **_days(table["rows"][y])} for y in ys},
    }
    companies = [main]
    peers = [p for p in (extras.get("peers") or []) if not p.get("main")]
    for i, p in enumerate(peers):
        pys = sorted(int(y) for y in p["series"])
        companies.append({
            "id": f"p{i + 1}", "name": p["name"], "stock_code": p["stock_code"], "fs_label": p["fs_label"], "main": False,
            "color": f"--c{(i + 1) % 7 + 1}", "years": pys, "fy_last": p["fy"], "vals": p["values"],
            "fy": {y: {**p["series"][y], "rev_growth": (p["series"][y]["revenue"] / p["series"][y - 1]["revenue"] - 1)
                       if p["series"].get(y - 1, {}).get("revenue") and p["series"][y].get("revenue") is not None else None} for y in pys},
        })
    main_peer = next((p for p in (extras.get("peers") or []) if p.get("main")), None)
    main["vals"] = main_peer["values"] if main_peer else {k: table["rows"][ys[-1]].get(k) for _, k, _ in PEER_METRICS}
    data = {
        "meta": {k: meta.get(k) for k in ("corp_name", "stock_code", "market", "fs_label", "rcept_nos", "ceo_nm", "induty", "est_dt", "acc_mt", "adres", "hm_url")},
        "companies": companies, "comments": comments, "generated": date.today().isoformat(), "offline": offline,
        "quarter": None, "macro": extras.get("macro") or None, "peer_metrics": PEER_METRICS,
    }
    q = extras.get("quarter")
    if q:
        data["quarter"] = {k: q[k] for k in ("year", "label", "months", "fs_label", "rcept_no")}
        data["quarter"]["rows"] = quarter_rows(q)
        data["quarter"]["bs"] = bs_rows(q)
    title = f"{meta.get('corp_name', '')} 재무분석" + (f" · 동종 {len(peers)}사 비교" if peers else "")
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(page(title, BODY, data, APP))
    return out_path
