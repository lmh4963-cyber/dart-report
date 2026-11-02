"""엑셀 내보내기 — 맑은 고딕, 제목 14pt / 머리글 11pt / 본문 10pt / 주석 9pt (dart_report 와 동일 규칙).
민감도·커버리지는 엑셀 수식으로 계산 → 계수·룰 셀만 고치면 재계산."""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

FONT = "맑은 고딕"
NAVY, LBLUE, ORG, RED = "00338D", "0091DA", "ED7D31", "C00000"
F_TITLE = Font(name=FONT, size=14, bold=True, color=NAVY)
F_HDR = Font(name=FONT, size=11, bold=True, color="FFFFFF")
F_BODY = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_NOTE = Font(name=FONT, size=9, color="7F7F7F")
F_SEC = Font(name=FONT, size=11, bold=True, color=NAVY)
FILL_HDR = PatternFill("solid", fgColor=NAVY)
FILL_LBL = PatternFill("solid", fgColor="F2F2F2")
FILL_IN = PatternFill("solid", fgColor="FFF2CC")  # 사용자 입력 셀
FILL_KEY = PatternFill("solid", fgColor="DDEBF7")
BOX = Border(bottom=Side(style="thin", color="D9D9D9"))
STATE_COLOR = {"상승": RED, "하락": NAVY, "안정": LBLUE}


def _hdr(ws, row, labels, start=1):
    for i, t in enumerate(labels):
        c = ws.cell(row=row, column=start + i, value=t)
        c.font, c.fill, c.border = F_HDR, FILL_HDR, BOX
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 22


def _title(ws, text, sub):
    ws["A1"], ws["A2"] = text, sub
    ws["A1"].font, ws["A2"].font = F_TITLE, F_NOTE
    ws.sheet_view.showGridLines = False


def _cell(ws, r, c, v, fmt=None, font=F_BODY, fill=None, align="right"):
    x = ws.cell(row=r, column=c, value=v)
    x.font, x.border = font, BOX
    x.alignment = Alignment(horizontal=align, vertical="center")
    if fmt:
        x.number_format = fmt
    if fill:
        x.fill = fill
    return x


def _ym(ym):
    return f"{ym[:4]}.{ym[4:6]}" if ym else "-"


def _fmt(kind):
    return "0.00" if kind == "rate" else "#,##0.0"


