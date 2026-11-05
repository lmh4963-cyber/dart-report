"""파생상품 손익 이력 재검토 보고 — 공시 수치와 '환헤지는 위험하다' 사내 인식 대조 (원자재 선물 에이전트 검토 기록 10단계·대안방향 ④).
사용: python -m reviews.derivatives --out out/   → 파생상품_손익이력_제이브이엠.html
데이터: reviews/derivatives_jvm.json (사업보고서 원문 발췌, 연도별 접수번호 포함)"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dashkit import page

DATA = Path(__file__).resolve().parent / "derivatives_jvm.json"


def summarize(d: dict) -> dict:
    rows = []
    for y in d["years"]:
        parts = [y.get(k) for k in ("eval_gain", "trade_gain", "eval_loss", "trade_loss")]
        known = [p for p in parts if p is not None]
        net = None if not known else (y.get("eval_gain") or 0) + (y.get("trade_gain") or 0) - (y.get("eval_loss") or 0) - (y.get("trade_loss") or 0)
        rows.append({**y, "net": net, "partial": any(p is None for p in parts)})
    s = lambda f: sum(r["net"] for r in rows if r["net"] is not None and f(r["year"]))
    used = [r["year"] for r in rows if (r.get("eval_loss") or r.get("trade_loss") or r.get("trade_gain") or r.get("eval_gain"))]
    return {"rows": rows, "total": s(lambda y: True), "y2008": s(lambda y: y == 2008), "y0910": s(lambda y: y in (2009, 2010)),
            "after": s(lambda y: y >= 2011), "fwd_min": min(r["net"] for r in rows if 2015 <= r["year"] <= 2020),
            "fwd_max": max(r["net"] for r in rows if 2015 <= r["year"] <= 2020), "last_use": max(used) if used else None}


BODY = r"""
<header class="top"><div class="top-in">
  <div class="ident"><h1 id="ttl"></h1><span class="ticker" id="tick"></span><span class="cos">사내 인식 '환헤지는 위험함' ↔ 공시 수치 대조</span></div>
  <div class="top-note"><span id="asof"></span><button class="tbtn" id="themeBtn" type="button">다크 모드</button></div>
</div></header>
<main class="wrap">
  <h2 class="sec">핵심 수치<small>연도별 파생상품 평가·거래 손익 합계 (이익 + / 손실 −)</small></h2>
  <div class="rail" id="rail"></div>

  <h2 class="sec">연도별 파생상품 손익<small>금융수익·비용 주석 · 단위 억원</small></h2>
  <div class="grid">
    <section class="panel wide"><div class="p-head"><h3 class="p-title">순손익 추이</h3><div class="seg xs" id="scaleSeg"></div><span class="p-unit">억원</span></div>
      <div class="p-sub">순손익 = 평가이익 + 거래이익 − 평가손실 − 거래손실 · 2008년 규모가 커서 '2008 제외' 보기 제공</div><div id="cL"></div><div class="chart" id="c"></div></section>
    <section class="panel wide"><div class="p-head"><h3 class="p-title">연도별 내역</h3><div class="sright"><button class="tbtn" id="copyBtn" type="button">표 복사</button></div></div>
      <div class="p-sub">단위 천원 · 공란 = 해당 행 확인 못 함 · 접수번호 = 근거 사업보고서</div><div class="tbl-wrap"><table id="tbl"></table></div></section>
  </div>

  <h2 class="sec">2008년 통화옵션 계약 구조<small>FY2008 사업보고서 「파생상품 등에 관한 사항」 · 기말환율 1,257.5원/USD</small></h2>
  <section class="panel"><div class="p-sub">기본 매도액 대비 환율 상단 돌파 시 매도 의무 2배 · 하단 이탈 시 소멸 → 환율 하락 이익은 제한, 상승 손실은 확대되는 비대칭 구조</div>
    <div class="tbl-wrap"><table id="kiko"></table></div></section>

  <h2 class="sec">검토 기록 기준 대조<small>원자재 선물 에이전트 검토 기록 10단계 '실제 손실 발생 유형'</small></h2>
  <div class="reads" id="reads"></div>

  <h2 class="sec">검토 기록과 공시가 다른 부분</h2>
  <div class="reads" id="diff" style="grid-template-columns:1fr"></div>

  <footer class="notes"><h4>데이터 출처 · 방법</h4><ol id="notes"></ol></footer>
