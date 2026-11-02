# dart-report — DART 기업분석 자동 리포트

회사명(또는 종목코드)만 넣으면 OpenDART 공시에서 5개년 재무를 받아 **엑셀 리포트**(맑은 고딕)를 만듦.

## 준비 (최초 1회)
1. https://opendart.fss.or.kr 에서 무료 API 키 발급
2. 이 폴더에 `.env` 파일 생성 → `DART_API_KEY=발급받은키` 한 줄 (`.env.example` 참고). `.env` 는 git 에 올라가지 않음
3. `pip install -r requirements.txt`

## 사용법
```bash
python -m dart_report 제이브이엠                    # 회사명
python -m dart_report 054950 --years 5 --out out/   # 종목코드, 5개년
python -m dart_report 삼성전자 --fs OFS              # 별도 기준
python -m dart_report 제이브이엠 --fixtures fixtures # 오프라인 샘플 데이터로 체험
```
동명 회사가 여럿이면 후보 목록이 뜨고 `--pick 번호`로 선택.

## 결과 (엑셀 7시트)
| 시트 | 내용 |
|---|---|
| 요약 | 기업 개요 · 핵심 지표 5개년 · 매출/영업이익률 차트 · 개조식 핵심 코멘트 |
| 손익 | 매출~순이익, 이익률, 증가율, EPS |
| 재무상태 | 자산·부채·자본 주요 계정, 부채비율·유동비율·순차입금 |
| 현금흐름 | 영업·투자·재무 CF, CAPEX, FCF, 배당성향 |
| 지분·배당 | 최대주주 현황 · 배당 · 임직원 |
| 최근 공시 | 최근 1년 공시 목록 (DART 링크) |
| 출처 | API·산식 정리 |

## 산식
- ROE/ROA = 지배주주순이익 ÷ 평균 자본/자산 · 순차입금 = 차입금+사채 − 현금성자산 − 단기금융상품 · FCF = 영업CF − (유형+무형 취득)
- 연결(CFS) 우선, 없으면 별도(OFS) 대체. 전체 재무제표가 없는 연도는 주요계정 API 로 보완 (현금흐름 '-')
- 공시값 그대로 사용, 추정·보정 없음

## 검증
`python -m unittest -q tests.test_report` — 제이브이엠 실제 공시값 픽스처로 추출·지표·엑셀 검증 5건

## 폴더
`dart_report/` client(API·캐시) · extract(계정 매핑) · metrics(지표) · report(엑셀) · cli  /  `fixtures/` 오프라인 샘플  /  `cache/` API 응답 캐시(자동)
