"""분기·반기 실적 — 최신 분·반기보고서의 누적(YTD)·해당 분기 값을 전년 동기와 비교. 공시값 그대로, 추정 없음.

필드 규칙 (OpenDART 분·반기 전체 재무제표):
  손익(IS·CIS): thstrm_add_amount = 당기 누적, thstrm_amount = 해당 분기 3개월, frmtrm_add_amount / frmtrm_q_amount = 전년 동기 누적 / 분기
  현금흐름(CF): thstrm_amount = 당기 누적, 전년 동기 = frmtrm_q_amount (없으면 frmtrm_add_amount·frmtrm_amount)
  재무상태(BS): thstrm_amount = 분기말, frmtrm_amount = 전기말(직전 사업연도말)
"""
from __future__ import annotations

from .client import DartClient
from .extract import MAP, OUTFLOW, SJ_FOR, pick, to_num
from .metrics import _div, _sum

# (보고서코드, 라벨, 누적 개월) — 최신순으로 시도
REPORTS = [("11014", "3분기", 9), ("11012", "반기", 6), ("11013", "1분기", 3)]


def _first(it: dict, *cols):
    for c in cols:
        v = to_num(it.get(c))
        if v is not None:
            return v
    return None


def extract_quarter(items: list[dict]) -> dict:
    """→ {'cum','cum_prev','q','q_prev','bs','bs_prev','cf','cf_prev'} 각 {표준키: 값(원)}"""
    out = {k: {} for k in ("cum", "cum_prev", "q", "q_prev", "bs", "bs_prev", "cf", "cf_prev")}
    for key in MAP:
        it = pick(items, key)
        if not it:
            continue
        sj = SJ_FOR.get(key, ("BS",))[0]
        if sj in ("IS", "CIS"):
            vals = {"cum": _first(it, "thstrm_add_amount", "thstrm_amount"), "cum_prev": _first(it, "frmtrm_add_amount", "frmtrm_amount"),
                    "q": _first(it, "thstrm_amount"), "q_prev": _first(it, "frmtrm_q_amount", "frmtrm_amount")}
        elif sj == "CF":
            vals = {"cf": _first(it, "thstrm_amount"), "cf_prev": _first(it, "frmtrm_q_amount", "frmtrm_add_amount", "frmtrm_amount")}
        else:
            vals = {"bs": _first(it, "thstrm_amount"), "bs_prev": _first(it, "frmtrm_amount")}
        for k, v in vals.items():
            if v is not None:
                out[k][key] = abs(v) if key in OUTFLOW else v
    return out


def _derive(d: dict) -> dict:
    """손익·현금흐름 묶음 하나에 대한 비율"""
    ni = d.get("ni_owner") if d.get("ni_owner") is not None else d.get("ni")
    capex = _sum(d.get("capex_ppe"), d.get("capex_intangible"))
    return {
        "gpm": _div(d.get("gross"), d.get("revenue")), "opm": _div(d.get("op"), d.get("revenue")), "npm": _div(ni, d.get("revenue")),
        "capex": capex, "fcf": d["ocf"] - capex if d.get("ocf") is not None and capex is not None else None,
    }


def _bs_derive(d: dict) -> dict:
    cash_like = _sum(d.get("cash"), d.get("st_fin"))
    borrow = _sum(d.get("st_borrow"), d.get("cur_lt_borrow"), d.get("lt_borrow"), d.get("bonds"))
    return {"cash_like": cash_like, "borrowings": borrow,
            "net_debt": (borrow or 0) - (cash_like or 0) if (borrow is not None or cash_like is not None) else None,
            "debt_ratio": _div(d.get("liabilities"), d.get("equity")), "current_ratio": _div(d.get("cur_assets"), d.get("cur_liab"))}


