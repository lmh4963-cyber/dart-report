"""사용법:
  python -m macro_dash --out out/                        # ECOS 최신 36개월 → HTML 대시보드 + 엑셀 + CSV
  python -m macro_dash --fixtures fixtures/ecos --out out/  # 오프라인(예시) 데이터로 생성
  python -m macro_dash --check                           # 통계표·항목명 해석 결과만 확인
  python -m macro_dash --extra lme.csv --coef usdkrw=1.5 --coef imp_raw=3
키: .env 파일에 ECOS_API_KEY=발급키 (https://ecos.bok.or.kr/api 에서 무료 발급)
외부 CSV(--extra): 열 '월,지표,값' (월=YYYY-MM 또는 YYYYMM) — 구리·알루미늄·니켈(LME), 두바이유 등
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

from .analysis import build, ym_add
from .client import EcosClient, EcosError, load_api_key
from .html import build_html
from .series import SERIES, resolve
from .xlsx import build_workbook


def default_end(today: date | None = None) -> str:
    t = today or date.today()
    return ym_add(f"{t.year:04d}{t.month:02d}", -1)


def load_extra(path: str) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """외부 CSV → (지표 정의, 데이터). 지표명마다 1개 시리즈, kind=index"""
    data: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fp:
        for row in csv.reader(fp):
            if len(row) < 3 or not row[0].strip() or not row[0].strip()[0].isdigit():
                continue  # 머리글·빈 줄
            ym = row[0].strip().replace("-", "").replace(".", "")[:6]
            try:
                v = float(row[2].replace(",", ""))
            except ValueError:
                continue
            data.setdefault(row[1].strip(), {})[ym] = v
    specs, out = [], {}
    for k, (name, s) in enumerate(data.items()):
        key = f"extra{k + 1}"
        specs.append({"key": key, "name": name, "group": "원자재(외부)", "kind": "index", "unit": "",
                      "source": {"stat": "외부 CSV", "stat_name": Path(path).name, "items": [name]}})
        out[key] = s
    return specs, out


def collect(client: EcosClient, end: str, months: int = 36, series: list[dict] = SERIES) -> tuple[list[dict], dict[str, dict[str, float]], list[str]]:
    """ECOS 수집 — 이동평균·전년비용 24개월 여유분 포함. 실패 지표는 경고 후 건너뜀."""
    from .analysis import to_series

    start = ym_add(end, -(months + 23))
    specs, data, warns = [], {}, []
    for sp in series:
        try:
            rs = resolve(client, sp)
            rows = client.search(sp["stat"], "M", start, end, rs["codes"])
        except EcosError as e:
            warns.append(str(e))
            continue
        unit = rs["unit"] or (rows[0].get("UNIT_NAME", "") if rows else "")
        specs.append({**sp, "unit": unit, "source": {"stat": sp["stat"], "stat_name": rs["stat_name"], "items": rs["names"], "codes": rs["codes"]}})
        data[sp["key"]] = to_series(rows)
        if not rows:
            warns.append(f"{sp['name']}: {start}~{end} 데이터 없음")
    return specs, data, warns


def write_csv(path: Path, months: list[str], specs: list[dict], data: dict) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["월"] + [f"{s['name']}({s.get('unit') or ''})" for s in specs])
        for m in months:
            w.writerow([f"{m[:4]}-{m[4:]}"] + ["" if data.get(s["key"], {}).get(m) is None else data[s["key"]][m] for s in specs])


def _coefs(items: list[str]) -> dict[str, float]:
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        try:
            out[k.strip()] = float(v)
        except ValueError:
            raise SystemExit(f"--coef 형식 오류: {it} (예: usdkrw=1.5)")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="macro_dash", description="ECOS 거시지표 → 의사결정 대시보드(HTML)·엑셀")
    ap.add_argument("--out", default="out", help="출력 폴더")
    ap.add_argument("--months", type=int, default=36, help="표시 기간(개월, 기본 36)")
    ap.add_argument("--end", help="기준월 YYYYMM (기본: 전월, 픽스처 모드는 데이터 최신월)")
    ap.add_argument("--key", help="ECOS API 키 (생략 시 .env / 환경변수)")
    ap.add_argument("--fixtures", help="오프라인 응답 폴더 (테스트용)")
    ap.add_argument("--cache", default="cache", help="API 응답 캐시 폴더")
    ap.add_argument("--extra", help="외부 원자재 CSV (월,지표,값)")
    ap.add_argument("--coef", action="append", help="민감도 계수 초기값 key=억원 (usdkrw·eurkrw·jpykrw·imp_raw), 여러 번 가능")
    ap.add_argument("--check", action="store_true", help="통계표·항목명 해석 결과만 출력")
    a = ap.parse_args(argv)

    client = EcosClient(api_key=load_api_key(a.key), cache_dir=a.cache, fixtures=a.fixtures)
    if a.check:
        bad = 0
        for sp in SERIES:
            try:
                rs = resolve(client, sp)
                print(f"  OK  {sp['name']:<14} {sp['stat']} {rs['stat_name']} → {' / '.join(rs['names'])} ({','.join(rs['codes'])}) [{rs['unit']}]")
            except EcosError as e:
                bad += 1
                print(f"  NG  {e}")
        return 1 if bad else 0

    end = a.end or default_end()
    try:
        specs, data, warns = collect(client, end, a.months)
    except EcosError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    if not specs:
        print("오류: 받은 지표 없음\n  " + "\n  ".join(warns), file=sys.stderr)
        return 1
    if not a.end:  # 실제 데이터 최신월로 기준월 조정 (발표 시차)
        latest = max((max(s) for s in data.values() if s), default=end)
        end = min(end, latest)
    extra_label = ""
    if a.extra:
        es, ed = load_extra(a.extra)
        specs += es
        data.update(ed)
        extra_label = f"{Path(a.extra).name} ({', '.join(s['name'] for s in es)})"

    dash = build(data, specs, end, a.months, _coefs(a.coef))
    dash.update({
        "generated": date.today().isoformat(),
        "source_label": "한국은행 ECOS Open API" + (" (오프라인 픽스처)" if a.fixtures else ""),
        "sample": bool(a.fixtures), "extra_label": extra_label,
    })

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = f"거시지표_대시보드_{end}"
    xlsx = out / f"{base}.xlsx"
    build_workbook(dash, str(xlsx))
    build_html(dash, str(out / f"{base}.html"), xlsx.name)
    csv_months = sorted({m for s in data.values() for m in s if m <= end})
    write_csv(out / f"거시지표_데이터_{end}.csv", csv_months, specs, data)
    if not a.fixtures:
        write_csv(Path(a.cache) / "macro_monthly.csv", csv_months, specs, data)

    print(f"기준월 {end[:4]}.{end[4:]} · 지표 {len(specs)}개 · {a.months}개월")
    for s in dash["signals"]:
        print(f"  · {s['title']}: {s['state']} ({s['name']})")
    if dash["coverage"]:
        print(f"  · 원자재 변동성 {dash['volatility']:.1f}% → 권장 커버리지 {dash['coverage']['weeks']}주 (추정)")
    for w in warns:
        print(f"  ! {w}")
    print(f"\n완료: {out / (base + '.html')}\n      {xlsx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
