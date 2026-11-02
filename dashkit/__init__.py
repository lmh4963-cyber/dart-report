"""dashkit — 참고 대시보드 양식(docs/DASHBOARD_STYLE.md)의 공통 CSS·JS. 단일 HTML 파일로 조립."""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent
CSS = (_DIR / "kit.css").read_text(encoding="utf-8")
JS = (_DIR / "kit.js").read_text(encoding="utf-8")
FONT_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">'


def to_json(data) -> str:
    """페이지 내장용 JSON — </script> 끊김 방지"""
    return json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")


def page(title: str, body: str, data, app_js: str, extra_css: str = "") -> str:
    """완성 HTML 한 파일: 공통 CSS + 본문 + 데이터 + 공통 JS + 앱 JS"""
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{FONT_LINK}
<style>
{CSS}
{extra_css}
</style>
</head>
<body>
{body}
<div id="tip" role="tooltip"></div>
<script>
const D = {to_json(data)};
{JS}
{app_js}
</script>
</body>
</html>
"""
