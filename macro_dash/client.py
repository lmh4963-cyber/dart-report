"""한국은행 ECOS API 클라이언트 — 키는 환경변수 ECOS_API_KEY 또는 .env 파일에서 읽음. 응답은 cache/ 에 저장.

오프라인 모드: --fixtures 폴더에 아래 이름으로 둔 응답을 그대로 사용 (테스트용).
  StatisticItemList_{통계표}.json
  StatisticSearch_{통계표}_{항목1}[_{항목2}]_{주기}.json   (기간 무관 전체 → 요청 기간으로 잘라 씀)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

BASE = "https://ecos.bok.or.kr/api"
PAGE = 10000  # ECOS 1회 최대 건수


class EcosError(RuntimeError):
    pass


def load_api_key(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    if os.environ.get("ECOS_API_KEY"):
        return os.environ["ECOS_API_KEY"]
    for p in (Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ECOS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


class EcosClient:
    def __init__(self, api_key: str | None = None, cache_dir: str | Path = "cache", fixtures: str | Path | None = None, sleep: float = 0.2):
        self.api_key = api_key
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.fixtures = Path(fixtures) if fixtures else None
        self.sleep = sleep

    # ── 공통 ──
    def _fixture(self, name: str) -> dict | None:
        if not self.fixtures:
            return None
        p = self.fixtures / f"{name}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def _get(self, service: str, path: list[str], cache_name: str, fixture_name: str, max_age: float | None = None) -> list[dict]:
        if self.fixtures:
            fx = self._fixture(fixture_name)
            if fx is None:
                raise EcosError(f"픽스처 없음: {self.fixtures / (fixture_name + '.json')}")
            return _rows(service, fx)
        cp = self.cache / f"{cache_name}.json"
        if cp.exists() and (max_age is None or time.time() - cp.stat().st_mtime < max_age):
            return _rows(service, json.loads(cp.read_text(encoding="utf-8")))
        if not self.api_key:
            raise EcosError("ECOS API 키 없음 — .env 에 ECOS_API_KEY=발급키 를 넣거나 --fixtures 사용")
        import requests  # 지연 import: 오프라인 테스트에서 불필요

        url = "/".join([BASE, service, self.api_key, "json", "kr", "1", str(PAGE), *path])
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        rows = _rows(service, data)  # 오류면 여기서 예외
        cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        time.sleep(self.sleep)
        return rows

    # ── 데이터 ──
    def item_list(self, stat: str) -> list[dict]:
        """통계표의 항목 목록 (GRP_CODE·ITEM_CODE·ITEM_NAME·CYCLE·UNIT_NAME …). 캐시 30일."""
        name = f"StatisticItemList_{stat}"
        return self._get("StatisticItemList", [stat], name, name, max_age=30 * 86400)

    def search(self, stat: str, cycle: str, start: str, end: str, items: list[str]) -> list[dict]:
        """StatisticSearch — TIME·DATA_VALUE·UNIT_NAME … 행 목록 (start~end 포함)."""
        key = "_".join([stat, *items, cycle])
        rows = self._get("StatisticSearch", [stat, cycle, start, end, *items], f"StatisticSearch_{key}_{start}_{end}", f"StatisticSearch_{key}")
        return [r for r in rows if start <= str(r.get("TIME", "")) <= end]


def _rows(service: str, data: dict) -> list[dict]:
    if service in data:
        return data[service].get("row", []) or []
    res = data.get("RESULT") or {}
    code = res.get("CODE", "")
    if code == "INFO-200":  # 해당 데이터 없음 (정상 처리)
        return []
    raise EcosError(f"{service}: [{code}] {res.get('MESSAGE', '알 수 없는 응답')}")
