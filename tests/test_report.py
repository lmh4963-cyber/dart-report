"""오프라인 픽스처(제이브이엠 실제 공시값)로 추출·지표·리포트 생성 검증. 실행: python -m pytest -q 또는 python -m unittest"""
import datetime, json, os, tempfile, unittest
from pathlib import Path

from dart_report.client import DartClient
from dart_report.cli import collect
from dart_report.extract import extract_filing, to_num
from dart_report.metrics import comments
from dart_report.report import build_workbook

FX = Path(__file__).resolve().parent.parent / "fixtures"


def _ensure_list_fixture():
    t = datetime.date.today(); b = (t - datetime.timedelta(days=365)).strftime("%Y%m%d"); e = t.strftime("%Y%m%d")
    p = FX / f"list_00361381_{b}_{e}.json"
    if not p.exists():
        p.write_text(json.dumps({"status": "000", "list": [{"rcept_no": "20260323001116", "report_nm": "사업보고서 (2025.12)", "flr_nm": "제이브이엠", "rcept_dt": "20260323"}]}, ensure_ascii=False), encoding="utf-8")


class T(unittest.TestCase):
    def setUp(self):
        _ensure_list_fixture()
        self.c = DartClient(api_key=None, cache_dir=tempfile.mkdtemp(), fixtures=FX)

    def test_to_num(self):
        self.assertEqual(to_num("1,234"), 1234); self.assertEqual(to_num("(50)"), -50); self.assertIsNone(to_num("-"))

    def test_extract_2025(self):
        items = self.c.financials_all("00361381", 2025)
        d = extract_filing(items, 2025)
        self.assertAlmostEqual(d[2025]["revenue"] / 1e8, 1731.3, places=1)
        self.assertAlmostEqual(d[2023]["op"] / 1e8, 297.7, places=1)
        self.assertEqual(d[2025]["st_borrow"], 31185820000)

    def test_collect_5y(self):
        corp = self.c.find_corp("제이브이엠")[0]
        meta, table, extras = collect(self.c, corp, 5, fy=2025)
        ys = table["summary"]["years"]
        self.assertEqual(ys, [2021, 2022, 2023, 2024, 2025])
        r25 = table["rows"][2025]
        self.assertAlmostEqual(r25["opm"], 0.1922, places=3)
        self.assertAlmostEqual(r25["net_debt"] / 1e8, -1034.9, places=0)  # 순현금 약 1,035억
        self.assertAlmostEqual(r25["fcf"] / 1e8, 255.1, places=0)
        self.assertAlmostEqual(table["summary"]["rev_cagr"], 0.1057, places=3)
        self.assertEqual(meta["fs_label"], "연결")
        cm = comments(table, "제이브이엠")
        self.assertTrue(any("순현금 1,035억" in x for x in cm))

    def test_find_corp(self):
        self.assertEqual(self.c.find_corp("054950")[0]["corp_code"], "00361381")
        self.assertEqual(self.c.find_corp("제이브이엠")[0]["stock_code"], "054950")

    def test_workbook(self):
        corp = self.c.find_corp("제이브이엠")[0]
        meta, table, extras = collect(self.c, corp, 5, fy=2025)
        out = os.path.join(tempfile.mkdtemp(), "t.xlsx")
        build_workbook(meta, table, comments(table, "x"), extras, out)
        import openpyxl
        wb = openpyxl.load_workbook(out)
        self.assertEqual(wb["요약"]["A1"].font.name, "맑은 고딕")
        self.assertIn("손익", wb.sheetnames)
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None and cell.font and cell.font.sz:
                        self.assertEqual(float(cell.font.sz), int(cell.font.sz), f"소수점 글자크기 {ws.title}!{cell.coordinate}")


if __name__ == "__main__":
    unittest.main()
