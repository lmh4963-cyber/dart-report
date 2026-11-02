"""거시지표 연결 — macro_dash 의 월별 CSV(거시지표_데이터_YYYYMM.csv)를 연평균으로 묶어 회사 매출원가와 나란히 표시.
원가 영향은 사용자 입력 계수 기반 '추정'. 상관·회귀 같은 추론은 하지 않음."""
from __future__ import annotations

import csv
from pathlib import Path

# (키, CSV 열 이름 앞부분, 표시명, 민감도 단위 설명, step, 종류)
LINKS = [
    ("usdkrw", "원/달러", "원/달러 연평균", "원/달러 10원 ↑", 10.0, "fx"),
    ("eurkrw", "원/유로", "원/유로 연평균", "원/유로 10원 ↑", 10.0, "fx"),
    ("jpykrw", "원/100엔", "원/100엔 연평균", "원/100엔 10원 ↑", 10.0, "fx"),
    ("imp_raw", "수입물가(원재료)", "수입물가(원재료) 연평균", "수입물가(원재료) 1% ↑", 1.0, "index"),
]


def load_macro_csv(path: str) -> dict[str, dict[str, float]]:
    """→ {키: {YYYYMM: 값}} — 열 이름이 LINKS 의 앞부분과 일치하는 것만"""
    out: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fp:
        rd = csv.reader(fp)
        head = next(rd)
        cols = {}
        for i, h in enumerate(head):
            for key, prefix, *_ in LINKS:
                if h.strip().startswith(prefix) and key not in cols.values():
                    cols[i] = key
        for row in rd:
            if not row or not row[0].strip():
                continue
            ym = row[0].strip().replace("-", "").replace(".", "")[:6]
            for i, key in cols.items():
                if i < len(row) and row[i].strip():
                    try:
                        out.setdefault(key, {})[ym] = float(row[i].replace(",", ""))
                    except ValueError:
                        pass
    return out


def annual(monthly: dict[str, float], year: int) -> tuple[float | None, int]:
    vals = [v for ym, v in monthly.items() if ym[:4] == str(year)]
    return (sum(vals) / len(vals) if vals else None), len(vals)


def build_link(table: dict, monthly: dict[str, dict[str, float]], source: str, coefs: dict | None = None) -> dict:
    """연도별 매출·매출원가·원가율 + 거시지표 연평균(개월수) + 민감도 동인"""
    ys = table["summary"]["years"]
    rows = table["rows"]
    years = []
    for y in ys:
        r = rows.get(y, {})
        e = {"year": y, "revenue": r.get("revenue"), "cogs": r.get("cogs"),
             "cogs_ratio": (r["cogs"] / r["revenue"]) if r.get("cogs") is not None and r.get("revenue") else None, "macro": {}}
        for key, *_ in LINKS:
            avg, n = annual(monthly.get(key, {}), y)
            e["macro"][key] = {"avg": avg, "months": n}
        years.append(e)
    present = [k for k, *_ in LINKS if any(e["macro"][k]["avg"] is not None for e in years)]
    # 민감도 기준 연도: 12개월 모두 있고 전년도 12개월도 있는 가장 최근 연도
    base = None
    for e in reversed(years):
        prev = next((p for p in years if p["year"] == e["year"] - 1), None)
        if prev and present and all(e["macro"][k]["months"] == 12 and prev["macro"][k]["months"] == 12 for k in present):
            base = e["year"]
            break
    drivers = []
    for key, _, name, label, step, kind in LINKS:
        if key not in present:
            continue
        d = None
        if base:
            cur = next(e for e in years if e["year"] == base)["macro"][key]["avg"]
            prv = next(e for e in years if e["year"] == base - 1)["macro"][key]["avg"]
            d = (cur - prv) / step if kind == "fx" else ((cur / prv - 1) * 100 / step if prv else None)
        drivers.append({"key": key, "name": name, "label": label, "step": step, "kind": kind, "delta": d, "coef": (coefs or {}).get(key, 0.0)})
    return {"years": years, "present": present, "names": {k: n for k, _, n, *_ in LINKS}, "base_year": base,
            "drivers": drivers, "source": source, "file": Path(source).name}
