"""원가·환율 노출 브리핑 — 원자재 선물 에이전트 검토 기록의 판단 공식(1·6·7단계)을 제이브이엠 FY2025 공시 수치에 대입.
사용: python -m reviews.cost_exposure --out out/   → 원가환율노출_제이브이엠_FY2025.html
데이터: reviews/cost_exposure_jvm.json (사업보고서 원문 발췌, 접수번호 포함)"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dashkit import page

DATA = Path(__file__).resolve().parent / "cost_exposure_jvm.json"


def derive(d: dict) -> dict:
    s, pl, raw, fx = d["sales"], d["pl"], d["raw"], d["fx"]
    rev = [a + b for a, b in zip(s["domestic"], s["export"])]
    raw_to_cogs = raw["total"] * 1e6 / pl["cogs"]          # 매입액 기준 근사 (재고 증감 미반영)
    cogs_ratio = pl["cogs"] / pl["revenue"]
    return {"rev": rev, "export_share": [e / r for e, r in zip(s["export"], rev)], "raw_to_cogs": raw_to_cogs, "cogs_ratio": cogs_ratio,
            "raw_in_price": raw_to_cogs * cogs_ratio, "fx_net": fx["assets"]["합계"] - fx["liabs"]["합계"], "sens_per_pct": fx["sens5"]["net"] / 5}


BODY = r"""
<header class="top"><div class="top-in">
  <div class="ident"><h1 id="ttl"></h1><span class="ticker" id="tick"></span><span class="cos">원자재 선물 에이전트 검토 기록 판단 공식 × 공시 수치</span></div>
  <div class="top-note"><span id="asof"></span><button class="tbtn" id="themeBtn" type="button">다크 모드</button></div>
</div></header>
<main class="wrap">
  <h2 class="sec">핵심 수치<small>FY2025 사업보고서 · 연결</small></h2>
  <div class="rail" id="rail"></div>

  <h2 class="sec">매출 구조 · 판가<small>내수·수출 · 제품별 · 평균 판매단가</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">내수 · 수출 매출</h3><span class="p-unit">억원</span></div><div class="p-sub" id="chSub"></div><div id="c1L"></div><div class="chart" id="c1"></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">제품별 매출 (FY2025)</h3><span class="p-unit">억원 · %</span></div><div class="p-sub">사업보고서 II-4 매출실적 · 수출 비중 = 수출 ÷ 품목 합계</div><div class="tbl-wrap"><table id="t1"></table></div></section>
  </div>

  <h2 class="sec">원재료 · 판가 단가 추이<small>대표 원재료 단가 vs 조제시스템 평균 판매단가 · FY2023 = 100</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">단가 지수</h3><span class="p-unit">FY2023 = 100</span></div>
      <div class="p-sub">원재료 = 품목별 가장 대표적인 원재료 단가 · 판가 = 총매출액 ÷ 총매출수량 (기종 판매비율에 따라 변동)</div><div id="c2L"></div><div class="chart" id="c2"></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">원재료 매입 구성 · 조달</h3><span class="p-unit">백만원</span></div><div class="p-sub" id="srcSub"></div><div class="tbl-wrap"><table id="t2"></table></div>
      <div class="tbl-wrap" style="margin-top:12px"><table id="t3"></table></div></section>
  </div>

  <h2 class="sec">환율 노출<small>연결감사보고서 주석 31 · 화폐성 외화 금융자산·부채</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">통화별 노출</h3><span class="p-unit">천원</span></div><div class="p-sub" id="fxSub"></div><div class="tbl-wrap"><table id="t4"></table></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">환율 변동 → 세전이익<span class="est">추정</span></h3><span class="p-unit">억원</span></div>
      <div class="p-sub">공시 민감도: 원화 환율 5% 상승 시 법인세차감전순이익 −10.4억 · 다른 변동률은 공시 민감도를 선형 환산</div>
      <div class="tbl-wrap"><table id="t5"></table></div><div class="k-label" style="margin-top:14px">세전이익 영향</div><div class="k-val" id="fxImp"></div><div class="k-sub" id="fxNote"></div></section>
  </div>

  <h2 class="sec">검토 기록 판단 공식 대입<small>7단계 원가 전가 · 1·6단계 선구매 부등식</small></h2>
  <div class="grid">
    <section class="panel"><div class="p-head"><h3 class="p-title">원가 전가 한계 (7단계)<span class="est">추정</span></h3><span class="p-unit">%</span></div>
      <div class="p-sub">판가 영향 = 원자재 변동률 × 원가 중 원재료 비중 × 원가율 · 기본값 = 제이브이엠 FY2025 (원재료 비중은 매입액 ÷ 매출원가 근사, 재고 증감 미반영)</div>
      <div class="tbl-wrap"><table id="t6"></table></div><div class="k-label" style="margin-top:14px">판가 영향</div><div class="k-val" id="ptOut" style="color:var(--accent)"></div><div class="k-sub" id="ptNote"></div></section>
    <section class="panel"><div class="p-head"><h3 class="p-title">선구매 부등식 (1·6단계)<span class="est">추정</span></h3><span class="p-unit">억원</span></div>
      <div class="p-sub">선구매 타당 조건: 리드타임 중 예상 가격상승분 &gt; 자본비용 + 보관비 + 진부화 + 환리스크 · 기본값 = 검토 기록 6단계 예시 (10억·8%·6개월·연 20%)</div>
      <div class="tbl-wrap"><table id="t7"></table></div><div class="k-label" style="margin-top:14px">순효과 (적중 시)</div><div class="k-val" id="pbOut"></div><div class="k-sub" id="pbNote"></div></section>
  </div>

  <h2 class="sec">공시 사실 정리<small>판단·권유 아님</small></h2>
  <div class="reads" id="reads"></div>
  <footer class="notes"><h4>데이터 출처 · 방법</h4><ol id="notes"></ol></footer>