def latest_quarter(client: DartClient, corp_code: str, year: int, fs_div: str = "CFS") -> dict | None:
    """year 사업연도의 최신 분·반기보고서 (3분기 → 반기 → 1분기 순). 없으면 None"""
    for code, label, months in REPORTS:
        used = fs_div
        items = client.financials_all(corp_code, year, fs_div=used, reprt_code=code)
        if not items and used == "CFS":
            used = "OFS"
            items = client.financials_all(corp_code, year, fs_div=used, reprt_code=code)
        if not items:
            continue
        q = extract_quarter(items)
        cf = {**q["cf"], **{k: v for k, v in q["cum"].items()}}
        cf_prev = {**q["cf_prev"], **{k: v for k, v in q["cum_prev"].items()}}
        return {
            "year": year, "reprt_code": code, "label": label, "months": months, "fs_label": "연결" if used == "CFS" else "별도",
            "rcept_no": next((it.get("rcept_no") for it in items if it.get("rcept_no")), ""),
            **q, "cum_m": _derive(cf), "cum_prev_m": _derive(cf_prev), "q_m": _derive(q["q"]), "q_prev_m": _derive(q["q_prev"]),
            "bs_m": _bs_derive(q["bs"]), "bs_prev_m": _bs_derive(q["bs_prev"]),
        }
    return None


def yoy(a, b):
    if a is None or b in (None, 0) or b < 0:
        return None
    return a / b - 1


def quarter_rows(qd: dict) -> list[dict]:
    """표시용 행 — 금액(원) / 비율. kind: amt·pct"""
    cum, cp, q, qp = qd["cum"], qd["cum_prev"], qd["q"], qd["q_prev"]
    cm, cpm, qm, qpm = qd["cum_m"], qd["cum_prev_m"], qd["q_m"], qd["q_prev_m"]
    rows = []
    for label, key in (("매출액", "revenue"), ("매출총이익", "gross"), ("영업이익", "op"), ("당기순이익", "ni")):
        rows.append({"label": label, "kind": "amt", "cum": cum.get(key), "cum_prev": cp.get(key), "q": q.get(key), "q_prev": qp.get(key)})
    for label, key in (("매출총이익률", "gpm"), ("영업이익률", "opm"), ("순이익률", "npm")):
        rows.append({"label": label, "kind": "pct", "cum": cm.get(key), "cum_prev": cpm.get(key), "q": qm.get(key), "q_prev": qpm.get(key)})
    for label, key in (("영업활동현금흐름", "ocf"), ("CAPEX", "capex"), ("FCF", "fcf")):
        a = qd["cf"].get(key) if key == "ocf" else cm.get(key)
        b = qd["cf_prev"].get(key) if key == "ocf" else cpm.get(key)
        rows.append({"label": label, "kind": "amt", "cum": a, "cum_prev": b, "q": None, "q_prev": None})
    for r in rows:
        r["cum_yoy"] = yoy(r["cum"], r["cum_prev"]) if r["kind"] == "amt" else (None if r["cum"] is None or r["cum_prev"] is None else r["cum"] - r["cum_prev"])
        r["q_yoy"] = yoy(r["q"], r["q_prev"]) if r["kind"] == "amt" else (None if r["q"] is None or r["q_prev"] is None else r["q"] - r["q_prev"])
    return rows


def bs_rows(qd: dict) -> list[dict]:
    b, bp, m, mp = qd["bs"], qd["bs_prev"], qd["bs_m"], qd["bs_prev_m"]
    out = []
    for label, src, key, kind in (("자산총계", "raw", "assets", "amt"), ("부채총계", "raw", "liabilities", "amt"), ("자본총계", "raw", "equity", "amt"),
                                  ("현금성자산(현금+단기금융)", "m", "cash_like", "amt"), ("총차입금", "m", "borrowings", "amt"), ("순차입금(−=순현금)", "m", "net_debt", "amt"),
                                  ("재고자산", "raw", "inventories", "amt"), ("부채비율", "m", "debt_ratio", "pct"), ("유동비율", "m", "current_ratio", "pct")):
        cur, prev = (b.get(key), bp.get(key)) if src == "raw" else (m.get(key), mp.get(key))
        out.append({"label": label, "kind": kind, "cur": cur, "prev": prev,
                    "chg": None if cur is None or prev is None else (cur - prev)})
    return out
