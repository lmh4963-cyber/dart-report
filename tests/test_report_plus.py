"""10개년 · 분기/반기 · 동종업체 · 거시지표 연결 · HTML 대시보드 검증.
픽스처: 제이브이엠 FY2016·2019 주요계정, 2026 반기 전체 재무제표, 인바디·뷰웍스 FY2025 주요계정 = 2026.11.2 DART MCP 실제 공시값.
거시지표 CSV = macro_dash 예시 픽스처로 생성 (실제 통계 아님). 실행: python -m unittest -q tests.test_report_plus"""
import os
import re
import tempfile
import unittest
from pathlib import Path

from dart_report.cli import collect_financials, main
from dart_report.client import DartClient
from dart_report.macro import build_link, load_macro_csv
from dart_report.peers import collect_peers
from dart_report.quarter import bs_rows, latest_quarter, quarter_rows

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "fixtures"


def _macro_csv() -> str:
    from macro_dash.cli import main as macro_main

    out = tempfile.mkdtemp()
    macro_main(["--fixtures", str(FX / "ecos"), "--end", "202609", "--out", out, "--cache", tempfile.mkdtemp()])
    return os.path.join(out, "거시지표_데이터_202609.csv")


class Plus(unittest.TestCase):
    def setUp(self):
        from tests.test_report import _ensure_list_fixture

        _ensure_list_fixture()
        self.c = DartClient(api_key=None, cache_dir=tempfile.mkdtemp(), fixtures=FX)

    def test_ten_years(self):
        t, used, rc = collect_financials(self.c, "00361381", 10, 2025)
        self.assertEqual(t["summary"]["years"], list(range(2016, 2026)))
        self.assertEqual(t["rows"][2016]["revenue"], 98148858097)
        self.assertAlmostEqual(t["rows"][2017]["op"] / 1e8, 187.4, places=1)
        self.assertAlmostEqual(t["rows"][2020]["revenue"] / 1e8, 1154.1, places=1)  # 2022 사업보고서의 전전기
        self.assertAlmostEqual(t["summary"]["rev_cagr"], 0.0651, places=3)
        self.assertIn("20200330002527", rc)

    def test_half_year(self):
        q = latest_quarter(self.c, "00361381", 2026)
        self.assertEqual((q["label"], q["months"], q["rcept_no"]), ("반기", 6, "20260814003335"))  # 3분기(11014) 미공시 → 반기
        rows = {r["label"]: r for r in quarter_rows(q)}
        self.assertEqual(rows["매출액"]["cum"], 94790499581)
        self.assertEqual(rows["매출액"]["q"], 49306359684)
        self.assertAlmostEqual(rows["매출액"]["cum_yoy"], 94790499581 / 90356594166 - 1)
        self.assertAlmostEqual(rows["영업이익"]["cum_yoy"], 0.1541, places=4)
        self.assertEqual(rows["FCF"]["cum"], 23588210893 - (1151385824 + 1811149320))
        self.assertIsNone(rows["FCF"]["q"])  # 현금흐름은 누적만
        bs = {r["label"]: r for r in bs_rows(q)}
        self.assertEqual(bs["순차입금(−=순현금)"]["cur"], 34869582000 - (15436600653 + 136000000000))
        self.assertIsNone(latest_quarter(self.c, "00361381", 2027))

    def test_peers(self):
        peers, warns = collect_peers(self.c, ["인바디", "100120", "없는회사"], 2025)
        self.assertEqual([p["name"] for p in peers], ["인바디", "뷰웍스"])
        ib = peers[0]["values"]
        self.assertEqual(ib["revenue"], 233948308378)
        self.assertAlmostEqual(ib["rev_cagr2"], (233948308378 / 170351229733) ** 0.5 - 1)
        self.assertAlmostEqual(ib["debt_ratio"], 41272803270 / 319788882815)
        self.assertTrue(any("없는회사" in w for w in warns))

    def test_macro_link(self):
        t, _, _ = collect_financials(self.c, "00361381", 5, 2025)
        monthly = load_macro_csv(_macro_csv())
        link = build_link(t, monthly, "x.csv", {"usdkrw": 2.0})
        self.assertEqual(link["base_year"], 2025)
        y25 = next(e for e in link["years"] if e["year"] == 2025)
        self.assertAlmostEqual(y25["cogs_ratio"], y25["cogs"] / y25["revenue"])
        self.assertEqual(y25["macro"]["usdkrw"]["months"], 12)
        u = next(d for d in link["drivers"] if d["key"] == "usdkrw")
        avg = lambda y: sum(v for k, v in monthly["usdkrw"].items() if k[:4] == str(y)) / 12
        self.assertAlmostEqual(u["delta"], (avg(2025) - avg(2024)) / 10)
        self.assertEqual(u["coef"], 2.0)

    def test_cli_all(self):
        out = tempfile.mkdtemp()
        rc = main(["제이브이엠", "--fixtures", str(FX), "--years", "10", "--peers", "인바디,뷰웍스", "--macro", _macro_csv(), "--coef", "usdkrw=2", "--out", out])
        self.assertEqual(rc, 0)
        import openpyxl

        wb = openpyxl.load_workbook(os.path.join(out, "제이브이엠_기업분석_2016-2025.xlsx"))
        for s in ("분기실적", "동종비교", "거시연결"):
            self.assertIn(s, wb.sheetnames)
        self.assertEqual(wb.sheetnames[-1], "출처")
        mx = wb["거시연결"]
        usd = next(r for r in range(1, mx.max_row + 1) if mx.cell(row=r, column=1).value == "원/달러 10원 ↑")
        self.assertEqual(mx.cell(row=usd, column=2).value, 2.0)  # --coef 반영
        self.assertEqual(mx.cell(row=usd, column=4).value, f'=IF(C{usd}="","",B{usd}*C{usd})')
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        self.assertEqual(cell.font.name, "맑은 고딕", f"{ws.title}!{cell.coordinate}")
                        self.assertEqual(float(cell.font.sz), int(cell.font.sz), f"소수점 글자크기 {ws.title}!{cell.coordinate}")
        html = Path(out, "제이브이엠_기업분석_2016-2025.html").read_text(encoding="utf-8")
        for s in ("Pretendard", "--accent:#6c5ce7", "추정", "출처", "20260814003335", "인바디", "동종 2사 비교", "재무 안정성", "표 복사"):
            self.assertIn(s, html)
        self.assertNotIn("#00338D", html)
        self.assertEqual(html.lower().count("</script>"), 1)
        from tests.test_macro_dash import assert_integer_sizes

        assert_integer_sizes(self, html)

    def test_cli_minimal(self):
        out = tempfile.mkdtemp()
        self.assertEqual(main(["제이브이엠", "--fixtures", str(FX), "--no-quarter", "--no-html", "--out", out]), 0)
        files = os.listdir(out)
        self.assertEqual([f for f in files if f.endswith(".html")], [])
        import openpyxl

        wb = openpyxl.load_workbook(os.path.join(out, files[0]))
        self.assertNotIn("분기실적", wb.sheetnames)
        self.assertEqual(main(["제이브이엠", "--fixtures", str(FX), "--years", "20", "--out", out]), 1)


