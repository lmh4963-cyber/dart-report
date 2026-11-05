"""원자재 가격 현황판 빌더.
사용:
  python -m commodity_board                          # 예시 데이터(sample.csv, 실제 시세 아님)
  python -m commodity_board 시세.csv --out out/       # 실데이터 내장
CSV 형식 (UTF-8, 둘 중 하나):
  ① 긴 형식: 월,품목,값[,단위,통화]        예) 2026-09,구리,9969.4,USD/톤,USD
  ② 넓은 형식: 월,품목1(단위),품목2(단위)…   예) macro_dash 의 거시지표_데이터_YYYYMM.csv
월: YYYY-MM / YYYYMM / YYYY-MM-DD(월로 절사) · 같은 달 여러 값이면 평균
HTML 안에서도 CSV 파일을 끌어다 놓으면 브라우저에서 같은 규칙으로 교체 (서버 전송 없음)"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

from dashkit import page

SAMPLE = Path(__file__).resolve().parent / "sample.csv"


def _ym(s: str) -> str | None:
    t = re.sub(r"[^0-9]", "", s or "")
    return f"{t[:4]}{t[4:6]}" if len(t) >= 6 else None


def _num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def parse(text: str) -> dict:
    """→ {품목: {unit, cur, data: {YYYYMM: 값}}}"""
    rows = [r for r in csv.reader(text.lstrip("﻿").splitlines()) if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("빈 CSV")
    head = [h.strip() for h in rows[0]]
    acc: dict[str, dict] = {}

    def add(name, ym, v, unit="", cur=""):
        s = acc.setdefault(name, {"unit": unit, "cur": cur, "sum": {}, "n": {}})
        s["unit"] = s["unit"] or unit
        s["cur"] = s["cur"] or cur
        s["sum"][ym] = s["sum"].get(ym, 0) + v
        s["n"][ym] = s["n"].get(ym, 0) + 1

    if "품목" in head and "값" in head:
        ix = {k: head.index(k) for k in ("품목", "값")}
        iu = head.index("단위") if "단위" in head else None
        ic = head.index("통화") if "통화" in head else None
        for r in rows[1:]:
            ym, v = _ym(r[0]), _num(r[ix["값"]]) if len(r) > ix["값"] else None
            if ym and v is not None:
                add(r[ix["품목"]].strip(), ym, v, r[iu].strip() if iu is not None and iu < len(r) else "", r[ic].strip() if ic is not None and ic < len(r) else "")
    else:
        cols = []
        for h in head[1:]:
            m = re.match(r"^(.*)\(([^()]*)\)$", h)  # 마지막 괄호 = 단위 (예: 수입물가(원재료)(2020=100))
            cols.append((m.group(1).strip(), m.group(2).strip()) if m else (h, ""))
        for r in rows[1:]:
            ym = _ym(r[0])
            if not ym:
                continue
            for (name, unit), c in zip(cols, r[1:]):
                v = _num(c)
                if v is not None and name:
                    add(name, ym, v, unit)
    if not acc:
        raise ValueError("읽을 수 있는 값 없음 — 형식 확인 (월,품목,값 또는 월,품목1,품목2…)")
    return {k: {"unit": s["unit"], "cur": s["cur"] or ("USD" if "USD" in s["unit"] else ""), "data": {ym: s["sum"][ym] / s["n"][ym] for ym in sorted(s["sum"])}}
            for k, s in acc.items()}


BODY = r"""
<header class="top"><div class="top-in">
  <div class="ident"><h1>원자재 가격 현황판</h1><span class="ticker" id="tick"></span><span class="cos" id="srcName"></span></div>
  <div class="top-note"><span id="asof"></span><button class="tbtn" id="themeBtn" type="button">다크 모드</button></div>