def build_workbook(dash: dict, out_path: str) -> None:
    inds, months = dash["indicators"], dash["months"]
    sub = f"기준월 {_ym(dash['end'])} · 생성일 {dash['generated']} · 출처 {dash['source_label']}" + (" · ※ 오프라인 예시 데이터 (실제값 아님)" if dash.get("sample") else "")
    wb = Workbook()

    # ── 1. 요약 ──
    ws = wb.active
    ws.title = "요약"
    _title(ws, "거시지표 대시보드 — 국면 요약", sub)
    for col, w in zip("ABCDEFGH", (18, 18, 10, 12, 12, 12, 12, 30)):
        ws.column_dimensions[col].width = w
    ws["A4"] = "국면 신호등 (3개월 vs 12개월 이동평균)"
    ws["A4"].font = F_SEC
    _hdr(ws, 5, ["구분", "기준 지표", "판정", "3M 평균", "12M 평균", "괴리", "", "판정 기준"])
    th = dash["thresholds"]
    by = {i["key"]: i for i in inds}
    r = 6
    for s in dash["signals"]:
        kind = by[s["key"]]["kind"]
        _cell(ws, r, 1, s["title"], font=F_BOLD, fill=FILL_LBL, align="left")
        _cell(ws, r, 2, s["name"], align="left")
        _cell(ws, r, 3, s["state"], font=Font(name=FONT, size=10, bold=True, color=STATE_COLOR.get(s["state"], "7F7F7F")), align="center")
        _cell(ws, r, 4, s.get("ma3"), _fmt(kind))
        _cell(ws, r, 5, s.get("ma12"), _fmt(kind))
        _cell(ws, r, 6, s.get("gap"), '+0.00"%p";-0.00"%p"' if kind == "rate" else "+0.0%;-0.0%")
        _cell(ws, r, 8, f"±{th['rate']:.2f}%p 초과" if kind == "rate" else f"±{th[kind] * 100:.0f}% 초과", font=F_NOTE, align="left")
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="지표별 최근값").font = F_SEC
    r += 1
    _hdr(ws, r, ["구분", "지표", "기준월", "최근값", "단위", "전월 대비", "전년 대비", "국면"])
    for i in inds:
        r += 1
        pct = '+0.00"%p";-0.00"%p"' if i["kind"] == "rate" else "+0.0%;-0.0%"
        _cell(ws, r, 1, i["group"], fill=FILL_LBL, align="left")
        _cell(ws, r, 2, i["name"], align="left")
        _cell(ws, r, 3, _ym(i["last_ym"]), align="center")
        _cell(ws, r, 4, i["last"], _fmt(i["kind"]))
        _cell(ws, r, 5, i.get("unit") or "", align="center")
        _cell(ws, r, 6, i["mom"], pct)
        _cell(ws, r, 7, i["yoy"], pct)
        st = i["regime"]["state"]
        _cell(ws, r, 8, st, font=Font(name=FONT, size=10, bold=True, color=STATE_COLOR.get(st, "7F7F7F")), align="center")
    r += 2
    for t in ("목적: 가격 예측이 아닌 국면 판정·민감도 표시", "원가 영향·권장 커버리지는 사용자 입력 계수·룰 기반 추정치", "판정 불가: 최근 12개월 중 결측 존재"):
        ws.cell(row=r, column=1, value="· " + t).font = F_NOTE
        r += 1

    # ── 2. 데이터 (36개월) ──
    wd = wb.create_sheet("데이터")
    _title(wd, f"지표별 추이 (최근 {len(months)}개월)", sub)
    wd.column_dimensions["A"].width = 10
    _hdr(wd, 4, ["월"] + [f"{i['name']}\n({i.get('unit') or ''})" for i in inds])
    wd.row_dimensions[4].height = 36
    for k, ym in enumerate(months):
        _cell(wd, 5 + k, 1, _ym(ym), align="center", fill=FILL_LBL)
        for j, i in enumerate(inds):
            _cell(wd, 5 + k, 2 + j, i["values"][k], _fmt(i["kind"]))
    for j in range(len(inds)):
        wd.column_dimensions[get_column_letter(2 + j)].width = 13
    wd.freeze_panes = "B5"
    data_row = {ym: 5 + k for k, ym in enumerate(months)}
    col_of = {i["key"]: get_column_letter(2 + j) for j, i in enumerate(inds)}
    # 차트: 환율 3종 (단일 축)
    fx = [i for i in inds if i["kind"] == "fx"]
    if fx:
        ch = LineChart()
        ch.title, ch.height, ch.width = "환율 추이", 8, 18
        for i in fx:
            c = 2 + inds.index(i)
            ch.add_data(Reference(wd, min_col=c, min_row=4, max_row=4 + len(months)), titles_from_data=True)
        ch.set_categories(Reference(wd, min_col=1, min_row=5, max_row=4 + len(months)))
        for s, color in zip(ch.series, (NAVY, LBLUE, ORG)):
            s.graphicalProperties.line.solidFill = color
            s.smooth = False
        wd.add_chart(ch, f"{get_column_letter(len(inds) + 3)}4")

    # ── 3. 민감도 (수식) ──
    wsn = wb.create_sheet("민감도")
    _title(wsn, "민감도 시트 — 월별 원가 영향 (추정)", sub)
    wsn.column_dimensions["A"].width = 24
    for col in "BCDEFG":
        wsn.column_dimensions[col].width = 14
    wsn["A4"] = "① 계수 입력 (노란 셀) — 동인 1단위 ↑ 시 월 원가 증가액, 억원"
    wsn["A4"].font = F_SEC
    _hdr(wsn, 5, ["동인", "계수(억원)", "단위"])
    drv = [d for d in dash["drivers"] if d["key"] in col_of]
    coef_cell = {}
    for k, d in enumerate(drv):
        rr = 6 + k
        _cell(wsn, rr, 1, d["label"], fill=FILL_LBL, align="left")
        _cell(wsn, rr, 2, d["coef"], "#,##0.0", font=F_BOLD, fill=FILL_IN)
        _cell(wsn, rr, 3, "10원" if by[d["key"]]["kind"] == "fx" else "1%", align="center")
        coef_cell[d["key"]] = f"$B${rr}"
    r0 = 6 + len(drv) + 1
    wsn.cell(row=r0, column=1, value="② 월별 원가 영향 (추정, 억원) = Σ 계수 × 전년 동월 대비 동인 변화(단위수)").font = F_SEC
    _hdr(wsn, r0 + 1, ["월"] + [by[d["key"]]["name"] for d in drv] + ["합계(추정)"])
    imp_months = [m for m in months[-12:] if data_row.get(m) and data_row[m] - 12 >= 5]
    for k, ym in enumerate(imp_months):
        rr = r0 + 2 + k
        cur, prev = data_row[ym], data_row[ym] - 12
        _cell(wsn, rr, 1, _ym(ym), align="center", fill=FILL_LBL)
        for j, d in enumerate(drv):
            col = col_of[d["key"]]
            a, b = f"데이터!{col}{cur}", f"데이터!{col}{prev}"
            if by[d["key"]]["kind"] == "fx":
                f = f'=IF(OR({a}="",{b}=""),"",({a}-{b})/10*{coef_cell[d["key"]]})'
            else:
                f = f'=IF(OR({a}="",{b}="",{b}=0),"",({a}/{b}-1)*100*{coef_cell[d["key"]]})'
            _cell(wsn, rr, 2 + j, f, '#,##0.0;(#,##0.0);"-"')
        last = get_column_letter(1 + len(drv))
        _cell(wsn, rr, 2 + len(drv), f"=SUM(B{rr}:{last}{rr})", '#,##0.0;(#,##0.0);"-"', font=F_BOLD, fill=FILL_KEY)
    rr = r0 + 3 + len(imp_months)
    for t in ("추정: 계수는 사용자 입력값, 동인 외 요인(물량·단가 협상 등) 미반영", "양수 = 원가 증가 · 환율은 10원 단위, 수입물가는 1% 단위"):
        wsn.cell(row=rr, column=1, value="· " + t).font = F_NOTE
        rr += 1

    # ── 4. 재고 커버리지 (수식) ──
    wc = wb.create_sheet("재고커버리지")
    _title(wc, "권장 재고 커버리지 (추정)", sub)
    for col, w in zip("ABCD", (18, 14, 14, 30)):
        wc.column_dimensions[col].width = w
    wc["A4"] = "① 변동성 구간별 룰 (노란 셀 편집, 하한 오름차순)"
    wc["A4"].font = F_SEC
    _hdr(wc, 5, ["변동성 하한(%)", "상한(%)", "커버리지(주)", "비고"])
    rules = dash["coverage_rules"]
    for k, ru in enumerate(rules):
        rr = 6 + k
        _cell(wc, rr, 1, ru["lo"], "0.0", fill=FILL_IN)
        _cell(wc, rr, 2, ru["hi"], "0.0", fill=FILL_IN)
        _cell(wc, rr, 3, ru["weeks"], "0", font=F_BOLD, fill=FILL_IN)
        _cell(wc, rr, 4, ru["note"], align="left")
    last = 5 + len(rules)
    rr = last + 2
    wc.cell(row=rr, column=1, value="② 현재 판정").font = F_SEC
    _cell(wc, rr + 1, 1, "원자재 변동성(%)", fill=FILL_LBL, align="left")
    _cell(wc, rr + 1, 2, dash["volatility"], "0.0", font=F_BOLD)
    _cell(wc, rr + 2, 1, "권장 커버리지(주)", fill=FILL_KEY, font=F_BOLD, align="left")
    _cell(wc, rr + 2, 2, f'=IFERROR(LOOKUP(B{rr + 1},A6:A{last},C6:C{last}),"")', "0", font=F_BOLD, fill=FILL_KEY)
    _cell(wc, rr + 2, 3, "추정", font=Font(name=FONT, size=10, bold=True, color=ORG), align="center")
    wc.cell(row=rr + 4, column=1, value="· 변동성 = 수입물가(원재료) 최근 12개월 월간 변화율 표준편차").font = F_NOTE
    wc.cell(row=rr + 5, column=1, value="· 룰은 예시 기준 — 회사 리드타임·보관비용에 맞게 수정").font = F_NOTE

    # ── 5. 출처 ──
    wsrc = wb.create_sheet("출처")
    _title(wsrc, "출처 · 기준", sub)
    for col, w in zip("ABCDE", (18, 34, 34, 12, 12)):
        wsrc.column_dimensions[col].width = w
    _hdr(wsrc, 4, ["지표", "통계표", "항목", "단위", "최근 기준월"])
    for k, i in enumerate(inds):
        s = i.get("source") or {}
        rr = 5 + k
        _cell(wsrc, rr, 1, i["name"], fill=FILL_LBL, align="left")
        _cell(wsrc, rr, 2, f"{s.get('stat', '')} {s.get('stat_name', '')}".strip(), align="left")
        _cell(wsrc, rr, 3, " · ".join(s.get("items", [])), align="left")
        _cell(wsrc, rr, 4, i.get("unit") or "", align="center")
        _cell(wsrc, rr, 5, _ym(i["last_ym"]), align="center")
    rr = 6 + len(inds)
    for t in (f"출처: {dash['source_label']} · 기준일 {dash['generated']}", f"원자재 외부 CSV: {dash.get('extra_label') or '없음'}",
              "국면 판정 = 3개월 이동평균 vs 12개월 이동평균", "추정 항목: 민감도 원가 영향, 권장 재고 커버리지"):
        wsrc.cell(row=rr, column=1, value="· " + t).font = F_NOTE
        rr += 1

    wb.save(out_path)