</main>
"""

APP = r"""
const $ = id => document.getElementById(id), {num, pct, spct, esc, dir} = K, X = D.x, S = D.sales, Y = S.years;
const e8k = v => v / 1e5;            // 천원 → 억원
$("ttl").textContent = `${D.corp} 원가 · 환율 노출 브리핑`; document.title = $("ttl").textContent;
$("tick").textContent = `FY${D.fy} · 접수 ${D.rcept}`; $("asof").textContent = `OpenDART 사업보고서 원문 · 수집 ${D.collected}`; K.theme($("themeBtn"));
const cell = (l, v, u, s, hero, est) => `<div class="cell${hero ? " hero" : ""}"><div class="k-label">${l}${est ? '<span class="est">추정</span>' : ""}</div><div class="k-val">${v}<span class="k-unit">${u}</span></div><div class="k-sub">${s}</div></div>`;
$("rail").innerHTML = cell("수출 매출 비중", num(X.export_share[2] * 100, 1), "%", `수출 ${num(e8k(S.export[2]), 0)}억 · 내수 ${num(e8k(S.domestic[2]), 0)}억 · 3년 전 ${num(X.export_share[0] * 100, 1)}%`, true) +
  cell("원재료 매입", num(D.raw.total / 100, 0), "억원", `매출원가 ${num(D.pl.cogs / 1e8, 0)}억 대비 ${num(X.raw_to_cogs * 100, 1)}% (매입액 기준 근사)`) +
  cell("판가 내 원재료 비중", num(X.raw_in_price * 100, 1), "%", `원재료 ${num(X.raw_to_cogs * 100, 1)}% × 원가율 ${num(X.cogs_ratio * 100, 1)}%`, false, true) +
  cell("외화 순노출", num(e8k(X.fx_net), 1), "억원", `화폐성 외화부채 ${num(e8k(D.fx.liabs["합계"]), 1)}억 (EUR ${num(e8k(D.fx.liabs.EUR), 1)}억)`) +
  cell("환율 5% 상승 시", num(e8k(D.fx.sens5.net), 1), "억원", "법인세차감전순이익 영향 (공시)");