</div></header>
<main class="wrap">
  <div id="sampleWarn"></div>
  <h2 class="sec">현황<small>최신월 · 전월·전년 대비 · 3개월 vs 12개월 평균 국면</small></h2>
  <section class="slicer">
    <div class="srow"><span class="sname">품목</span><div class="chips" id="itemChips"></div></div>
    <div class="srow"><span class="sname">기간</span><div class="seg" id="spanSeg"></div>
      <span class="sname" style="margin-left:12px">표시</span><div class="seg" id="modeSeg"></div>
      <div class="sright"><label class="tbtn" style="cursor:pointer">CSV 불러오기<input type="file" id="file" accept=".csv,text/csv" hidden></label><button class="tbtn" id="resetBtn" type="button">기본 데이터로</button></div></div>
    <div class="srow foot" id="slFoot"></div>
  </section>
  <div class="cos-rail" id="cards"></div>

  <h2 class="sec">품목 비교<small id="cmpSub"></small></h2>
  <section class="panel"><div id="cmpL"></div><div class="chart" id="cmp"></div></section>

  <h2 class="sec">품목별 추이<small>실선 = 월 시세 · 점선 = 12개월 이동평균</small></h2>
  <div class="grid g3" id="charts"></div>

  <h2 class="sec">변동 요약<small>기간별 변화율 · 12개월 최고·최저 · 월간 변동성</small></h2>
  <div class="tbl-wrap"><table id="chgT"></table></div>

  <h2 class="sec" id="dataTitle">데이터</h2>
  <section class="slicer"><div class="srow"><span class="sname">표</span><div class="sright"><button class="tbtn" id="csvBtn" type="button">CSV 다운로드</button><button class="tbtn" id="copyBtn" type="button">표 복사</button></div></div></section>
  <div class="tbl-wrap"><table id="tbl"></table></div>

  <footer class="notes"><h4>데이터 · 방법</h4><ol id="notes"></ol></footer>
</main>
"""

APP = r"""
const $ = id => document.getElementById(id), {num, pct, spct, dir, esc} = K;
const COLS = ["--c1", "--c2", "--c3", "--c4", "--c5", "--c6", "--c7"];
const FX_NAMES = ["원/달러", "USD/KRW", "원달러", "원/달러 환율"];
let DS = K.store.get("cb_upload", null) || D.ds;
let st = Object.assign({span: 36, mode: "raw", sel: null}, K.store.get("cb_state", {}));
const save = () => K.store.set("cb_state", st);
K.theme($("themeBtn"));

/* CSV 파싱 (빌더와 같은 규칙) */
function csvRows(t){ const out = []; let row = [], f = "", q = false;
  for (let i = 0; i < t.length; i++){ const c = t[i];
    if (q){ if (c === '"' && t[i + 1] === '"'){ f += '"'; i++; } else if (c === '"') q = false; else f += c; }
    else if (c === '"') q = true; else if (c === ","){ row.push(f); f = ""; } else if (c === "\n" || c === "\r"){ if (c === "\r" && t[i + 1] === "\n") i++; row.push(f); out.push(row); row = []; f = ""; } else f += c; }
  if (f || row.length){ row.push(f); out.push(row); } return out.filter(r => r.some(c => c.trim())); }
const ymOf = s => { const t = String(s || "").replace(/[^0-9]/g, ""); return t.length >= 6 ? t.slice(0, 6) : null; };
const nOf = s => { const v = parseFloat(String(s).replace(/,/g, "")); return isNaN(v) ? null : v; };
function parse(text){
  const rows = csvRows(text.replace(/^﻿/, "")); if (!rows.length) throw new Error("빈 CSV");
  const head = rows[0].map(h => h.trim()), acc = {};
  const add = (n, ym, v, u = "", c = "") => { const s = acc[n] || (acc[n] = {unit: u, cur: c, sum: {}, cnt: {}}); s.unit = s.unit || u; s.cur = s.cur || c; s.sum[ym] = (s.sum[ym] || 0) + v; s.cnt[ym] = (s.cnt[ym] || 0) + 1; };
  if (head.includes("품목") && head.includes("값")){
    const ip = head.indexOf("품목"), iv = head.indexOf("값"), iu = head.indexOf("단위"), ic = head.indexOf("통화");
    rows.slice(1).forEach(r => { const ym = ymOf(r[0]), v = nOf(r[iv]); if (ym && v != null) add(r[ip].trim(), ym, v, iu >= 0 ? (r[iu] || "").trim() : "", ic >= 0 ? (r[ic] || "").trim() : ""); });
  } else {
    const cols = head.slice(1).map(h => { const m = h.match(/^(.*)\(([^()]*)\)$/); return m ? [m[1].trim(), m[2].trim()] : [h, ""]; });
    rows.slice(1).forEach(r => { const ym = ymOf(r[0]); if (!ym) return; cols.forEach(([n, u], k) => { const v = nOf(r[k + 1]); if (v != null && n) add(n, ym, v, u); }); });
  }
  const series = {}; Object.entries(acc).forEach(([k, s]) => { const data = {}; Object.keys(s.sum).sort().forEach(ym => data[ym] = s.sum[ym] / s.cnt[ym]); series[k] = {unit: s.unit, cur: s.cur || (s.unit.includes("USD") ? "USD" : ""), data}; });
  if (!Object.keys(series).length) throw new Error("읽을 수 있는 값 없음 — 형식: 월,품목,값 또는 월,품목1,품목2…"); return series;
}
$("file").onchange = e => { const f = e.target.files[0]; if (!f) return; const rd = new FileReader();
  rd.onload = () => { try { DS = {name: f.name, sample: false, uploaded: true, series: parse(rd.result)}; K.store.set("cb_upload", DS); st.sel = null; save(); renderAll(); } catch(err){ alert("CSV 오류: " + err.message); } };
  rd.readAsText(f, "utf-8"); };
