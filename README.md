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

---

# 원자재 검토 기록 대안방향 구현 (2026.11.5)

「원자재 선물 추적 에이전트 구상 검토 기록」의 대안방향 4개 중 공개 데이터로 가능한 부분 구현. 예측 아닌 귀속·검증·추정 도구.

| 대안방향 | 구현 위치 | 데이터 |
|---|---|---|
| ① 마진 귀속 분석 | `margin_bridge/` 품목별 물량·믹스·판가·원자재원가·기타원가·신규/단종 분해 · `dart_report` 영업이익 증감 워터폴(공시 손익 기준) | 품목 손익 CSV(사내, 접근 확인 필요) · DART |
| ② 민감도 시나리오 | `dart_report` HTML '민감도 시나리오' — 원가 중 노출 비중 × 변동률(또는 환율 목표) → 영업이익 영향(추정) | DART 매출원가 + 사용자 가정 |
| ③ 지수 추적 대시보드 | `macro_dash` HTML '공급사 인상 요구 검증'(지표 변화 × 원가 비중 vs 요구율) · '원가 전가 계산기' | ECOS · 외부 CSV(LME 등) |
| ④ 파생상품 손실 이력 재검토 | `reviews/derivatives.py` + `reviews/derivatives_jvm.json` — 제이브이엠 FY2007~2025 파생상품 손익·2008 통화옵션(KIKO) 계약 구조, 연도별 접수번호 | DART 사업보고서 원문 주석 |

```bash
python -m margin_bridge 품목손익.csv --base 2025-H1 --comp 2026-H1 --out out/   # 열: 기간,품목,수량,매출액,매출원가[,원자재원가]
python -m margin_bridge --sample --out out/                                     # 예시 템플릿
python -m reviews.derivatives --out out/                                        # 파생상품 손익 이력 HTML
python -m reviews.cost_exposure --out out/                                      # 원가·환율 노출 브리핑 HTML (FY2025)
python -m commodity_board 시세.csv --out out/                                    # 원자재 가격 현황판 (생략 시 예시 데이터)
```
- 영업이익 귀속(공시 기준): 매출 효과 = 매출 증감 × 전기 매출총이익률 · 원가율 효과 = −원가율 변화 × 당기 매출 · 판관비 효과 · 기타(경상연구비 등) — 합계 = 영업이익 증감
- 원가율 효과에는 원자재·환율·믹스가 섞여 있음 → 품목 단위 분해는 margin_bridge (사내 데이터 필요)
- **원가·환율 노출 브리핑** (`reviews/cost_exposure.py` + `cost_exposure_jvm.json`): 제이브이엠 FY2025 사업보고서의 내수·수출 매출, 대표 원재료·판가 단가 추이, 원재료 매입, 외화 노출·환율 민감도에 검토 기록 1·6·7단계 공식(원가 전가 한계·선구매 부등식) 대입
- 검증: `python -m unittest -q tests.test_tools` (8건)

## commodity_board — 원자재 가격 현황판
- CSV 1개 → HTML 한 파일: 품목 카드(최신·전월·전년·국면·변동성) · 지수 비교 · 품목별 추이(12M 이동평균) · 변동 요약 · 데이터 표
- 표시: 원 단위 / 지수(첫 달=100) / 원화 환산(USD 품목 × 같은 달 원/달러)
- **HTML에서 CSV 끌어다 놓기로 실데이터 교체** (브라우저에만 저장) · 형식: `월,품목,값[,단위,통화]` 또는 `월,품목1(단위),…` (macro_dash CSV 호환)
- 기본 내장 `commodity_board/sample.csv`는 **예시값** — 이 개발 환경에서 외부 시세 사이트 접근 불가

## live_board — 원자재·환율 실시간 현황판 (claude.ai 아티팩트)
- `python -m live_board.build out/` → 아티팩트 HTML 조각 생성, Artifact 게시 시 capabilities = `live_board.build.MANIFEST` (Alpha Vantage MCP Server: COPPER·ALUMINUM·WTI·BRENT·CURRENCY_EXCHANGE_RATE)
- 보는 사람의 Alpha Vantage 커넥터로 조회, watchTool 자동 갱신 (원자재 12시간 캐시·6시간 주기, 환율 30분 캐시·2시간 주기) — 무료 키 한도 초당 1회·하루 25회
- 한국 주식(한미약품 128940·한미사이언스 008930·제이브이엠 054950): Alpha Vantage에서 KRX 조회 안 됨(2026-11-05 확인) → 미지원 표시
