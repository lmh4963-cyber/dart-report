# 대시보드 양식 가이드 (참고 양식)

2026.11.2 사용자 제공 참고 대시보드 3종에서 공통 양식 정리. **이후 만드는 HTML 대시보드는 이 양식을 기준으로 함.**

- 참고 원본: 「항공우주 5사 비교」 · 「대구 천억클럽 5사 비교」 · 「폐플라스틱 7사 비교」 (단일 HTML 파일, 각 약 120~130KB)
- 원본 파일은 CRETOP 유료 데이터 포함 → 공개 저장소에 올리지 않음. 양식(구조·토큰·컴포넌트)만 이 문서로 보관
- 3개 파일의 CSS 변수·섹션 순서·컴포넌트·차트 함수 동일 → 하나의 디자인 시스템

## 0. 구현 (dashkit)

- `dashkit/kit.css` — 아래 토큰·컴포넌트를 정수 px로 옮긴 공통 CSS (라이트·다크, 960px·560px 반응형, 인쇄)
- `dashkit/kit.js` — `K.combo`(막대+선 단일 축, 호버 띠 툴팁, 끝 라벨, 단조 곡선) · `K.waterfall`(귀속 분해) · `K.spark` · `K.legend` · `K.seg` · `K.chips` · `K.copyTable` · `K.theme` · `K.store`
- `dashkit.page(title, body, data, app_js)` → 외부 라이브러리 없는 단일 HTML (Pretendard CDN만 사용)
- 적용: `dart_report/html.py`(기업 재무·동종 N사 비교), `macro_dash/html.py`(거시지표), `margin_bridge/report.py`(품목 귀속), `reviews/derivatives.py`(파생상품 이력)

## 1. 사용자 규칙과의 정합 (우선 적용)

| 항목 | 참고 양식 | 적용 기준 |
|---|---|---|
| 글꼴 | Pretendard Variable (jsdelivr CDN) | 그대로 사용 |
| 글자 크기 | 10.5px · 11.5px · 12.5px 등 소수점 다수 | **정수로 반올림** (10.5→11, 11.5→12, 12.5→13). 같은 구성 요소는 문서 전체 동일 크기 |
| 문체 | 패널 설명 문장형 일부 | **개조식, ~함/음·명사 종결**로 통일 |
| 추정값 | 해당 없음 (공시·CRETOP 값만) | 추정 포함 시 "추정" 배지 필수 |
| 색 팔레트 | 보라 계열 accent `#6c5ce7` + s1~s4 | **참고 양식 보라 팔레트 사용** (2026.11.2 사용자 결정). 이전 명세의 NAVY 팔레트(`#00338D`·`#0091DA`·`#ED7D31`·`#C00000`, consulting-pptx)는 HTML 대시보드에 쓰지 않음 |

## 2. 페이지 골격 (섹션 순서)

1. **상단 헤더** `.top` — 제목 "○○ N사 비교" + 회사명 나열 + 우측 기준일·테마 전환 버튼(`.tbtn`)
2. **한눈에 보는 N사** — 기업개요 · 소속 관계(최대주주) · 자료 범위 (`.panel.wide` 2개)
3. **핵심 지표** — 슬라이서 + KPI 레일. 안내 문구: "기업·연도·단위를 고르면 아래 모든 차트와 표가 함께 바뀜"
4. **실적 · 성장성 FY○ — FY○** — 매출 규모 / 매출 성장 지수(첫해=100) / 영업이익률 추이 / 이익률 비교(GPM·OPM·NPM, 막대 위 매출원가율) / 영업이익·순이익 금액 / 1인당 매출액
5. **재무 안정성** — 재무 안정성 지표표(업종평균 대비 칸 색) / 총차입금·만기 구조 / 현금흐름등급·현금영업이익 / 운전자본 회전기간(재고·매출채권·매입채무 일수, 막대 위 순운전자본 일수)
6. **업종 내 위치** — 재무진단 5칸 / 업종평균 대비 규모(배수) / 업종 내 매출 순위·인증
7. **사업 구조 · 거래처** — 매출 구성 / 주요 구매처·판매처 비중 / 인증·산업재산권 / (상장사) 감사인·감사의견·핵심감사사항
8. **비교 요약** — 요약 카드 3열 (`.read` 좋음·주의·참고)
9. **N사 재무 비교표** — 표 설정(금액+전년비 증감률 / 금액만) · 표 복사 버튼
10. **푸터** `#noteList` — 데이터 출처 목록 (출처명·조회 일시·기준일)

## 3. 인터랙션

- **슬라이서** `.slicer` — 행 단위(`.srow`): 표시 기업 칩(`.chip[aria-pressed]`, 전체 해제 불가) · 기준 연도 세그먼트(`.seg`) · 단위 세그먼트(백만/억) · 초기화. 변경 시 `renderAll()`로 모든 차트·표 재그림
- **패널별 소형 세그먼트** `.seg.xs` — "기준 연도 / 전체 3년" 전환
- **툴팁** `#tip` (position:fixed) — 제목(`.t-h`) · 계열별 행(`.t-r` 이름·값) · 하단 주석(`.t-f`) · 근거 설명(`.t-why`). 차트는 연도 띠(hover band) 단위로 표시
- **표 강조** — `td.hl-up`(연두) · `td.hl-down`(분홍) · `td.hl-key`(노랑, 핵심 수치 + `data-why` 툴팁 근거) + 범례 `.hl-legend` + 핵심 근거 목록 `.keylist`
- **테마** — `prefers-color-scheme` 자동 + `data-theme="light|dark"` 수동 전환
- **표 복사** — 현재 표시 상태 그대로 클립보드 복사

## 4. 디자인 토큰 (원본 그대로)