/* 매출 */
$("chSub").textContent = S.channel;
const ser1 = [{name: "내수", color: "--s3", vals: S.domestic.map(e8k)}, {name: "수출", color: "--s1", vals: S.export.map(e8k)}, {name: "수출 비중", color: "--s4", type: "line", vals: X.export_share.map(v => v * 1000), fmt: v => num(v / 10, 1) + "%", noTip: false}];
function d1(){ $("c1L").innerHTML = K.legend(ser1.slice(0, 2)); K.combo($("c1"), {cats: Y.map(y => "FY" + y), series: ser1.slice(0, 2), fmt: v => num(v, 1) + "억", h: 230, tipFoot: i => `수출 비중 ${num(X.export_share[i] * 100, 1)}%`}); }
$("t1").innerHTML = `<thead><tr><th class="lab">품목</th><th>내수</th><th>수출</th><th>합계</th><th>매출 비중</th><th>수출 비중</th><th>평균 단가(천원)</th></tr></thead><tbody>` +
  S.items.map(it => { const d = it.domestic[2], e = it.export[2], t = d + e, pr = D.price.items.find(p => p.name === it.name);
    return `<tr><td class="lab">${esc(it.name)}</td><td>${num(e8k(d), 1)}</td><td>${num(e8k(e), 1)}</td><td><b>${num(e8k(t), 1)}</b></td><td>${num(t / X.rev[2] * 100, 1)}%</td><td>${num(e / t * 100, 1)}%</td><td>${pr ? num(pr.v[0]) + " → " + num(pr.v[2]) : "-"}</td></tr>`; }).join("") +
  `<tr class="tot"><td class="lab">합계</td><td>${num(e8k(S.domestic[2]), 1)}</td><td>${num(e8k(S.export[2]), 1)}</td><td>${num(e8k(X.rev[2]), 1)}</td><td>100.0%</td><td>${num(X.export_share[2] * 100, 1)}%</td><td></td></tr></tbody>`;

/* 단가 지수 */
const idx = v => v.map(x => v[0] ? x / v[0] * 100 : null), cols = ["--c3", "--c2", "--c5", "--c4"];
const ser2 = D.raw.prices.map((p, k) => ({name: "원재료 · " + p.name, color: cols[k], type: "line", vals: idx(p.v), fmt: v => num(v, 1)})).concat([{name: "판가 · 조제시스템", color: "--s1", type: "line", width: 3, vals: idx(D.price.items[0].v), fmt: v => num(v, 1)}]);
function d2(){ $("c2L").innerHTML = K.legend(ser2); K.combo($("c2"), {cats: Y.map(y => "FY" + y), series: ser2, h: 250, zero: false, endLabels: true,
  tipFoot: i => [...D.raw.prices.map(p => `${p.name} ${num(p.v[i])}천원`), `조제시스템 ${num(D.price.items[0].v[i])}천원`].join(" · ")}); }
$("srcSub").textContent = D.raw.sourcing;
$("t2").innerHTML = `<thead><tr><th class="lab">원재료</th><th>FY2025 매입액</th><th>비율</th></tr></thead><tbody>` + D.raw.purchase.map(p => `<tr><td class="lab">${esc(p.name)}</td><td>${num(p.amt)}</td><td>${num(p.pct, 1)}%</td></tr>`).join("") + `<tr class="tot"><td class="lab">합계</td><td>${num(D.raw.total)}</td><td>100.0%</td></tr></tbody>`;
$("t3").innerHTML = `<thead><tr><th class="lab">대표 원재료 단가(천원)</th>${Y.map(y => `<th>FY${y}</th>`).join("")}<th>3년 변화</th></tr></thead><tbody>` +
  D.raw.prices.map(p => { const c = p.v[2] / p.v[0] - 1; return `<tr><td class="lab">${esc(p.name)}</td>${p.v.map(v => `<td>${num(v)}</td>`).join("")}<td><span class="delta inv ${dir(c)}">${spct(c)}</span></td></tr>`; }).join("") +
  D.price.items.slice(0, 1).map(p => { const c = p.v[2] / p.v[0] - 1; return `<tr class="tot"><td class="lab">판가 · ${esc(p.name)}</td>${p.v.map(v => `<td>${num(v)}</td>`).join("")}<td><span class="delta ${dir(c)}">${spct(c)}</span></td></tr>`; }).join("") + "</tbody>";

