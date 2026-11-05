"""원자재·환율 실시간 현황판 (claude.ai 아티팩트용 HTML 조각).
사용: python -m live_board.build → out/원자재_실시간_현황판.html  (Artifact 도구로 게시, capabilities = MANIFEST)
- Alpha Vantage MCP Server 커넥터를 '보는 사람' 권한으로 호출 (mcp 기능, watchTool 자동 갱신)
- 무료 키 한도: 초당 1회 · 하루 25회 (2026-11-05 커넥터 응답 문구) → 원자재 월간 12시간 캐시·6시간 주기, 환율 30분 캐시·2시간 주기, 호출 간격 1.5초
- 응답 형식은 2026-11-05 실제 호출로 확인: COPPER·WTI = {name, interval, unit, data:[{date, value}]} · CURRENCY_EXCHANGE_RATE = {"Realtime Currency Exchange Rate": {...}}
  ALUMINUM·BRENT 는 같은 계열로 보고 같은 형식으로 읽되, 형식이 다르면 해당 카드에 '형식 다름' 표시
- 한국 주식(한미약품·한미사이언스·제이브이엠): 이 커넥터에서 KRX 종목 조회 안 됨 (SYMBOL_SEARCH 결과 없음, 128940.KS 거부) → 미지원 표시
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = "Alpha Vantage MCP Server"
MANIFEST = {"mcp": {"servers": [{"server": SERVER, "tools": ["COPPER", "ALUMINUM", "WTI", "BRENT", "CURRENCY_EXCHANGE_RATE"]}]}}

EXTRA_CSS = """
.wrap{padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); padding-bottom:56px}
.top-in{padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px))}
body{font-family:"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",system-ui,sans-serif}
.live{display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:700; color:var(--good)}
.live::before{content:""; width:8px; height:8px; border-radius:999px; background:currentColor; animation:pulse 2s ease-in-out infinite}
.live.off{color:var(--ink-3)} .live.off::before{animation:none}
@keyframes pulse{50%{opacity:.35}}
@media (prefers-reduced-motion: reduce){.live::before{animation:none}}
.note{font-size:12px; color:var(--ink-3); font-weight:500; line-height:1.6}
.err{font-size:12px; font-weight:600; color:var(--bad)}
.stale{font-size:11px; color:var(--warn); font-weight:700}
.fxhero{display:flex; gap:24px; align-items:flex-end; flex-wrap:wrap}
.fxhero .k-val{font-size:44px}
"""

BODY = r"""
<header class="top"><div class="top-in">
  <div class="ident"><h1>원자재·환율 실시간 현황판</h1><span class="ticker">Alpha Vantage</span><span id="liveBadge" class="live off">연결 확인 중</span></div>
  <div class="top-note"><span id="topNote">보는 사람의 Alpha Vantage 커넥터로 조회</span></div>