document.addEventListener("dragover", e => e.preventDefault());
document.addEventListener("drop", e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f){ const dt = new DataTransfer(); dt.items.add(f); $("file").files = dt.files; $("file").onchange({target: $("file")}); } });
$("resetBtn").onclick = () => { try { localStorage.removeItem("cb_upload"); } catch(e){} DS = D.ds; st.sel = null; save(); renderAll(); };

/* 계산 */
const ym = s => s.slice(0, 4) + "." + s.slice(4);
const names = () => Object.keys(DS.series), fxName = () => names().find(n => FX_NAMES.includes(n));
function months(){ const all = new Set(); names().forEach(n => Object.keys(DS.series[n].data).forEach(m => all.add(m))); return [...all].sort(); }
function vals(n, ms){ const s = DS.series[n], fx = fxName(); return ms.map(m => { let v = s.data[m]; if (v == null) return null;
  if (st.mode === "krw" && s.cur === "USD" && fx){ const r = DS.series[fx].data[m]; v = r == null ? null : v * r; } return v; }); }
const chg = (a, b) => a == null || b == null || !b ? null : a / b - 1;
function stats(n){ const s = DS.series[n].data, ks = Object.keys(s).sort(), L = ks[ks.length - 1], v = k => s[k];
  const at = k => { const i = ks.indexOf(L) - k; return i >= 0 ? s[ks[i]] : null; };
  const last12 = ks.slice(-12).map(v), ma3 = ks.slice(-3).map(v), m12 = last12.reduce((a, b) => a + b, 0) / last12.length, m3 = ma3.reduce((a, b) => a + b, 0) / ma3.length;
  const rets = ks.slice(-13).map((k, i, a) => i ? s[k] / s[a[i - 1]] - 1 : null).filter(x => x != null), mu = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const vol = rets.length > 2 ? Math.sqrt(rets.reduce((a, b) => a + (b - mu) ** 2, 0) / rets.length) : null;
  const gap = ks.length >= 12 ? m3 / m12 - 1 : null;
  return {last: L, v: s[L], m1: chg(s[L], at(1)), m3: chg(s[L], at(3)), m6: chg(s[L], at(6)), m12: chg(s[L], at(12)), hi: Math.max(...last12), lo: Math.min(...last12), vol, gap,
    state: gap == null ? "판정불가" : gap > 0.01 ? "상승" : gap < -0.01 ? "하락" : "안정"}; }
const stCls = s => s === "상승" ? "st-up" : s === "하락" ? "st-down" : s === "안정" ? "st-flat" : "st-na";

