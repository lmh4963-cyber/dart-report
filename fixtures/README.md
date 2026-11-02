# 테스트용 오프라인 응답

재무제표(fnlttSinglAcntAll_…2025, fnlttSinglAcnt_…2022)는 2026.11.2 DART MCP로 받은 제이브이엠 실제 공시값.
추가(2026.11.2 DART MCP 실제 공시값, 코드가 쓰는 행만 발췌):
- `fnlttSinglAcnt_00361381_2019/2016` 제이브이엠 FY2017~2019·FY2014~2016 주요계정 (10개년용)
- `fnlttSinglAcntAll_00361381_2026_CFS_11012` 제이브이엠 2026 반기 전체 재무제표 (접수 20260814003335) · `_11014` 3분기 = 미공시(013)
- `fnlttSinglAcnt_00269922_2025` 인바디 · `fnlttSinglAcnt_00609324_2025` 뷰웍스 FY2023~2025 주요계정 (동종비교 테스트용 — 동종업체 선정 의미 없음)

- `fnlttSinglAcntAll_00361381_2022_CFS`·`_2019_CFS` 제이브이엠 FY2017~2022 전체 재무제표 (현금흐름 포함, 접수 20230316000975·20200330002527) — 기존 2022 '데이터 없음(013)' 픽스처는 사실과 달라 교체
- `hyslrSttus`·`empSttus`·`alotMatter`·`accnutAdtorNmNdAdtOpinion` 제이브이엠 FY2025 최대주주·직원·배당·감사의견 (접수 20260323001116) — 기존 예시값 교체
- `empSttus`·`accnutAdtorNmNdAdtOpinion` 인바디(00269922)·뷰웍스(00609324) FY2025

공시목록(list_…)만 형식 확인용 **예시값**이며 실제와 다를 수 있음.
오프라인 모드에서 픽스처가 없는 조회는 "데이터 없음(013)"으로 처리.
공시목록 파일명은 실행 날짜에 따라 달라지므로 테스트는 tests/ 에서 날짜를 맞춰 생성함.

## ecos/ (macro_dash)
`ecos/` 의 ECOS 응답은 **형식만 맞춘 예시값**임 (실제 통계 아님, 항목코드도 가상 `EX…`). `python tests/make_ecos_fixtures.py` 로 재생성.
`ecos/extra_sample.csv` 의 LME 구리·두바이유도 예시값.