```css
:root{
  --page:#eaeef8; --page-2:#f4f6fc;
  --surface:#ffffff; --surface-2:#f6f8fd; --sunk:#e9edf8;
  --ink:#2e2c5f; --ink-2:#6a6a92; --ink-3:#9a9bba;
  --grid:#edeff8; --axis:#d9ddee; --line:rgba(46,44,95,.07); --line-2:rgba(46,44,95,.045);
  --accent:#6c5ce7; --accent-ink:#ffffff; --accent-soft:#efecfe; --accent-line:#d9d3fb;
  --s1:#6c5ce7; --s2:#12a97a; --s3:#3b9df8; --s4:#f0674a;
  --good:#12a97a; --bad:#f0674a; --warn:#e0a10b;
  --hl-up:#c9f7a1; --hl-down:#ffc6dc; --hl-key:#fff35c;
  --card:0 1px 2px rgba(46,44,95,.04), 0 14px 34px -20px rgba(46,44,95,.28);
  --card-2:0 1px 2px rgba(46,44,95,.03), 0 8px 22px -16px rgba(46,44,95,.22);
}
/* 다크: --page:#0c0c18 --surface:#161726 --ink:#f1f1fa --accent:#7c6bf0 --s2:#10a272 --s3:#2e8fe0 --s4:#e4643f
   --good:#25c08c --bad:#f4785c --warn:#d9a531, 강조색은 rgba 30~36% 투명 */
```
- 회사별 색: `--c1`~`--cN` 변수로 회사마다 고정 (데이터 `color` 필드가 변수명 참조)
- 본문: `font-feature-settings:"tnum"`(숫자 고정폭) · `word-break:keep-all` · 기본 14px · 최대 폭 1280px · 좌우 여백 24px

## 5. 컴포넌트

| 컴포넌트 | 클래스 | 요점 |
|---|---|---|
| KPI 레일 | `.rail` > `.cell(.hero)` | 5열 `1.5fr + 4×1fr`, 라벨(대문자·자간) · 큰 숫자(굵기 300) · 단위 · 증감(`.delta.up/down`) · 스파크라인 |
| 패널 | `.grid` > `.panel(.wide)` | 2열 그리드, 모서리 20px, 그림자 `--card`. 머리 `.p-head`(제목 16px · 단위 우측) + 부제 `.p-sub`(출처·산식) |
| 범례 | `.legend` > `.swatch(.ln)` | 원형 점 = 막대, 가로선 = 선 그래프 |
| 요약 카드 | `.reads` > `.read(.warn/.note)` | 3열, 제목 앞 색 점(초록·주황·파랑), 수치는 `.fig` 굵게 |
| 업종 비교 막대 | `.cmp-row` | 라벨 · 막대(업종평균 위치 세로선 `u`) · 값 |
| 재무진단 | `.diag` > `.dcell` | 5칸, 등급 색 `.lv.g/y/r` |
| 표 | `.tbl-wrap` > `table` | 머리글 10px 대문자, 첫 열 sticky(`th.lab/td.lab`), 증감 보조 열 `td.d.up/down`, 합계 `tr.tot`, 들여쓰기 `td.lab.ind` |
| 재무제표 카드 | `.stmt.is/.bs/.mc/.rt` | 상단 5px 색 띠 + 태그(`.stag`) + 기준 시점 배지(`.when`) |

## 6. 차트 (라이브러리 없이 인라인 SVG 직접 생성)

- 공통: `baseSVG` · `yAxisLin` · `niceStep`(눈금) · `xLabels` · `hoverBands`(연도 띠 툴팁) · `smoothPath`(곡선) · `topRoundRect`/`botRoundRect`(막대 둥근 끝)
- 종류: `columnChart` · `signedColumnChart`(음수) · `groupedChart`(회사×연도) · `stackChart`(구성비) · `lineChart` · `sparkline` · `yearGroupChart`
- 렌더 함수: `renderSlicer` · `renderRail` · `renderOver` · `renderGrow` · `renderStab` · `renderPeer` · `renderBiz` · `renderReads` · `renderTable` → `renderAll`

## 7. 데이터 구조

```js
const CO = [{
  id, name, short, color:"--c1",            // 식별·표시명·회사색
  ind, est, type, emp, prod, addr, owner,     // 개요 (기준일 필드 ownAsof 등 함께)
  audit, kam, src, basis,                     // 감사·출처·회계기준
  mix, sell, buy,                             // 매출구성·판매처·구매처 [[이름, %], …]
  diag, avg, scale, rank, certs, ip,          // 재무진단·업종평균·규모배수·순위·인증
  fy: [{ year, rev, cogs, gp, sga, op, ni, assets, liab, eq, cash, …,   // 원천 금액(천원)
         revg, gpm, opm, roe, roa, debtratio, currratio, icr, dso, invdays, dpo, … }]  // 비율(%)
}]
```
- 원천 금액 단위 그대로 저장 → 슬라이서 단위(백만/억)로 표시 변환
- 값이 없는 항목은 지어내지 않고 "확인 불가 (출처에 없음)" 문구 표시

## 8. 출처 표기 규칙

- 패널마다 `.p-sub`에 출처·기준일·산식 명시 (예: "CRETOP 거래처현황(2026-05-14)", "DART 사업보고서 2025 「사업의 내용」")
- 계산 지표는 산식 명시 (예: 총차입금 = 단기차입금 + 유동성장기부채 + 전환사채 + 장기차입금·사채, 리스부채 제외)
- 출처가 회사마다 다르면(비상장 CRETOP / 상장 DART) 패널 부제에 회사별로 구분
- 푸터 `#noteList`에 전체 출처 목록 + 조회 일시
