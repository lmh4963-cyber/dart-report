/* dashkit — 인라인 SVG 차트 · 툴팁 · 세그먼트 · 칩 · 테마 · 표 복사 (외부 라이브러리 없음). 글자 크기 정수 px */
const K = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const SVGF = '"Pretendard Variable", Pretendard, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif';
  const CSSV = c => (c && c.startsWith("--")) ? getComputedStyle(document.documentElement).getPropertyValue(c).trim() : c;

  /* 저장 (실패해도 동작) */
  const store = {
    get(k, d){ try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch(e){ return d; } },
    set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch(e){} },
  };

  /* 숫자 형식 */
  const nz = (v, d) => Math.abs(v) < 0.5 * Math.pow(10, -d) ? 0 : v;
  const num = (v, d = 0) => v == null || isNaN(v) ? "-" : nz(v, d).toLocaleString("ko-KR", {minimumFractionDigits: d, maximumFractionDigits: d});
  const pct = (v, d = 1) => v == null || isNaN(v) ? "-" : num(v * 100, d) + "%";
  const spct = (v, d = 1) => v == null || isNaN(v) ? "-" : (v > 0 ? "+" : "") + num(v * 100, d) + "%";
  const spp = (v, d = 1) => v == null || isNaN(v) ? "-" : (v > 0 ? "+" : "") + num(v * 100, d) + "%p";
  /* 증감 방향 — 표시 반올림 기준(기본 0.05%p) 이내는 보합 */
  const dir = (v, eps = 5e-4) => v == null || isNaN(v) || Math.abs(v) < eps ? "flat" : v > 0 ? "up" : "down";
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

  /* 툴팁 */
  let tip = null;
  function tipEl(){ if(!tip){ tip = document.getElementById("tip") || Object.assign(document.createElement("div"), {id: "tip"}); if(!tip.parentNode) document.body.appendChild(tip); } return tip; }
  function showTip(html, ev){
    const t = tipEl(); t.innerHTML = html; t.style.opacity = 1;
    const r = t.getBoundingClientRect();
    let x = ev.clientX + 14, y = ev.clientY - r.height - 12;
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
    if (y < 8) y = ev.clientY + 18;
    t.style.left = Math.max(8, x) + "px"; t.style.top = y + "px";
  }
  const hideTip = () => { if (tip) tip.style.opacity = 0; };
  addEventListener("scroll", hideTip, {passive: true});
  const tipRows = (title, rows, foot) => `<div class="t-h">${esc(title)}</div>` +
    rows.map(r => `<div class="t-r"><span class="nm"><i class="swatch" style="background:${CSSV(r.color)}"></i>${esc(r.name)}</span><span class="vl">${r.value}</span></div>`).join("") +
    (foot ? `<div class="t-f">${foot}</div>` : "");

  /* SVG 기본 */
  function el(tag, a = {}){ const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); return e; }
  function txt(s, a){ const t = el("text", Object.assign({"font-family": SVGF}, a)); t.textContent = s; return t; }
  function niceStep(v){
    if (v <= 0) return 1;
    const e = Math.pow(10, Math.floor(Math.log10(v))), m = v / e;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * e;
  }
  function scale(lo, hi, zero){
    if (zero){ lo = Math.min(0, lo); hi = Math.max(0, hi); }
    if (lo === hi){ lo -= 1; hi += 1; }
    const step = niceStep((hi - lo) / 4);
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    return {lo, hi, ticks: Math.max(1, Math.round((hi - lo) / step))};
  }
  function smoothPath(p){
    if (p.length < 3) return p.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + "," + q[1].toFixed(1)).join("");
    /* 단조 3차 보간 (넘침 없음) */
    const n = p.length, dx = [], m = [], t = [];
    for (let i = 0; i < n - 1; i++){ dx[i] = p[i+1][0] - p[i][0]; m[i] = (p[i+1][1] - p[i][1]) / (dx[i] || 1); }
    t[0] = m[0]; t[n-1] = m[n-2];
    for (let i = 1; i < n - 1; i++) t[i] = m[i-1] * m[i] <= 0 ? 0 : (m[i-1] + m[i]) / 2;
    for (let i = 0; i < n - 1; i++){
      if (m[i] === 0){ t[i] = 0; t[i+1] = 0; continue; }
      const a = t[i] / m[i], b = t[i+1] / m[i], h = a * a + b * b;
      if (h > 9){ const s = 3 / Math.sqrt(h); t[i] = s * a * m[i]; t[i+1] = s * b * m[i]; }
    }
    let d = `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
    for (let i = 0; i < n - 1; i++){
      const h = dx[i] / 3;
      d += `C${(p[i][0] + h).toFixed(1)},${(p[i][1] + t[i] * h).toFixed(1)} ${(p[i+1][0] - h).toFixed(1)},${(p[i+1][1] - t[i+1] * h).toFixed(1)} ${p[i+1][0].toFixed(1)},${p[i+1][1].toFixed(1)}`;
    }
    return d;
  }
  function roundBar(x, y0, w, y1, r){
    /* y0 = 기준선, y1 = 끝. 끝쪽 모서리만 둥글게 */
    const up = y1 < y0, h = Math.abs(y1 - y0); r = Math.min(r, w / 2, h);
    if (h < 0.5) return `M${x},${y0}h${w}`;
    return up
      ? `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 + r}V${y0}Z`
      : `M${x},${y0}V${y1 - r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 - r}V${y0}Z`;
  }

  /* 콤보 차트 — 단일 축, 막대(묶음) + 선. series: {name,color,vals,type:"bar"|"line",dash,fmt} */
  function combo(box, o){
    const cats = o.cats, S = o.series.filter(s => s.vals.some(v => v != null));
    const w = Math.max(280, box.clientWidth || 600), h = o.h || 240;
    const M = {t: 16, r: o.endLabels ? 56 : 12, b: 28, l: o.l || 48};
    box.innerHTML = "";
    const svg = el("svg", {viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: "img"});
    svg.style.width = "100%"; svg.style.height = "auto";
    box.appendChild(svg);
    if (!S.length){ svg.appendChild(txt("데이터 없음", {x: w / 2, y: h / 2, "text-anchor": "middle", fill: CSSV("--ink-3"), "font-size": 13})); return; }
    const all = S.flatMap(s => s.vals).filter(v => v != null);
    const bars = S.filter(s => (s.type || "bar") === "bar");
    const sc = scale(Math.min(...all), Math.max(...all), o.zero ?? bars.length > 0);
    const pw = w - M.l - M.r, ph = h - M.t - M.b, n = cats.length, band = pw / n;
    const Y = v => M.t + ph * (1 - (v - sc.lo) / (sc.hi - sc.lo));
    const X = i => M.l + band * (i + .5);
    const stp = (sc.hi - sc.lo) / sc.ticks;
    let adp = 0; while (adp < 3 && Math.abs(Math.round(stp * 10 ** adp) - stp * 10 ** adp) > 1e-6) adp++;
    let pdp = 0; while (pdp < 2 && Math.abs(Math.round(stp * 100 * 10 ** pdp) - stp * 100 * 10 ** pdp) > 1e-6) pdp++;
    const afmt = o.axisPct ? (v => num(v * 100, pdp) + "%") : (o.axisFmt || (v => num(v, adp)));
    for (let i = 0; i <= sc.ticks; i++){
      const v = sc.lo + (sc.hi - sc.lo) * i / sc.ticks, y = Y(v);
      svg.appendChild(el("line", {x1: M.l, x2: w - M.r, y1: y, y2: y, stroke: CSSV(Math.abs(v) < 1e-9 && sc.lo < 0 ? "--axis" : "--grid"), "stroke-width": 1}));
      svg.appendChild(txt(afmt(v), {x: M.l - 8, y: y + 4, "text-anchor": "end", fill: CSSV("--ink-3"), "font-size": 11}));
    }
    const every = Math.ceil(n / Math.max(1, Math.floor(pw / 52)));
    cats.forEach((c, i) => { if ((i % every === 0 && n - 1 - i >= every * .7) || i === n - 1) svg.appendChild(txt(c, {x: X(i), y: h - M.b + 17, "text-anchor": "middle", fill: CSSV("--ink-3"), "font-size": 11})); });
    /* 강조 띠 */
    const hl = el("rect", {x: 0, y: M.t - 6, width: Math.max(0, band - 4), height: ph + 8, rx: 10, fill: CSSV("--accent-soft"), opacity: 0});
    svg.appendChild(hl);
    /* 막대 */
    if (bars.length){
      const gw = Math.min(band * .7, bars.length * (o.slot || 26)), gap = bars.length > 1 ? 3 : 0, bw = Math.max(3, (gw - gap * (bars.length - 1)) / bars.length);
      const y0 = Y(Math.max(sc.lo, Math.min(0, sc.hi)));
      bars.forEach((s, j) => s.vals.forEach((v, i) => {
        if (v == null) return;
        const x = X(i) - gw / 2 + j * (bw + gap);
        svg.appendChild(el("path", {d: roundBar(x, y0, bw, Y(v), 5), fill: CSSV(s.colors ? s.colors[i] : s.color), opacity: s.opacity ?? 1}));
        if (o.barLabels && bars.length === 1) svg.appendChild(txt(o.barLabels(v, i), {x: x + bw / 2, y: (v >= 0 ? Y(v) - 5 : Y(v) + 13), "text-anchor": "middle", fill: CSSV("--ink"), "font-size": 11, "font-weight": 700}));
      }));
    }
    /* 선 */
    const ends = [];
    S.filter(s => s.type === "line").forEach(s => {
      const col = CSSV(s.color);
      const pts = s.vals.map((v, i) => v == null ? null : [X(i), Y(v), v]).filter(Boolean);
      if (!pts.length) return;
      // 결측 구간은 끊어서 그림
      let seg = [];
      s.vals.forEach((v, i) => {
        if (v == null){ if (seg.length) draw(seg); seg = []; } else seg.push([X(i), Y(v)]);
      });
      if (seg.length) draw(seg);
      function draw(q){ if (q.length > 1) svg.appendChild(el("path", {d: smoothPath(q), fill: "none", stroke: col, "stroke-width": s.width || 2.2, "stroke-linecap": "round", "stroke-dasharray": s.dash ? "5 4" : "none"})); }
      if (!s.dash && pts.length <= 16) pts.forEach(p => svg.appendChild(el("circle", {cx: p[0], cy: p[1], r: 3, fill: col, stroke: CSSV("--surface"), "stroke-width": 1.5})));
      if (o.endLabels && !s.dash){ const lp = pts[pts.length - 1]; ends.push({x: lp[0], y: lp[1], t: (s.fmt || o.fmt || num)(lp[2]), col}); }
    });
    ends.sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i-1].y < 13) ends[i].y = ends[i-1].y + 13;
    ends.forEach(e => svg.appendChild(txt(e.t, {x: e.x + 8, y: e.y + 4, fill: e.col, "font-size": 11, "font-weight": 700})));
    /* 호버 */
    const fmt = o.fmt || (v => num(v));
    cats.forEach((c, i) => {
      const hit = el("rect", {x: M.l + band * i, y: M.t - 8, width: band, height: ph + 12, fill: "transparent"});
      hit.style.cursor = "crosshair";
      const on = e => {
        hl.setAttribute("x", M.l + band * i + 2); hl.setAttribute("opacity", .55);
        const rows = S.filter(s => !s.noTip).map(s => ({name: s.colors ? c : s.name, color: s.colors ? s.colors[i] : s.color, value: s.vals[i] == null ? "-" : (s.fmt || fmt)(s.vals[i])}));
        showTip(tipRows(o.tipTitle ? o.tipTitle(i) : c, rows, o.tipFoot ? o.tipFoot(i) : ""), e);
      };
      hit.addEventListener("mousemove", on); hit.addEventListener("click", on);
      hit.addEventListener("mouseleave", () => { hl.setAttribute("opacity", 0); hideTip(); });
      svg.appendChild(hit);
    });
  }

  function spark(vals, color){
    const v = vals.filter(x => x != null);
    if (v.length < 2) return "";
    const w = 200, h = 44, pad = 4, lo = Math.min(...v), hi = Math.max(...v), span = (hi - lo) || 1, n = v.length;
    const pts = v.map((x, i) => [pad + (w - 2 * pad) * i / (n - 1), h - pad - (h - 2 * pad) * (x - lo) / span]);
    const c = CSSV(color), line = smoothPath(pts);
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
      <path d="${line} L${pts[n-1][0]},${h} L${pts[0][0]},${h} Z" fill="${c}" opacity=".13"/>
      <path d="${line}" fill="none" stroke="${c}" stroke-width="2" vector-effect="non-scaling-stroke"/>
      <circle cx="${pts[n-1][0]}" cy="${pts[n-1][1]}" r="2.6" fill="${c}"/></svg>`;
  }

  const legend = ss => `<div class="legend">${ss.map(s => `<span><i class="swatch ${s.type === "line" ? (s.dash ? "dash" : "ln") : ""}" style="${s.dash ? "border-color" : "background"}:${CSSV(s.color)}"></i>${esc(s.name)}</span>`).join("")}</div>`;

  /* 세그먼트 · 칩 */
  function seg(box, opts, cur, onChange){
    box.innerHTML = opts.map(([v, l]) => `<button type="button" aria-pressed="${String(v) === String(cur)}" data-v="${esc(v)}">${esc(l)}</button>`).join("");
    box.querySelectorAll("button").forEach(b => b.onclick = () => onChange(opts.find(o => String(o[0]) === b.dataset.v)[0]));
  }
  function chips(box, items, sel, onChange, fixed){
    box.innerHTML = items.map(it => `<button type="button" class="chip" aria-pressed="${sel.has(it.id)}" data-id="${esc(it.id)}" ${fixed === it.id ? "disabled" : ""}><i style="background:${CSSV(it.color)}"></i>${esc(it.label)}</button>`).join("");
    box.querySelectorAll(".chip").forEach(b => b.onclick = () => {
      const id = b.dataset.id; if (sel.has(id)){ if (sel.size > 1) sel.delete(id); } else sel.add(id);
      onChange(sel);
    });
  }

  /* 표 복사 (TSV) */
  async function copyTable(table, btn){
    const tsv = [...table.rows].map(r => [...r.cells].map(c => c.innerText.replace(/\s+/g, " ").trim()).join("\t")).join("\n");
    try { await navigator.clipboard.writeText(tsv); if (btn){ const t = btn.textContent; btn.textContent = "복사됨"; setTimeout(() => btn.textContent = t, 1200); } }
    catch(e){ if (btn) btn.textContent = "복사 실패"; }
  }

  /* 테마 */
  function theme(btn){
    const root = document.documentElement;
    const apply = t => { if (t) root.setAttribute("data-theme", t); else root.removeAttribute("data-theme"); };
    apply(store.get("dk_theme", null));
    const label = () => { const dark = (root.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark"; btn.textContent = dark ? "라이트 모드" : "다크 모드"; return dark; };
    label();
    btn.onclick = () => { const dark = label(); const t = dark ? "light" : "dark"; apply(t); store.set("dk_theme", t); label(); dispatchEvent(new Event("dk-theme")); };
  }

  function onResize(fn){ let t; addEventListener("resize", () => { clearTimeout(t); t = setTimeout(fn, 120); }); addEventListener("dk-theme", fn); }

  return {CSSV, store, num, pct, spct, spp, dir, esc, showTip, hideTip, tipRows, combo, spark, legend, seg, chips, copyTable, theme, onResize};
})();
