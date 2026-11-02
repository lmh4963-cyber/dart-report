"""동종업체 비교 — 사용자가 지정한 회사들의 최근 연도 핵심 지표를 나란히 비교. 공시값 그대로, 동종업체 선정은 사용자 몫."""
from __future__ import annotations

import sys

from .client import DartClient, DartError

# (라벨, 키, 종류) — amt: 억원 / pct: 비율
PEER_METRICS = [
    ("매출액", "revenue", "amt"), ("영업이익", "op", "amt"), ("당기순이익", "ni", "amt"),
    ("매출 증가율(전년비)", "rev_growth", "pct"), ("매출 CAGR(2개년)", "rev_cagr2", "pct"),
    ("영업이익률", "opm", "pct"), ("순이익률", "npm", "pct"), ("ROE", "roe", "pct"),
    ("자산총계", "assets", "amt"), ("부채비율", "debt_ratio", "pct"), ("유동비율", "current_ratio", "pct"),
    ("직원 수(명)", "staff", "cnt"), ("1인당 매출액", "rev_per_head", "amt1"),
]


def _cagr2(rows: dict, fy: int):
    a, b = rows.get(fy - 2, {}).get("revenue"), rows.get(fy, {}).get("revenue")
    if not a or b is None or a < 0 or b < 0:
        return None
    return (b / a) ** 0.5 - 1


def peer_entry(name: str, stock: str, fs_label: str, table: dict, fy: int, is_main: bool = False, gov: dict | None = None) -> dict:
    rows = table["rows"]
    r = dict(rows.get(fy, {}))
    r["rev_cagr2"] = _cagr2(rows, fy)
    st = (gov or {}).get("staff") or {}
    r["staff"], r["rev_per_head"] = st.get("total"), st.get("rev_per_head")
    return {"name": name, "stock_code": stock, "fs_label": fs_label, "fy": fy, "main": is_main, "gov": gov or {},
            "values": {k: r.get(k) for _, k, _ in PEER_METRICS},
            "series": {y: {k: rows[y].get(k) for k in ("revenue", "op", "opm", "roe")} for y in sorted(rows)}}


def collect_peers(client: DartClient, queries: list[str], fy: int, fs_div: str = "CFS") -> tuple[list[dict], list[str]]:
    """회사명·종목코드 목록 → 비교용 항목 (최근 3개년 = 사업보고서 1건). 찾지 못한 회사는 경고."""
    from .cli import collect_financials

    out, warns = [], []
    for q in queries:
        q = q.strip()
        if not q:
            continue
        try:
            cands = client.find_corp(q)
        except DartError as e:
            warns.append(f"{q}: {e}")
            continue
        if not cands:
            warns.append(f"{q}: 회사를 찾지 못함")
            continue
        c = cands[0]
        if len(cands) > 1 and c.get("corp_name") != q:
            warns.append(f"{q}: 후보 {len(cands)}개 중 '{c.get('corp_name')}' 사용 (정확한 회사명·종목코드 권장)")
        try:
            table, used, _ = collect_financials(client, c["corp_code"], 3, fy, fs_div)
        except DartError as e:
            warns.append(f"{c.get('corp_name')}: {e}")
            continue
        if not table["rows"].get(fy, {}).get("revenue"):
            warns.append(f"{c.get('corp_name')}: FY{fy} 매출 데이터 없음")
        from .governance import audit_rows, staff

        def _try(fn):
            try:
                return fn() or []
            except DartError:
                return []

        gov = {"audit": audit_rows(_try(lambda: client.auditor(c["corp_code"], fy)), fy),
               "staff": staff(_try(lambda: client.employees(c["corp_code"], fy)), table["rows"].get(fy, {}).get("revenue"))}
        out.append(peer_entry(c.get("corp_name", q), c.get("stock_code", ""), "연결" if used == "CFS" else "별도", table, fy, gov=gov))
    for w in warns:
        print(f"  ! 동종업체 {w}", file=sys.stderr)
    return out, warns