if __name__ == "__main__":
    unittest.main()


class Governance(unittest.TestCase):
    """감사·최대주주·직원·배당 + 전체 재무제표 FY2017~2022 (2026.11.2 DART MCP 실제 공시값)"""

    def setUp(self):
        from tests.test_report import _ensure_list_fixture

        _ensure_list_fixture()
        self.c = DartClient(api_key=None, cache_dir=tempfile.mkdtemp(), fixtures=FX)

    def test_cashflow_backfill(self):
        t, _, rc = collect_financials(self.c, "00361381", 10, 2025)
        r22, r17 = t["rows"][2022], t["rows"][2017]
        self.assertEqual(r22["ocf"], 14762962853)
        self.assertEqual(r22["dividends_paid"], 2303593600)  # 공시 음수 → 절대값
        self.assertEqual(r22["capex"], 3065536223 + 1638612706)
        self.assertEqual(r17["cogs"], 61052173670)
        self.assertAlmostEqual(r22["net_debt"], 30257021050 - (7232634004 + 60700000000))
        self.assertIsNone(t["rows"][2016].get("ocf"))  # FY2016은 주요계정만
        self.assertIn("20230316000975", rc)

    def test_governance(self):
        from dart_report.cli import collect

        meta, table, ex = collect(self.c, self.c.find_corp("제이브이엠")[0], 5, fy=2025)
        g = ex["gov"]
        self.assertEqual([(a["year"], a["auditor"]) for a in g["audit"]], [(2025, "삼일회계법인"), (2024, "삼일회계법인"), (2023, "도원회계법인")])
        self.assertEqual(g["audit"][0]["kam"], "계약부채")
        self.assertEqual(g["holders"]["largest"]["name"], "한미사이언스(주)")
        self.assertEqual(g["holders"]["total_ratio"], 39.19)
        self.assertEqual(g["staff"]["total"], 322)
        self.assertAlmostEqual(g["staff"]["rev_per_head"], 173129219712 / 322)
        self.assertEqual([d["dps"] for d in g["div"]], [400, 500, 650])

    def test_tenure_parse(self):
        from dart_report.governance import _years

        self.assertAlmostEqual(_years("7년 2개월"), 7 + 2 / 12)
        self.assertEqual(_years("9.8"), 9.8)
        self.assertIsNone(_years("-"))

    def test_peer_staff_and_sheet(self):
        out = tempfile.mkdtemp()
        self.assertEqual(main(["제이브이엠", "--fixtures", str(FX), "--peers", "인바디,뷰웍스", "--out", out]), 0)
        import openpyxl

        wb = openpyxl.load_workbook(os.path.join(out, "제이브이엠_기업분석_2021-2025.xlsx"))
        ws = wb["감사·인원"]
        vals = [c.value for row in ws.iter_rows() for c in row if c.value is not None]
        self.assertIn("성현회계법인", vals)
        self.assertIn("교체", vals)
        pv = [c.value for row in wb["동종비교"].iter_rows() for c in row]
        self.assertIn(370, pv)  # 인바디 직원 수
        html = Path(out, "제이브이엠_기업분석_2021-2025.html").read_text(encoding="utf-8")
        for s in ("지배구조 · 감사 · 인원", "핵심감사사항", "한미사이언스(주)", "재고자산평가"):
            self.assertIn(s, html)
