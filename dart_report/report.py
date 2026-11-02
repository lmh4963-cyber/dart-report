"""엑셀 리포트 생성 — 맑은 고딕, 제목 14pt / 머리글 11pt / 본문 10pt / 주석 9pt (정수 pt 통일)."""
from __future__ import annotations

from datetime import date

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .metrics import EOK

FONT = "맑은 고딕"
NAVY = "1F3864"
F_TITLE = Font(name=FONT, size=14, bold=True, color=NAVY)
F_HDR = Font(name=FONT, size=11, bold=True, color="FFFFFF")
F_BODY = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
F_NOTE = Font(name=FONT, size=9, color="7F7F7F")
F_SEC = Font(name=FONT, size=11, bold=True, color=NAVY)
FILL_HDR = PatternFill("solid", fgColor=NAVY)
FILL_LBL = PatternFill("solid", fgColor="F2F2F2")
FILL_KEY = PatternFill("solid", fgColor="DDEBF7")
THIN = Side(style="thin", color="D9D9D9")
BOX = Border(bottom=THIN)
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
PCT = '0.0%;(0.0%);"-"'
MULT = '0.00"x";(0.00"x");"-"'


def _hdr(ws, row, labels, start=1):
    for i, t in enumerate(labels):
        c = ws.cell(row=row, column=start + i, value=t)
        c.font, c.fill, c.border = F_HDR, FILL_HDR, BOX
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 22


def _title(ws, text, sub):
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    ws["A2"] = sub
    ws["A2"].font = F_NOTE
    ws.sheet_view.showGridLines = False


def _row(ws, r, label, values, fmt, key=False, bold=False):
    c = ws.cell(row=r, column=1, value=label)
    c.font = F_BOLD if (key or bold) else F_BODY
    c.fill = FILL_KEY if key else FILL_LBL
    c.border = BOX
    for i, v in enumerate(values):
        cell = ws.cell(row=r, column=2 + i, value=v)
        cell.font = F_BOLD if (key or bold) else F_BODY
        cell.number_format = fmt
        cell.alignment = Alignment(horizontal="right")
        cell.border = BOX
        if key:
            cell.fill = FILL_KEY


def _eok(v):
    return None if v is None else v / EOK