/* 환율 */
$("fxSub").textContent = `${D.fx.src} · 약정: ${D.fx.facility}`;
const cur = ["USD", "EUR", "CNY", "기타", "합계"];
$("t4").innerHTML = `<thead><tr><th class="lab">구분</th>${cur.map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>` +
  [["외화자산", D.fx.assets], ["외화부채", D.fx.liabs]].map(([l, o]) => `<tr${l === "외화부채" ? ' class="tot"' : ""}><td class="lab">${l}</td>${cur.map(c => `<td>${num(o[c])}</td>`).join("")}</tr>`).join("") +
  `<tr><td class="lab">순노출(자산−부채)</td>${cur.map(c => `<td class="${c === "EUR" ? "hl-key" : ""}">${num(D.fx.assets[c] - D.fx.liabs[c])}</td>`).join("")}</tr></tbody>`;
let fxp = K.store.get("ce_fx", 5);
function d5(){
  $("t5").innerHTML = `<tbody><tr><td class="lab">원화 환율 변동률(%) · +는 원화 약세</td><td><input type="number" step="1" id="fxIn" value="${fxp}"></td></tr></tbody>`;
  $("fxIn").onchange = e => { fxp = parseFloat(e.target.value) || 0; K.store.set("ce_fx", fxp); d5(); };
  const v = X.sens_per_pct * fxp;
  $("fxImp").innerHTML = `${v > 0 ? "+" : ""}${num(e8k(v), 1)}<span class="k-unit">억원</span>`;
  $("fxNote").textContent = `= 공시 5% 민감도 ${num(e8k(D.fx.sens5.net), 2)}억 × (${num(fxp, 1)} ÷ 5) · FY2025 영업이익 ${num(D.pl.op / 1e8, 1)}억 대비 ${num(Math.abs(v * 1000) / D.pl.op * 100, 1)}% · 매출·매입 거래 환율효과 미포함`;
}

/* 전가 · 선구매 */
let pt = Object.assign({raw: +(X.raw_to_cogs * 100).toFixed(1), cost: +(X.cogs_ratio * 100).toFixed(1), chg: 10}, K.store.get("ce_pt", {}));
function d6(){
  $("t6").innerHTML = `<tbody>${[["raw", "원가 중 원재료 비중(%)"], ["cost", "원가율(%)"], ["chg", "원자재 가격 변동률(%)"]].map(([k, l]) => `<tr><td class="lab">${l}</td><td><input type="number" step="0.1" data-k="${k}" value="${pt[k]}"></td></tr>`).join("")}</tbody>`;
  $("t6").querySelectorAll("input").forEach(el => el.onchange = () => { pt[el.dataset.k] = parseFloat(el.value) || 0; K.store.set("ce_pt", pt); d6(); });
  const share = pt.raw / 100 * pt.cost / 100, imp = share * pt.chg / 100;
  $("ptOut").innerHTML = `${imp >= 0 ? "+" : ""}${num(imp * 100, 2)}<span class="k-unit">% 판가 상당</span>`;
  $("ptNote").textContent = `판가 내 원재료 비중 ${num(share * 100, 1)}% · FY2025 매출 기준 ${num(D.pl.revenue * imp / 1e8, 1)}억 상당 (검토 기록 예시는 30%×70% = 21%)`;
}
let pb = Object.assign({buy: 10, up: 8, months: 6, carry: 20, hit: 100}, K.store.get("ce_pb", {}));
function d7(){
  $("t7").innerHTML = `<tbody>${[["buy", "연간 구매액(억원)"], ["up", "리드타임 중 예상 상승률(%)"], ["months", "선구매 기간(개월)"], ["carry", "재고보유비용(연 %, 자본·보관·진부화·환)"], ["hit", "예측 적중률(%)"]].map(([k, l]) => `<tr><td class="lab">${l}</td><td><input type="number" step="1" data-k="${k}" value="${pb[k]}"></td></tr>`).join("")}</tbody>`;
  $("t7").querySelectorAll("input").forEach(el => el.onchange = () => { pb[el.dataset.k] = parseFloat(el.value) || 0; K.store.set("ce_pb", pb); d7(); });
  const save = pb.buy * pb.up / 100, stock = pb.buy * pb.months / 12, carry = stock * pb.months / 12 * pb.carry / 100, net = save - carry, exp = save * pb.hit / 100 - carry;
  $("pbOut").innerHTML = `<span class="delta ${dir(net)}">${net > 0 ? "+" : ""}${num(net, 2)}</span><span class="k-unit">억원</span>`;
  $("pbNote").innerHTML = `절감 ${num(save, 2)}억 − 재고보유비용 ${num(carry, 2)}억 (재고 ${num(stock, 1)}억 × ${num(pb.months, 0)}개월 × 연 ${num(pb.carry, 0)}%) · 적중률 ${num(pb.hit, 0)}% 반영 기대값 <b>${exp > 0 ? "+" : ""}${num(exp, 2)}억</b> (검토 기록 예시: 8천만 − 5천만 = 3천만, 적중률 50% 시 순손실)`;
}

