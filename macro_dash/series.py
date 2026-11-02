"""지표 정의 + 항목코드 해석.

항목코드는 하드코딩하지 않고 StatisticItemList 의 항목명으로 찾음 (코드 변경·오기 방지).
통계표 코드(stat)와 항목명은 ECOS 화면 기준 — 처음 실제 키로 돌릴 때 `python -m macro_dash --check` 로 해석 결과 확인.
groups: 항목 그룹(Group1, Group2 …) 순서대로 매칭할 이름. exact 우선, 없으면 포함 검색 첫 항목.
"""
from __future__ import annotations

from .client import EcosClient, EcosError

# kind: rate(금리, %p 비교) · fx(환율, 10원 단위 민감도) · index(지수, % 비교)
SERIES: list[dict] = [
    {"key": "base_rate", "name": "기준금리", "group": "금리", "stat": "722Y001", "groups": ["기준금리"], "kind": "rate"},
    {"key": "ktb3y", "name": "국고채 3년", "group": "금리", "stat": "721Y001", "groups": ["국고채(3년)"], "kind": "rate"},
    {"key": "corp3y", "name": "회사채 AA- 3년", "group": "금리", "stat": "721Y001", "groups": ["AA-"], "kind": "rate"},
    {"key": "usdkrw", "name": "원/달러", "group": "환율", "stat": "731Y004", "groups": ["미국달러", "평균"], "kind": "fx"},
    {"key": "eurkrw", "name": "원/유로", "group": "환율", "stat": "731Y004", "groups": ["유로", "평균"], "kind": "fx"},
    {"key": "jpykrw", "name": "원/100엔", "group": "환율", "stat": "731Y004", "groups": ["일본엔", "평균"], "kind": "fx"},
    {"key": "imp_raw", "name": "수입물가(원재료)", "group": "물가", "stat": "401Y015", "groups": ["원재료", "원화"], "kind": "index"},
    {"key": "ppi_metal", "name": "PPI 1차금속", "group": "물가", "stat": "404Y014", "groups": ["1차 금속"], "kind": "index"},
    {"key": "ppi_chem", "name": "PPI 화학", "group": "물가", "stat": "404Y014", "groups": ["화학제품"], "kind": "index"},
    {"key": "ppi_elec", "name": "PPI 전기전자", "group": "물가", "stat": "404Y014", "groups": ["전자"], "kind": "index"},
    {"key": "cpi", "name": "소비자물가", "group": "물가", "stat": "901Y009", "groups": ["총지수"], "kind": "index"},
    {"key": "bsi_mfg", "name": "제조업 BSI", "group": "경기", "stat": "512Y013", "groups": ["제조업", "업황실적"], "kind": "index"},
]

# 상단 신호등 3종: (제목, 지표 key)
SIGNALS = [("금리 방향", "ktb3y"), ("환율 추세", "usdkrw"), ("원자재 국면", "imp_raw")]


def _norm(s: str) -> str:
    return "".join(str(s).split())


def resolve(client: EcosClient, spec: dict, cycle: str = "M") -> dict:
    """spec 의 groups 이름 → 항목코드 목록. {'codes': [...], 'names': [...], 'unit': str, 'stat_name': str}"""
    rows = [r for r in client.item_list(spec["stat"]) if not r.get("CYCLE") or r.get("CYCLE") == cycle]
    if not rows:
        raise EcosError(f"{spec['name']}: 통계표 {spec['stat']} 항목 목록이 비어 있음 (주기 {cycle})")
    grp_codes = sorted({r.get("GRP_CODE", "Group1") for r in rows})
    codes, names, unit = [], [], ""
    for i, want in enumerate(spec["groups"]):
        grp = f"Group{i + 1}" if f"Group{i + 1}" in grp_codes else grp_codes[min(i, len(grp_codes) - 1)]
        cand = [r for r in rows if r.get("GRP_CODE", "Group1") == grp]
        w = _norm(want)
        hit = [r for r in cand if _norm(r.get("ITEM_NAME", "")) == w] or [r for r in cand if w in _norm(r.get("ITEM_NAME", ""))]
        if not hit:
            sample = ", ".join(r.get("ITEM_NAME", "") for r in cand[:15])
            raise EcosError(f"{spec['name']}: {spec['stat']} {grp} 에서 '{want}' 항목을 찾지 못함 — 후보: {sample} … (series.py 수정)")
        codes.append(hit[0]["ITEM_CODE"])
        names.append(hit[0].get("ITEM_NAME", ""))
        unit = hit[0].get("UNIT_NAME") or unit
    return {"codes": codes, "names": names, "unit": unit, "stat_name": rows[0].get("STAT_NAME", "")}
