# dart-report 작업 지침

- HTML 대시보드를 새로 만들거나 고칠 때 `docs/DASHBOARD_STYLE.md` 양식을 기준으로 함 (사용자 제공 참고 대시보드 3종에서 정리)
- 새 대시보드는 `dashkit/`(공통 CSS 토큰·SVG 차트·툴팁·슬라이서·테마·표 복사) 재사용 → `dashkit.page(title, body, data, app_js)`로 한 파일 조립. 예시: `dart_report/html.py`, `macro_dash/html.py`
- 색은 참고 양식 보라 팔레트 (`--accent:#6c5ce7`, `--s1~s4`) — NAVY 팔레트 사용 안 함 (2026.11.2 사용자 결정)
- 글자 크기는 정수만 사용 (참고 양식의 소수점 크기는 반올림), 문체는 개조식(~함/음·명사)
- HTML 글꼴 Pretendard, 엑셀·문서 글꼴 맑은 고딕
- 추정값은 "추정" 표기, 모든 수치에 출처·기준일 명시. 출처에 없는 값은 지어내지 않음
- 테스트: `python -m unittest -q tests.test_report tests.test_report_plus tests.test_macro_dash tests.test_tools`
- 회사 지정: 사용자가 명시한 회사(2026.11.5 "제이브이엠으로")만 분석 대상으로 사용, 임의로 소속 회사 가정하지 않음
- 공개 저장소 — 유료 데이터(CRETOP 등) 원문·파일은 커밋하지 않음
