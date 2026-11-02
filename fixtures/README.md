# 테스트용 오프라인 응답

재무제표(fnlttSinglAcntAll_…2025, fnlttSinglAcnt_…2022)는 2026.11.2 DART MCP로 받은 제이브이엠 실제 공시값.
최대주주·배당·임직원·공시목록은 형식 확인용 **예시값**이며 실제와 다를 수 있음.
공시목록 파일명은 실행 날짜에 따라 달라지므로 테스트는 tests/ 에서 날짜를 맞춰 생성함.

## ecos/ (macro_dash)
`ecos/` 의 ECOS 응답은 **형식만 맞춘 예시값**임 (실제 통계 아님, 항목코드도 가상 `EX…`). `python tests/make_ecos_fixtures.py` 로 재생성.
`ecos/extra_sample.csv` 의 LME 구리·두바이유도 예시값.
