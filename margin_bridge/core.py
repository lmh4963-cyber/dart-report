"""매출총이익 증감 귀속 (Price-Volume-Mix-Cost).

입력 행: 기간 · 품목 · 수량 · 매출액 · 매출원가 · [원자재원가] (원 단위)
두 기간(기준 0, 비교 1)에 모두 있는 품목(공통 품목) 기준:
  물량 효과   = (Q₁ − Q₀) × 기준 평균 단위마진 m̄₀              (m̄₀ = 공통 품목 GM₀ ÷ Q₀)
  믹스 효과   = Σ (Q₁ᵢ − Q₁·s₀ᵢ) × m₀ᵢ                         (s₀ᵢ = 기준 수량 비중)
  판가 효과   = Σ Q₁ᵢ × (p₁ᵢ − p₀ᵢ)
  원자재원가  = −Σ Q₁ᵢ × (r₁ᵢ − r₀ᵢ)                            (원자재원가 열 있을 때)
  기타원가    = −Σ Q₁ᵢ × ((c₁ᵢ − r₁ᵢ) − (c₀ᵢ − r₀ᵢ))            (없으면 원가 효과 하나로)
  신규 품목   = 비교 기간에만 있는 품목 GM
  단종 품목   = −(기준 기간에만 있는 품목 GM)
합계 = GM₁ − GM₀ (항등식)
"""
from __future__ import annotations

import csv
from collections import OrderedDict

COLS = {"기간": "period", "품목": "item", "수량": "qty", "매출액": "rev", "매출원가": "cogs", "원자재원가": "raw"}


class BridgeError(ValueError):
    pass


def _num(s):
    t = str(s or "").replace(",", "").strip()
    if t in ("", "-"):
        return None
    return float(t)


def load_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fp:
        rd = csv.DictReader(fp)
        miss = [k for k in ("기간", "품목", "수량", "매출액", "매출원가") if k not in (rd.fieldnames or [])]
        if miss:
            raise BridgeError(f"필수 열 없음: {', '.join(miss)} (템플릿: 기간,품목,수량,매출액,매출원가[,원자재원가])")
        rows = []
        for i, r in enumerate(rd, 2):
            e = {COLS[k]: (v.strip() if k in ("기간", "품목") else _num(v)) for k, v in r.items() if k in COLS}
            if not e.get("period") or not e.get("item"):
                continue
            if not e.get("qty") or e["qty"] <= 0:
                raise BridgeError(f"{i}행 '{e['item']}': 수량은 0보다 커야 함")
            if e.get("rev") is None or e.get("cogs") is None:
                raise BridgeError(f"{i}행 '{e['item']}': 매출액·매출원가 필요")
            rows.append(e)
    return rows


def periods(rows: list[dict]) -> list[str]:
    return sorted({r["period"] for r in rows})


def _agg(rows, period):
    out = OrderedDict()
    for r in rows:
        if r["period"] != period:
            continue
        a = out.setdefault(r["item"], {"qty": 0.0, "rev": 0.0, "cogs": 0.0, "raw": 0.0, "has_raw": True})
        for k in ("qty", "rev", "cogs"):
            a[k] += r[k]
        if r.get("raw") is None:
            a["has_raw"] = False
        else:
            a["raw"] += r["raw"]
    return out


def bridge(rows: list[dict], p0: str, p1: str) -> dict:
    A, B = _agg(rows, p0), _agg(rows, p1)
    if not A or not B:
        raise BridgeError(f"기간 데이터 없음: {p0 if not A else p1}")
    common = [i for i in A if i in B]
    use_raw = all(A[i]["has_raw"] and B[i]["has_raw"] for i in common) and bool(common)
    gm = lambda d: d["rev"] - d["cogs"]
    q0 = sum(A[i]["qty"] for i in common)
    q1 = sum(B[i]["qty"] for i in common)
    gm0c = sum(gm(A[i]) for i in common)
    mbar0 = gm0c / q0 if q0 else 0.0
    items, mix, price, raw, other = [], 0.0, 0.0, 0.0, 0.0
    vol = (q1 - q0) * mbar0  # 물량은 공통 품목 전체 기준 (품목별로 나누지 않음)
    for i in common:
        a, b = A[i], B[i]
        p0_, p1_ = a["rev"] / a["qty"], b["rev"] / b["qty"]
        c0, c1 = a["cogs"] / a["qty"], b["cogs"] / b["qty"]
        m0 = p0_ - c0
        s0 = a["qty"] / q0 if q0 else 0.0
        e_mix = (b["qty"] - q1 * s0) * m0
        e_price = b["qty"] * (p1_ - p0_)
        if use_raw:
            r0, r1 = a["raw"] / a["qty"], b["raw"] / b["qty"]
            e_raw = -b["qty"] * (r1 - r0)
            e_oth = -b["qty"] * ((c1 - r1) - (c0 - r0))
        else:
            e_raw, e_oth = 0.0, -b["qty"] * (c1 - c0)
        mix += e_mix; price += e_price; raw += e_raw; other += e_oth
        items.append({"item": i, "status": "공통", "qty0": a["qty"], "qty1": b["qty"], "p0": p0_, "p1": p1_, "c0": c0, "c1": c1,
                      "gm0": gm(a), "gm1": gm(b), "mix": e_mix, "price": e_price, "raw": e_raw, "other": e_oth})
    new = sum(gm(B[i]) for i in B if i not in A)
    gone = -sum(gm(A[i]) for i in A if i not in B)
    for i in B:
        if i not in A:
            items.append({"item": i, "status": "신규", "qty0": 0, "qty1": B[i]["qty"], "gm0": 0, "gm1": gm(B[i]), "effect": gm(B[i])})
    for i in A:
        if i not in B:
            items.append({"item": i, "status": "단종", "qty0": A[i]["qty"], "qty1": 0, "gm0": gm(A[i]), "gm1": 0, "effect": -gm(A[i])})
    GM0, GM1 = sum(gm(v) for v in A.values()), sum(gm(v) for v in B.values())
    eff = {"volume": vol, "mix": mix, "price": price, "raw": raw, "other": other, "new": new, "gone": gone}
    resid = (GM1 - GM0) - sum(eff.values())
    if abs(resid) > max(1.0, abs(GM1 - GM0) * 1e-9):
        raise BridgeError(f"합계 불일치 {resid:,.0f}")  # 항등식이라 발생하면 입력 오류
    return {"p0": p0, "p1": p1, "gm0": GM0, "gm1": GM1, "rev0": sum(v["rev"] for v in A.values()), "rev1": sum(v["rev"] for v in B.values()),
            "effects": eff, "use_raw": use_raw, "items": items, "n_common": len(common)}
