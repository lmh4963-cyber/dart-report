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

### 추가 옵션
```bash
python -m dart_report 제이브이엠 --years 10                     # 10개년 (2~12, 재무 데이터는 2015 사업연도 공시부터)
python -m dart_report 제이브이엠 --peers 인바디,뷰웍스            # 동종업체 비교 (회사 선정은 사용자 판단)
python -m dart_report 제이브이엠 --macro out/거시지표_데이터_202609.csv --coef usdkrw=2   # macro_dash CSV 연결
python -m dart_report 제이브이엠 --no-quarter --no-html          # 분기 실적·HTML 생략
```
- **HTML 대시보드**: 엑셀과 같은 이름의 `.html` 자동 생성 — 참고 양식(`docs/DASHBOARD_STYLE.md`, 보라 팔레트·라이트/다크) · 한눈에 보기 · 슬라이서(표시 기업·5/10개년·억원/백만원) · KPI 레일 · 실적·성장성 6종 · 재무 안정성(전년 대비 칸 색·운전자본 일수) · 분기 · 동종 N사 비교 · 지배구조·감사·인원 · 원가×거시 · 요약 · 재무표(표 복사)
- **분기·반기**: 최신 사업연도 다음 해의 3분기 → 반기 → 1분기 보고서 순으로 자동 조회. 누적·해당분기 vs 전년 동기, 분기말 vs 직전 사업연도말
- **동종업체**: 최근 사업보고서 1건(3개년)으로 매출·이익률·ROE·부채비율·2개년 CAGR 비교 + 비교군 중앙값
- **거시지표 연결**: `python -m macro_dash` 로 만든 월별 CSV를 연평균으로 묶어 매출원가율과 나란히 표시. 원가 영향 = 사용자 계수 × 전년 대비 변화 (**추정**, 상관·회귀 아님)

## 결과 (엑셀 7시트 + 옵션 시트)
| 시트 | 내용 |
|---|---|
| 요약 | 기업 개요 · 핵심 지표 5개년 · 매출/영업이익률 차트 · 개조식 핵심 코멘트 |
| 손익 | 매출~순이익, 이익률, 증가율, EPS |
| 재무상태 | 자산·부채·자본 주요 계정, 부채비율·유동비율·순차입금 |
| 현금흐름 | 영업·투자·재무 CF, CAPEX, FCF, 배당성향 |
| 지분·배당 | 최대주주 현황 · 배당 · 임직원 |
| 최근 공시 | 최근 1년 공시 목록 (DART 링크) |
| 분기실적 | 최신 분·반기 누적·해당분기 vs 전년 동기, 재무상태 vs 직전 연말 (자동, 공시 있을 때) |
| 동종비교 | `--peers` 지정 시 — 핵심 지표 나란히 + 중앙값 (직원 수·1인당 매출 포함) |
| 감사·인원 | 감사인·감사의견·핵심감사사항(교체 표시, 동종업체 포함) · 최대주주 · 직원·1인당 매출 · 배당 3개년 |
| 거시연결 | `--macro` 지정 시 — 원가율 × 환율·수입물가 연평균, 민감도 계수(노란 셀) → 원가 영향 수식 (추정) |
| 출처 | API·산식 정리 |

## 산식
- ROE/ROA = 지배주주순이익 ÷ 평균 자본/자산 · 순차입금 = 차입금+사채 − 현금성자산 − 단기금융상품 · FCF = 영업CF − (유형+무형 취득)
- 연결(CFS) 우선, 없으면 별도(OFS) 대체. 전체 재무제표가 없는 연도는 주요계정 API 로 보완 (현금흐름 '-')
- 공시값 그대로 사용, 추정·보정 없음

## 검증
`python -m unittest -q tests.test_report tests.test_report_plus` — 제이브이엠·인바디·뷰웍스 실제 공시값 픽스처로 추출·지표·엑셀 검증 5건 + 10개년·반기·동종업체·거시연결·HTML·감사·인원·현금흐름 보강 검증 10건

## 폴더
`dashkit/` 대시보드 공통 CSS·JS  /  `dart_report/` client(API·캐시) · extract(계정 매핑) · metrics(지표) · quarter(분·반기) · peers(동종업체) · macro(거시 연결) · report·report_extra(엑셀) · html(대시보드) · cli  /  `fixtures/` 오프라인 샘플  /  `cache/` API 응답 캐시(자동)

---

# macro_dash — 거시지표 의사결정 대시보드

한국은행 ECOS 거시지표 → **국면 신호등·추이·민감도·재고 커버리지** 대시보드(HTML 한 파일) + 엑셀. 가격 예측 아님, 국면 판정·추정만.

## 준비
1. https://ecos.bok.or.kr/api 에서 무료 API 키 발급
2. `.env` 에 `ECOS_API_KEY=발급받은키` 추가
3. 최초 1회 `python -m macro_dash --check` → 통계표·항목명 해석 결과 확인 (NG 항목은 `macro_dash/series.py` 의 이름 수정)

## 사용법
```bash
python -m macro_dash --out out/                               # 최근 36개월
python -m macro_dash --end 202609 --months 24                  # 기준월·기간 지정
python -m macro_dash --extra lme.csv                           # 구리·알루미늄·니켈·두바이유 외부 CSV (월,지표,값)
python -m macro_dash --coef usdkrw=1.5 --coef imp_raw=3        # 민감도 계수 초기값(억원)
python -m macro_dash --fixtures fixtures/ecos --end 202609     # 오프라인 예시 데이터로 체험
```

## 결과
| 파일 | 내용 |
|---|---|
| `거시지표_대시보드_YYYYMM.html` | 참고 양식 · 국면 신호등 레일 · 슬라이서(지표 그룹·12/24/36개월·이동평균) · 지표별 추이 · 원가 민감도(추정) · 재고 커버리지(추정) · 요약 · 데이터 표(복사·CSV) |
| `거시지표_대시보드_YYYYMM.xlsx` | 요약 · 데이터 · 민감도(수식) · 재고커버리지(수식) · 출처 — 맑은 고딕, 노란 셀 수정 시 재계산 |
| `거시지표_데이터_YYYYMM.csv` | 월별 원자료 (실데이터 실행 시 `cache/macro_monthly.csv` 에도 저장) |

## 지표·판정
- 금리: 기준금리(722Y001) · 국고채 3년 · 회사채 AA- 3년(721Y001)
- 환율 월평균: 원/달러 · 원/유로 · 원/100엔(731Y004)
- 물가: 수입물가 원재료(401Y015) · PPI 1차금속·화학·전기전자(404Y014) · CPI(901Y009) / 경기: 제조업 업황실적 BSI(512Y013)
- 항목코드는 하드코딩 없이 `StatisticItemList` 항목명으로 자동 매칭 → `--check` 로 확인
- 국면: 3개월 vs 12개월 이동평균 — 금리 ±0.10%p, 환율·지수 ±1% 초과 시 상승/하락
- 원가 영향(추정) = Σ 계수 × 전년 동월 대비 변화 (환율 10원 / 수입물가 1% 단위)
- 변동성 = 수입물가(원재료) 최근 12개월 월간 변화율 표준편차 → 룰 테이블(예시 4·6·8주)로 커버리지

## 검증
`python -m unittest -q tests.test_macro_dash` — 예시 픽스처로 수집·판정·민감도·HTML·엑셀(글꼴·정수 pt·수식) 검증 11건
