/* 黑底白线讲解视频 · 渲染引擎
 *
 * 画面完全由时间决定：seek(t) 把舞台摆成第 t 秒的样子，Python 端逐帧截图。
 * 不用任何 CSS 动画/过渡，所以同一时间永远得到同一帧。
 *
 * 入口：init(video) → seek(t) / showCover()
 * video 的结构见 make_video.py 里的 build_timeline()。 */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const SHAPES = 'path,line,polyline,polygon,circle,ellipse,rect';

  // ---------- 小工具 ----------
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const E = {
    out: p => 1 - Math.pow(1 - p, 3),
    inOut: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    back: p => { const c = 1.9; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); },
  };
  function rng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const hash = n => rng(Math.floor(n) * 9301 + 49297)();
  const arr = x => (x == null ? [] : Array.isArray(x) ? x : [x]);

  function h(tag, cls, parent, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function s(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  // 估算文字宽度（单位：字号），中文按 1，英文数字按 0.58
  const units = str => { let u = 0; for (const ch of String(str)) u += /[\x00-\xff]/.test(ch) ? 0.58 : 1; return u; };
  const fit = (lines, maxW, base, min) =>
    Math.round(Math.max(min, Math.min(base, maxW / Math.max(1, ...lines.map(units)))));

  // 把文字里的重点词包成 <span class="hl">
  function rich(parent, text, hls) {
    text = String(text);
    hls = arr(hls).filter(Boolean).map(String).sort((a, b) => b.length - a.length);
    let i = 0;
    while (i < text.length) {
      let hit = null, at = text.length;
      for (const w of hls) {
        const j = text.indexOf(w, i);
        if (j >= 0 && j < at) { at = j; hit = w; }
      }
      if (at > i) parent.appendChild(document.createTextNode(text.slice(i, at)));
      if (!hit) break;
      h('span', 'hl', parent, hit);
      i = at + hit.length;
    }
    return parent;
  }

  // 线宽随图形大小变化，大图 7px 左右，小图 3px 左右
  const strokePx = size => clamp(size / 52, 3, 7.5);

  function icon(name, size, parent, cls) {
    const nodes = window.ICONS[name] || window.ICONS['circle-help'];
    const svg = s('svg', { viewBox: '0 0 24 24', width: size, height: size, class: 'ico ' + (cls || '') }, parent);
    const sw = (strokePx(size) * 24) / size;
    for (const [tag, attrs] of nodes) s(tag, Object.assign({}, attrs, { pathLength: 1, 'stroke-width': sw }), svg);
    return svg;
  }

  // 自定义线稿：sc.svg 是 viewBox（默认 0 0 100 100）里的 SVG 片段
  function drawing(markup, viewBox, w, hgt, parent, cls) {
    const svg = s('svg', { viewBox: viewBox || '0 0 100 100', width: w, height: hgt, class: 'ico ' + (cls || '') }, parent);
    svg.innerHTML = markup;
    const vb = (viewBox || '0 0 100 100').split(/[\s,]+/).map(Number);
    const scale = vb[2] / w;
    svg.querySelectorAll(SHAPES).forEach(e => {
      e.setAttribute('pathLength', 1);
      if (!e.getAttribute('stroke-width')) e.setAttribute('stroke-width', strokePx(Math.max(w, hgt)) * scale);
    });
    return svg;
  }
  const visual = (sc, size, parent, cls) =>
    sc.svg ? drawing(sc.svg, sc.viewBox, size, size, parent, cls) : icon(sc.icon || 'sparkles', size, parent, cls);

  // ---------- 全局状态 ----------
  let V, W, H, P, stage, bgCtx, built = [], subEl, subIdx = -2, segs = [], flashEl;
  const CW = () => (P ? 900 : 1560);   // 文字可用宽度（左右留边）

  // 第 k 个元素在场景里出现的时间：跟着第几句旁白出现
  function cues(sc, k, items) {
    const L = sc.lines || [];
    const n = L.length;
    return Array.from({ length: k }, (_, i) => {
      if (!n) return 0.2 + i * 0.6;
      const it = items && items[i] && items[i].at != null ? items[i].at
        : sc.cues && sc.cues[i] != null ? sc.cues[i] : Math.floor((i * n) / k);
      return Math.max(0.12, L[clamp(it, 0, n - 1)].start - 0.08);
    });
  }

  // ---------- 场景类型 ----------
  const B = {};

  // 大标题：钩子、观点、结论都能用
  B.headline = (sc, root, R) => {
    if (sc.kicker) R.add('fade', h('div', 'kicker', root, sc.kicker), 0, 0.45);
    if (sc.icon || sc.svg) R.add('draw', visual(sc, P ? 240 : 200, root, 'glow-soft'), 0.05, 0.9);
    const lines = String(sc.text || (sc.lines || []).map(l => l.text).join('\n')).split('\n');
    const size = fit(lines, CW(), sc.size || (P ? 150 : 140), 60);
    const box = h('div', 'headline', root);
    box.style.fontSize = size + 'px';
    const hls = arr(sc.highlight);
    const ts = sc.together ? lines.map(() => 0.1) : cues(sc, lines.length);
    lines.forEach((ln, i) => {
      const d = rich(h('div', 'hline', box), ln, hls);
      const key = hls.some(w => ln.includes(w));
      R.add(key ? 'glitch' : 'fade', d, ts[i], key ? 0.5 : 0.4);
    });
    if (sc.sub) R.add('fade', rich(h('div', 'sub-label', root), sc.sub, hls), cues(sc, 2)[1] + 0.2, 0.5);
  };

  // 大问号 + 问题
  B.question = (sc, root, R) => {
    const q = s('svg', { viewBox: '0 0 100 140', width: P ? 260 : 190, height: P ? 364 : 266, class: 'ico accent' }, root);
    s('path', { d: 'M27 44 C27 20 42 9 53 9 C70 9 80 22 80 39 C80 58 53 62 53 84 L53 94', pathLength: 1, 'stroke-width': 8 }, q);
    s('circle', { cx: 53, cy: 120, r: 3.5, pathLength: 1, 'stroke-width': 9 }, q);
    R.add('draw', q, 0.05, 0.9);
    R.add('pulse', q, 1.1, 1.8);
    const lines = String(sc.text || '').split('\n').filter(Boolean);
    if (lines.length) {
      const box = h('div', 'headline', root);
      box.style.fontSize = fit(lines, CW(), sc.size || (P ? 110 : 110), 56) + 'px';
      const ts = cues(sc, lines.length);
      lines.forEach((ln, i) => R.add('fade', rich(h('div', 'hline', box), ln, sc.highlight), ts[i], 0.4));
    }
  };

  // 大数字：数字从 0 滚到目标值，外圈画一个环
  B.number = (sc, root, R) => {
    const raw = String(sc.value);
    const m = raw.match(/-?\d+(\.\d+)?/);
    const to = m ? parseFloat(m[0]) : 0;
    const dec = m && m[1] ? m[1].length - 1 : 0;
    const unit = sc.unit != null ? sc.unit : m ? raw.slice(m.index + m[0].length) : '';
    const pre = m ? raw.slice(0, m.index) : '';
    const D = P ? 600 : 460;
    const wrap = h('div', 'num-wrap', root);
    wrap.style.width = wrap.style.height = D + 'px';
    const ring = s('svg', { viewBox: '0 0 200 200', width: D, height: D, class: 'ring' }, wrap);
    s('circle', { cx: 100, cy: 100, r: 92, class: 'ring-bg', 'stroke-width': 1 }, ring);
    for (let i = 0; i < 60; i++) {
      const a = (i / 60) * Math.PI * 2, r1 = 97, r2 = i % 5 ? 99 : 101;
      s('line', { x1: 100 + r1 * Math.cos(a), y1: 100 + r1 * Math.sin(a), x2: 100 + r2 * Math.cos(a), y2: 100 + r2 * Math.sin(a), class: 'tick', 'stroke-width': 0.6 }, ring);
    }
    const arc = s('circle', { cx: 100, cy: 100, r: 92, pathLength: 1, class: 'ring-fg', 'stroke-width': 2.6, transform: 'rotate(-90 100 100)' }, ring);
    const pct = /%$/.test(unit.trim()) && to > 0 && to <= 100 ? to / 100 : sc.fill != null ? sc.fill : 1;
    R.add('draw', arc, 0.05, 1.3, { max: pct });
    const inner = h('div', 'num-inner', wrap);
    if (sc.prefix) h('div', 'num-prefix', inner, sc.prefix);
    const row = h('div', 'num-row', inner);
    const val = h('span', 'num-val', row);
    val.style.fontSize = fit([pre + to.toFixed(dec)], D * 0.72 - units(unit) * 64, P ? 200 : 160, 70) + 'px';
    if (unit) h('span', 'num-unit', row, unit);
    if (m) R.add('count', val, 0.1, 1.3, { to, dec, pre });
    else { val.textContent = raw; R.add('pop', val, 0.1, 0.5); }
    R.add('pop', inner, 0.05, 0.5);
    if (sc.label) {
      const lb = rich(h('div', 'big-label', root), sc.label, sc.highlight);
      lb.style.fontSize = fit([sc.label], CW(), P ? 76 : 70, 44) + 'px';
      R.add('fade', lb, cues(sc, 2)[1], 0.45);
    }
  };

  // 一个大图标（或自定义线稿）+ 文字
  B.icon = (sc, root, R) => {
    const size = sc.svg ? (P ? 620 : 470) : P ? 400 : 330;
    R.add('draw', visual(sc, size, root, sc.accent ? 'accent' : 'glow-soft'), 0.05, sc.svg ? 1.6 : 1.0);
    const ts = cues(sc, 2);
    if (sc.label) {
      const lb = rich(h('div', 'big-label', root), sc.label, sc.highlight);
      lb.style.fontSize = fit([sc.label], CW(), P ? 100 : 90, 52) + 'px';
      const key = arr(sc.highlight).some(w => String(sc.label).includes(w));
      R.add(key ? 'glitch' : 'fade', lb, ts[0] + 0.35, 0.45);
    }
    if (sc.sub) R.add('fade', rich(h('div', 'sub-label', root), sc.sub, sc.highlight), ts[1] + 0.1, 0.45);
  };
  B.draw = B.icon;

  // 2~6 个图标一组
  B.icons = (sc, root, R) => {
    const items = sc.items || [];
    const k = items.length;
    const grid = h('div', 'grid g' + k, root);
    const ts = cues(sc, k, items);
    const size = P ? (k <= 2 || k === 4 ? 250 : 220) : k <= 3 ? 220 : 170;
    items.forEach((it, i) => {
      const c = h('div', 'cell' + (it.hl ? ' on' : ''), grid);
      const ic = it.svg ? drawing(it.svg, it.viewBox, size, size, c) : icon(it.icon, size, c, it.hl ? '' : 'glow-soft');
      const lb = h('div', 'cell-label', c, it.label);
      lb.style.fontSize = fit([it.label || ''], P ? (k === 2 || k === 4 ? 400 : 290) : 290, P ? 64 : 56, 36) + 'px';
      if (it.note) h('div', 'cell-note', c, it.note);
      R.add('pop', c, ts[i], 0.45);
      R.add('draw', ic, ts[i], 0.8);
    });
  };

  // 左右对比：vs（默认）/ arrow（从左到右）/ fix（左边打叉，右边才是对的）
  B.compare = (sc, root, R) => {
    const mode = sc.mode || 'vs';
    const wrap = h('div', 'cmp', root);
    const ts = cues(sc, 2);
    const size = P ? 250 : 230;
    const panel = (d, on) => {
      const p = h('div', 'cmp-panel' + (on ? ' on' : ''), wrap);
      const ib = h('div', 'cmp-icon', p);
      const ic = d.svg ? drawing(d.svg, d.viewBox, size, size, ib) : icon(d.icon, size, ib, on ? '' : 'glow-soft');
      const tx = h('div', 'cmp-text', p);
      if (d.title) h('div', 'cmp-tag', tx, d.title);
      const lb = rich(h('div', 'cmp-label', tx), d.label || '', d.highlight);
      lb.style.fontSize = fit([d.label || ''], P ? 520 : 600, P ? 110 : 90, 44) + 'px';
      if (d.note) h('div', 'cmp-note', tx, d.note);
      return { p, ib, ic };
    };
    const L = panel(sc.left || {}, false);
    const mid = mode === 'vs' ? h('div', 'cmp-mid', wrap, 'VS') : null;
    let arrowSvg = null;
    if (mode === 'arrow' || mode === 'fix') {
      arrowSvg = P ? s('svg', { viewBox: '0 0 60 90', width: 60, height: 90, class: 'arrow' }, wrap)
        : s('svg', { viewBox: '0 0 120 60', width: 120, height: 60, class: 'arrow' }, wrap);
      const d = P ? 'M30 6 V80 M14 64 L30 82 L46 64' : 'M6 30 H110 M92 14 L112 30 L92 46';
      s('path', { d, pathLength: 1, 'stroke-width': 5 }, arrowSvg);
    }
    const Rt = panel(sc.right || {}, mode !== 'vs' || (sc.right || {}).hl);
    R.add('fade', L.p, ts[0], 0.45);
    R.add('draw', L.ic, ts[0], 0.8);
    if (mid) R.add('glitch', mid, ts[1] - 0.25, 0.4);
    if (arrowSvg) R.add('draw', arrowSvg, ts[1] - 0.3, 0.35);
    R.add('fade', Rt.p, ts[1], 0.45);
    R.add('draw', Rt.ic, ts[1], 0.8);
    if (mode === 'fix') {
      const x = s('svg', { viewBox: '0 0 100 100', class: 'strike ico accent' }, L.ib);
      s('path', { d: 'M15 15 L85 85 M85 15 L15 85', pathLength: 1, 'stroke-width': 6 }, x);
      R.add('draw', x, ts[1] - 0.1, 0.35);
      R.add('dim', L.p, ts[1] - 0.1, 0.3);
    }
  };

  // 流程：一步接一步，箭头连起来
  B.flow = (sc, root, R) => {
    const steps = sc.steps || [];
    const k = steps.length;
    const wrap = h('div', 'flow', root);
    const ts = cues(sc, k, steps);
    const gap = P ? 64 : 80;
    const nw = P ? 800 : Math.min(360, (1600 - (k - 1) * gap) / k);
    const nh = P ? Math.min(170, (980 - (k - 1) * gap) / k) : 300;
    const isz = P ? Math.min(96, nh * 0.6) : 120;
    steps.forEach((st, i) => {
      if (i) {
        const ar = P ? s('svg', { viewBox: '0 0 40 64', width: 40, height: gap, class: 'arrow' }, wrap)
          : s('svg', { viewBox: '0 0 80 40', width: gap, height: 40, class: 'arrow' }, wrap);
        s('path', { d: P ? 'M20 6 V56 M8 44 L20 58 L32 44' : 'M4 20 H72 M60 8 L74 20 L60 32', pathLength: 1, 'stroke-width': 4 }, ar);
        R.add('draw', ar, ts[i] - 0.3, 0.3);
      }
      const node = h('div', 'node' + (st.hl ? ' on' : ''), wrap);
      node.style.width = nw + 'px';
      node.style.height = nh + 'px';
      const fr = s('svg', { class: 'frame', viewBox: `0 0 ${nw} ${nh}`, width: nw, height: nh }, node);
      s('rect', { x: 0, y: 0, width: nw, height: nh, rx: Math.min(28, nh / 3), pathLength: 1, 'stroke-width': 3 }, fr);
      h('div', 'node-idx', node, String(i + 1).padStart(2, '0'));
      const body = h('div', 'node-body', node);
      const ic = st.svg ? drawing(st.svg, st.viewBox, isz, isz, body) : icon(st.icon, isz, body, st.hl ? 'accent' : '');
      const tx = h('div', '', body);
      const lb = h('div', 'node-label', tx, st.label);
      lb.style.fontSize = fit([st.label || ''], P ? nw - isz - 140 : nw - 40, P ? 60 : 50, 34) + 'px';
      if (st.note) h('div', 'node-note', tx, st.note);
      R.add('draw', fr, ts[i], 0.6);
      R.add('fade', body, ts[i] + 0.1, 0.4);
      R.add('draw', ic, ts[i] + 0.1, 0.7);
    });
  };

  // 循环：几个环节绕成一圈（恶性循环、飞轮效应）
  B.cycle = (sc, root, R) => {
    const steps = sc.steps || [];
    const k = steps.length;
    const S = P ? 860 : 640, c = S / 2, r0 = S * 0.37, nd = P ? 180 : 140;
    const wrap = h('div', 'cyc', root);
    wrap.style.width = wrap.style.height = S + 'px';
    const svg = s('svg', { viewBox: `0 0 ${S} ${S}`, width: S, height: S }, wrap);
    const ts = cues(sc, k, steps);
    const ang = i => -Math.PI / 2 + (i * 2 * Math.PI) / k;
    const pt = a => [c + r0 * Math.cos(a), c + r0 * Math.sin(a)];
    const gapA = (nd / 2 + 22) / r0;
    steps.forEach((st, i) => {
      const a = ang(i), [x, y] = pt(a);
      const n = h('div', 'cyc-node' + (st.hl ? ' on' : ''), wrap);
      n.style.cssText = `left:${x - nd / 2}px;top:${y - nd / 2}px;width:${nd}px;height:${nd}px`;
      const o = s('svg', { viewBox: `0 0 ${nd} ${nd}`, width: nd, height: nd, class: 'ring-o' }, n);
      s('circle', { cx: nd / 2, cy: nd / 2, r: nd / 2 - 2, pathLength: 1, 'stroke-width': 3 }, o);
      const ic = icon(st.icon, nd * 0.5, n, st.hl ? 'accent' : '');
      const lb = h('div', 'cyc-label', n, st.label);
      const below = Math.sin(a) > -0.2;
      lb.style.top = below ? nd + 14 + 'px' : 'auto';
      lb.style.bottom = below ? 'auto' : nd + 14 + 'px';
      if (P) lb.style.fontSize = fit([st.label || ''], 300, 46, 32) + 'px';
      // 从这一环指向下一环的弧线
      const a1 = a + gapA, a2 = ang(i + 1) - gapA;
      const [x1, y1] = pt(a1), [x2, y2] = pt(a2);
      const g = s('g', {}, svg);
      s('path', { d: `M${x1} ${y1} A${r0} ${r0} 0 0 1 ${x2} ${y2}`, pathLength: 1, 'stroke-width': 3.5 }, g);
      const ta = a2 + Math.PI / 2, L = 20;
      const w1 = [x2 - L * Math.cos(ta - 0.5), y2 - L * Math.sin(ta - 0.5)];
      const w2 = [x2 - L * Math.cos(ta + 0.5), y2 - L * Math.sin(ta + 0.5)];
      s('polyline', { points: `${w1} ${x2},${y2} ${w2}`, pathLength: 1, 'stroke-width': 3.5 }, g);
      R.add('draw', o, ts[i], 0.5);
      R.add('draw', ic, ts[i] + 0.05, 0.6);
      R.add('show', lb, ts[i] + 0.1, 0.35);
      R.add('draw', g, (i + 1 < k ? ts[i + 1] : ts[i] + 0.6) - 0.35, 0.4);
    });
    if (sc.center) {
      const ce = rich(h('div', '', h('div', 'cyc-center', wrap)), sc.center, sc.highlight);
      ce.style.fontSize = fit([sc.center], r0 * 1.15, P ? 70 : 56, 36) + 'px';
      R.add('glitch', ce, ts[k - 1] + 0.7, 0.5);
    }
  };

  // 编号清单
  B.list = (sc, root, R) => {
    const items = (sc.items || []).map(it => (typeof it === 'string' ? { text: it } : it));
    const k = items.length;
    const ts = cues(sc, k, items);
    if (sc.title) R.add('fade', rich(h('div', 'list-title', root), sc.title, sc.highlight), 0, 0.4);
    const ul = h('div', 'list', root);
    const fs = fit(items.map(it => it.text), P ? 760 : 1400, P ? 62 : 62, 38);
    items.forEach((it, i) => {
      const row = h('div', 'row' + (it.hl ? ' on' : ''), ul);
      const b = h('div', 'badge', row, String(i + 1).padStart(2, '0'));
      const ring = s('svg', { viewBox: '0 0 104 104', width: 104, height: 104 }, b);
      s('circle', { cx: 52, cy: 52, r: 49, pathLength: 1, 'stroke-width': 3 }, ring);
      const tx = h('div', '', row);
      const t = rich(h('div', 'row-text', tx), it.text, it.highlight || sc.highlight);
      t.style.fontSize = fs + 'px';
      if (it.note) h('div', 'row-note', tx, it.note);
      R.add('fade', row, ts[i], 0.4);
      R.add('draw', ring, ts[i], 0.5);
    });
  };

  // 横向柱状图
  B.bars = (sc, root, R) => {
    const items = sc.items || [];
    const k = items.length;
    const ts = cues(sc, k, items);
    if (sc.title) R.add('fade', rich(h('div', 'list-title', root), sc.title, sc.highlight), 0, 0.4);
    const max = Math.max(...items.map(it => +it.value || 0), 1e-9);
    const top = items.reduce((b, it, i) => ((+it.value || 0) > (+items[b].value || 0) ? i : b), 0);
    const wrap = h('div', 'bars', root);
    items.forEach((it, i) => {
      const on = it.hl != null ? it.hl : sc.highlightMax !== false && i === top;
      const bar = h('div', 'bar' + (on ? ' on' : ''), wrap);
      const head = h('div', 'bar-head', bar);
      h('div', 'bar-label', head, it.label);
      const v = h('div', 'bar-val', head);
      const tr = h('div', 'bar-track', bar);
      const f = h('div', 'bar-fill', tr);
      f.style.width = ((+it.value || 0) / max) * 100 + '%';
      const raw = String(it.value);
      const dec = raw.includes('.') ? raw.split('.')[1].length : 0;
      R.add('fade', bar, ts[i] - 0.05, 0.3);
      R.add('grow', f, ts[i], 0.9);
      R.add('count', v, ts[i], 0.9, { to: +it.value || 0, dec, post: sc.unit || it.unit || '' });
    });
  };

  // 金句：引号 + 一句话
  B.quote = (sc, root, R) => {
    R.add('draw', icon('quote', P ? 170 : 140, root, 'accent'), 0.05, 0.7);
    const lines = String(sc.text || '').split('\n');
    const box = h('div', 'quote-text', root);
    box.style.fontSize = fit(lines, CW(), sc.size || (P ? 112 : 104), 54) + 'px';
    const hls = arr(sc.highlight);
    const ts = cues(sc, lines.length);
    lines.forEach((ln, i) => {
      const key = hls.some(w => ln.includes(w));
      R.add(key ? 'glitch' : 'fade', rich(h('div', 'hline', box), ln, hls), ts[i], key ? 0.5 : 0.4);
    });
    if (sc.by) R.add('fade', h('div', 'quote-by', root, '— ' + sc.by), ts[lines.length - 1] + 0.5, 0.4);
  };

  // 结尾：关注 + 下期预告
  B.cta = (sc, root, R) => {
    const row = h('div', 'cta-icons', root);
    const ics = arr(sc.icons || ['user-plus', 'heart', 'message-circle']);
    ics.forEach((n, i) => R.add('draw', icon(n, P ? 130 : 110, row, i === 1 ? 'accent' : 'glow-soft'), 0.05 + i * 0.18, 0.6));
    const text = sc.text || '关注我';
    const tx = rich(h('div', 'cta-text', root), text, sc.highlight);
    tx.style.fontSize = fit(String(text).split('\n'), CW(), P ? 130 : 120, 60) + 'px';
    R.add('glitch', tx, 0.25, 0.5);
    const ts = cues(sc, 2);
    if (V.brand) R.add('fade', h('div', 'cta-brand', root, V.brand), 0.6, 0.4);
    if (sc.next) {
      const c = h('div', 'capsule', root);
      h('b', '', c, '下期 · ');
      c.appendChild(document.createTextNode(sc.next));
      R.add('pop', c, Math.max(0.9, ts[1]), 0.45);
    }
  };

  // ---------- 动作（reveal）----------
  function applyReveal(r, tl, t) {
    const p = clamp((tl - r.at) / r.dur);
    const e = r.el;
    switch (r.kind) {
      case 'fade': {
        const q = E.out(p);
        e.style.opacity = q;
        e.style.transform = q < 1 ? `translateY(${(1 - q) * 40}px)` : 'none';
        break;
      }
      case 'pop':
        e.style.opacity = clamp(p * 2.5);
        e.style.transform = p < 1 ? `scale(${0.55 + 0.45 * E.back(p)})` : 'none';
        break;
      case 'show':
        e.style.opacity = E.out(p);
        break;
      case 'dim':
        e.style.opacity = 1 - 0.5 * E.out(p);
        break;
      case 'draw': {
        const sh = r.shapes, n = sh.length;
        const st = n > 1 ? Math.min(0.12, 0.45 / (n - 1)) : 0;
        sh.forEach((x, j) => {
          const q = clamp((p - j * st) / (1 - (n - 1) * st));
          x.style.strokeDasharray = '1 1';
          x.style.strokeDashoffset = 1 - E.out(q) * (r.max || 1);
          x.style.opacity = q > 0 ? 1 : 0;
        });
        r.texts.forEach(x => (x.style.opacity = p));
        break;
      }
      case 'glitch': {
        if (p <= 0) { e.style.opacity = 0; break; }
        if (p >= 1) { e.style.opacity = 1; e.style.transform = 'none'; e.style.textShadow = ''; e.style.clipPath = 'none'; break; }
        const f = Math.floor(t * 30), k = 1 - p;
        const r1 = hash(f * 7 + r.seed), r2 = hash(f * 13 + r.seed + 1), r3 = hash(f * 17 + r.seed + 2);
        e.style.opacity = r1 < 0.22 * k ? 0.2 : 1;
        e.style.transform = `translateX(${(r2 - 0.5) * 40 * k}px)`;
        const o = 12 * k;
        e.style.textShadow = `${o}px 0 rgba(255,45,85,.85), ${-o}px 0 rgba(0,229,255,.85)`;
        if (k > 0.35 && r2 > 0.55) {
          const y0 = r3 * 70, hh = 12 + r1 * 30;
          e.style.clipPath = `inset(${y0}% 0 ${Math.max(0, 100 - y0 - hh)}% 0)`;
        } else e.style.clipPath = 'none';
        break;
      }
      case 'count': {
        const v = r.to * E.out(p);
        e.textContent = (r.pre || '') + v.toFixed(r.dec || 0) + (r.post || '');
        break;
      }
      case 'grow':
        e.style.transform = `scaleX(${E.out(p)})`;
        break;
      case 'pulse': {
        if (tl < r.at) { e.style.transform = 'none'; break; }
        const k = ((tl - r.at) % r.dur) / r.dur;
        e.style.transform = `scale(${1 + 0.045 * Math.sin(k * Math.PI * 2)})`;
        break;
      }
    }
  }

  function buildScene(sc, idx) {
    const root = h('div', 'scene', document.getElementById('scenes'));
    const inner = h('div', 'inner', root);
    const reveals = [];
    const R = {
      add(kind, el, at, dur, opts) {
        const r = Object.assign({ kind, el, at: Math.max(0, at), dur, seed: idx * 101 + reveals.length * 7 }, opts || {});
        if (kind === 'draw') {
          r.shapes = el.matches && el.matches(SHAPES) ? [el] : [...el.querySelectorAll(SHAPES)];
          r.texts = [...el.querySelectorAll('text')];
        }
        reveals.push(r);
        return r;
      },
    };
    (B[sc.type] || B.headline)(sc, inner, R);
    root.style.display = 'none';
    return { sc, root, inner, reveals, start: sc.start, end: sc.end };
  }

  // ---------- 背景 ----------
  let stars = [];
  function hexRGB(hex) {
    const m = String(hex).replace('#', '');
    const n = parseInt(m.length === 3 ? m.replace(/./g, '$&$&') : m, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function drawBg(t) {
    const c = bgCtx;
    c.globalAlpha = 1;
    c.fillStyle = '#040407';
    c.fillRect(0, 0, W, H);
    const [ar, ag, ab] = hexRGB(V.accent);
    const fog = (x, y, r, col) => {
      const g = c.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, col);
      g.addColorStop(1, 'rgba(0,0,0,0)');
      c.fillStyle = g;
      c.fillRect(0, 0, W, H);
    };
    const M = Math.max(W, H);
    fog(W * (0.26 + 0.07 * Math.sin(t * 0.13)), H * (0.3 + 0.04 * Math.cos(t * 0.11)), M * 0.55, `rgba(${ar},${ag},${ab},0.15)`);
    fog(W * (0.8 + 0.05 * Math.cos(t * 0.09)), H * (0.78 + 0.03 * Math.sin(t * 0.12)), M * 0.5, 'rgba(50,80,190,0.10)');
    if (V.bg === 'dots') {
      const sp = 40;
      c.fillStyle = '#fff';
      for (let y = sp / 2; y < H; y += sp) {
        for (let x = sp / 2; x < W; x += sp) {
          const w = Math.sin(x * 0.008 + t * 0.9) + Math.sin(y * 0.006 - t * 0.6) + Math.sin((x + y) * 0.004 + t * 0.4);
          const v = (w + 3) / 6;
          c.globalAlpha = 0.04 + 0.32 * Math.pow(v, 3);
          c.beginPath();
          c.arc(x, y, 1 + 2.2 * Math.pow(v, 2), 0, Math.PI * 2);
          c.fill();
        }
      }
    } else if (V.bg !== 'none') {
      c.fillStyle = '#fff';
      for (const st of stars) {
        const y = (((st.y - t * 0.006 * st.z) % 1) + 1) % 1;
        const a = 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(t * (0.7 + st.z * 1.5) + st.ph));
        c.globalAlpha = a * st.z;
        const r = st.big ? 2.4 : 0.7 + st.z * 1.3;
        c.beginPath();
        c.arc(st.x * W, y * H, r, 0, Math.PI * 2);
        c.fill();
        if (st.big) {
          c.globalAlpha = a * 0.35;
          c.fillRect(st.x * W - 10, y * H - 0.6, 20, 1.2);
          c.fillRect(st.x * W - 0.6, y * H - 10, 1.2, 20);
        }
      }
    }
    c.globalAlpha = 1;
    const v = c.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, M * 0.75);
    v.addColorStop(0, 'rgba(0,0,0,0)');
    v.addColorStop(1, 'rgba(0,0,0,0.6)');
    c.fillStyle = v;
    c.fillRect(0, 0, W, H);
  }

  // ---------- 字幕 / 顶部信息 / 进度条 ----------
  function updateSubs(t) {
    const S = V.subtitles;
    let idx = -1;
    for (let i = 0; i < S.length; i++) if (t >= S[i].start && t < S[i].end) { idx = i; break; }
    if (idx !== subIdx) {
      subEl.textContent = '';
      if (idx >= 0) {
        rich(subEl, S[idx].text, S[idx].hl);
        const fs = P ? 64 : 54;
        subEl.style.fontSize = fit([S[idx].text], W - 120, fs, 36) + 'px';
      }
      subIdx = idx;
    }
    if (idx >= 0) {
      const p = clamp((t - S[idx].start) / 0.12);
      subEl.style.opacity = p;
      subEl.style.transform = `scale(${0.94 + 0.06 * E.out(p)})`;
    } else subEl.style.opacity = 0;
  }

  function updateHud(t) {
    const sec = V.sections.find(x => t >= x.start && t < x.end) || V.sections[V.sections.length - 1];
    document.querySelector('#hud-title em').textContent = (sec && sec.label) || '';
    V.sections.forEach((x, i) => {
      const p = clamp((t - x.start) / (x.end - x.start));
      segs[i].style.transform = `scaleX(${p})`;
    });
  }

  // ---------- 对外接口 ----------
  window.init = video => {
    V = video;
    W = V.width;
    H = V.height;
    P = H > W;
    stage = document.getElementById('stage');
    stage.className = P ? 'portrait' : 'landscape';
    stage.style.width = W + 'px';
    stage.style.height = H + 'px';
    const [ar, ag, ab] = hexRGB(V.accent);
    const rs = document.documentElement.style;
    rs.setProperty('--accent', V.accent);
    rs.setProperty('--glow', `rgba(${ar},${ag},${ab},.55)`);
    rs.setProperty('--glow2', `rgba(${ar},${ag},${ab},.25)`);
    const cv = document.getElementById('bg');
    cv.width = W;
    cv.height = H;
    bgCtx = cv.getContext('2d');
    const rnd = rng(7);
    stars = Array.from({ length: Math.round((W * H) / 8500) }, () => ({ x: rnd(), y: rnd(), z: 0.25 + rnd() * 0.75, ph: rnd() * 6.28, big: rnd() < 0.05 }));

    document.getElementById('hud-brand').textContent = V.brand || '';
    document.querySelector('#hud-title span').textContent = V.hudTitle || V.title || '';
    if (V.hud === false) document.getElementById('hud').style.display = 'none';
    const pr = document.getElementById('progress');
    segs = V.sections.map(x => {
      const seg = h('div', 'seg', pr);
      seg.style.flex = String(x.end - x.start);
      return h('b', '', seg);
    });
    subEl = document.querySelector('#subs .sub');
    flashEl = document.getElementById('flash');
    built = V.scenes.map(buildScene);
    buildCover();
  };

  window.seek = t => {
    drawBg(t);
    const last = built[built.length - 1];
    let flash = 0;
    for (const b of built) {
      const on = (t >= b.start && t < b.end) || (b === last && t >= b.end);
      b.root.style.display = on ? '' : 'none';
      if (!on) continue;
      const d = b.end - b.start, tl = Math.min(t - b.start, d);
      const pin = E.out(clamp(tl / 0.28));
      const pout = b === last ? 1 : clamp((d - tl) / 0.18);
      b.root.style.opacity = Math.min(pin, pout);
      const blur = (1 - pin) * 10;
      b.root.style.filter = blur > 0.05 ? `blur(${blur}px)` : 'none';
      let sx = 0, sy = 0;
      if (b.sc.impact && tl < 0.45) {
        const k = 1 - tl / 0.45, f = Math.floor(t * 30);
        sx = (hash(f * 3 + 1) - 0.5) * 34 * k;
        sy = (hash(f * 5 + 2) - 0.5) * 34 * k;
        flash = Math.max(flash, 0.5 * clamp(1 - tl / 0.22));
      }
      const sc = (0.965 + 0.035 * pin) * (1 + (1 - pout) * 0.05) * (1 + 0.035 * E.inOut(clamp(tl / d)));
      b.inner.style.transform = `translate(${sx}px,${sy}px) scale(${sc})`;
      for (const r of b.reveals) applyReveal(r, tl, t);
    }
    flashEl.style.opacity = flash;
    updateSubs(t);
    updateHud(t);
  };

  // 封面：大标题 + 重点词发光
  function buildCover() {
    const cv = document.getElementById('cover');
    const C = V.cover || {};
    if (V.brand) h('div', 'kicker', cv, V.brand);
    const lines = String(C.text || V.title || '').split('\n');
    const tt = h('div', 'cover-title', cv);
    tt.style.fontSize = fit(lines, P ? 940 : 1600, P ? 170 : 160, 70) + 'px';
    lines.forEach(ln => rich(h('div', 'hline', tt), ln, C.highlight));
    h('div', 'cover-line', cv);
    if (C.sub) h('div', 'cover-sub', cv, C.sub);
  }
  window.showCover = () => {
    drawBg(3);
    built.forEach(b => (b.root.style.display = 'none'));
    for (const id of ['subs', 'progress', 'hud']) document.getElementById(id).style.display = 'none';
    flashEl.style.opacity = 0;
    document.getElementById('cover').style.display = 'flex';
  };
})();