/* 사실 정리 */
const F = s => `<span class="fig">${s}</span>`, card = (cls, t, list) => `<div class="read ${cls}"><h3>${t}</h3><ul>${list.map(x => `<li>${x}</li>`).join("")}</ul></div>`;
const rp = D.raw.prices, ch = p => spct(p.v[2] / p.v[0] - 1, 0);
$("reads").innerHTML =
  card("note", "원재료 · 판가", [`대표 원재료 단가 3년: ${rp.map(p => `${p.name} ${F(ch(p))}`).join(" · ")}`, `조제시스템 평균 판매단가 ${F(ch(D.price.items[0]))} (FY2023→FY2025)`,
    "부품 대부분 국내 40여 업체 조달 · 공시상 원자재 선물 지수 직접 연동 품목 기재 없음 → 검토 기록 3단계 'BOM 원가구조 선행 분석' 대상"]) +
  card("warn", "환율", [`수출 매출 비중 ${F(num(X.export_share[2] * 100, 1) + "%")} (${num(e8k(S.export[2]), 0)}억)`, `화폐성 외화자산 ${F(num(D.fx.assets["합계"]) + "천원")} — 수출 판매경로: 한미약품(주) 경유`,
    `외화부채 ${F(num(e8k(D.fx.liabs["합계"]), 1) + "억")} 중 EUR ${num(e8k(D.fx.liabs.EUR), 1)}억 · 원화 5% 약세 시 세전 ${F(num(e8k(D.fx.sens5.net), 1) + "억")}`]) +
  card("", "검토 기록 공식 대입", [`판가 내 원재료 비중 약 ${F(num(X.raw_in_price * 100, 1) + "%")} (검토 기록 예시 21%) → 원재료 10% 변동 시 판가 ${num(X.raw_in_price * 10, 1)}% 상당`,
    "선구매는 '예상 상승분 > 재고보유비용'일 때만 성립 · 적중률 반영 필수 (6단계)", "파생상품 손익 공시: FY2021 이후 기재 없음 (별도 보고서 '파생상품 손익 이력')"]);
$("notes").innerHTML = [`OpenDART FY${D.fy} 사업보고서 (접수 ${D.rcept}) — II-2 주요 제품 가격변동추이 · II-3 원재료 및 생산설비 · II-4 매출실적 · 연결감사보고서 주석 31 재무위험관리 · 우발채무와 약정사항`,
  "매출원가·영업이익: OpenDART 전체 재무제표 FY2025 연결", "원재료 비중 = 원재료 매입액 ÷ 매출원가 (재고 증감 미반영 근사) · 환율 변동률별 영향은 공시 5% 민감도 선형 환산",
  "검토 기준: 원자재 선물 추적 에이전트 구상 검토 기록(2026-11-05) 1·3·6·7단계 · 수치 외 판단·권유 아님"].map(t => `<li>${esc(t)}</li>`).join("");

function drawAll(){ d1(); d2(); }
drawAll(); d5(); d6(); d7(); K.onResize(drawAll);
"""


def build(out_dir: str, data_path: Path = DATA) -> Path:
    d = json.loads(Path(data_path).read_text(encoding="utf-8"))
    payload = {**{k: d[k] for k in ("corp", "fy", "rcept", "collected", "sales", "price", "raw", "fx", "pl")}, "x": derive(d)}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"원가환율노출_{d['corp']}_FY{d['fy']}.html"
    p.write_text(page(f"{d['corp']} 원가·환율 노출", BODY, payload, APP), encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="원가·환율 노출 브리핑 HTML")
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    print(f"완료: {build(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
