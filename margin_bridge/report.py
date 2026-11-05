"""margin_bridge 출력 — 엑셀(맑은 고딕, 14/11/10/9pt) + HTML(dashkit 참고 양식)."""
from __future__ import annotations

from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from dashkit import page

FONT = "맑은 고딕"
F_T, F_H, F_B, F_BB, F_N, F_S = (Font(name=FONT, size=14, bold=True, color="2E2C5F"), Font(name=FONT, size=11, bold=True, color="FFFFFF"),
                                 Font(name=FONT, size=10), Font(name=FONT, size=10, bold=True), Font(name=FONT, size=9, color="7F7F7F"),
                                 Font(name=FONT, size=11, bold=True, color="6C5CE7"))
FILL_H, FILL_L, FILL_K = PatternFill("solid", fgColor="6C5CE7"), PatternFill("solid", fgColor="F2F2F2"), PatternFill("solid", fgColor="EFECFE")
BOX = Border(bottom=Side(style="thin", color="D9D9D9"))
EOK, NUM1 = 1e8, '#,##0.0;(#,##0.0);"-"'
LABELS = [("volume", "물량 효과"), ("mix", "믹스 효과"), ("price", "판가 효과"), ("raw", "원자재원가 효과"), ("other", "기타원가 효과"), ("new", "신규 품목"), ("gone", "단종 품목")]


def _labels(b):
    return [(k, ("원가 효과" if k == "other" and not b["use_raw"] else l)) for k, l in LABELS if not (k == "raw" and not b["use_raw"])]


def _c(ws, r, c, v, fmt=None, font=F_B, fill=None, align="right"):
    x = ws.cell(row=r, column=c, value=v)
    x.font, x.border, x.alignment = font, BOX, Alignment(horizontal=align)
    if fmt:
        x.number_format = fmt
    if fill:
        x.fill = fill


def _hdr(ws, r, labels):
    for i, t in enumerate(labels):
        _c(ws, r, 1 + i, t, font=F_H, fill=FILL_H, align="center")