</main>
"""

APP = r"""
const $ = id => document.getElementById(id), {num, esc} = K;
const S = D.summary, R = S.rows, eok = v => v == null ? null : v / 1e5;   // 천원 → 억원
const fe = (v, d = 1) => v == null ? "-" : (v > 0 ? "+" : "") + num(eok(v), d);
$("ttl").textContent = `${D.corp} 파생상품 손익 이력`;
$("tick").textContent = `FY${R[0].year}–FY${R[R.length - 1].year}`;
$("asof").textContent = `OpenDART 사업보고서 원문 · 수집 ${D.collected}`;
K.theme($("themeBtn"));
const cell = (l, v, sub, hero) => `<div class="cell${hero ? " hero" : ""}"><div class="k-label">${l}</div><div class="k-val">${v}<span class="k-unit">억원</span></div><div class="k-sub">${sub}</div></div>`;
$("rail").innerHTML = cell("FY2008 파생상품 순손익", fe(S.y2008, 0), "통화옵션(KIKO·Target Forward) 5건 · 순손실 788억 · 계속기업 불확실성 주석", true) +
  cell("FY2009–2010", fe(S.y0910, 0), "평가이익 151억·거래이익 91억 등 · 2008년말 잔존 계약 만기 2010.03~2011.03") + cell("FY2011 이후 합계", fe(S.after, 1), `통화선도 위주 · 연간 ${fe(S.fwd_min)} ~ ${fe(S.fwd_max)}억 (2015–2020)`) +
  cell("확인 기간 누계", fe(S.total, 0), "공란 연도 제외 합계") + `<div class="cell"><div class="k-label">마지막 사용 연도</div><div class="k-val">${S.last_use ?? "-"}</div><div class="k-sub">FY2021·2022·2025 보고서 손익 기재 없음</div></div>`;
let ex08 = false;
function chart(){
  K.seg($("scaleSeg"), [[false, "전체"], [true, "2008 제외"]], ex08, v => { ex08 = v; chart(); });
  const rs = R.filter(r => !(ex08 && r.year === 2008)), cats = rs.map(r => "'" + String(r.year).slice(2));
  const ser = [{name: "순손익", color: "--s1", vals: rs.map(r => eok(r.net)), colors: rs.map(r => r.net == null ? "--ink-3" : r.net >= 0 ? "--good" : "--bad")}];
  $("cL").innerHTML = `<div class="legend"><span><i class="swatch" style="background:${K.CSSV("--good")}"></i>이익</span><span><i class="swatch" style="background:${K.CSSV("--bad")}"></i>손실</span></div>`;
  K.combo($("c"), {cats, series: ser, fmt: v => num(v, 1) + "억", h: 260, slot: 30, tipFoot: i => esc(rs[i].product + (rs[i].note ? " · " + rs[i].note : ""))});
}
chart(); K.onResize(chart);
const n = v => v == null ? "" : num(v);
$("tbl").innerHTML = `<thead><tr><th class="lab">연도</th><th>평가이익</th><th>거래이익</th><th>평가손실</th><th>거래손실</th><th>순손익</th><th class="lab">상품</th><th class="lab">접수번호</th><th class="lab">비고</th></tr></thead><tbody>` +
  R.map(r => `<tr class="${r.year === 2008 ? "tot" : ""}"><td class="lab">FY${r.year}</td><td>${n(r.eval_gain)}</td><td>${n(r.trade_gain)}</td><td>${n(r.eval_loss)}</td><td>${n(r.trade_loss)}</td>
    <td class="${r.net < 0 ? "hl-down" : r.net > 0 ? "hl-up" : ""}">${r.net == null ? "" : num(r.net)}${r.partial ? "*" : ""}</td><td class="lab" style="font-weight:500">${esc(r.product)}</td><td class="lab" style="font-weight:500">${r.rcept}</td><td class="lab" style="font-weight:500;white-space:normal;min-width:220px">${esc(r.note)}</td></tr>`).join("") + "</tbody>";
$("copyBtn").onclick = () => K.copyTable($("tbl"), $("copyBtn"));
$("kiko").innerHTML = `<thead><tr><th class="lab">거래 상대방</th><th class="lab">거래시작(최초계약)</th><th class="lab">만기</th><th>약정환율</th><th class="lab">기본 매도</th><th class="lab">상단 돌파 시</th><th class="lab">소멸 조건</th><th class="lab">상품</th><th>잔액 기본/상단(USD M)</th><th>평가손실(천원)</th></tr></thead><tbody>` +
  D.kiko.contracts.map(c => `<tr><td class="lab">${esc(c.bank)}</td><td class="lab" style="font-weight:500">${esc(c.start)}</td><td class="lab" style="font-weight:500">${esc(c.maturity)}</td><td>${esc(c.strike)}</td><td class="lab" style="font-weight:500">${esc(c.base)}</td>
    <td class="lab hl-key">${esc(c.upper)}</td><td class="lab" style="font-weight:500">${esc(c.knockout)}</td><td class="lab" style="font-weight:500">${esc(c.type)}</td><td>${num(c.rem_base_usd_m, 1)} / ${num(c.rem_upper_usd_m, 1)}</td><td>${num(c.loss)}</td></tr>`).join("") +
  `<tr class="tot"><td class="lab" colspan="9">합계 (= 공시 평가손실 102,016,799)</td><td>${num(D.kiko.contracts.reduce((a, c) => a + c.loss, 0))}</td></tr></tbody>`;
