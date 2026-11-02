"""엑셀 추가 시트 — 분기실적 · 동종비교 · 거시연결. 글꼴·크기 규칙은 report.py 와 동일 (맑은 고딕, 14/11/10/9pt)."""
from __future__ import annotations

from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .metrics import EOK
from .peers import PEER_METRICS
from .quarter import bs_rows, quarter_rows
from .report import BOX, F_BODY, F_BOLD, F_NOTE, F_SEC, FILL_KEY, FILL_LBL, FONT, NUM, NUM1, PCT, _hdr, _title

FILL_IN = PatternFill("solid", fgColor="FFF2CC")  # 사용자 입력 셀
PP = '+0.0"%p";-0.0"%p";"-"'
F_EST = Font(name=FONT, size=10, bold=True, color="ED7D31")


def _c(ws, r, col, v, fmt=None, font=F_BODY, fill=None, align="right"):
    x = ws.cell(row=r, column=col, value=v)
    x.font, x.border = font, BOX
    x.alignment = Alignment(horizontal=align, vertical="center")
    if fmt:
        x.number_format = fmt
    if fill:
        x.fill = fill
    return x


def _eok(v):
    return None if v is None else v / EOK


def quarter_sheet(wb, qd: dict, corp_name: str):
    ws = wb.create_sheet("분기실적")
    y, lbl = qd["year"], qd["label"]
    _title(ws, f"{corp_name} {y}년 {lbl} 실적", f"출처 OpenDART {lbl}보고서({qd['fs_label']}) · 접수번호 {qd.get('rcept_no') or '-'} · 단위 억원 · 공시값 그대로")
    ws.column_dimensions["A"].width = 24
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 14
    ws["A4"] = f"손익·현금흐름 — 누적 {qd['months']}개월 vs 전년 동기"
    ws["A4"].font = F_SEC
    _hdr(ws, 5, ["항목", f"{y} 누적", f"{y - 1} 누적", "증감률", f"{y} 해당분기", f"{y - 1} 해당분기", "증감률"])
    r = 6
    for row in quarter_rows(qd):
        amt = row["kind"] == "amt"
        conv = _eok if amt else (lambda v: v)
        key = row["label"] in ("매출액", "영업이익")
        _c(ws, r, 1, row["label"], font=F_BOLD if key else F_BODY, fill=FILL_KEY if key else FILL_LBL, align="left")
        _c(ws, r, 2, conv(row["cum"]), NUM1 if amt else PCT)
        _c(ws, r, 3, conv(row["cum_prev"]), NUM1 if amt else PCT)
        _c(ws, r, 4, row["cum_yoy"] if amt else (None if row["cum_yoy"] is None else row["cum_yoy"] * 100), PCT if amt else PP)
        _c(ws, r, 5, conv(row["q"]), NUM1 if amt else PCT)
        _c(ws, r, 6, conv(row["q_prev"]), NUM1 if amt else PCT)
        _c(ws, r, 7, row["q_yoy"] if amt else (None if row["q_yoy"] is None else row["q_yoy"] * 100), PCT if amt else PP)
        r += 1
    r += 1
    ws.cell(row=r, column=1, value=f"재무상태 — {lbl}말 vs 직전 사업연도말").font = F_SEC
    r += 1
    _hdr(ws, r, ["항목", f"{y} {lbl}말", f"{y - 1}말", "증감"])
    r += 1
    for row in bs_rows(qd):
        amt = row["kind"] == "amt"
        _c(ws, r, 1, row["label"], fill=FILL_LBL, align="left")
        _c(ws, r, 2, _eok(row["cur"]) if amt else row["cur"], NUM1 if amt else PCT)
        _c(ws, r, 3, _eok(row["prev"]) if amt else row["prev"], NUM1 if amt else PCT)
        _c(ws, r, 4, _eok(row["chg"]) if amt else (None if row["chg"] is None else row["chg"] * 100), NUM1 if amt else PP)
        r += 1
    r += 1
    for t in ("손익 누적 = 당기 누적(thstrm_add_amount), 해당분기 = 3개월(thstrm_amount)", "현금흐름은 누적값만 공시 → 해당분기 '-'",
              "비율 증감은 %p", "CAPEX = 유형+무형자산 취득, FCF = 영업CF − CAPEX"):
        ws.cell(row=r, column=1, value="· " + t).font = F_NOTE
        r += 1


