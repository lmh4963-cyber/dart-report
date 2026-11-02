"""국면 판정·증감·변동성·민감도·재고 커버리지 계산 (예측 아님, 판정·추정만)."""
from __future__ import annotations

from statistics import mean, pstdev

# 국면 판정 임계값: 3개월 이동평균이 12개월 이동평균 대비 이 이상 벗어나면 상승/하락
THRESH = {"rate": 0.10, "fx": 0.01, "index": 0.01}  # rate 는 %p, 나머지는 변화율

# 권장 재고 커버리지 기본 룰 (예시 기준 — 사용자 편집): 원자재 월간 변동성(표준편차, %) 구간 → 주
DEFAULT_COVERAGE = [
    {"lo": 0.0, "hi": 2.0, "weeks": 4, "note": "안정 — 기본 재고"},
    {"lo": 2.0, "hi": 4.0, "weeks": 6, "note": "보통 — 완충 재고 추가"},
    {"lo": 4.0, "hi": None, "weeks": 8, "note": "고변동 — 선확보·분할 매입"},
]

# 민감도 동인: (key, 단위 설명, step) — 계수는 사용자가 입력 (억원)
DRIVERS = [
    ("usdkrw", "원/달러 10원 ↑", 10.0),
    ("eurkrw", "원/유로 10원 ↑", 10.0),
    ("jpykrw", "원/100엔 10원 ↑", 10.0),
    ("imp_raw", "수입물가(원재료) 1% ↑", 1.0),
]


def ym_add(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[4:6])
    t = y * 12 + (m - 1) + n
    return f"{t // 12:04d}{t % 12 + 1:02d}"


def ym_range(start: str, end: str) -> list[str]:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = ym_add(cur, 1)
    return out


def to_series(rows: list[dict]) -> dict[str, float]:
    out = {}
    for r in rows:
        v = str(r.get("DATA_VALUE", "")).replace(",", "").strip()
        try:
            out[str(r["TIME"])[:6]] = float(v)
        except (ValueError, KeyError):
            continue
    return out


def change(s: dict[str, float], ym: str, lag: int, kind: str) -> float | None:
    """lag 개월 전 대비 증감 — rate 는 %p 차이, 나머지는 변화율"""
    a, b = s.get(ym), s.get(ym_add(ym, -lag))
    if a is None or b is None:
        return None
    if kind == "rate":
        return a - b
    return None if b == 0 else a / b - 1


def regime(s: dict[str, float], end: str, kind: str) -> dict:
    """3개월 vs 12개월 이동평균 비교 → 상승·안정·하락"""
    last12 = [s.get(ym_add(end, -i)) for i in range(12)]
    if any(v is None for v in last12):
        return {"state": "판정불가", "ma3": None, "ma12": None, "gap": None}
    ma3, ma12 = mean(last12[:3]), mean(last12)
    gap = ma3 - ma12 if kind == "rate" else (ma3 / ma12 - 1 if ma12 else 0.0)
    t = THRESH[kind]
    state = "상승" if gap > t else "하락" if gap < -t else "안정"
    return {"state": state, "ma3": ma3, "ma12": ma12, "gap": gap}


def volatility(s: dict[str, float], end: str, n: int = 12) -> float | None:
    """최근 n개월 월간 변화율 표준편차 (%)"""
    ch = [change(s, ym_add(end, -i), 1, "index") for i in range(n)]
    if any(c is None for c in ch):
        return None
    return pstdev(ch) * 100


def coverage_weeks(vol: float | None, rules: list[dict] = DEFAULT_COVERAGE) -> dict | None:
    if vol is None:
        return None
    for r in rules:
        if vol >= r["lo"] and (r["hi"] is None or vol < r["hi"]):
            return r
    return rules[-1]


def driver_delta(s: dict[str, float], ym: str, kind: str, step: float) -> float | None:
    """전년 동월 대비 동인 변화량을 '단위 step' 개수로 환산 (환율 10원 단위 / 지수 1% 단위)"""
    a, b = s.get(ym), s.get(ym_add(ym, -12))
    if a is None or b is None:
        return None
    if kind == "fx":
        return (a - b) / step
    return ((a / b - 1) * 100 / step) if b else None


def cost_impact(data: dict[str, dict[str, float]], months: list[str], coefs: dict[str, float]) -> list[dict]:
    """월별 원가 영향(추정, 억원) = Σ 계수 × 전년 동월 대비 동인 변화(단위수)"""
    kinds = {"usdkrw": "fx", "eurkrw": "fx", "jpykrw": "fx", "imp_raw": "index"}
    out = []
    for ym in months:
        parts = {}
        for key, _, step in DRIVERS:
            d = driver_delta(data.get(key, {}), ym, kinds[key], step)
            parts[key] = None if d is None else d * coefs.get(key, 0.0)
        vals = [v for v in parts.values() if v is not None]
        out.append({"ym": ym, "parts": parts, "total": sum(vals) if vals else None})
    return out


def build(data: dict[str, dict[str, float]], specs: list[dict], end: str, months: int = 36, coefs: dict | None = None) -> dict:
    """대시보드 데이터 묶음"""
    win = ym_range(ym_add(end, -(months - 1)), end)
    indicators = []
    for sp in specs:
        s = data.get(sp["key"], {})
        last = max((k for k in s if k <= end), default=None)
        indicators.append({
            **{k: sp.get(k) for k in ("key", "name", "group", "kind", "unit", "source")},
            "values": [s.get(m) for m in win],
            "last_ym": last, "last": s.get(last) if last else None,
            "mom": change(s, last, 1, sp["kind"]) if last else None,
            "yoy": change(s, last, 12, sp["kind"]) if last else None,
            "regime": regime(s, last, sp["kind"]) if last else {"state": "판정불가"},
        })
    by = {i["key"]: i for i in indicators}
    from .series import SIGNALS

    signals = [{"title": t, "key": k, "name": by[k]["name"], **by[k]["regime"]} for t, k in SIGNALS if k in by]
    vol = volatility(data.get("imp_raw", {}), end)
    return {
        "end": end, "months": win, "indicators": indicators, "signals": signals,
        "volatility": vol, "coverage_rules": DEFAULT_COVERAGE, "coverage": coverage_weeks(vol),
        "drivers": [{"key": k, "label": lbl, "step": st, "coef": (coefs or {}).get(k, 0.0)} for k, lbl, st in DRIVERS],
        "impact": cost_impact(data, win[-12:], coefs or {}),
        "thresholds": THRESH,
    }