def build_xlsx(b: dict, out: str, source: str, sample: bool):
    wb = Workbook()
    ws = wb.active
    ws.title = "요약 브리지"
    sub = f"{b['p0']} → {b['p1']} · 단위 억원 · 입력 {source}" + (" · ※ 예시 데이터 (실제값 아님)" if sample else "")
    ws["A1"], ws["A2"] = "매출총이익 증감 귀속", sub
    ws["A1"].font, ws["A2"].font = F_T, F_N
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width, ws.column_dimensions["C"].width = 22, 14, 14
    _hdr(ws, 4, ["항목", "금액(억원)", "비중"])
    d = b["gm1"] - b["gm0"]
    rows = [("기준 매출총이익", b["gm0"], True)] + [(l, b["effects"][k], False) for k, l in _labels(b)] + [("비교 매출총이익", b["gm1"], True)]
    for i, (l, v, key) in enumerate(rows):
        r = 5 + i
        _c(ws, r, 1, l, font=F_BB if key else F_B, fill=FILL_K if key else FILL_L, align="left")
        _c(ws, r, 2, v / EOK, NUM1, font=F_BB if key else F_B, fill=FILL_K if key else None)
        _c(ws, r, 3, None if key or not d else v / d, '0.0%;(0.0%);"-"')
    r = 6 + len(rows)
    for t in ("물량 = (공통 품목 수량 증감) × 기준 평균 단위마진 · 믹스 = 수량 비중 변화 × 기준 품목 단위마진",
              "판가 = 비교 수량 × 단가 변화 · 원가 = −비교 수량 × 단위원가 변화 (원자재원가 열 있으면 원자재·기타로 분리)",
              "합계 = 매출총이익 증감 (항등식) · 비중 = 각 효과 ÷ 매출총이익 증감"):
        ws.cell(row=r, column=1, value="· " + t).font = F_N
        r += 1
    wi = wb.create_sheet("품목별")
    wi["A1"], wi["A2"] = "품목별 내역", sub
    wi["A1"].font, wi["A2"].font = F_T, F_N
    heads = ["품목", "구분", "수량(기준)", "수량(비교)", "단가(기준)", "단가(비교)", "단위원가(기준)", "단위원가(비교)", "GM 기준(억)", "GM 비교(억)", "믹스(억)", "판가(억)", "원자재(억)", "기타원가(억)", "신규·단종(억)"]
    _hdr(wi, 4, heads)
    for col, w in zip("ABCDEFGHIJKLMNO", (18, 8, 11, 11, 12, 12, 13, 13, 11, 11, 10, 10, 10, 11, 12)):
        wi.column_dimensions[col].width = w
    for j, it in enumerate(b["items"]):
        r = 5 + j
        vals = [it["item"], it["status"], it["qty0"], it["qty1"], it.get("p0"), it.get("p1"), it.get("c0"), it.get("c1"), it["gm0"] / EOK, it["gm1"] / EOK,
                *(None if it.get(k) is None else it[k] / EOK for k in ("mix", "price", "raw", "other")), None if it.get("effect") is None else it["effect"] / EOK]
        for i, v in enumerate(vals):
            _c(wi, r, 1 + i, v, None if i < 2 else ('#,##0' if i < 8 else NUM1), align="left" if i < 2 else "right")
    ws2 = wb.create_sheet("방법")
    ws2["A1"] = "방법 · 출처"
    ws2["A1"].font = F_T
    for i, t in enumerate(["입력: " + source, "입력 템플릿 열: 기간, 품목, 수량, 매출액, 매출원가, 원자재원가(선택) — 원 단위",
                           "공통 품목 = 두 기간 모두 있는 품목 · 신규 = 비교 기간에만 · 단종 = 기준 기간에만",
                           "예측 아닌 기발생 변동 설명 (검토 기록 대안방향 ① 마진 귀속 분석)", f"생성 {date.today().isoformat()} · dart-report/margin_bridge"]):
        ws2.cell(row=3 + i, column=1, value="· " + t).font = F_B
    ws2.column_dimensions["A"].width = 100
    wb.save(out)


BODY = r"""
<header class="top"><div class="top-in"><div class="ident"><h1>매출총이익 증감 귀속</h1><span class="ticker" id="tick"></span><span class="cos" id="src"></span></div>
<div class="top-note"><span id="asof"></span><button class="tbtn" id="themeBtn" type="button">다크 모드</button></div></div></header>
<main class="wrap">
  <h2 class="sec">핵심 수치<small>예측 아닌 기발생 변동 설명 · 합계 = 매출총이익 증감</small></h2><div class="rail" id="rail"></div>
  <h2 class="sec">귀속 워터폴</h2>
  <section class="panel"><div class="p-head"><h3 class="p-title">기준 → 비교 매출총이익</h3><span class="p-unit">억원</span></div>
    <div class="p-sub">물량 = 공통 품목 수량 증감 × 기준 평균 단위마진 · 믹스 = 수량 비중 변화 × 기준 단위마진 · 판가 = 비교 수량 × 단가 변화 · 원가 = −비교 수량 × 단위원가 변화</div><div class="chart" id="wf"></div></section>
  <h2 class="sec">품목별 내역</h2>
  <section class="slicer"><div class="srow"><span class="sname">표 설정</span><div class="sright"><button class="tbtn" id="copyBtn" type="button">표 복사</button></div></div></section>
  <div class="tbl-wrap"><table id="tbl"></table></div>
  <footer class="notes"><h4>방법 · 출처</h4><ol id="notes"></ol></footer>
</main>
"""