</div></header>
<main class="wrap">
  <section class="slicer" style="margin-top:20px"><div class="srow"><span class="sname">상태</span><span id="status" class="note">커넥터 연결을 확인하는 중</span>
    <div class="sright"><button class="tbtn" id="fxRefresh" type="button" hidden>환율 지금 새로고침</button></div></div>
    <div class="srow foot">무료 키 한도 초당 1회 · 하루 25회 → 원자재(월간 시세)는 12시간마다, 환율은 2시간마다 자동 갱신 · 마지막 정상값은 이 브라우저에 보관</div></section>

  <h2 class="sec">원/달러 환율<small>실시간 · Alpha Vantage CURRENCY_EXCHANGE_RATE</small></h2>
  <section class="panel"><div class="fxhero">
    <div><div class="k-label">USD → KRW</div><div class="k-val" id="fxVal">-</div><div class="k-sub" id="fxSub"></div></div>
    <div><div class="k-label">매수 · 매도 호가</div><div class="k-sub" id="fxBidAsk" style="font-size:14px">-</div></div>
  </div><div id="fxErr" class="err"></div></section>

  <h2 class="sec">원자재 시세<small>월평균 · 전월·전년 대비 · 원화 환산은 최신 월평균 × 현재 환율 (참고)</small></h2>
  <div class="cos-rail" id="cards"></div>

  <h2 class="sec">36개월 비교<small>각 품목 36개월 전 = 100</small></h2>
  <section class="panel"><div id="cmpL"></div><div class="chart" id="cmp"></div></section>

  <h2 class="sec">품목별 추이<small>최근 36개월 월평균</small></h2>
  <div class="grid" id="charts"></div>

  <h2 class="sec">관심 종목<small>한미약품 · 한미사이언스 · 제이브이엠</small></h2>
  <section class="panel"><div class="p-sub">이 커넥터는 한국거래소(KRX) 종목을 지원하지 않음 — 2026-11-05 확인: 'Hanmi Pharm' 종목 검색 결과 없음, 128940.KS 일별 시세 요청 거부, 'Samsung Electronics' 검색도 미국 장외·런던·프랑크푸르트 상장분만 반환</div>
    <div class="tbl-wrap"><table><thead><tr><th class="lab">종목</th><th>종목코드</th><th class="lab">시장</th><th class="lab">실시간 시세</th></tr></thead><tbody>
      <tr><td class="lab">한미약품</td><td>128940</td><td class="lab">코스피</td><td class="lab"><span class="stale">미지원</span></td></tr>
      <tr><td class="lab">한미사이언스</td><td>008930</td><td class="lab">코스피</td><td class="lab"><span class="stale">미지원</span></td></tr>
      <tr><td class="lab">제이브이엠</td><td>054950</td><td class="lab">코스닥</td><td class="lab"><span class="stale">미지원</span></td></tr>
    </tbody></table></div>
    <p class="note">한국 주식 시세는 KRX 시세를 주는 다른 커넥터 연결 시 추가 가능 · 종목코드: DART 기업정보</p></section>

  <footer class="notes"><h4>데이터 · 방법</h4><ol>
    <li>원자재: Alpha Vantage COPPER · ALUMINUM · WTI · BRENT (월간, 월평균 국제가격) · 환율: CURRENCY_EXCHANGE_RATE (USD/KRW, 실시간 호가 · 기준 시각 UTC → 한국시간 표기)</li>
    <li>전월·전년 대비 = 같은 시리즈의 1개월·12개월 전 월평균 대비 · 원화 환산 = 최신 월평균 × 현재 환율 (기준 시점이 달라 참고용)</li>
    <li>보는 사람의 커넥터 자격으로 조회 · 호출 한도 초과 시 마지막 정상값과 시각 표시</li>
  </ol></footer>
