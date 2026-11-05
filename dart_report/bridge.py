"""영업이익 증감 귀속 (공시 손익 기준) — 예측 아닌 기발생 변동 설명.

ΔOP = 매출 효과 + 원가율 효과 + 판관비 효과 + 기타 영업손익 효과 (항등식, 합계 일치)
  매출 효과      = (매출₁ − 매출₀) × 매출총이익률₀        — 원가율이 그대로였다면 늘었을 이익
  원가율 효과    = −(원가율₁ − 원가율₀) × 매출₁           — 원자재·환율·믹스 등이 섞인 원가 구조 변화
  판관비 효과    = −(판관비₁ − 판관비₀)
  기타 효과      = 나머지 (경상연구비 등 판관비 외 영업비용, 공시 구조에 따라 다름)
"""
from __future__ import annotations

KEYS = ("revenue", "cogs", "sga", "op")


def bridge(a: dict, b: dict) -> dict | None:
    """a = 기준기간, b = 비교기간 (각 revenue·cogs·sga·op, 원)"""
    if any(x.get(k) is None for x in (a, b) for k in KEYS) or not a["revenue"] or not b["revenue"]:
        return None
    gpm0 = (a["revenue"] - a["cogs"]) / a["revenue"]
    c0, c1 = a["cogs"] / a["revenue"], b["cogs"] / b["revenue"]
    rev = (b["revenue"] - a["revenue"]) * gpm0
    cost = -(c1 - c0) * b["revenue"]
    sga = -(b["sga"] - a["sga"])
    d_op = b["op"] - a["op"]
    other = d_op - rev - cost - sga
    return {"op0": a["op"], "op1": b["op"], "d_op": d_op, "rev": rev, "cost": cost, "sga": sga, "other": other,
            "cogs_ratio0": c0, "cogs_ratio1": c1}


def annual_bridges(table: dict) -> list[dict]:
    rows, ys = table["rows"], table["summary"]["years"]
    out = []
    for y in ys:
        br = bridge(rows.get(y - 1, {}), rows.get(y, {}))
        if br:
            out.append({"label": f"FY{y - 1}→FY{y}", "year": y, **br})
    return out


def quarter_bridge(qd: dict) -> dict | None:
    if not qd:
        return None
    br = bridge(qd["cum_prev"], qd["cum"])
    return {"label": f"{qd['year'] - 1}→{qd['year']} {qd['label']} 누적", "year": qd["year"], **br} if br else None