APP = r"""
const $ = id => document.getElementById(id), {num, pct, esc, dir} = K, B = D.b, E = B.effects, e8 = v => v == null ? null : v / 1e8;
const fe = v => v == null ? "-" : (v > 0 ? "+" : "") + num(e8(v), 1);
$("tick").textContent = `${B.p0} → ${B.p1}`; $("src").textContent = D.source + (D.sample ? " · 예시 데이터 (실제값 아님)" : "");
$("asof").textContent = `생성 ${D.generated}`; K.theme($("themeBtn"));
const d = B.gm1 - B.gm0, big = D.labels.map(([k, l]) => [l, E[k]]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
$("rail").innerHTML = [["매출총이익 증감", fe(d), `${num(e8(B.gm0), 1)} → ${num(e8(B.gm1), 1)}억`, true], ["매출총이익률", num(B.gm1 / B.rev1 * 100, 1), `% (기준 ${num(B.gm0 / B.rev0 * 100, 1)}%)`],
  ["최대 요인", esc(big[0]), `${fe(big[1])}억`], ["공통 품목", B.n_common, `개 · 신규 ${B.items.filter(i => i.status === "신규").length} · 단종 ${B.items.filter(i => i.status === "단종").length}`],
  ["원자재원가 효과", B.use_raw ? fe(E.raw) : "-", B.use_raw ? "억 (원자재원가 열 기준)" : "원자재원가 열 없음"]]
  .map(([l, v, s, h]) => `<div class="cell${h ? " hero" : ""}"><div class="k-label">${l}</div><div class="k-val">${v}${h ? '<span class="k-unit">억원</span>' : ""}</div><div class="k-sub">${s}</div></div>`).join("");
const draw = () => K.waterfall($("wf"), {steps: [{name: "기준 매출총이익", value: e8(B.gm0), total: true}, ...D.labels.map(([k, l]) => ({name: l, value: e8(E[k])})), {name: "비교 매출총이익", value: e8(B.gm1), total: true}], fmt: v => num(v, 1), h: 300});
draw(); K.onResize(draw);
const n0 = v => v == null ? "" : num(v), n1 = v => v == null ? "" : num(e8(v), 2);
$("tbl").innerHTML = `<thead><tr><th class="lab">품목</th><th class="lab">구분</th><th>수량 기준→비교</th><th>단가 기준→비교</th><th>단위원가 기준→비교</th><th>GM 기준</th><th>GM 비교</th><th>믹스</th><th>판가</th><th>원자재</th><th>기타원가</th><th>신규·단종</th></tr></thead><tbody>` +
  B.items.map(i => `<tr><td class="lab">${esc(i.item)}</td><td class="lab" style="font-weight:500">${i.status}</td><td>${n0(i.qty0)} → ${n0(i.qty1)}</td><td>${i.p0 == null ? "-" : n0(i.p0) + " → " + n0(i.p1)}</td><td>${i.c0 == null ? "-" : n0(i.c0) + " → " + n0(i.c1)}</td>
    <td>${n1(i.gm0)}</td><td>${n1(i.gm1)}</td>${["mix", "price", "raw", "other", "effect"].map(k => `<td><span class="delta ${dir(i[k] == null ? null : i[k] / 1e10)}">${i[k] == null ? "" : (i[k] > 0 ? "+" : "") + n1(i[k])}</span></td>`).join("")}</tr>`).join("") + "</tbody>";
$("copyBtn").onclick = () => K.copyTable($("tbl"), $("copyBtn"));
$("notes").innerHTML = ["단위: 금액 억원(표 GM·효과), 단가·단위원가 원", "공통 품목 = 두 기간 모두 존재 · 물량 효과는 공통 품목 전체 기준이라 품목별로 나누지 않음", "입력 " + D.source, "검토 기록 대안방향 ① 마진 귀속 분석 — 품목별 손익 데이터 접근 시 적용"].map(t => `<li>${esc(t)}</li>`).join("");
"""


def build_html(b: dict, out: str, source: str, sample: bool):
    data = {"b": b, "labels": _labels(b), "source": source, "sample": sample, "generated": date.today().isoformat()}
    with open(out, "w", encoding="utf-8") as fp:
        fp.write(page(f"매출총이익 귀속 {b['p0']}→{b['p1']}", BODY, data, APP))
