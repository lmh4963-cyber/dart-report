"""사용법:
  python -m margin_bridge 품목손익.csv --out out/                 # 가장 최근 두 기간 비교
  python -m margin_bridge 품목손익.csv --base 2025-H1 --comp 2026-H1
  python -m margin_bridge --sample --out out/                   # 예시 템플릿(margin_bridge/template.csv)으로 체험
CSV 열: 기간, 품목, 수량, 매출액, 매출원가, 원자재원가(선택) — 원 단위, UTF-8
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import BridgeError, bridge, load_csv, periods
from .report import build_html, build_xlsx

TEMPLATE = Path(__file__).resolve().parent / "template.csv"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="margin_bridge", description="품목별 매출총이익 증감 귀속 (물량·믹스·판가·원가·신규/단종)")
    ap.add_argument("csv", nargs="?", help="입력 CSV")
    ap.add_argument("--base", help="기준 기간 (기간 열 값)")
    ap.add_argument("--comp", help="비교 기간")
    ap.add_argument("--out", default="out")
    ap.add_argument("--sample", action="store_true", help="예시 템플릿 사용")
    a = ap.parse_args(argv)
    src = str(TEMPLATE) if a.sample or not a.csv else a.csv
    try:
        rows = load_csv(src)
        ps = periods(rows)
        if len(ps) < 2:
            raise BridgeError(f"기간이 2개 이상 필요 (현재 {ps})")
        p0, p1 = a.base or ps[-2], a.comp or ps[-1]
        b = bridge(rows, p0, p1)
    except (BridgeError, OSError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sample = src == str(TEMPLATE)
    name = f"매출총이익_귀속_{p0}_{p1}"
    build_xlsx(b, str(out / f"{name}.xlsx"), Path(src).name, sample)
    build_html(b, str(out / f"{name}.html"), Path(src).name, sample)
    d = b["gm1"] - b["gm0"]
    print(f"{p0} → {p1} 매출총이익 {b['gm0'] / 1e8:,.1f} → {b['gm1'] / 1e8:,.1f}억 ({d / 1e8:+,.1f}억)")
    for k, v in b["effects"].items():
        if k != "raw" or b["use_raw"]:
            print(f"  · {k}: {v / 1e8:+,.2f}억")
    print(f"\n완료: {out / (name + '.html')}\n      {out / (name + '.xlsx')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
