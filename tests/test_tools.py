"""원자재 검토 기록 대안방향 구현 검증 — 영업이익 귀속·민감도(dart_report), 공급사 인상 검증(macro_dash), 품목 귀속(margin_bridge), 파생상품 이력(reviews).
실행: python -m unittest -q tests.test_tools"""
import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.test_macro_dash import assert_integer_sizes

ROOT = Path(__file__).resolve().parent.parent


class OpBridge(unittest.TestCase):
    def test_identity_real(self):
        from dart_report.bridge import annual_bridges, bridge
        from dart_report.cli import collect_financials
        from dart_report.client import DartClient

        c = DartClient(api_key=None, cache_dir=tempfile.mkdtemp(), fixtures=ROOT / "fixtures")
        t, _, _ = collect_financials(c, "00361381", 10, 2025)
        bs = annual_bridges(t)
        self.assertEqual(bs[0]["label"], "FY2017→FY2018")  # 매출원가·판관비 있는 첫 구간
        for b in bs:
            self.assertAlmostEqual(b["op0"] + b["rev"] + b["cost"] + b["sga"] + b["other"], b["op1"], delta=1)
        last = bs[-1]
        self.assertAlmostEqual(last["rev"] / 1e8, 54.7, places=1)
        self.assertAlmostEqual(last["sga"] / 1e8, -40.6, places=1)
        self.assertIsNone(bridge({"revenue": 1}, {"revenue": 2}))