const F = s => `<span class="fig">${s}</span>`, card = (cls, t, list) => `<div class="read ${cls}"><h3>${t}</h3><ul>${list.map(x => `<li>${x}</li>`).join("")}</ul></div>`;
$("reads").innerHTML =
  card("warn", "② 비대칭 상품 (KIKO) — 2008년 해당", [`공시 명칭 그대로 ${F("'Window Barrier Target Forward KIKO거래'")} 등 5건`, `환율 상단 돌파 시 매도 의무 ${F("2배")} (예: USD1.5M → 3.0M/월), 하단 이탈 시 소멸`,
    `평가손실 ${F("1,020억")} + 거래손실 ${F("213억")} → 순손실 788억, 계속기업 불확실성`, "검토 기록 표현: '헤지가 아니었던 것임'"]) +
  card("note", "① 오버헤지 — 공시만으로 판단 불가", ["판단 기준 = 계약 잔액 vs 외화 매출(노출) 규모", `2008년말 계약잔액 합계: 기본 구간 ${F("USD " + num(D.kiko.contracts.reduce((a, c) => a + c.rem_base_usd_m, 0), 1) + "M")} · 상단 돌파 시 ${F("USD " + num(D.kiko.contracts.reduce((a, c) => a + c.rem_upper_usd_m, 0), 1) + "M")} (공시 계약잔액 열 합)`, "같은 기간 외화 매출액은 이번에 조회 안 함 → 비교 필요"]) +
  card("", "③ 회계 미스매치 — 2015~2020 통화선도 해당 여부 확인 필요", [`FY2019 주석: 파생상품 손익이 ${F("당기손익-공정가치 측정 금융부채")} 범주로 분류`, "위험회피회계 적용 기재는 이번 조회에서 확인 못 함", `연간 순손익 ${F(fe(S.fwd_min) + " ~ " + fe(S.fwd_max) + "억")} — 2008년과 규모 차이 큼`]);
$("diff").innerHTML = card("warn", "검토 기록 '15년간 유지된 리스크 관리 수단 배제 정책' vs 공시", [
  `공시상 2009–2020년에도 파생상품 손익 존재 — 2015–2020 ${F("통화선도")} (FY2019 주석: '외화채권의 환율회피 등의 목적')`,
  `파생상품 손익이 없는 연도는 공시상 ${F("FY2021 이후")} (FY2021·2022·2025 확인, FY2023·2024 미조회)`,
  "→ '2008년 이후 헤지 전면 중단'이라는 전제라면 공시와 다름 · 사내 정책 시점·범위 확인 필요"]);
$("notes").innerHTML = [D.method, "단위 천원(표), 억원(차트·카드) · 순손익은 평가·거래 손익 4개 항목 합 — 외환차손익 등 현물 손익은 포함 안 함",
  "* = 일부 항목 미확인 연도 · 2011·2012 이익 항목, 2013·2014 거래이익 행은 이번 조회 범위 밖",
  "검토 기준: 원자재 선물 추적 에이전트 구상 검토 기록(2026-11-05) 10단계 · 대안방향 ④ '파생상품 손실 이력 재검토 보고'",
  "공시 사실 정리 — 투자·헤지 권유 아님"].map(t => `<li>${esc(t)}</li>`).join("");
"""


def build(out_dir: str, data_path: Path = DATA) -> Path:
    d = json.loads(Path(data_path).read_text(encoding="utf-8"))
    payload = {"corp": d["corp"], "collected": d["collected"], "method": d["method"], "summary": summarize(d), "kiko": d["kiko2008"]}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"파생상품_손익이력_{d['corp']}.html"
    p.write_text(page(f"{d['corp']} 파생상품 손익 이력", BODY, payload, APP), encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="파생상품 손익 이력 재검토 HTML")
    ap.add_argument("--out", default="out")
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args(argv)
    print(f"완료: {build(a.out, Path(a.data))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