def peers_sheet(wb, peers: list[dict]):
    ws = wb.create_sheet("동종비교")
    fy = peers[0]["fy"]
    _title(ws, f"동종업체 비교 (FY{fy})", "출처 OpenDART 사업보고서 · 단위 억원 · 동종업체는 사용자 지정 · 공시값 그대로")
    ws.column_dimensions["A"].width = 22
    for i in range(len(peers) + 1):
        ws.column_dimensions[get_column_letter(2 + i)].width = 15
    _hdr(ws, 4, ["항목"] + [f"{p['name']}\n({p['stock_code'] or '비상장'}·{p['fs_label']})" for p in peers] + ["비교군 중앙값"])
    ws.row_dimensions[4].height = 36
    r = 5
    for label, key, kind in PEER_METRICS:
        _c(ws, r, 1, label, fill=FILL_LBL, align="left")
        vals = [p["values"].get(key) for p in peers]
        conv = (lambda v: _eok(v)) if kind in ("amt", "amt1") else (lambda v: v)
        fmt = {"amt": NUM, "amt1": NUM1, "cnt": NUM}.get(kind, PCT)
        for i, (p, v) in enumerate(zip(peers, vals)):
            _c(ws, r, 2 + i, conv(v), fmt, font=F_BOLD if p["main"] else F_BODY, fill=FILL_KEY if p["main"] else None)
        others = sorted(v for p, v in zip(peers, vals) if not p["main"] and v is not None)
        med = None
        if others:
            n = len(others)
            med = others[n // 2] if n % 2 else (others[n // 2 - 1] + others[n // 2]) / 2
        _c(ws, r, 2 + len(peers), conv(med) if med is not None else None, fmt)
        r += 1
    r += 1
    for t in ("파란 열 = 분석 대상 회사 · 중앙값은 대상 회사 제외", "매출 CAGR(2개년) = FY-2 → FY 매출 연평균 증가율",
              "ROE = 지배주주순이익(없으면 당기순이익) ÷ 평균 자본총계", "비교 기준(연결·별도)이 회사마다 다를 수 있음 — 머리글 표시 확인",
              "1인당 매출액 = 연결 매출 ÷ 사업보고서 직원 수(회사 단독 기준) — 기준 불일치 참고"):
        ws.cell(row=r, column=1, value="· " + t).font = F_NOTE
        r += 1


def macro_sheet(wb, link: dict, corp_name: str):
    ws = wb.create_sheet("거시연결")
    _title(ws, f"{corp_name} 원가 × 거시지표", f"재무 OpenDART · 거시지표 {link['file']} (macro_dash, 한국은행 ECOS) · 단위 억원 · 원가 영향은 추정")
    ws.column_dimensions["A"].width = 26
    years = link["years"]
    for i in range(len(years)):
        ws.column_dimensions[get_column_letter(2 + i)].width = 12
    ws["A4"] = "① 연도별 원가율 · 거시지표 연평균"
    ws["A4"].font = F_SEC
    _hdr(ws, 5, ["항목"] + [f"FY{e['year']}" for e in years])
    r = 6
    for label, key, fmt in (("매출액", "revenue", NUM), ("매출원가", "cogs", NUM), ("매출원가율", "cogs_ratio", PCT)):
        _c(ws, r, 1, label, font=F_BOLD, fill=FILL_KEY, align="left")
        for i, e in enumerate(years):
            v = e.get(key)
            _c(ws, r, 2 + i, _eok(v) if fmt == NUM else v, fmt)
        r += 1
    for key in link["present"]:
        _c(ws, r, 1, link["names"][key], fill=FILL_LBL, align="left")
        for i, e in enumerate(years):
            m = e["macro"][key]
            x = _c(ws, r, 2 + i, m["avg"], NUM1)
            if m["avg"] is not None and m["months"] < 12:
                x.number_format = NUM1 + '"*"'
        r += 1
    ws.cell(row=r, column=1, value="· * = 12개월 미만 평균 (데이터 기간 제한)").font = F_NOTE
    r += 2
    ws.cell(row=r, column=1, value=f"② 민감도 (노란 셀 계수 입력) — FY{link['base_year'] or '-'} 연평균 vs 전년").font = F_SEC
    r += 1
    _hdr(ws, r, ["동인", "계수(억원/단위·연)", "전년비 변화(단위)", "원가 영향(억원)", "추정"])
    first = r + 1
    for d in link["drivers"]:
        r += 1
        _c(ws, r, 1, d["label"], fill=FILL_LBL, align="left")
        _c(ws, r, 2, d["coef"], NUM1, font=F_BOLD, fill=FILL_IN)
        _c(ws, r, 3, d["delta"], NUM1)
        _c(ws, r, 4, f'=IF(C{r}="","",B{r}*C{r})', NUM1)
        _c(ws, r, 5, "추정", font=F_EST, align="center")
    if link["drivers"]:
        r += 1
        _c(ws, r, 1, "합계", font=F_BOLD, fill=FILL_KEY, align="left")
        _c(ws, r, 4, f"=SUM(D{first}:D{r - 1})", NUM1, font=F_BOLD, fill=FILL_KEY)
        base = next((e for e in years if e["year"] == link["base_year"]), None)
        if base and base.get("cogs"):
            r += 1
            _c(ws, r, 1, f"FY{link['base_year']} 매출원가 대비", fill=FILL_LBL, align="left")
            _c(ws, r, 4, f"=D{r - 1}/{base['cogs'] / EOK:.4f}", PCT)
    r += 2
    for t in ("계수 = 동인 1단위 ↑ 시 연간 원가 증가액(억원) — 사용자 입력 (수입 비중·환헤지 반영해 설정)",
              "원가 영향(추정) = 계수 × 기준연도 연평균의 전년 대비 변화 (환율 10원 / 수입물가 1% 단위)",
              "상관·회귀 분석 아님 — 연도별 수치 병치 + 사용자 가정 기반 추정"):
        ws.cell(row=r, column=1, value="· " + t).font = F_NOTE
        r += 1


def gov_sheet(wb, gov: dict, peers: list[dict], corp_name: str):
    ws = wb.create_sheet("감사·인원")
    fy = gov["fy"]
    _title(ws, f"{corp_name} 감사 · 최대주주 · 인원 · 배당", f"출처 OpenDART FY{fy} 사업보고서 정형 섹션 · 공시값 그대로")
    for col, w in zip("ABCDEFG", (16, 10, 18, 12, 30, 20, 12)):
        ws.column_dimensions[col].width = w
    r = 4
    ws.cell(row=r, column=1, value="① 감사인 · 감사의견 · 핵심감사사항").font = F_SEC
    r += 1
    _hdr(ws, r, ["회사", "사업연도", "감사인", "감사의견", "핵심감사사항", "강조사항", "감사인 교체"])
    comps = [{"name": corp_name, "gov": gov}] + [p for p in peers if not p.get("main")]
    for c in comps:
        rows = (c.get("gov") or {}).get("audit") or []
        for i, a in enumerate(rows):
            r += 1
            prev = rows[i + 1]["auditor"] if i + 1 < len(rows) else None
            _c(ws, r, 1, c["name"], fill=FILL_LBL, align="left")
            _c(ws, r, 2, f"FY{a['year']}", align="center")
            _c(ws, r, 3, a["auditor"], align="left")
            _c(ws, r, 4, a["opinion"], align="center")
            _c(ws, r, 5, a["kam"] or "-", align="left")
            _c(ws, r, 6, a["emphasis"] or "-", align="left")
            _c(ws, r, 7, "교체" if prev and prev != a["auditor"] else "", align="center", font=F_BOLD)
    r += 2
    ws.cell(row=r, column=1, value=f"② 최대주주 및 특수관계인 (FY{fy}말)").font = F_SEC
    r += 1
    _hdr(ws, r, ["성명", "관계", "주식 종류", "기말 주식수", "기말 지분율"])
    h = gov.get("holders") or {}
    for p in h.get("list", []):
        r += 1
        _c(ws, r, 1, p["name"], align="left"); _c(ws, r, 2, p["relate"], align="center"); _c(ws, r, 3, p["kind"], align="center")
        _c(ws, r, 4, p["shares"], NUM); _c(ws, r, 5, None if p["ratio"] is None else p["ratio"] / 100, '0.00%')
    if h.get("total_ratio") is not None:
        r += 1
        _c(ws, r, 1, "보통주 합계", font=F_BOLD, fill=FILL_KEY, align="left"); _c(ws, r, 5, h["total_ratio"] / 100, '0.00%', font=F_BOLD, fill=FILL_KEY)
    r += 2
    ws.cell(row=r, column=1, value=f"③ 인원 · 생산성 (FY{fy}말)").font = F_SEC
    r += 1
    st = gov.get("staff") or {}
    for label, v, fmt in (("직원 수(명)", st.get("total"), NUM), ("정규직 / 계약직", f"{st.get('regular', 0):,.0f} / {st.get('contract', 0):,.0f}" if st else None, None),
                          ("평균 근속연수(년, 인원 가중)", st.get("tenure"), NUM1), ("1인 평균 급여(백만원)", None if st.get("avg_pay") is None else st["avg_pay"] / 1e6, NUM1),
                          ("1인당 매출액(억원)", None if st.get("rev_per_head") is None else st["rev_per_head"] / EOK, NUM1)):
        r += 1
        _c(ws, r, 1, label, fill=FILL_LBL, align="left")
        _c(ws, r, 2, v, fmt, align="right" if fmt else "left")
    r += 2
    ws.cell(row=r, column=1, value="④ 배당 (보통주)").font = F_SEC
    r += 1
    dv = gov.get("div") or []
    _hdr(ws, r, ["항목"] + [f"FY{d['year']}" for d in dv])
    for label, key, fmt in (("주당 현금배당금(원)", "dps", NUM), ("현금배당금총액(백만원)", "total", NUM), ("(연결)현금배당성향(%)", "payout", NUM1), ("현금배당수익률(%)", "yield", NUM1)):
        r += 1
        _c(ws, r, 1, label, fill=FILL_LBL, align="left")
        for i, d in enumerate(dv):
            _c(ws, r, 2 + i, d.get(key), fmt)
    r += 2
    for t in ("감사의견 표의 '교체' = 직전 연도와 감사인 다름", "1인당 매출액 = 연결 매출 ÷ 직원 수(회사 단독 기준) — 기준 불일치 참고",
              "배당성향은 공시값(선언 기준) — 재무제표 시트의 배당성향(현금흐름 지급액 ÷ 순이익)과 다를 수 있음"):
        ws.cell(row=r, column=1, value="· " + t).font = F_NOTE
        r += 1


def add_extra_sheets(wb, meta: dict, table: dict, extras: dict):
    if extras.get("gov"):
        gov_sheet(wb, extras["gov"], extras.get("peers") or [], meta["corp_name"])
    if extras.get("quarter"):
        quarter_sheet(wb, extras["quarter"], meta["corp_name"])
    if extras.get("peers"):
        peers_sheet(wb, extras["peers"])
    if extras.get("macro"):
        macro_sheet(wb, extras["macro"], meta["corp_name"])
