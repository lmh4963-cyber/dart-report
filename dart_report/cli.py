"""사용법:
  python -m dart_report 제이브이엠                 # 회사명 (종목코드 054950, corp_code 도 가능)
  python -m dart_report 제이브이엠 --years 5 --out out/
  python -m dart_report 제이브이엠 --fixtures fixtures/   # 오프라인(테스트) 데이터로 생성
  python -m dart_report 제이브이엠 --years 10 --peers 인바디,뷰웍스 --macro out/거시지표_데이터_202609.csv
  → 엑셀 + HTML 대시보드 (분기·반기 실적은 최신 분·반기보고서 자동 조회, --no-quarter 로 끔)
키: .env 파일에 DART_API_KEY=발급키 (https://opendart.fss.or.kr 에서 무료 발급)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from .client import DartClient, DartError, load_api_key
from .extract import extract_filing, merge_years
from .metrics import build_table, comments
from .report import build_workbook


def latest_fiscal_year(today: date | None = None) -> int:
    """12월 결산 기준: 3월 말 이후면 전년도 사업보고서가 최신"""
    t = today or date.today()
    return t.year - 1 if t.month > 3 or (t.month == 3 and t.day >= 31) else t.year - 2


def collect_financials(client: DartClient, code: str, years: int, fy: int | None = None, fs_div: str = "CFS") -> tuple[dict, str, list[str]]:
    """연간 재무 수집 → (table, 사용 기준 CFS/OFS, 접수번호 목록)"""
    last = fy or latest_fiscal_year()
    first = last - years + 1
    filings = []
    rcepts = []
    used_fs = fs_div
    # 사업보고서 1건에 3개년이 들어오므로 3년 간격으로 조회. 전체 재무제표 → 없으면 별도 → 없으면 주요계정
    y = last
    while y >= first:
        items = client.financials_all(code, y, fs_div=used_fs)
        if not items and used_fs == "CFS":
            items = client.financials_all(code, y, fs_div="OFS")
            if items:
                used_fs = "OFS"
        if not items:
            items = [it for it in client.financials_summary(code, y) if it.get("fs_div", used_fs) == used_fs] or client.financials_summary(code, y)
        if items:
            filings.append(extract_filing(items, y))
            rcepts += sorted({it.get("rcept_no") for it in items if it.get("rcept_no")})
        y -= 3
    data = merge_years(filings)
    ys = [yy for yy in range(first, last + 1)]
    return build_table(data, ys), used_fs, rcepts


def collect(client: DartClient, corp: dict, years: int, fy: int | None = None, fs_div: str = "CFS") -> tuple[dict, dict, dict]:
    code = corp["corp_code"]
    last = fy or latest_fiscal_year()
    table, used_fs, rcepts = collect_financials(client, code, years, last, fs_div)

    prof = client.company(code)
    meta = {
        "corp_name": prof.get("corp_name") or corp.get("corp_name"), "stock_code": prof.get("stock_code") or corp.get("stock_code", ""),
        "market": {"Y": "코스피", "K": "코스닥", "N": "코넥스", "E": "기타"}.get(prof.get("corp_cls"), prof.get("corp_cls", "")),
        "ceo_nm": prof.get("ceo_nm"), "induty": prof.get("induty_code"), "est_dt": _dt(prof.get("est_dt")), "acc_mt": f"{prof.get('acc_mt')}월" if prof.get("acc_mt") else "",
        "adres": prof.get("adres"), "hm_url": prof.get("hm_url"), "fs_label": "연결" if used_fs == "CFS" else "별도", "rcept_nos": sorted(set(rcepts), reverse=True),
    }
    today = date.today()
    extras = {
        "holders": _safe(lambda: client.major_holders(code, last)),
        "dividends": _safe(lambda: client.dividends(code, last)),
        "employees": _safe(lambda: client.employees(code, last)),
        "disclosures": _safe(lambda: client.disclosures(code, (today - timedelta(days=365)).strftime("%Y%m%d"), today.strftime("%Y%m%d"))),
        "auditor": _safe(lambda: client.auditor(code, last)),
    }
    extras["gov"] = governance(extras, table["rows"].get(last, {}).get("revenue"), last)
    return meta, table, extras


def governance(extras: dict, revenue, fy: int) -> dict:
    """감사·최대주주·인원·배당 요약 (공시값 그대로)"""
    from .governance import audit_rows, dividends, holders, staff

    return {"fy": fy, "audit": audit_rows(extras.get("auditor") or [], fy), "holders": holders(extras.get("holders") or []),
            "staff": staff(extras.get("employees") or [], revenue), "div": dividends(extras.get("dividends") or [], fy)}


def _safe(fn):
    try:
        return fn() or []
    except Exception as e:  # 부가 데이터는 실패해도 리포트는 생성
        print(f"  (부가 데이터 생략: {e})", file=sys.stderr)
        return []


def _dt(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:]}" if s and len(s) == 8 else s


def main(argv=None):
    ap = argparse.ArgumentParser(description="DART 기업분석 자동 리포트 (엑셀)")
    ap.add_argument("corp", help="회사명 · 종목코드(6자리) · corp_code(8자리)")
    ap.add_argument("--years", type=int, default=5, help="분석 연수 (기본 5)")
    ap.add_argument("--fy", type=int, help="기준 사업연도 (기본: 최신 공시 연도)")
    ap.add_argument("--fs", choices=["CFS", "OFS"], default="CFS", help="연결(CFS, 기본) / 별도(OFS)")
    ap.add_argument("--out", default="out", help="출력 폴더")
    ap.add_argument("--key", help="OpenDART API 키 (생략 시 .env / 환경변수)")
    ap.add_argument("--fixtures", help="오프라인 응답 폴더 (테스트용)")
    ap.add_argument("--pick", type=int, default=0, help="동명 회사가 여럿일 때 선택 번호")
    ap.add_argument("--peers", help="동종업체 회사명·종목코드, 쉼표 구분 (예: 인바디,뷰웍스)")
    ap.add_argument("--macro", help="macro_dash 월별 CSV 경로 (거시지표_데이터_YYYYMM.csv) → 원가 × 거시지표 시트")
    ap.add_argument("--coef", action="append", help="거시 민감도 계수 초기값 key=억원 (usdkrw·eurkrw·jpykrw·imp_raw)")
    ap.add_argument("--no-quarter", action="store_true", help="분기·반기 실적 생략")
    ap.add_argument("--no-html", action="store_true", help="HTML 대시보드 생략 (엑셀만)")
    a = ap.parse_args(argv)
    if a.years < 2 or a.years > 12:
        print("--years 는 2~12 (OpenDART 재무 데이터는 2015 사업연도 공시부터)", file=sys.stderr)
        return 1

    client = DartClient(api_key=load_api_key(a.key), fixtures=a.fixtures)
    try:
        cands = client.find_corp(a.corp)
        if not cands:
            print(f"'{a.corp}' 에 해당하는 회사를 찾지 못함", file=sys.stderr)
            return 1
        if len(cands) > 1 and a.pick == 0:
            print("동명 회사 후보 — --pick 번호로 선택:")
            for i, c in enumerate(cands, 1):
                print(f"  {i}. {c['corp_name']} (종목 {c.get('stock_code') or '비상장'}, corp_code {c['corp_code']})")
            if cands[0].get("corp_name") != a.corp:
                return 1
            print("  → 정확히 일치하는 1번으로 진행")
        corp = cands[a.pick - 1 if a.pick else 0]
        print(f"대상: {corp['corp_name']} ({corp.get('stock_code') or '비상장'}) · {a.years}개년 · {'연결' if a.fs == 'CFS' else '별도'}")
        meta, table, extras = collect(client, corp, a.years, a.fy, a.fs)
    except DartError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    ys = table["summary"]["years"]
    fs_used = "CFS" if meta["fs_label"] == "연결" else "OFS"
    if not a.no_quarter:
        from .quarter import latest_quarter

        extras["quarter"] = _safe(lambda: latest_quarter(client, corp["corp_code"], ys[-1] + 1, fs_used)) or None
    if a.peers:
        from .peers import collect_peers, peer_entry

        others, _ = collect_peers(client, a.peers.split(","), ys[-1], a.fs)
        extras["peers"] = [peer_entry(meta["corp_name"], meta.get("stock_code", ""), meta["fs_label"], table, ys[-1], is_main=True, gov=extras.get("gov"))] + others
    if a.macro:
        from .macro import build_link, load_macro_csv

        try:
            extras["macro"] = build_link(table, load_macro_csv(a.macro), a.macro, _coefs(a.coef))
        except (OSError, StopIteration) as e:
            print(f"  ! 거시지표 CSV 읽기 실패: {e}", file=sys.stderr)

    cm = comments(table, meta["corp_name"])
    Path(a.out).mkdir(parents=True, exist_ok=True)
    out = Path(a.out) / f"{meta['corp_name']}_기업분석_{ys[0]}-{ys[-1]}.xlsx"
    build_workbook(meta, table, cm, extras, str(out))
    html_out = None
    if not a.no_html:
        from .html import build_html

        html_out = build_html(meta, table, cm, extras, str(out.with_suffix(".html")), offline=bool(a.fixtures))
    print(f"\n[{meta['corp_name']}] 핵심 요약")
    for c in cm:
        print("  · " + c)
    missing = [str(y) for y in ys if not table["rows"][y].get("revenue")]
    if missing:
        print(f"  ! 매출 데이터 없는 연도: {', '.join(missing)}")
    q = extras.get("quarter")
    if q:
        rv = q["cum"].get("revenue"), q["cum_prev"].get("revenue")
        op = q["cum"].get("op"), q["cum_prev"].get("op")
        if all(v is not None for v in rv + op):
            print(f"  · {q['year']} {q['label']} 누적: 매출 {rv[0]/1e8:,.0f}억 ({(rv[0]/rv[1]-1)*100:+.1f}%) · 영업이익 {op[0]/1e8:,.0f}억 ({(op[0]/op[1]-1)*100:+.1f}%)" if rv[1] and op[1] else "")
    print(f"\n완료: {out}" + (f"\n      {html_out}" if html_out else ""))
    return 0


def _coefs(items):
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        try:
            out[k.strip()] = float(v)
        except ValueError:
            raise SystemExit(f"--coef 형식 오류: {it} (예: usdkrw=1.5)")
    return out


if __name__ == "__main__":
    sys.exit(main())
