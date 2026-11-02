"""OpenDART API 클라이언트 — 키는 환경변수 DART_API_KEY 또는 .env 파일에서 읽음. 응답은 cache/ 에 저장.

오프라인 모드: --fixtures 폴더에 {api}_{corp_code}_{year}[_{fs}][_{보고서코드}].json 형태로 둔 응답을 그대로 사용 (테스트용).
픽스처가 없는 조회는 "데이터 없음(013)"으로 처리.
보고서코드: 11011 사업 · 11013 1분기 · 11012 반기 · 11014 3분기
"""
from __future__ import annotations

import io
import json
import os
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = "https://opendart.fss.or.kr/api"


class DartError(RuntimeError):
    pass


def load_api_key(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    if os.environ.get("DART_API_KEY"):
        return os.environ["DART_API_KEY"]
    for p in (Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DART_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


class DartClient:
    def __init__(self, api_key: str | None = None, cache_dir: str | Path = "cache", fixtures: str | Path | None = None, sleep: float = 0.2):
        self.api_key = api_key
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.fixtures = Path(fixtures) if fixtures else None
        self.sleep = sleep
        self._corp_index: list[dict] | None = None

    # ── 공통 ──
    def _fixture(self, name: str) -> dict | None:
        if not self.fixtures:
            return None
        p = self.fixtures / f"{name}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def _get(self, api: str, cache_name: str, **params) -> dict:
        fx = self._fixture(cache_name)
        if fx is not None:
            return fx
        if self.fixtures:  # 오프라인 모드: 픽스처 없는 조회 = 데이터 없음(013)
            return {"status": "013", "list": []}
        cp = self.cache / f"{cache_name}.json"
        if cp.exists():
            return json.loads(cp.read_text(encoding="utf-8"))
        if not self.api_key:
            raise DartError("OpenDART API 키 없음 — .env 에 DART_API_KEY=발급키 를 넣거나 --fixtures 사용")
        import requests  # 지연 import: 오프라인 테스트에서 불필요

        r = requests.get(f"{BASE}/{api}.json", params={"crtfc_key": self.api_key, **params}, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status not in ("000", "013"):  # 013 = 조회 데이터 없음 (정상 처리)
            raise DartError(f"{api}: [{status}] {data.get('message')}")
        cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        time.sleep(self.sleep)
        return data

    # ── 회사 식별 ──
    def corp_index(self) -> list[dict]:
        if self._corp_index is not None:
            return self._corp_index
        fx = self._fixture("corpCode")
        if fx is not None:
            self._corp_index = fx["list"]
            return self._corp_index
        cp = self.cache / "corpCode.json"
        if cp.exists() and time.time() - cp.stat().st_mtime < 7 * 86400:
            self._corp_index = json.loads(cp.read_text(encoding="utf-8"))["list"]
            return self._corp_index
        if not self.api_key:
            raise DartError("OpenDART API 키 없음")
        import requests

        r = requests.get(f"{BASE}/corpCode.xml", params={"crtfc_key": self.api_key}, timeout=60)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        root = ET.fromstring(z.read(z.namelist()[0]))
        rows = []
        for el in root.iter("list"):
            rows.append({c.tag: (c.text or "").strip() for c in el})
        cp.write_text(json.dumps({"list": rows}, ensure_ascii=False), encoding="utf-8")
        self._corp_index = rows
        return rows

    def find_corp(self, query: str, listed_only: bool = True) -> list[dict]:
        q = query.strip()
        rows = self.corp_index()
        if q.isdigit() and len(q) == 8:
            return [r for r in rows if r.get("corp_code") == q]
        if q.isdigit() and len(q) == 6:
            return [r for r in rows if r.get("stock_code") == q]
        exact = [r for r in rows if r.get("corp_name") == q]
        partial = [r for r in rows if q in r.get("corp_name", "") and r not in exact]
        out = exact + partial
        if listed_only:
            out = [r for r in out if r.get("stock_code")] or out
        return out[:20]

    # ── 데이터 ──
    def company(self, corp_code: str) -> dict:
        return self._get("company", f"company_{corp_code}", corp_code=corp_code)

    def financials_all(self, corp_code: str, year: int, fs_div: str = "CFS", reprt_code: str = "11011") -> list[dict]:
        sfx = "" if reprt_code == "11011" else f"_{reprt_code}"
        d = self._get("fnlttSinglAcntAll", f"fnlttSinglAcntAll_{corp_code}_{year}_{fs_div}{sfx}", corp_code=corp_code, bsns_year=str(year), reprt_code=reprt_code, fs_div=fs_div)
        return d.get("list", []) or []

    def financials_summary(self, corp_code: str, year: int, reprt_code: str = "11011") -> list[dict]:
        sfx = "" if reprt_code == "11011" else f"_{reprt_code}"
        d = self._get("fnlttSinglAcnt", f"fnlttSinglAcnt_{corp_code}_{year}{sfx}", corp_code=corp_code, bsns_year=str(year), reprt_code=reprt_code)
        return d.get("list", []) or []

    def dividends(self, corp_code: str, year: int) -> list[dict]:
        d = self._get("alotMatter", f"alotMatter_{corp_code}_{year}", corp_code=corp_code, bsns_year=str(year), reprt_code="11011")
        return d.get("list", []) or []

    def major_holders(self, corp_code: str, year: int) -> list[dict]:
        d = self._get("hyslrSttus", f"hyslrSttus_{corp_code}_{year}", corp_code=corp_code, bsns_year=str(year), reprt_code="11011")
        return d.get("list", []) or []

    def employees(self, corp_code: str, year: int) -> list[dict]:
        d = self._get("empSttus", f"empSttus_{corp_code}_{year}", corp_code=corp_code, bsns_year=str(year), reprt_code="11011")
        return d.get("list", []) or []

    def disclosures(self, corp_code: str, bgn_de: str, end_de: str) -> list[dict]:
        d = self._get("list", f"list_{corp_code}_{bgn_de}_{end_de}", corp_code=corp_code, bgn_de=bgn_de, end_de=end_de, page_count="100")
        return d.get("list", []) or []