</main>
"""

APP = r"""
const SERVER = "Alpha Vantage MCP Server";
const $ = id => document.getElementById(id), {num, spct, dir, esc} = K;
const ITEMS = [
  {key: "copper", tool: "COPPER", name: "구리", unit: "USD/톤", color: "--c3"},
  {key: "aluminum", tool: "ALUMINUM", name: "알루미늄", unit: "USD/톤", color: "--c2"},
  {key: "wti", tool: "WTI", name: "WTI 원유", unit: "USD/배럴", color: "--c4"},
  {key: "brent", tool: "BRENT", name: "브렌트유", unit: "USD/배럴", color: "--c5"},
];
const ST = {fx: K.store.get("lb_fx", null)};
ITEMS.forEach(it => { it.rows = (K.store.get("lb_" + it.key, null) || {}).rows || null; it.at = (K.store.get("lb_" + it.key, null) || {}).at || null; it.err = ""; });
const kst = ms => ms ? new Date(ms).toLocaleString("ko-KR", {timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit"}) : "-";
const ERR_TXT = {
  needs_reauth: "Alpha Vantage 연결이 만료됨 — claude.ai 설정 → 커넥터에서 다시 연결",
  server_not_connected: "Alpha Vantage 커넥터가 없음 — claude.ai 설정 → 커넥터에서 추가",
  selection_required: "같은 이름의 커넥터가 여러 개 — 어느 것을 쓸지 선택 필요",
  not_in_manifest: "이 페이지에서 Alpha Vantage 사용이 허용되지 않음",
  approval_required: "이 페이지의 Alpha Vantage 사용 승인 필요",
  blocked_by_policy: "조직 정책으로 차단됨",
  server_unavailable: "Alpha Vantage 응답 없음 — 잠시 후 자동 재시도",
};
const DENY = new Set(["needs_reauth", "server_not_connected", "selection_required", "not_in_manifest", "approval_required", "blocked_by_policy", "not_granted", "capability_disabled"]);
const errText = e => ERR_TXT[e.code] || (e.code === "tool_error" ? "Alpha Vantage 오류: " + (e.message || "").slice(0, 120) : "조회 실패 (" + e.code + ")");

/* 응답 해석 — 실제 호출로 확인한 형식 */
function parseSeries(p){
  if (p && p.error) return {limit: true, msg: p.error.message || p.error.type};
  if (!p || !Array.isArray(p.data)) return {bad: true};
  const rows = p.data.map(d => ({ym: String(d.date).slice(0, 7), v: parseFloat(d.value)})).filter(r => !isNaN(r.v)).sort((a, b) => a.ym < b.ym ? -1 : 1);
  return {rows};
}
function parseFx(p){
  if (p && p.error) return {limit: true, msg: p.error.message || p.error.type};
  const o = p && p["Realtime Currency Exchange Rate"]; if (!o) return {bad: true};
  const t = String(o["6. Last Refreshed"] || "").replace(" ", "T") + "Z";
  return {rate: parseFloat(o["5. Exchange Rate"]), bid: parseFloat(o["8. Bid Price"]), ask: parseFloat(o["9. Ask Price"]), at: Date.parse(t) || null};
}

/* 렌더 */
function renderFx(){
  const f = ST.fx;
  $("fxVal").innerHTML = f ? `${num(f.rate, 2)}<span class="k-unit">원</span>` : "-";
  $("fxSub").textContent = f ? `기준 ${kst(f.at)} (한국시간)` : "아직 받은 값 없음";
  $("fxBidAsk").textContent = f && !isNaN(f.bid) ? `${num(f.bid, 2)} · ${num(f.ask, 2)}` : "-";
}
function renderCards(){
  const fx = ST.fx && ST.fx.rate;
  $("cards").innerHTML = ITEMS.map(it => {
    if (!it.rows) return `<div class="cocard" style="--cc:${K.CSSV(it.color)}"><div class="nm">${it.name}</div><div class="ty">${it.unit}</div><div class="v" style="font-size:16px;color:var(--ink-3)">불러오는 중</div><div class="err">${esc(it.err)}</div></div>`;
    const r = it.rows, L = r[r.length - 1], p1 = r[r.length - 2], p12 = r[r.length - 13], m1 = p1 ? L.v / p1.v - 1 : null, m12 = p12 ? L.v / p12.v - 1 : null, d = L.v < 100 ? 2 : 1;
    return `<div class="cocard" style="--cc:${K.CSSV(it.color)}"><div class="nm">${it.name}</div><div class="ty">${it.unit} · ${L.ym.replace("-", ".")} 월평균</div>
      <div class="v">${num(L.v, d)}</div><div class="s">전월 <span class="delta inv ${dir(m1)}">${spct(m1)}</span> · 전년 <span class="delta inv ${dir(m12)}">${spct(m12)}</span></div>
      <div class="s">원화 환산 <b>${fx ? num(L.v * fx, 0) + "원" : "-"}</b> (참고)</div>
      <div class="s">받은 시각 ${kst(it.at)}${it.err ? ` · <span class="stale">${esc(it.err)}</span>` : ""}</div>${K.spark(r.slice(-24).map(x => x.v), it.color)}</div>`;
  }).join("");
}
function renderCharts(){
  const have = ITEMS.filter(it => it.rows && it.rows.length > 12);
  if (!have.length){ $("cmp").innerHTML = '<p class="note">원자재 시세를 받으면 차트가 그려짐</p>'; $("charts").innerHTML = ""; return; }
  const allYm = [...new Set(have.flatMap(it => it.rows.map(r => r.ym)))].sort().slice(-36), cats = allYm.map(m => m.slice(2).replace("-", "."));
  const ser = have.map(it => { const m = Object.fromEntries(it.rows.map(r => [r.ym, r.v])), v = allYm.map(y => m[y] ?? null), b = v.find(x => x != null);
    return {name: it.name, color: it.color, type: "line", vals: v.map(x => x == null ? null : x / b * 100), fmt: x => num(x, 1)}; });
  $("cmpL").innerHTML = K.legend(ser); K.combo($("cmp"), {cats, series: ser, zero: false, endLabels: true, h: 260});
  $("charts").innerHTML = have.map((it, i) => `<section class="panel"><div class="p-head"><h3 class="p-title">${it.name}</h3><span class="p-unit">${it.unit}</span></div><div class="chart" id="ch${i}"></div></section>`).join("");
  have.forEach((it, i) => { const m = Object.fromEntries(it.rows.map(r => [r.ym, r.v]));
    K.combo($("ch" + i), {cats, h: 200, l: 52, zero: false, fmt: x => num(x, x < 100 ? 2 : 1), series: [{name: it.name, color: it.color, type: "line", vals: allYm.map(y => m[y] ?? null)}]}); });
}
function renderAll(){ renderFx(); renderCards(); renderCharts(); }
renderAll();
K.onResize(renderCharts);

/* 커넥터 연결 */
const setStatus = (t, live) => { $("status").textContent = t; const b = $("liveBadge"); b.className = "live" + (live ? "" : " off"); b.textContent = live ? "자동 갱신 중" : "갱신 꺼짐"; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const mcp = window.claude && window.claude.use ? await window.claude.use("mcp") : null;
  if (!mcp){ setStatus("이 화면에서는 커넥터를 쓸 수 없음 — claude.ai에서 열면 Alpha Vantage로 자동 조회 (마지막 저장값 표시 중)", false); return; }
  setStatus("Alpha Vantage 조회 중", true);
  let denied = false;
  const retried = new Set();
  const onLimit = (tool, input) => { if (retried.has(tool)) return; retried.add(tool); setTimeout(() => mcp.invalidate(SERVER, tool, input).catch(() => {}), 65000); };
  const watch = (tool, input, apply, opts) => mcp.watchTool(SERVER, tool, input, ev => {
    if (ev.type === "error"){ const e = ev.error; if (DENY.has(e.code)){ denied = true; setStatus(errText(e), false); } apply(null, errText(e), DENY.has(e.code)); return; }
    apply(ev.result.payload, "", false, ev.result.cache ? ev.result.cache.storedAt : Date.now(), () => onLimit(tool, input));
  }, opts);
  const fxIn = {from_currency: "USD", to_currency: "KRW", datatype: "json"};
  watch("CURRENCY_EXCHANGE_RATE", fxIn, (p, err, deny, at, limit) => {
    if (err){ $("fxErr").textContent = err; if (deny){ ST.fx = null; } renderFx(); return; }
    const f = parseFx(p);
    if (f.limit){ $("fxErr").textContent = "호출 한도 도달 — 마지막 정상값 표시, 잠시 후 다시 시도"; limit(); return; }
    if (f.bad){ $("fxErr").textContent = "예상과 다른 응답 형식"; return; }
    $("fxErr").textContent = ""; ST.fx = f; K.store.set("lb_fx", f); renderAll();
  }, {cache: {staleTime: 30 * 60e3, gcTime: 24 * 3600e3}, refetchInterval: 2 * 3600e3});
  $("fxRefresh").hidden = false;
  $("fxRefresh").onclick = async () => {
    $("fxRefresh").disabled = true;
    try { const r = await mcp.callTool(SERVER, "CURRENCY_EXCHANGE_RATE", fxIn, {cache: {staleTime: 0, gcTime: 24 * 3600e3, refresh: true}}); const f = parseFx(r.payload);
      if (f.rate){ ST.fx = f; K.store.set("lb_fx", f); $("fxErr").textContent = ""; renderAll(); } else $("fxErr").textContent = f.limit ? "호출 한도 도달 — 1분 뒤 다시" : "예상과 다른 응답 형식"; }
    catch(e){ $("fxErr").textContent = errText(e); }
    setTimeout(() => $("fxRefresh").disabled = false, 5000);
  };
  for (const it of ITEMS){
    await sleep(1500);   // 초당 1회 한도
    if (denied) break;
    const input = {datatype: "json", interval: "monthly"};
    watch(it.tool, input, (p, err, deny, at, limit) => {
      if (err){ it.err = err; if (deny) it.rows = null; renderCards(); return; }
      const s = parseSeries(p);
      if (s.limit){ it.err = "호출 한도 도달 — 마지막 정상값 표시"; limit(); renderCards(); return; }
      if (s.bad){ it.err = "예상과 다른 응답 형식"; renderCards(); return; }
      it.rows = s.rows.slice(-60); it.at = at; it.err = ""; K.store.set("lb_" + it.key, {rows: it.rows, at}); renderAll();
    }, {cache: {staleTime: 12 * 3600e3, gcTime: 7 * 24 * 3600e3}, refetchInterval: 6 * 3600e3});
  }
  if (!denied) setStatus("Alpha Vantage 연결됨 · 원자재 12시간 · 환율 2시간 주기 자동 갱신", true);
})();
"""


def build(out_dir: str = "out") -> Path:
    css = (ROOT / "dashkit" / "kit.css").read_text(encoding="utf-8")
    js = (ROOT / "dashkit" / "kit.js").read_text(encoding="utf-8")
    html = ('<title>원자재·환율 실시간 현황판</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f"<style>\n{css}\n{EXTRA_CSS}\n</style>\n{BODY}\n<div id=\"tip\" role=\"tooltip\"></div>\n<script>\n{js}\n{APP}\n</script>\n")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / "원자재_실시간_현황판.html"
    p.write_text(html, encoding="utf-8")
    return p


if __name__ == "__main__":
    print(f"완료: {build(sys.argv[1] if len(sys.argv) > 1 else 'out')}")
