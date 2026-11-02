"""연도별 표준 항목 → 비율·파생지표. 금액은 원 단위 입력, 결과 표시는 억원."""
from __future__ import annotations

EOK = 1e8


def _div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def _sum(*vals):
    vs = [v for v in vals if v is not None]
    return sum(vs) if vs else None


def derive_year(d: dict, prev: dict | None) -> dict:
    cash_like = _sum(d.get("cash"), d.get("st_fin"))
    borrow = _sum(d.get("st_borrow"), d.get("cur_lt_borrow"), d.get("lt_borrow"), d.get("bonds"))
    capex = _sum(d.get("capex_ppe"), d.get("capex_intangible"))
    avg_eq = _div(_sum(d.get("equity"), prev.get("equity")), 2) if prev and prev.get("equity") else d.get("equity")
    avg_as = _div(_sum(d.get("assets"), prev.get("assets")), 2) if prev and prev.get("assets") else d.get("assets")
    ni = d.get("ni_owner") if d.get("ni_owner") is not None else d.get("ni")
    m = {
        "gpm": _div(d.get("gross"), d.get("revenue")),
        "opm": _div(d.get("op"), d.get("revenue")),
        "npm": _div(ni, d.get("revenue")),
        "roe": _div(ni, avg_eq),
        "roa": _div(ni, avg_as),
        "debt_ratio": _div(d.get("liabilities"), d.get("equity")),
        "current_ratio": _div(d.get("cur_assets"), d.get("cur_liab")),
        "equity_ratio": _div(d.get("equity"), d.get("assets")),
        "borrowings": borrow,
        "cash_like": cash_like,
        "net_debt": (borrow or 0) - (cash_like or 0) if (borrow is not None or cash_like is not None) else None,
        "capex": capex,
        "fcf": d.get("ocf") - capex if d.get("ocf") is not None and capex is not None else None,
        "ocf_to_op": _div(d.get("ocf"), d.get("op")),
        "payout": _div(d.get("dividends_paid"), ni),
        "rev_growth": _div(d.get("revenue"), prev.get("revenue")) - 1 if prev and prev.get("revenue") and d.get("revenue") is not None else None,
        "op_growth": _div(d.get("op"), prev.get("op")) - 1 if prev and prev.get("op") and d.get("op") is not None and prev.get("op") > 0 else None,
        "ni_growth": _div(ni, prev.get("ni_owner") or prev.get("ni")) - 1 if prev and (prev.get("ni_owner") or prev.get("ni")) and ni is not None and (prev.get("ni_owner") or prev.get("ni")) > 0 else None,
    }
    if m["net_debt"] is not None and d.get("op") not in (None, 0):
        m["net_debt_to_op"] = m["net_debt"] / d["op"]
    else:
        m["net_debt_to_op"] = None
    return m


def cagr(first, last, years):
    if first in (None, 0) or last is None or years <= 0 or first < 0 or last < 0:
        return None
    return (last / first) ** (1 / years) - 1


def build_table(years_data: dict[int, dict], years: list[int]) -> dict:
    rows = {}
    prev = None
    for y in years:
        d = years_data.get(y, {})
        rows[y] = {**d, **derive_year(d, prev)}
        prev = d
    y0, y1 = years[0], years[-1]
    n = y1 - y0
    summary = {
        "rev_cagr": cagr(years_data.get(y0, {}).get("revenue"), years_data.get(y1, {}).get("revenue"), n),
        "op_cagr": cagr(years_data.get(y0, {}).get("op"), years_data.get(y1, {}).get("op"), n),
        "ni_cagr": cagr(years_data.get(y0, {}).get("ni"), years_data.get(y1, {}).get("ni"), n),
        "years": years,
    }
    return {"rows": rows, "summary": summary}


def comments(table: dict, name: str) -> list[str]:
    """개조식 핵심 코멘트 — 숫자가 있는 항목만 생성"""
    ys = table["summary"]["years"]
    last, first = table["rows"][ys[-1]], table["rows"][ys[0]]
    s = table["summary"]
    out = []
    if last.get("revenue") is not None:
        g = f", 전년 대비 {last['rev_growth']*100:+.1f}%" if last.get("rev_growth") is not None else ""
        c = f", {ys[0]}~{ys[-1]} CAGR {s['rev_cagr']*100:.1f}%" if s.get("rev_cagr") is not None else ""
        out.append(f"매출 {last['revenue']/EOK:,.0f}억 ('{str(ys[-1])[2:]}){g}{c}")
    if last.get("op") is not None and last.get("opm") is not None:
        d = f" (전년 {first_or(table, ys, 'opm')})" if len(ys) > 1 else ""
        out.append(f"영업이익 {last['op']/EOK:,.0f}억 · 영업이익률 {last['opm']*100:.1f}%" + (f", 전년 {table['rows'][ys[-2]]['opm']*100:.1f}%" if len(ys) > 1 and table['rows'][ys[-2]].get('opm') is not None else ""))
    if last.get("roe") is not None:
        out.append(f"ROE {last['roe']*100:.1f}% · ROA {last['roa']*100:.1f}%" if last.get("roa") is not None else f"ROE {last['roe']*100:.1f}%")
    if last.get("debt_ratio") is not None:
        out.append(f"부채비율 {last['debt_ratio']*100:.0f}% · 유동비율 {last['current_ratio']*100:.0f}%" if last.get("current_ratio") is not None else f"부채비율 {last['debt_ratio']*100:.0f}%")
    if last.get("net_debt") is not None:
        nd = last["net_debt"] / EOK
        out.append(f"순현금 {-nd:,.0f}억 (차입 {(last.get('borrowings') or 0)/EOK:,.0f}억 − 현금성 {(last.get('cash_like') or 0)/EOK:,.0f}억)" if nd < 0 else f"순차입금 {nd:,.0f}억 (차입 {(last.get('borrowings') or 0)/EOK:,.0f}억 − 현금성 {(last.get('cash_like') or 0)/EOK:,.0f}억)")
    if last.get("ocf") is not None:
        t = f"영업현금흐름 {last['ocf']/EOK:,.0f}억"
        if last.get("fcf") is not None:
            t += f" · FCF {last['fcf']/EOK:,.0f}억 (CAPEX {last['capex']/EOK:,.0f}억)"
        if last.get("ocf_to_op") is not None:
            t += f" · 영업CF/영업이익 {last['ocf_to_op']*100:.0f}%"
        out.append(t)
    if last.get("payout") is not None:
        out.append(f"배당성향 {last['payout']*100:.1f}% (배당금 {last['dividends_paid']/EOK:,.0f}억)")
    return out


def first_or(table, ys, key):
    v = table["rows"][ys[-2]].get(key) if len(ys) > 1 else None
    return f"{v*100:.1f}%" if v is not None else "–"
