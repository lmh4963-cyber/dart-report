"""macro_dash 오프라인 검증 — fixtures/ecos 는 형식만 맞춘 예시값. 실행: python -m unittest -q tests.test_macro_dash"""
import os
import tempfile
import unittest
from pathlib import Path

from macro_dash.analysis import build, change, cost_impact, coverage_weeks, regime, volatility, ym_add, ym_range
from macro_dash.cli import collect, load_extra, main
from macro_dash.client import EcosClient, EcosError
from macro_dash.series import SERIES, resolve

FX = Path(__file__).resolve().parent.parent / "fixtures" / "ecos"


def assert_integer_sizes(tc, html: str):
    """HTML·SVG 글자 크기는 정수만 (CSS px/pt, JS font-size 속성)"""
    import re

    css = re.findall(r"font-size:\s*([\d.]+)(?:px|pt)", html)
    svg = re.findall(r'"font-size":\s*([\d.]+)', html)
    tc.assertTrue(css, "CSS 글자크기 없음")
    bad = [x for x in css + svg if float(x) != int(float(x))]
    tc.assertEqual(bad, [], "소수점 글자크기")


class Client(unittest.TestCase):
    def setUp(self):
        self.c = EcosClient(api_key=None, cache_dir=tempfile.mkdtemp(), fixtures=FX)

    def test_search_period_filter(self):
        rows = self.c.search("721Y001", "M", "202501", "202512", ["EX01"])
        self.assertEqual([r["TIME"] for r in rows], ym_range("202501", "202512"))

    def test_no_key(self):
        c = EcosClient(api_key=None, cache_dir=tempfile.mkdtemp())
        with self.assertRaises(EcosError):
            c.item_list("722Y001")

    def test_resolve_by_name(self):
        sp = next(s for s in SERIES if s["key"] == "usdkrw")
        r = resolve(self.c, sp)
        self.assertEqual(r["codes"], ["EX01", "EXA"])  # 미국달러 · 평균자료
        corp = resolve(self.c, next(s for s in SERIES if s["key"] == "corp3y"))
        self.assertEqual(corp["names"], ["회사채(3년, AA-)"])  # BBB- 와 혼동 없음

    def test_resolve_missing(self):
        with self.assertRaises(EcosError) as cm:
            resolve(self.c, {"name": "x", "stat": "721Y001", "groups": ["없는항목"]})
        self.assertIn("후보", str(cm.exception))


class Analysis(unittest.TestCase):
    def test_ym(self):
        self.assertEqual(ym_add("202601", -1), "202512")
        self.assertEqual(ym_add("202512", 13), "202701")

    def test_change_and_regime(self):
        months = ym_range("202401", "202512")
        rising = {m: 100 + k for k, m in enumerate(months)}  # 꾸준히 상승
        self.assertAlmostEqual(change(rising, "202512", 12, "index"), 123 / 111 - 1)
        self.assertEqual(regime(rising, "202512", "index")["state"], "상승")
        flat = {m: 3.0 for m in months}
        self.assertEqual(regime(flat, "202512", "rate")["state"], "안정")
        cut = {m: 3.5 - 0.05 * k for k, m in enumerate(months)}
        r = regime(cut, "202512", "rate")
        self.assertEqual(r["state"], "하락")
        self.assertAlmostEqual(r["gap"], -0.225)  # %p: 3M 평균 − 12M 평균
        self.assertEqual(regime({"202512": 1.0}, "202512", "rate")["state"], "판정불가")

    def test_volatility_coverage(self):
        months = ym_range("202401", "202512")
        s = {m: 100 * (1.05 if k % 2 else 1.0) for k, m in enumerate(months)}  # ±5% 진동
        self.assertGreater(volatility(s, "202512"), 4)
        self.assertEqual(coverage_weeks(1.0)["weeks"], 4)
        self.assertEqual(coverage_weeks(3.0)["weeks"], 6)
        self.assertEqual(coverage_weeks(9.0)["weeks"], 8)
        self.assertIsNone(coverage_weeks(None))

    def test_cost_impact(self):
        data = {"usdkrw": {"202412": 1300.0, "202512": 1350.0}, "imp_raw": {"202412": 100.0, "202512": 102.0}}
        r = cost_impact(data, ["202512"], {"usdkrw": 1.0, "imp_raw": 3.0})[0]
        self.assertAlmostEqual(r["parts"]["usdkrw"], 5.0)  # 50원 = 10원×5 × 1억
        self.assertAlmostEqual(r["parts"]["imp_raw"], 6.0)  # 2% × 3억
        self.assertAlmostEqual(r["total"], 11.0)
        self.assertIsNone(r["parts"]["eurkrw"])


class EndToEnd(unittest.TestCase):
    def test_collect_build(self):
        c = EcosClient(api_key=None, cache_dir=tempfile.mkdtemp(), fixtures=FX)
        specs, data, warns = collect(c, "202609", 36)
        self.assertEqual(len(specs), len(SERIES))
        self.assertEqual(warns, [])
        d = build(data, specs, "202609", 36)
        self.assertEqual(len(d["months"]), 36)
        self.assertEqual(d["months"][-1], "202609")
        self.assertEqual([s["title"] for s in d["signals"]], ["금리 방향", "환율 추세", "원자재 국면"])
        self.assertTrue(all(s["state"] in ("상승", "안정", "하락") for s in d["signals"]))

    def test_extra_csv(self):
        specs, data = load_extra(str(FX / "extra_sample.csv"))
        self.assertEqual([s["name"] for s in specs], ["LME 구리(예시)", "두바이유(예시)"])
        self.assertIn("202609", data["extra1"])

    def test_cli_outputs(self):
        out = tempfile.mkdtemp()
        rc = main(["--fixtures", str(FX), "--end", "202609", "--out", out, "--cache", tempfile.mkdtemp(),
                   "--extra", str(FX / "extra_sample.csv"), "--coef", "usdkrw=1.5"])
        self.assertEqual(rc, 0)
        html = Path(out, "거시지표_대시보드_202609.html").read_text(encoding="utf-8")
        for s in ("Pretendard", "추정", "--accent:#6c5ce7", "--s2:#12a97a", "prefers-color-scheme: dark", "예시 데이터", "출처", "국면 신호등", "권장 재고 커버리지"):
            self.assertIn(s, html)
        self.assertNotIn("#00338D", html)  # 보라 팔레트로 통일 (NAVY 미사용)
        self.assertEqual(html.lower().count("</script>"), 1)  # 내장 데이터가 스크립트를 끊지 않음
        assert_integer_sizes(self, html)
        self.assertTrue(Path(out, "거시지표_데이터_202609.csv").exists())

        import openpyxl
        wb = openpyxl.load_workbook(os.path.join(out, "거시지표_대시보드_202609.xlsx"))
        self.assertEqual(wb.sheetnames, ["요약", "데이터", "민감도", "재고커버리지", "출처"])
        self.assertEqual(wb["민감도"]["B6"].value, 1.5)  # --coef 반영
        self.assertTrue(str(wb["민감도"]["F14"].value).startswith("=SUM("))
        self.assertTrue(str(wb["재고커버리지"]["B12"].value).startswith("=IFERROR(LOOKUP("))
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        self.assertEqual(cell.font.name, "맑은 고딕", f"{ws.title}!{cell.coordinate}")
                        self.assertEqual(float(cell.font.sz), int(cell.font.sz), f"소수점 글자크기 {ws.title}!{cell.coordinate}")


if __name__ == "__main__":
    unittest.main()