def build_workbook(meta: dict, table: dict, comments: list[str], extras: dict, out_path: str):
    ys = table["summary"]["years"]
    rows = table["rows"]
    yl = [f"FY{y}" for y in ys]
    wb = Workbook()

    # ── 1. 요약 ──
    ws = wb.active
    ws.title = "요약"
    _title(ws, f"{meta['corp_name']} 기업분석 리포트", f"기준일 {date.today().isoformat()} · 출처 OpenDART 사업보고서({meta.get('fs_label','연결')}) · 단위 억원")
    ws.column_dimensions["A"].width = 26
    for i in range(len(ys)):
        ws.column_dimensions[get_column_letter(2 + i)].width = 13
    ws.column_dimensions[get_column_letter(2 + len(ys))].width = 60

    ws["A4"] = "기업 개요"
    ws["A4"].font = F_SEC
    info = [("회사명", meta.get("corp_name")), ("종목코드 / 시장", f"{meta.get('stock_code','')} / {meta.get('market','')}"), ("대표자", meta.get("ceo_nm")), ("업종", meta.get("induty")),
            ("설립일", meta.get("est_dt")), ("결산월", meta.get("acc_mt")), ("주소", meta.get("adres")), ("홈페이지", meta.get("hm_url"))]
    r = 5
    for k, v in info:
        ws.cell(row=r, column=1, value=k).font = F_BOLD
        ws.cell(row=r, column=1).fill = FILL_LBL
        ws.cell(row=r, column=2, value=v or "").font = F_BODY
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=2 + len(ys))
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="핵심 지표").font = F_SEC
    r += 1
    _hdr(ws, r, ["항목"] + yl)
    r += 1
    key_rows = [
        ("매출액", "revenue", NUM, True), ("영업이익", "op", NUM, True), ("당기순이익", "ni", NUM, True),
        ("영업이익률", "opm", PCT, False), ("순이익률", "npm", PCT, False), ("ROE", "roe", PCT, False),
        ("자산총계", "assets", NUM, False), ("부채비율", "debt_ratio", PCT, False), ("순차입금(−=순현금)", "net_debt", NUM, False),
        ("영업현금흐름", "ocf", NUM, False), ("FCF", "fcf", NUM, False),
    ]
    for label, k, fmt, key in key_rows:
        vals = [(_eok(rows[y].get(k)) if fmt == NUM else rows[y].get(k)) for y in ys]
        _row(ws, r, label, vals, fmt, key=key)
        r += 1
    s = table["summary"]
    _row(ws, r, f"매출 CAGR ({ys[0]}~{ys[-1]})", [s.get("rev_cagr")] + [None] * (len(ys) - 1), PCT)
    r += 1
    _row(ws, r, f"영업이익 CAGR ({ys[0]}~{ys[-1]})", [s.get("op_cagr")] + [None] * (len(ys) - 1), PCT)
    r += 2

    ws.cell(row=r, column=1, value="핵심 코멘트").font = F_SEC
    r += 1
    for c in comments:
        ws.cell(row=r, column=1, value="· " + c).font = F_BODY
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2 + len(ys))
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="주: 재무 수치는 사업보고서 공시값 그대로이며 추정·보정 없음. 결측 항목은 '-' 표시. 기업 판단·투자 권유 아님.").font = F_NOTE

    # 차트: 매출 막대 + 영업이익률 선
    cs = wb.create_sheet("_chart")
    cs["A1"] = "연도"
    cs["B1"] = "매출액(억)"
    cs["C1"] = "영업이익률"
    for i, y in enumerate(ys):
        cs.cell(row=2 + i, column=1, value=f"FY{y}")
        cs.cell(row=2 + i, column=2, value=_eok(rows[y].get("revenue")))
        cs.cell(row=2 + i, column=3, value=rows[y].get("opm"))
    bar = BarChart()
    bar.type = "col"
    bar.title = "매출액(억) · 영업이익률"
    bar.add_data(Reference(cs, min_col=2, min_row=1, max_row=1 + len(ys)), titles_from_data=True)
    bar.set_categories(Reference(cs, min_col=1, min_row=2, max_row=1 + len(ys)))
    bar.y_axis.title = "억원"
    bar.y_axis.majorGridlines = None
    bar.dataLabels = DataLabelList()
    bar.dataLabels.showVal = True
    bar.series[0].graphicalProperties.solidFill = "0091DA"
    line = LineChart()
    line.add_data(Reference(cs, min_col=3, min_row=1, max_row=1 + len(ys)), titles_from_data=True)
    line.y_axis.axId = 200
    line.y_axis.number_format = "0%"
    line.y_axis.crosses = "max"
    line.series[0].graphicalProperties.line.solidFill = "ED7D31"
    line.series[0].marker.symbol = "circle"
    bar += line
    bar.height, bar.width = 8, 18
    ws.add_chart(bar, f"{get_column_letter(3 + len(ys))}4")
    cs.sheet_state = "hidden"

    # ── 2. 손익 ──
    ws2 = wb.create_sheet("손익")
    _title(ws2, "손익계산서 추이", "단위 억원 · 비율은 매출 대비")
    ws2.column_dimensions["A"].width = 24
    _hdr(ws2, 4, ["항목"] + yl)
    r = 5
    for label, k, fmt, key in [("매출액", "revenue", NUM, True), ("매출원가", "cogs", NUM, False), ("매출총이익", "gross", NUM, False), ("매출총이익률", "gpm", PCT, False),
                              ("판매비와관리비", "sga", NUM, False), ("영업이익", "op", NUM, True), ("영업이익률", "opm", PCT, False),
                              ("법인세차감전순이익", "pretax", NUM, False), ("법인세비용", "tax", NUM, False), ("당기순이익", "ni", NUM, True), ("지배주주순이익", "ni_owner", NUM, False), ("순이익률", "npm", PCT, False),
                              ("매출 증가율", "rev_growth", PCT, False), ("영업이익 증가율", "op_growth", PCT, False), ("기본주당이익(원)", "eps", '#,##0;(#,##0);"-"', False)]:
        vals = [(_eok(rows[y].get(k)) if fmt == NUM else rows[y].get(k)) for y in ys]
        _row(ws2, r, label, vals, fmt, key=key)
        r += 1

    # ── 3. 재무상태 ──
    ws3 = wb.create_sheet("재무상태")
    _title(ws3, "재무상태표 추이", "단위 억원 · 기말 기준")
    ws3.column_dimensions["A"].width = 24
    _hdr(ws3, 4, ["항목"] + yl)
    r = 5
    for label, k, fmt, key in [("자산총계", "assets", NUM, True), ("유동자산", "cur_assets", NUM, False), ("현금및현금성자산", "cash", NUM, False), ("단기금융상품", "st_fin", NUM, False), ("매출채권", "receivables", NUM, False), ("재고자산", "inventories", NUM, False),
                              ("유형자산", "ppe", NUM, False), ("무형자산", "intangibles", NUM, False),
                              ("부채총계", "liabilities", NUM, True), ("유동부채", "cur_liab", NUM, False), ("총차입금", "borrowings", NUM, False),
                              ("자본총계", "equity", NUM, True), ("자본금", "capital", NUM, False), ("이익잉여금", "retained", NUM, False),
                              ("부채비율", "debt_ratio", PCT, False), ("유동비율", "current_ratio", PCT, False), ("자기자본비율", "equity_ratio", PCT, False), ("순차입금", "net_debt", NUM, False), ("순차입금/영업이익", "net_debt_to_op", MULT, False)]:
        vals = [(_eok(rows[y].get(k)) if fmt == NUM else rows[y].get(k)) for y in ys]
        _row(ws3, r, label, vals, fmt, key=key)
        r += 1

    # ── 4. 현금흐름 ──
    ws4 = wb.create_sheet("현금흐름")
    _title(ws4, "현금흐름표 추이", "단위 억원 · CAPEX = 유형+무형자산 취득 · FCF = 영업CF − CAPEX")
    ws4.column_dimensions["A"].width = 24
    _hdr(ws4, 4, ["항목"] + yl)
    r = 5
    for label, k, fmt, key in [("영업활동현금흐름", "ocf", NUM, True), ("투자활동현금흐름", "icf", NUM, False), ("재무활동현금흐름", "fcf_fin", NUM, False), ("CAPEX", "capex", NUM, False), ("FCF", "fcf", NUM, True),
                              ("배당금 지급", "dividends_paid", NUM, False), ("이자 지급", "interest_paid", NUM, False), ("영업CF/영업이익", "ocf_to_op", PCT, False), ("배당성향", "payout", PCT, False)]:
        vals = [(_eok(rows[y].get(k)) if fmt == NUM else rows[y].get(k)) for y in ys]
        _row(ws4, r, label, vals, fmt, key=key)
        r += 1
    ws4.cell(row=r + 1, column=1, value="주: 현금흐름 항목은 전체 재무제표(fnlttSinglAcntAll) 조회가 가능한 연도만 채워짐. 요약 API만 가능한 연도는 '-'.").font = F_NOTE

    # ── 5. 지분·배당·인원 ──
    ws5 = wb.create_sheet("지분·배당")
    _title(ws5, "최대주주 · 배당 · 임직원", f"FY{ys[-1]} 사업보고서 기준")
    ws5.column_dimensions["A"].width = 24
    for col in "BCDEF":
        ws5.column_dimensions[col].width = 16
    r = 4
    ws5.cell(row=r, column=1, value="최대주주 및 특수관계인").font = F_SEC
    r += 1
    _hdr(ws5, r, ["성명", "관계", "주식 종류", "기말 주식수", "기말 지분율"])
    r += 1
    for h in extras.get("holders", [])[:15]:
        for i, v in enumerate([h.get("nm"), h.get("relate"), h.get("stock_knd"), _num(h.get("trmend_posesn_stock_co")), _pct(h.get("trmend_posesn_stock_qota_rt"))]):
            c = ws5.cell(row=r, column=1 + i, value=v)
            c.font = F_BODY
            c.border = BOX
            if i >= 3:
                c.number_format = NUM if i == 3 else PCT
                c.alignment = Alignment(horizontal="right")
        r += 1
    if not extras.get("holders"):
        ws5.cell(row=r, column=1, value="데이터 없음").font = F_NOTE
        r += 1
    r += 1
    ws5.cell(row=r, column=1, value="배당").font = F_SEC
    r += 1
    _hdr(ws5, r, ["구분", "주식 종류", "당기", "전기", "전전기"])
    r += 1
    for d in extras.get("dividends", []):
        for i, v in enumerate([d.get("se"), d.get("stock_knd") or "", _num(d.get("thstrm")), _num(d.get("frmtrm")), _num(d.get("lwfr"))]):
            c = ws5.cell(row=r, column=1 + i, value=v)
            c.font = F_BODY
            c.border = BOX
            if i >= 2:
                c.number_format = NUM1
                c.alignment = Alignment(horizontal="right")
        r += 1
    if not extras.get("dividends"):
        ws5.cell(row=r, column=1, value="데이터 없음").font = F_NOTE
        r += 1
    r += 1
    ws5.cell(row=r, column=1, value="임직원").font = F_SEC
    r += 1
    _hdr(ws5, r, ["사업부문", "성별", "정규직", "계약직", "합계", "평균 근속연수"])
    r += 1
    for e in extras.get("employees", []):
        for i, v in enumerate([e.get("fo_bbm"), e.get("sexdstn"), _num(e.get("rgllbr_co")), _num(e.get("cnttk_co")), _num(e.get("sm")), e.get("avrg_cnwk_sdytrn")]):
            c = ws5.cell(row=r, column=1 + i, value=v)
            c.font = F_BODY
            c.border = BOX
            if 2 <= i <= 4:
                c.number_format = NUM
                c.alignment = Alignment(horizontal="right")
        r += 1
    if not extras.get("employees"):
        ws5.cell(row=r, column=1, value="데이터 없음").font = F_NOTE

    # ── 6. 최근 공시 ──
    ws6 = wb.create_sheet("최근 공시")
    _title(ws6, "최근 1년 공시 목록", "출처 OpenDART 공시검색 · 최신순")
    ws6.column_dimensions["A"].width = 12
    ws6.column_dimensions["B"].width = 60
    ws6.column_dimensions["C"].width = 14
    ws6.column_dimensions["D"].width = 18
    _hdr(ws6, 4, ["접수일", "보고서명", "제출인", "접수번호"])
    r = 5
    for d in extras.get("disclosures", []):
        for i, v in enumerate([_dt(d.get("rcept_dt")), d.get("report_nm"), d.get("flr_nm"), d.get("rcept_no")]):
            c = ws6.cell(row=r, column=1 + i, value=v)
            c.font = F_BODY
            c.border = BOX
        if d.get("rcept_no"):
            ws6.cell(row=r, column=4).hyperlink = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={d['rcept_no']}"
            ws6.cell(row=r, column=4).font = Font(name=FONT, size=10, color="0563C1", underline="single")
        r += 1
    if not extras.get("disclosures"):
        ws6.cell(row=r, column=1, value="데이터 없음").font = F_NOTE

    # ── 7. 출처 ──
    ws7 = wb.create_sheet("출처")
    _title(ws7, "데이터 출처 · 산식", "")
    ws7.column_dimensions["A"].width = 26
    ws7.column_dimensions["B"].width = 90
    r = 4
    for k, v in [("재무제표", "OpenDART 단일회사 전체 재무제표(fnlttSinglAcntAll) / 주요계정(fnlttSinglAcnt), 사업보고서(11011) 기준"),
                 ("연결·별도", meta.get("fs_label", "연결")), ("접수번호", ", ".join(meta.get("rcept_nos", [])) or "-"),
                 ("ROE / ROA", "지배주주순이익 ÷ 평균 자본총계 / 평균 자산총계 (전년 값 없으면 기말)"),
                 ("순차입금", "단기차입금 + 유동성장기차입금 + 장기차입금 + 사채 − 현금및현금성자산 − 단기금융상품"),
                 ("FCF", "영업활동현금흐름 − (유형자산 취득 + 무형자산 취득)"), ("CAGR", "(기말 ÷ 기초)^(1/연수) − 1"),
                 ("기업 개황", "OpenDART 기업개황(company)"), ("지분·배당·임직원", "최대주주 현황(hyslrSttus) · 배당에 관한 사항(alotMatter) · 직원 현황(empSttus)"),
                 ("생성", f"dart-report · {date.today().isoformat()}")]:
        ws7.cell(row=r, column=1, value=k).font = F_BOLD
        ws7.cell(row=r, column=1).fill = FILL_LBL
        ws7.cell(row=r, column=2, value=v).font = F_BODY
        ws7.cell(row=r, column=2).alignment = Alignment(wrap_text=True)
        r += 1

    for sh in wb.worksheets:
        sh.freeze_panes = "B5" if sh.title not in ("요약", "출처", "_chart") else None
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.page_setup.fitToHeight = 0
        sh.sheet_properties.pageSetUpPr.fitToPage = True
    wb.save(out_path)
    return out_path


def _num(s):
    from .extract import to_num
    return to_num(s)


def _pct(s):
    v = _num(s)
    return None if v is None else v / 100


def _dt(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if s and len(s) == 8 else s