function renderAll(){
  const ns = names(), sel = new Set((st.sel || ns).filter(n => ns.includes(n))); if (!sel.size) ns.forEach(n => sel.add(n));
  const ms = months(), fx = fxName();
  $("tick").textContent = `최신 ${ym(ms[ms.length - 1])}`; $("srcName").textContent = DS.name + (DS.uploaded ? " · 업로드" : "");
  $("asof").textContent = `생성 ${D.generated}`;
  $("sampleWarn").innerHTML = DS.sample ? `<section class="panel" style="margin-top:20px;border:2px solid var(--warn)"><b style="color:var(--warn)">예시 데이터 (실제 시세 아님)</b><div class="p-sub" style="margin:4px 0 0">실제 시세 CSV를 'CSV 불러오기' 또는 화면에 끌어다 놓기로 교체 · 형식: 월,품목,값[,단위,통화] 또는 월,품목1(단위),품목2(단위)… · macro_dash 출력 CSV 그대로 사용 가능</div></section>` : "";
  K.chips($("itemChips"), ns.map((n, i) => ({id: n, label: n, color: COLS[i % 7]})), sel, s => { st.sel = [...s]; save(); renderAll(); });
  K.seg($("spanSeg"), [[12, "12개월"], [24, "24개월"], [36, "36개월"], [0, "전체"]], st.span, v => { st.span = v; save(); renderAll(); });
  K.seg($("modeSeg"), [["raw", "원 단위"], ["idx", "지수(첫 달=100)"]].concat(fx ? [["krw", "원화 환산"]] : []), st.mode, v => { st.mode = v; save(); renderAll(); });
  const win = st.span ? ms.slice(-st.span) : ms, cats = win.map(m => m.slice(2, 4) + "." + m.slice(4)), list = ns.filter(n => sel.has(n)), col = n => COLS[ns.indexOf(n) % 7];
  const unitOf = n => st.mode === "krw" && DS.series[n].cur === "USD" && fx ? "원 (원화 환산)" : DS.series[n].unit;
  $("slFoot").textContent = `${ym(win[0])}–${ym(win[win.length - 1])} · 국면 = 3개월 평균 vs 12개월 평균 ±1% · ${st.mode === "krw" ? `원화 환산 = USD 시세 × ${fx} 월평균` : st.mode === "idx" ? "지수 = 기간 첫 달 = 100" : "원 단위 = CSV 단위 그대로"}`;
  /* 카드 */
  $("cards").innerHTML = list.map(n => { const s = stats(n), dec = s.v < 100 ? 2 : 1;
    return `<div class="cocard" style="--cc:${K.CSSV(col(n))}"><div class="nm">${esc(n)}</div><div class="ty">${esc(DS.series[n].unit || "-")} · ${ym(s.last)}</div>
      <div class="v">${num(s.v, dec)}</div><div class="s">전월 <span class="delta inv ${dir(s.m1)}">${spct(s.m1)}</span> · 전년 <span class="delta inv ${dir(s.m12)}">${spct(s.m12)}</span></div>
      <div class="s"><span class="lamp ${stCls(s.state)}" style="font-size:12px">${s.state}</span> · 변동성 ${s.vol == null ? "-" : num(s.vol * 100, 1) + "%"}</div>${K.spark(Object.keys(DS.series[n].data).sort().slice(-24).map(k => DS.series[n].data[k]), col(n))}</div>`; }).join("");
  /* 비교 (지수) */
  $("cmpSub").textContent = `기간 첫 달 = 100 · ${st.mode === "krw" ? "원화 환산 기준" : "원 단위 기준"} · 선택 품목`;
  const idxSer = list.map(n => { const v = vals(n, win), b = v.find(x => x != null); return {name: n, color: col(n), type: "line", vals: v.map(x => x == null || !b ? null : x / b * 100), fmt: x => num(x, 1)}; });
  $("cmpL").innerHTML = K.legend(idxSer); K.combo($("cmp"), {cats, series: idxSer, zero: false, endLabels: true, h: 280});
  /* 품목별 */
  $("charts").innerHTML = list.map((n, i) => `<section class="panel"><div class="p-head"><h3 class="p-title">${esc(n)}</h3><span class="p-unit">${esc(st.mode === "idx" ? "지수" : unitOf(n))}</span></div><div class="p-sub" id="ps${i}"></div><div class="chart" id="pc${i}"></div></section>`).join("");
  list.forEach((n, i) => { const all = vals(n, ms), off = ms.length - win.length; let v = all.slice(off);
    let ma = all.map((_, k) => k < 11 || all.slice(k - 11, k + 1).some(x => x == null) ? null : all.slice(k - 11, k + 1).reduce((a, b) => a + b, 0) / 12).slice(off);
    if (st.mode === "idx"){ const b = v.find(x => x != null); v = v.map(x => x == null ? null : x / b * 100); ma = ma.map(x => x == null ? null : x / b * 100); }
    const s = stats(n); $("ps" + i).innerHTML = `${ym(s.last)} <b>${num(s.v, s.v < 100 ? 2 : 1)}</b> · 3M <span class="delta inv ${dir(s.m3)}">${spct(s.m3)}</span> · 12M 범위 ${num(s.lo, 1)}–${num(s.hi, 1)}`;
    K.combo($("pc" + i), {cats, h: 190, l: 50, zero: false, fmt: x => num(x, x < 100 ? 2 : 1), series: [{name: n, color: col(n), type: "line", vals: v}, {name: "12M 이동평균", color: "--ink-3", type: "line", dash: true, width: 1.6, vals: ma}]}); });
  /* 변동 요약 */
  $("chgT").innerHTML = `<thead><tr><th class="lab">품목</th><th class="lab">단위</th><th>최신월</th><th>최신값</th><th>1M</th><th>3M</th><th>6M</th><th>12M</th><th>12M 최고</th><th>12M 최저</th><th>월간 변동성</th><th>국면</th></tr></thead><tbody>` +
    list.map(n => { const s = stats(n), c = x => `<td class="${x == null ? "" : x > 0.05 ? "hl-down" : x < -0.05 ? "hl-up" : ""}">${spct(x)}</td>`;
      return `<tr><td class="lab">${esc(n)}</td><td class="lab" style="font-weight:500">${esc(DS.series[n].unit)}</td><td>${ym(s.last)}</td><td><b>${num(s.v, s.v < 100 ? 2 : 1)}</b></td>${c(s.m1)}${c(s.m3)}${c(s.m6)}${c(s.m12)}<td>${num(s.hi, 1)}</td><td>${num(s.lo, 1)}</td><td>${s.vol == null ? "-" : num(s.vol * 100, 1) + "%"}</td><td><span class="lamp ${stCls(s.state)}" style="font-size:12px">${s.state}</span></td></tr>`; }).join("") +
    `</tbody>`;
  /* 데이터 표 */
  $("dataTitle").innerHTML = `데이터<small>${ym(win[0])}–${ym(win[win.length - 1])} · 최신순 · ${st.mode === "krw" ? "원화 환산" : st.mode === "idx" ? "지수" : "원 단위"}</small>`;
  const tv = {}; list.forEach(n => { let v = vals(n, win); if (st.mode === "idx"){ const b = v.find(x => x != null); v = v.map(x => x == null ? null : x / b * 100); } tv[n] = v; });
  $("tbl").innerHTML = `<thead><tr><th class="lab">월</th>${list.map(n => `<th>${esc(n)}</th>`).join("")}</tr></thead><tbody>` + win.map((m, k) => k).reverse().map(k => `<tr><td class="lab">${ym(win[k])}</td>${list.map(n => `<td>${tv[n][k] == null ? "-" : num(tv[n][k], tv[n][k] < 100 ? 2 : 1)}</td>`).join("")}</tr>`).join("") + "</tbody>";
  $("notes").innerHTML = [`데이터: ${DS.name}${DS.sample ? " — 예시값 (실제 시세 아님)" : ""}`, "국면: 최근 3개월 평균이 12개월 평균 대비 +1% 초과 상승 · −1% 미만 하락 · 그 외 안정 (macro_dash 기준과 동일)",
    "월간 변동성: 최근 12개월 월간 변화율 표준편차 · 변화율 칸 색: ±5% 초과 (원가 관점 상승 = 분홍)", "원화 환산: 통화가 USD인 품목 × 같은 달 원/달러 값 (CSV에 '원/달러' 품목 있을 때)",
    "검토 기록 '데이터확보현황 · 무료가능' 품목(유가·LME 구리·알루미늄·나프타·환율) 대상 · 업로드 데이터는 브라우저에만 저장, 서버 전송 없음"].map(t => `<li>${esc(t)}</li>`).join("");
}
$("copyBtn").onclick = () => K.copyTable($("tbl"), $("copyBtn"));
$("csvBtn").onclick = () => { const t = $("tbl"), lines = [...t.rows].map(r => [...r.cells].map(c => c.innerText.replace(/,/g, "")).join(","));
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + lines.join("\n")], {type: "text/csv"})); a.download = "원자재_현황판.csv"; a.click(); };
renderAll(); K.onResize(renderAll);
"""


def build(csv_path: str | None, out_dir: str) -> Path:
    src = Path(csv_path) if csv_path else SAMPLE
    series = parse(src.read_text(encoding="utf-8-sig"))
    ds = {"name": src.name, "sample": src == SAMPLE, "uploaded": False, "series": series}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "원자재_가격_현황판.html"
    p.write_text(page("원자재 가격 현황판", BODY, {"ds": ds, "generated": date.today().isoformat()}, APP), encoding="utf-8")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="commodity_board", description="원자재 가격 현황판 HTML")
    ap.add_argument("csv", nargs="?", help="시세 CSV (생략 시 예시 데이터)")
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    try:
        p = build(a.csv, a.out)
    except (OSError, ValueError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    print(f"완료: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
