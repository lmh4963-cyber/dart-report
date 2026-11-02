"""macro_dash 오프라인 픽스처 생성 — ECOS 응답 형식만 맞춘 **예시값** (실제 통계 아님, 항목코드도 가상 'EX…').
실행: python tests/make_ecos_fixtures.py  → fixtures/ecos/*.json 덮어씀
"""
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "fixtures" / "ecos"
START, END = (2021, 1), (2026, 9)

# stat → (통계표명, [(그룹, 코드, 이름, 단위)])
ITEMS = {
    "722Y001": ("1.3.1. 한국은행 기준금리 및 여수신금리 (예시)", [("Group1", "EX01", "한국은행 기준금리", "연%")]),
    "721Y001": ("1.3.2.2. 시장금리(월,분기,년) (예시)", [("Group1", "EX01", "국고채(3년)", "연%"), ("Group1", "EX02", "회사채(3년, AA-)", "연%"), ("Group1", "EX03", "회사채(3년, BBB-)", "연%")]),
    "731Y004": ("3.1.2.2. 주요국 통화의 대원화환율 (예시)", [("Group1", "EX01", "원/미국달러(매매기준율)", "원"), ("Group1", "EX02", "원/일본엔(100엔)", "원"), ("Group1", "EX03", "원/유로", "원"),
                                                     ("Group2", "EXA", "평균자료", ""), ("Group2", "EXB", "말일자료", "")]),
    "401Y015": ("4.2.1.1. 수입물가지수(기본분류) (예시)", [("Group1", "EX00", "총지수", "2020=100"), ("Group1", "EX01", "원재료", "2020=100"), ("Group2", "EXW", "원화기준", ""), ("Group2", "EXD", "계약통화기준", "")]),
    "404Y014": ("4.1.1.1. 생산자물가지수(기본분류) (예시)", [("Group1", "EX01", "1차 금속제품", "2020=100"), ("Group1", "EX02", "화학제품", "2020=100"), ("Group1", "EX03", "컴퓨터, 전자 및 광학기기", "2020=100")]),
    "901Y009": ("4.2.1. 소비자물가지수 (예시)", [("Group1", "EX00", "총지수", "2020=100")]),
    "512Y013": ("7.1.1. 기업경기실사지수(실적) (예시)", [("Group1", "EXC", "제조업", ""), ("Group1", "EXN", "비제조업", ""), ("Group2", "EXAA", "업황실적BSI", ""), ("Group2", "EXBB", "매출실적BSI", "")]),
}


def months():
    y, m = START
    while (y, m) <= END:
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def gen(f):
    return [(f"{y:04d}{m:02d}", round(f(k), 2)) for k, (y, m) in enumerate(months())]


def wave(k, period, amp):
    return amp * math.sin(2 * math.pi * k / period)


# (stat, [codes]) → 값 함수(k = 2021.01 부터 경과 개월)
SERIES = {
    ("722Y001", ("EX01",)): lambda k: 0.5 if k < 8 else min(3.5, 0.5 + 0.25 * ((k - 8) // 2)) if k < 25 else 3.5 if k < 45 else max(2.5, 3.5 - 0.25 * ((k - 45) // 3)),
    ("721Y001", ("EX01",)): lambda k: 1.0 + 2.6 * (1 - math.exp(-k / 14)) - (0.035 * max(0, k - 40)) + wave(k, 9, 0.12),
    ("721Y001", ("EX02",)): lambda k: 1.6 + 3.2 * (1 - math.exp(-k / 14)) - (0.04 * max(0, k - 40)) + wave(k, 9, 0.15),
    ("731Y004", ("EX01", "EXA")): lambda k: 1110 + 4.2 * k + wave(k, 14, 35),
    ("731Y004", ("EX03", "EXA")): lambda k: 1350 + 2.4 * k + wave(k, 16, 30),
    ("731Y004", ("EX02", "EXA")): lambda k: 1060 - 2.8 * k + wave(k, 12, 25),
    ("401Y015", ("EX01", "EXW")): lambda k: 105 + 40 * math.sin(math.pi * min(k, 36) / 36) + 0.3 * k + wave(k, 5, 3),
    ("404Y014", ("EX01",)): lambda k: 102 + 0.45 * k + wave(k, 11, 4),
    ("404Y014", ("EX02",)): lambda k: 103 + 0.35 * k + wave(k, 13, 3),
    ("404Y014", ("EX03",)): lambda k: 98 - 0.1 * k + wave(k, 10, 1.5),
    ("901Y009", ("EX00",)): lambda k: 101 + 0.27 * k + wave(k, 12, 0.3),
    ("512Y013", ("EXC", "EXAA")): lambda k: 85 + wave(k, 18, 9) + wave(k, 5, 2),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for stat, (sname, items) in ITEMS.items():
        rows = [{"STAT_CODE": stat, "STAT_NAME": sname, "GRP_CODE": g, "GRP_NAME": "예시그룹", "ITEM_CODE": c, "ITEM_NAME": n,
                 "CYCLE": "M", "START_TIME": "202101", "END_TIME": "202609", "UNIT_NAME": u} for g, c, n, u in items]
        (OUT / f"StatisticItemList_{stat}.json").write_text(json.dumps({"StatisticItemList": {"list_total_count": len(rows), "row": rows}}, ensure_ascii=False, indent=1), encoding="utf-8")
    for (stat, codes), f in SERIES.items():
        sname, items = ITEMS[stat]
        names = {c: n for _, c, n, _ in items}
        unit = next(u for _, c, _, u in items if c == codes[0])
        rows = [{"STAT_CODE": stat, "STAT_NAME": sname, "ITEM_CODE1": codes[0], "ITEM_NAME1": names[codes[0]],
                 "ITEM_CODE2": codes[1] if len(codes) > 1 else None, "ITEM_NAME2": names.get(codes[1]) if len(codes) > 1 else None,
                 "UNIT_NAME": unit, "TIME": t, "DATA_VALUE": f"{v}"} for t, v in gen(f)]
        name = "_".join(["StatisticSearch", stat, *codes, "M"])
        (OUT / f"{name}.json").write_text(json.dumps({"StatisticSearch": {"list_total_count": len(rows), "row": rows}}, ensure_ascii=False), encoding="utf-8")
    (OUT / "extra_sample.csv").write_text("월,지표,값\n" + "".join(
        f"{t[:4]}-{t[4:]},{nm},{v}\n" for nm, fn in (("LME 구리(예시)", lambda k: 8500 + 30 * k + wave(k, 10, 600)), ("두바이유(예시)", lambda k: 70 + wave(k, 20, 18) + wave(k, 6, 4)))
        for t, v in gen(fn)), encoding="utf-8")
    print(f"생성: {OUT}")


if __name__ == "__main__":
    main()
