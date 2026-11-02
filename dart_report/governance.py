"""지배구조·감사·인원 정리 — 사업보고서 정형 섹션(감사의견·최대주주·직원·배당) 공시값 그대로."""
from __future__ import annotations

import re

from .extract import to_num

_PERIOD = {"당기": 0, "전기": 1, "전전기": 2}


def audit_rows(rows: list[dict], fy: int) -> list[dict]:
    """감사의견 응답(연결·별도 중복) → 연도별 1행: {year, term, auditor, opinion, kam, emphasis}"""
    out = {}
    for r in rows:
        label = str(r.get("bsns_year", ""))
        m = re.search(r"\((전전기|전기|당기)\)", label)
        if not m:
            continue
        y = fy - _PERIOD[m.group(1)]
        if y in out:
            continue
        kam = (r.get("core_adt_matter") or "").strip()
        emph = (r.get("emphs_matter") or "").strip()
        out[y] = {"year": y, "term": label.replace("\n", " "), "auditor": r.get("adtor") or "", "opinion": r.get("adt_opinion") or "",
                  "kam": "" if kam in ("-", "") else kam, "emphasis": "" if emph in ("-", "") or "없음" in emph else emph}
    return [out[y] for y in sorted(out, reverse=True)]


def holders(rows: list[dict]) -> dict:
    """최대주주 및 특수관계인 — 개별 주주 목록 + 보통주 합계 지분율"""
    people, total = [], None
    for r in rows:
        nm = (r.get("nm") or "").strip()
        rt = to_num(r.get("trmend_posesn_stock_qota_rt"))
        if nm == "계":
            if r.get("stock_knd") == "보통주":
                total = rt
            continue
        people.append({"name": nm, "relate": r.get("relate") or "", "kind": r.get("stock_knd") or "",
                       "shares": to_num(r.get("trmend_posesn_stock_co")), "ratio": rt})
    largest = next((p for p in people if p["relate"] == "최대주주"), people[0] if people else None)
    return {"list": people, "total_ratio": total, "largest": largest}


def _years(s) -> float | None:
    """평균 근속연수 표기('9.8', '7년 2개월') → 연"""
    if s is None:
        return None
    t = str(s).strip()
    m = re.match(r"(\d+)\s*년\s*(?:(\d+)\s*개월)?", t)
    if m:
        return int(m.group(1)) + (int(m.group(2) or 0) / 12)
    return to_num(t)


def staff(rows: list[dict], revenue: float | None = None) -> dict:
    """직원 현황 합계 — 총원·정규직·계약직·가중 평균 근속·1인 평균 급여·1인당 매출(연결 매출 ÷ 직원 수)"""
    tot = reg = con = 0
    tenure_w = pay = 0.0
    seen = False
    for r in rows:
        n = to_num(r.get("sm"))
        if n is None:
            continue
        seen = True
        tot += n
        reg += to_num(r.get("rgllbr_co")) or 0
        con += to_num(r.get("cnttk_co")) or 0
        y = _years(r.get("avrg_cnwk_sdytrn"))
        if y is not None:
            tenure_w += y * n
        pay += to_num(r.get("fyer_salary_totamt")) or 0
    if not seen or not tot:
        return {}
    return {"total": tot, "regular": reg, "contract": con, "tenure": tenure_w / tot if tenure_w else None,
            "avg_pay": pay / tot if pay else None, "rev_per_head": revenue / tot if revenue else None,
            "segments": sorted({r.get("fo_bbm") for r in rows if r.get("fo_bbm")})}


def dividends(rows: list[dict], fy: int) -> list[dict]:
    """배당 핵심 3종(주당 현금배당금·현금배당성향·현금배당수익률, 보통주) × 3개년"""
    want = [("주당 현금배당금(원)", "dps"), ("(연결)현금배당성향(%)", "payout"), ("현금배당수익률(%)", "yield"), ("현금배당금총액(백만원)", "total")]
    out = {y: {"year": y} for y in (fy - 2, fy - 1, fy)}
    for r in rows:
        se = (r.get("se") or "").strip()
        for label, key in want:
            if se == label and r.get("stock_knd") in ("보통주", "-", "", None):
                for col, y in (("thstrm", fy), ("frmtrm", fy - 1), ("lwfr", fy - 2)):
                    v = to_num(r.get(col))
                    if v is not None:
                        out[y][key] = v
    return [out[y] for y in sorted(out)]