class MarginBridge(unittest.TestCase):
    def test_template_identity(self):
        from margin_bridge.core import bridge, load_csv

        b = bridge(load_csv(str(ROOT / "margin_bridge" / "template.csv")), "2025-H1", "2026-H1")
        self.assertAlmostEqual(sum(b["effects"].values()), b["gm1"] - b["gm0"], delta=1)
        self.assertTrue(b["use_raw"])
        self.assertEqual({i["item"]: i["status"] for i in b["items"]}["예시 제품 E"], "신규")
        self.assertAlmostEqual(b["effects"]["gone"], -(750000000 - 525000000))

    def test_no_raw_and_errors(self):
        from margin_bridge.core import BridgeError, bridge, load_csv

        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.csv")
        with open(p, "w", encoding="utf-8", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(["기간", "품목", "수량", "매출액", "매출원가"])
            w.writerows([["P0", "a", 10, 1000, 600], ["P0", "b", 10, 500, 400], ["P1", "a", 12, 1320, 780], ["P1", "b", 6, 300, 250]])
        b = bridge(load_csv(p), "P0", "P1")
        self.assertFalse(b["use_raw"])
        self.assertEqual(b["effects"]["raw"], 0)
        self.assertAlmostEqual(sum(b["effects"].values()), (1620 - 1030) - (1500 - 1000))
        self.assertAlmostEqual(b["effects"]["price"], 12 * (110 - 100) + 6 * (50 - 50))
        with open(p, "w", encoding="utf-8") as fp:
            fp.write("기간,품목,수량\nP0,a,1\n")
        with self.assertRaises(BridgeError):
            load_csv(p)

    def test_cli_outputs(self):
        from margin_bridge.cli import main

        out = tempfile.mkdtemp()
        self.assertEqual(main(["--sample", "--out", out]), 0)
        html = Path(out, "매출총이익_귀속_2025-H1_2026-H1.html").read_text(encoding="utf-8")
        self.assertIn("예시 데이터", html)
        assert_integer_sizes(self, html)
        import openpyxl

        wb = openpyxl.load_workbook(os.path.join(out, "매출총이익_귀속_2025-H1_2026-H1.xlsx"))
        self.assertEqual(wb.sheetnames, ["요약 브리지", "품목별", "방법"])
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        self.assertEqual(cell.font.name, "맑은 고딕")
                        self.assertEqual(float(cell.font.sz), int(cell.font.sz))


class Derivatives(unittest.TestCase):
    def test_history(self):
        from reviews.derivatives import DATA, build, summarize

        d = json.loads(DATA.read_text(encoding="utf-8"))
        s = summarize(d)
        y = {r["year"]: r for r in s["rows"]}
        self.assertEqual(y[2008]["net"], 268350 - 102016799 - 21308313)
        self.assertEqual(sum(c["loss"] for c in d["kiko2008"]["contracts"]), -102016799)  # 계약별 합 = 공시 평가손실
        self.assertEqual(s["last_use"], 2020)
        self.assertTrue(all(r["rcept"] and len(r["rcept"]) == 14 for r in s["rows"]))
        html = build(tempfile.mkdtemp()).read_text(encoding="utf-8")
        for t in ("KIKO", "20090331000944", "검토 기록과 공시가 다른 부분"):
            self.assertIn(t, html)
        assert_integer_sizes(self, html)


class DashSections(unittest.TestCase):
    def test_macro_supplier_check(self):
        from macro_dash.cli import main

        out = tempfile.mkdtemp()
        main(["--fixtures", str(ROOT / "fixtures" / "ecos"), "--end", "202609", "--out", out, "--cache", tempfile.mkdtemp()])
        html = Path(out, "거시지표_대시보드_202609.html").read_text(encoding="utf-8")
        for t in ("공급사 인상 요구 검증", "원가 전가 계산기", "근거 인상률"):
            self.assertIn(t, html)
        assert_integer_sizes(self, html)

    def test_dart_bridge_section(self):
        from dart_report.cli import main

        out = tempfile.mkdtemp()
        main(["제이브이엠", "--fixtures", str(ROOT / "fixtures"), "--out", out])
        html = Path(out, "제이브이엠_기업분석_2021-2025.html").read_text(encoding="utf-8")
        for t in ("영업이익 증감 워터폴", "민감도 시나리오", '"qbridge"'):
            self.assertIn(t, html)


if __name__ == "__main__":
    unittest.main()


class CostExposure(unittest.TestCase):
    def test_numbers(self):
        from reviews.cost_exposure import DATA, build, derive

        d = json.loads(DATA.read_text(encoding="utf-8"))
        x = derive(d)
        self.assertEqual(x["rev"][2], 173129220)  # 천원 = 사업보고서 매출실적 합계
        self.assertAlmostEqual(x["rev"][2] * 1000, d["pl"]["revenue"], delta=1000)  # 재무제표 매출과 일치
        self.assertAlmostEqual(x["export_share"][2], 86607016 / 173129220)
        self.assertAlmostEqual(x["raw_to_cogs"], 64262e6 / 102290460903)
        self.assertEqual(x["fx_net"], 2973 - 20820262)
        self.assertEqual(d["fx"]["sens5"]["assets"] + d["fx"]["sens5"]["liabs"], d["fx"]["sens5"]["net"])
        html = build(tempfile.mkdtemp()).read_text(encoding="utf-8")
        for t in ("원가 전가 한계", "선구매 부등식", "20260323001116"):
            self.assertIn(t, html)
        assert_integer_sizes(self, html)


class CommodityBoard(unittest.TestCase):
    def test_parse_formats(self):
        from commodity_board.build import parse

        long = parse("월,품목,값,단위,통화\n2026-08,구리,100,USD/톤,USD\n2026-08,구리,110,USD/톤,USD\n2026-09,구리,120,USD/톤,USD\n")
        self.assertEqual(long["구리"]["data"], {"202608": 105.0, "202609": 120.0})  # 같은 달 평균
        self.assertEqual(long["구리"]["cur"], "USD")
        wide = parse("﻿월,원/달러(원),수입물가(원재료)(2020=100)\n2026-09,1368.2,123.6\n")
        self.assertIn("수입물가(원재료)", wide)
        self.assertEqual(wide["수입물가(원재료)"]["unit"], "2020=100")
        with self.assertRaises(ValueError):
            parse("월,x\nabc,def\n")

    def test_build(self):
        from commodity_board.build import build

        html = build(None, tempfile.mkdtemp()).read_text(encoding="utf-8")
        for t in ("예시 데이터 (실제 시세 아님)", "CSV 불러오기", "원화 환산"):
            self.assertIn(t, html)
        assert_integer_sizes(self, html)
