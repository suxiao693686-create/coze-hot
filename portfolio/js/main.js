/* =============================================================
 * 周琳 · 作品集  —— 纸上走廊
 * 一条用铅笔画出来的走廊：向下滚动往里走，推开门进入房间。
 * 纯 HTML / CSS / JS，无需构建，直接放到 GitHub Pages。
 * ============================================================= */
(function () {
  'use strict';

  var P = window.PROFILE, WORKS = window.WORKS;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var touch = window.matchMedia('(hover: none)').matches;

  /* ---------- 小工具 ---------- */
  function rng(seed) { // mulberry32：同一个种子每次画出一样的线
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  // 在受限的嵌入页面里改地址栏可能会报错，失败就忽略
  function hist(method, url) { try { history[method](null, '', url); } catch (e) {} }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function f(n) { return Math.round(n * 10) / 10; }

  // 一条带手抖的线：分几段、每段有微小偏移，用二次曲线连起来
  function wobble(x1, y1, x2, y2, r, amp) {
    var len = Math.hypot(x2 - x1, y2 - y1), n = Math.max(2, Math.round(len / 90));
    var nx = -(y2 - y1) / (len || 1), ny = (x2 - x1) / (len || 1);
    var d = 'M' + f(x1 + (r() - .5) * amp) + ' ' + f(y1 + (r() - .5) * amp);
    for (var i = 1; i <= n; i++) {
      var t = i / n, tm = (i - .5) / n, o = (r() - .5) * amp * 1.6;
      var mx = x1 + (x2 - x1) * tm + nx * o, my = y1 + (y2 - y1) * tm + ny * o;
      var ex = x1 + (x2 - x1) * t + (r() - .5) * amp * .5, ey = y1 + (y2 - y1) * t + (r() - .5) * amp * .5;
      d += 'Q' + f(mx) + ' ' + f(my) + ' ' + f(ex) + ' ' + f(ey);
    }
    return d;
  }
  // 铅笔线：同一条线描两遍，略有错位
  function pencil(x1, y1, x2, y2, r, amp) {
    return wobble(x1, y1, x2, y2, r, amp) + wobble(x1, y1, x2, y2, r, amp * 1.4);
  }
  function rectPath(x, y, w, h, r, amp) {
    return pencil(x, y, x + w, y, r, amp) + pencil(x + w, y, x + w, y + h, r, amp) +
      pencil(x + w, y + h, x, y + h, r, amp) + pencil(x, y + h, x, y, r, amp);
  }
  function svg(w, h, body, cls) {
    return '<svg class="' + (cls || '') + '" viewBox="0 0 ' + f(w) + ' ' + f(h) + '" width="' + f(w) + '" height="' + f(h) +
      '" preserveAspectRatio="none" aria-hidden="true">' + body + '</svg>';
  }

  /* ---------- 手绘小图标 ---------- */
  var ICON = {
    plane: '<path d="M4 30 L56 8 L40 52 L30 36 Z M30 36 L56 8 M30 36 L26 48 L34 40"/>',
    star: '<path d="M30 8 V52 M10 20 L50 40 M50 20 L10 40"/>',
    circle: '<path d="M30 10 C44 9 52 20 51 31 C50 44 38 51 28 50 C16 49 9 39 10 28 C11 17 21 10 33 11"/>',
    spiral: '<path d="M30 30 C33 28 35 32 32 35 C27 38 23 32 26 27 C30 21 39 23 41 30 C43 39 35 46 27 44 C17 42 14 30 19 22 C25 13 40 13 46 22"/>',
    cup: '<path d="M14 22 H42 L39 50 H17 Z M42 28 C52 28 52 40 40 40 M20 16 C18 12 22 10 20 6 M28 16 C26 12 30 10 28 6 M36 16 C34 12 38 10 36 6"/>',
    pencil: '<path d="M12 48 L16 36 L44 8 L52 16 L24 44 Z M16 36 L24 44 M40 12 L48 20 M12 48 L18 46"/>',
    bulb: '<path d="M30 8 C18 8 12 18 15 28 C17 34 22 36 22 42 H38 C38 36 43 34 45 28 C48 18 42 8 30 8 Z M23 47 H37 M25 52 H35 M30 42 V30 M26 26 L30 30 L34 26"/>',
    mega: '<path d="M10 26 V36 H18 L42 48 V14 L18 26 Z M18 36 L22 50 H28 L25 38 M48 24 C52 28 52 34 48 38"/>',
    bubble: '<path d="M10 14 H50 V40 H26 L16 50 L18 40 H10 Z M20 24 H40 M20 31 H34"/>',
    cloud: '<path d="M14 40 C6 40 6 28 15 28 C14 18 28 15 31 23 C34 14 48 16 47 27 C56 27 56 40 47 40 Z"/>',
    dots: '<path d="M10 30 h1 M22 26 h1 M34 30 h1 M46 26 h1"/>',
    heart: '<path d="M30 50 C14 38 8 30 10 21 C12 12 24 11 30 21 C36 11 48 12 50 21 C52 30 46 38 30 50 Z"/>'
  };
  function icon(name, cls) {
    return '<svg class="ic ' + (cls || '') + '" viewBox="0 0 60 60" aria-hidden="true">' + ICON[name] + '</svg>';
  }

  /* =============================================================
   * 1. 撕纸：加载 & 房间切换
   * ============================================================= */
  var tearEl = $('#tear');
  function newTear() {
    var pts = [[50, -2]], n = 14;
    for (var i = 1; i < n; i++) pts.push([50 + (Math.random() - .5) * 7, i / n * 100]);
    pts.push([50, 102]);
    var l = '0% 0%,', r = '100% 0%,100% 100%,', line = '';
    pts.forEach(function (p, i) { l += p[0] + '% ' + p[1] + '%,'; line += (i ? 'L' : 'M') + p[0] + ' ' + p[1] + ' '; });
    l += '0% 100%';
    for (var j = pts.length - 1; j >= 0; j--) r += pts[j][0] + '% ' + pts[j][1] + '%' + (j ? ',' : '');
    $('.tear__half--l', tearEl).style.clipPath = 'polygon(' + l + ')';
    $('.tear__half--r', tearEl).style.clipPath = 'polygon(' + r + ')';
    $('.tear__line path', tearEl).setAttribute('d', line);
  }
  var TEAR_MS = reduce ? 10 : 720;
  function tearClose() {
    newTear();
    tearEl.classList.remove('is-open');
    tearEl.classList.add('is-busy');
    return new Promise(function (res) { setTimeout(res, TEAR_MS + 60); });
  }
  function tearOpen() {
    tearEl.classList.add('is-open');
    return new Promise(function (res) { setTimeout(function () { tearEl.classList.remove('is-busy'); res(); }, TEAR_MS); });
  }

  /* =============================================================
   * 2. 走廊
   * ============================================================= */
  var stage = $('#stage'), world = $('#world'), corridor = $('#corridor');
  var D = {}; // 尺寸
  var doors = [], segs = [];

  // 走廊里的东西，d = 离入口的深度（px）
  var LAYOUT = {
    length: 3700,
    doors: [
      { go: 'works', side: 'L', d: 950, zh: '作品', en: 'works', ic: 'bulb' },
      { go: 'about', side: 'R', d: 1850, zh: '关于', en: 'about me', ic: 'plane' },
      { go: 'skills', side: 'L', d: 2750, zh: '能力', en: 'studio', ic: 'pencil' }
    ],
    // 墙上挂的作品框（取前两件作品，没有就是空画框）
    frames: [{ side: 'R', d: 1080 }, { side: 'L', d: 1560 }],
    notes: [
      { side: 'L', d: 520, h: .38, t: 'GPA 2 / 33', s: '专业前 6%' },
      { side: 'R', d: 640, h: .5, t: '广告学', s: '2026 届' },
      { side: 'L', d: 2180, h: .44, t: '8000+', s: '人次 · 露营生活节' },
      { side: 'R', d: 2540, h: .36, t: '大广赛', s: '省赛一等奖' },
      { side: 'R', d: 3080, h: .46, t: '700+', s: 'ToB 客户' }
    ]
  };

  function measure() {
    var vw = innerWidth, vh = innerHeight;
    D.vw = vw; D.vh = vh;
    D.P = Math.round(clamp(vh * .95, 560, 1000));          // 透视距离（≈ 眼睛到屏幕）
    D.W = Math.round(vw < 700 ? Math.max(vw * 1.15, 400) : Math.max(vw, 680)); // 走廊宽（手机上窄一点，侧墙的门才看得见）
    D.H = Math.round(vh);                                      // 走廊高
    D.S = Math.round(D.P * .9);                                // 走廊向镜头外延伸的长度
    D.L = LAYOUT.length;
    D.seg = 640;
    D.doorH = Math.round(D.H * .6);
    D.doorW = Math.round(D.doorH * .46);
    D.camMax = Math.round(D.L - D.P * .3);
    stage.style.perspective = D.P + 'px';
    corridor.style.height = Math.round(vh + D.camMax * .85) + 'px';
  }

  function plane(cls, w, h, tr) {
    var el = document.createElement('div');
    el.className = 'plane ' + cls;
    el.style.width = w + 'px'; el.style.height = h + 'px';
    el.style.transform = 'translate(-50%,-50%) ' + tr;
    world.appendChild(el);
    return el;
  }

  function floorSvg(w, h, r) {
    var d = '', g = '', lanes = 9, lw = w / lanes;
    for (var i = 1; i < lanes; i++) d += wobble(i * lw, 0, i * lw + (r() - .5) * 6, h, r, 2.4);
    for (i = 0; i < lanes; i++) {
      var y = r() * 260;
      while (y < h) {
        d += wobble(i * lw + 2, y, (i + 1) * lw - 2, y + (r() - .5) * 3, r, 1.5);
        y += 260 + r() * 260;
      }
      for (var k = 0; k < 3; k++) { // 木纹
        var gx = i * lw + lw * (.2 + r() * .6), gy = r() * h;
        g += 'M' + f(gx) + ' ' + f(gy) + ' q' + f((r() - .5) * 14) + ' 40 ' + f((r() - .5) * 6) + ' ' + f(80 + r() * 80);
      }
    }
    return svg(w, h, '<path class="ln" d="' + d + '"/><path class="ln ln--faint" d="' + g + '"/>');
  }
  function wallSvg(w, h, r, first) {
    var d = '', faint = '', base = h - 26, rail = h * .56;
    d += pencil(0, base, w, base + (r() - .5) * 2, r, 1.6) + wobble(0, h - 4, w, h - 4, r, 1.2);
    d += pencil(0, rail, w, rail + (r() - .5) * 3, r, 1.8) + wobble(0, rail + 8, w, rail + 8, r, 1.2);
    d += wobble(0, 10, w, 10, r, 1.4);
    for (var x = 80 + r() * 60; x < w - 60; x += 220 + r() * 40) { // 护墙板
      faint += rectPath(x, rail + 34, 150, base - rail - 64, r, 1.4);
    }
    for (var k = 0; k < 4; k++) { // 铅笔排线阴影
      var hx = r() * w, hy = base - 4 - r() * 40;
      for (var j = 0; j < 6; j++) faint += 'M' + f(hx + j * 6) + ' ' + f(hy + 14) + ' l10 -14';
    }
    return svg(w, h, '<path class="ln" d="' + d + '"/><path class="ln ln--faint" d="' + faint + '"/>');
  }
  function ceilSvg(w, h, r) {
    var d = '', lw = w * .26, lh = 70, y = h / 2 - lh / 2;
    d += rectPath(w / 2 - lw / 2, y, lw, lh, r, 1.6);
    d += wobble(w / 2 - lw / 2 + 12, y + 22, w / 2 + lw / 2 - 12, y + 22, r, 1) + wobble(w / 2 - lw / 2 + 12, y + 46, w / 2 + lw / 2 - 12, y + 46, r, 1);
    d += wobble(0, 2, w, 2, r, 1.5);
    return svg(w, h, '<path class="ln ln--faint" d="' + d + '"/>');
  }

  function doorHtml(o, w, h, r) {
    var sign = '<div class="door__sign">' + icon(o.ic) + '<b>' + esc(o.zh) + '</b><i>' + esc(o.en) + '</i></div>';
    var frame = svg(w + 24, h + 14, '<path class="ln ln--bold" d="' + rectPath(2, 2, w + 20, h + 20, r, 2.2) + '"/>', 'door__frame');
    var leaf = svg(w, h,
      '<path class="ln" d="' + rectPath(3, 3, w - 6, h - 6, r, 1.4) +
      rectPath(w * .16, h * .08, w * .68, h * .34, r, 1.4) + rectPath(w * .16, h * .52, w * .68, h * .38, r, 1.4) + '"/>' +
      '<path class="ln ln--faint" d="' + (function () { var s = ''; for (var i = 0; i < 9; i++) s += 'M' + f(w * .2 + i * 8) + ' ' + f(h * .4) + ' l14 -24'; return s; })() + '"/>' +
      '<circle class="knob" cx="' + f(w * .84) + '" cy="' + f(h * .52) + '" r="5"/>');
    return sign + frame + '<div class="door__hole"><span>' + esc(o.zh) + '</span></div><div class="door__leaf">' + leaf + '</div>';
  }

  function buildWorld() {
    world.innerHTML = ''; doors = []; segs = [];
    var W = D.W, H = D.H, S = D.S, L = D.L, seg = D.seg;

    for (var zN = S, i = 0; zN > -L; zN -= seg, i++) {
      var len = Math.min(seg, zN + L), zc = zN - len / 2, r = rng(100 + i);
      var parts = {
        L: plane('wall wall--l', len, H, 'translate3d(' + (-W / 2) + 'px,0,' + zc + 'px) rotateY(90deg)'),
        R: plane('wall wall--r', len, H, 'translate3d(' + (W / 2) + 'px,0,' + zc + 'px) rotateY(-90deg)'),
        F: plane('floor', W, len, 'translate3d(0,' + (H / 2) + 'px,' + zc + 'px) rotateX(90deg)'),
        C: plane('ceil', W, len, 'translate3d(0,' + (-H / 2) + 'px,' + zc + 'px) rotateX(-90deg)')
      };
      parts.L.innerHTML = wallSvg(len, H, r, i === 0);
      parts.R.innerHTML = wallSvg(len, H, r);
      parts.F.innerHTML = floorSvg(W, len, r);
      parts.C.innerHTML = ceilSvg(W, len, r);
      segs.push({ zNear: zN, zFar: zN - len, len: len, parts: parts });
    }

    // 尽头的墙 + 联系我的双开门
    var back = plane('backwall', W, H, 'translate3d(0,0,' + (-L) + 'px)');
    var r2 = rng(7), bw = D.doorW * 1.9, bh = D.doorH * 1.05;
    back.innerHTML = svg(W, H, '<path class="ln" d="' + wobble(0, H - 26, W, H - 26, r2, 1.6) + wobble(0, H * .56, W, H * .56, r2, 1.6) + '"/>') +
      '<div class="door door--back" data-go="contact" role="button" tabindex="0" aria-label="推门：联系我" style="width:' + bw + 'px;height:' + bh + 'px;left:' + (W / 2 - bw / 2) + 'px;top:' + (H - 26 - bh) + 'px">' +
      doorHtml({ zh: '联系', en: 'say hello', ic: 'bubble' }, bw, bh, r2) + '</div>' +
      '<p class="backwall__write">下一站，<br>也许就是你那儿。</p>';
    doors.push({ el: $('.door', back), go: 'contact', zh: '联系', d: L, back: true });

    // 侧墙上的门
    LAYOUT.doors.forEach(function (o, k) {
      var el = document.createElement('div');
      el.className = 'door';
      el.dataset.go = o.go;
      el.setAttribute('role', 'button'); el.tabIndex = 0;
      el.setAttribute('aria-label', '推门：' + o.zh);
      el.style.width = D.doorW + 'px'; el.style.height = D.doorH + 'px';
      el.innerHTML = doorHtml(o, D.doorW, D.doorH, rng(40 + k));
      place(el, o.side, o.d, D.doorW, H - 26 - D.doorH);
      doors.push({ el: el, go: o.go, zh: o.zh, d: o.d });
    });

    // 挂画：有作品就挂作品的黑白线稿（悬停上色），还没有就挂一个"待落笔"的空画框
    var real = WORKS.filter(function (w) { return !w.placeholder; });
    LAYOUT.frames.forEach(function (o, k) {
      var w = real[k];
      var fw = Math.round(D.doorW * 1.15), fh = Math.round(fw * 1.2);
      var el = document.createElement('figure');
      el.className = 'wallframe' + (w ? '' : ' wallframe--empty');
      el.setAttribute('role', 'button'); el.tabIndex = 0;
      el.style.width = fw + 'px'; el.style.height = fh + 'px';
      if (w) {
        el.dataset.work = w.id;
        el.setAttribute('aria-label', '查看作品：' + w.title);
      } else {
        el.dataset.go = 'works';
        el.setAttribute('aria-label', '去作品房间');
      }
      el.innerHTML = (w ? '<img src="' + esc(w.cover) + '" alt="" loading="lazy">' : '<div class="wallframe__blank">' + icon('pencil') + '<span>待落笔</span></div>') +
        svg(fw + 20, fh + 20, '<path class="ln ln--bold" d="' + rectPath(3, 3, fw + 14, fh + 14, rng(70 + k), 2) + '"/>', 'wallframe__line') +
        '<figcaption>' + (w ? 'No.' + esc(w.no) + ' ' + esc(w.title) : 'No.0' + (k + 1) + ' 作品待落笔') + '</figcaption>';
      place(el, o.side, o.d, fw, H * .12);
    });

    // 便利贴
    LAYOUT.notes.forEach(function (o, k) {
      var el = document.createElement('div');
      el.className = 'note note--' + (k % 3);
      el.style.setProperty('--rot', ((k % 2 ? 1 : -1) * (2 + k)) + 'deg');
      el.innerHTML = '<b>' + esc(o.t) + '</b><span>' + esc(o.s) + '</span>';
      place(el, o.side, o.d, 150, H * o.h - 80);
    });
  }

  // 把东西贴到某一侧墙上：side L/R，深度 d，宽度 w，离墙顶 top
  function place(el, side, d, w, top) {
    var z = -d, s = segs.filter(function (s) { return z <= s.zNear && z > s.zFar; })[0] || segs[segs.length - 1];
    var left = side === 'L' ? (s.zNear - z) - w / 2 : (z - s.zFar) - w / 2;
    el.style.left = left + 'px'; el.style.top = top + 'px';
    s.parts[side].appendChild(el);
    s.parts[side].classList.add('has-items');
  }

  /* ---------- 漂浮的涂鸦 ---------- */
  var doodles = [];
  function buildDoodles() {
    var box = $('#doodles'); box.innerHTML = ''; doodles = [];
    var names = ['plane', 'star', 'circle', 'cup', 'spiral', 'bulb', 'mega', 'dots', 'star', 'cloud', 'pencil', 'bubble', 'heart', 'star'];
    var r = rng(11);
    names.forEach(function (n, i) {
      var a = i / names.length * Math.PI * 2 + r() * .4, rad = .32 + r() * .14;
      var x = 50 + Math.cos(a) * rad * 100 * (D.vw > D.vh ? 1 : 1.2), y = 50 + Math.sin(a) * rad * 100 * .95;
      var el = document.createElement('div');
      el.className = 'doodle';
      el.style.left = clamp(x, 4, 92) + '%'; el.style.top = clamp(y, 8, 88) + '%';
      el.style.setProperty('--s', (.7 + r() * .7).toFixed(2));
      el.style.setProperty('--dl', (-r() * 6).toFixed(2) + 's');
      el.innerHTML = icon(n, n === 'star' || n === 'heart' ? 'ic--accent' : '');
      box.appendChild(el);
      doodles.push({ el: el, x: clamp(x, 4, 92), y: clamp(y, 8, 88), depth: .4 + r() * .8 });
    });
  }

  /* ---------- 小地图 ---------- */
  var map, mapDot, prompt;
  function buildMap() {
    map = document.createElement('nav');
    map.className = 'map'; map.setAttribute('aria-label', '走廊地图');
    var marks = [{ zh: '入口', cam: 0 }].concat(LAYOUT.doors.map(function (o) { return { zh: o.zh, cam: o.d - D.P * .55 }; }), [{ zh: '联系', cam: D.camMax }]);
    map.innerHTML = '<span class="map__line"></span><span class="map__dot"></span>' + marks.map(function (m) {
      var p = clamp(m.cam / D.camMax, 0, 1);
      return '<button style="top:' + (p * 100) + '%" data-cam="' + Math.max(0, m.cam) + '"><i></i><span>' + m.zh + '</span></button>';
    }).join('');
    $('#stage').appendChild(map);
    mapDot = $('.map__dot', map);
    $$('button', map).forEach(function (b) {
      b.addEventListener('click', function () { scrollToCam(+b.dataset.cam); });
    });

    prompt = document.createElement('button');
    prompt.className = 'prompt';
    $('#stage').appendChild(prompt);
    prompt.addEventListener('click', function () { if (prompt.dataset.go) enterDoor(prompt.dataset.go); });
  }
  function scrollToCam(cam) {
    var top = corridor.offsetTop + cam / D.camMax * (corridor.offsetHeight - D.vh);
    scrollTo({ top: top, behavior: reduce ? 'auto' : 'smooth' });
  }

  /* ---------- 每一帧 ---------- */
  var cam = 0, camT = 0, mx = 0, my = 0, mxT = 0, myT = 0, hero = $('#hero'), hint = $('#scrollHint');
  function readScroll() {
    var span = corridor.offsetHeight - D.vh;
    var p = span > 0 ? clamp((scrollY - corridor.offsetTop) / span, 0, 1) : 0;
    camT = p * D.camMax;
  }
  function frame() {
    var k = reduce ? 1 : .085;
    cam += (camT - cam) * k; if (Math.abs(camT - cam) < .05) cam = camT;
    mx += (mxT - mx) * .06; my += (myT - my) * .06;

    world.style.transform = 'translateZ(' + D.P + 'px) rotateX(' + f(my * 2.2) + 'deg) rotateY(' + f(mx * 3) + 'deg) translateZ(' + (-D.P) + 'px) translateZ(' + f(cam) + 'px)';

    // 镜头后面的墙段直接隐藏，省渲染
    for (var i = 0; i < segs.length; i++) {
      var hide = segs[i].zFar + cam > D.P * .97;
      if (segs[i].hidden !== hide) {
        segs[i].hidden = hide;
        for (var key in segs[i].parts) segs[i].parts[key].style.visibility = hide ? 'hidden' : '';
      }
    }

    var hp = clamp(cam / 520, 0, 1);
    hero.style.opacity = 1 - hp;
    hero.style.transform = 'translate3d(' + f(-mx * 12) + 'px,' + f(-my * 10 - hp * 40) + 'px,0) scale(' + f(1 + hp * .5) + ')';
    hero.style.visibility = hp >= 1 ? 'hidden' : '';
    hint.style.opacity = clamp(1 - cam / 160, 0, 1);

    for (var j = 0; j < doodles.length; j++) {
      var o = doodles[j], s = 1 + cam * o.depth / 700;
      var dx = (o.x - 50) * (s - 1) * D.vw / 100 + mx * 26 * o.depth, dy = (o.y - 50) * (s - 1) * D.vh / 100 + my * 20 * o.depth;
      o.el.style.transform = 'translate3d(' + f(dx) + 'px,' + f(dy) + 'px,0) scale(' + f(s) + ')';
      o.el.style.opacity = clamp(2.6 - s, 0, 1);
    }

    if (mapDot) mapDot.style.top = (cam / D.camMax * 100) + '%';

    // 离哪扇门最近，就提示推哪扇
    var best = null, bestD = 1e9;
    doors.forEach(function (o) {
      var dist = D.P - (-o.d + cam);
      var ok = o.back ? cam > D.camMax * .8 : dist > D.P * .55 && dist < D.P * 2.1;
      if (ok && (o.back || dist < bestD) && !(best && best.back)) { best = o; bestD = dist; }
    });
    if (prompt) {
      var go = best ? best.go : '';
      if (prompt.dataset.go !== go) {
        prompt.dataset.go = go;
        if (best) prompt.innerHTML = '推开「' + best.zh + '」的门 <span>→</span>';
        prompt.classList.toggle('is-on', !!best);
      }
    }
    raf = requestAnimationFrame(frame);
  }
  var raf;

  /* =============================================================
   * 3. 房间
   * ============================================================= */
  var current = null;
  function enterDoor(go) {
    var d = doors.filter(function (o) { return o.go === go; })[0];
    if (d && !reduce && !current) {
      d.el.classList.add('is-open');
      setTimeout(function () { openRoom(go); }, 380);
      setTimeout(function () { d.el.classList.remove('is-open'); }, 1600);
    } else openRoom(go);
  }
  function openRoom(name, fromHash) {
    var room = $('#room-' + name);
    if (!room || current === name) return Promise.resolve();
    return tearClose().then(function () {
      $$('.room').forEach(function (r) { r.classList.remove('is-active'); });
      room.classList.add('is-active');
      room.scrollTop = 0;
      document.body.classList.add('in-room');
      current = name;
      if (!fromHash) hist('pushState', '#' + name);
      markNav();
      return tearOpen();
    }).then(function () { revealIn(room); room.focus({ preventScroll: true }); });
  }
  function closeRoom(fromHash) {
    if (!current) return Promise.resolve();
    return tearClose().then(function () {
      $$('.room').forEach(function (r) { r.classList.remove('is-active'); });
      document.body.classList.remove('in-room');
      current = null;
      if (!fromHash) hist('pushState', location.pathname + location.search);
      markNav();
      return tearOpen();
    });
  }
  function markNav() {
    $$('.hud__nav button').forEach(function (b) { b.classList.toggle('is-on', b.dataset.go === current); });
  }

  // 入场：滚进视野的元素逐个"画"出来
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
    });
  }, { threshold: .12 }) : null;
  function revealIn(root) {
    $$('.rv:not(.is-in)', root).forEach(function (el, i) {
      el.style.transitionDelay = Math.min(i, 8) * 60 + 'ms';
      if (io && !reduce) io.observe(el); else el.classList.add('is-in');
    });
  }

  /* ---------- 作品 ---------- */
  function buildGallery() {
    var cats = ['全部'];
    WORKS.forEach(function (w) { if (!w.placeholder && w.category && cats.indexOf(w.category) < 0) cats.push(w.category); });
    $('#filters').hidden = cats.length < 3; // 只有一类作品时不需要筛选
    $('#filters').innerHTML = cats.map(function (c, i) {
      return '<button role="tab" aria-selected="' + (i === 0) + '" data-cat="' + esc(c) + '">' + esc(c) + '</button>';
    }).join('');

    $('#gallery').innerHTML = WORKS.map(function (w, i) {
      var tilt = ((i * 37) % 5 - 2) * .55;
      if (w.placeholder) {
        return '<article class="card card--empty rv" data-cat="' + esc(w.category) + '" style="--tilt:' + tilt + 'deg">' +
          '<div class="card__frame"><div class="card__blank">' + icon('pencil') + '<p>待落笔</p><small>new work coming soon</small></div></div>' +
          '<div class="card__meta"><span class="card__no">No.' + esc(w.no) + '</span><h3>' + esc(w.title) + '</h3><p>' + (w.category ? esc(w.category) + ' · ' : '') + '敬请期待</p></div></article>';
      }
      return '<article class="card rv" data-cat="' + esc(w.category) + '" data-work="' + esc(w.id) + '" tabindex="0" role="button" aria-label="查看作品：' + esc(w.title) + '" style="--tilt:' + tilt + 'deg">' +
        '<div class="card__frame"><span class="tape tape--a"></span><span class="tape tape--b"></span>' +
        '<img class="card__img card__img--sketch" src="' + esc(w.cover) + '" alt="" loading="lazy">' +
        '<img class="card__img card__img--color" src="' + esc(w.cover) + '" alt="' + esc(w.title) + '" loading="lazy">' +
        '<span class="card__cta">打开看看 →</span></div>' +
        '<div class="card__meta"><span class="card__no">No.' + esc(w.no) + ' · ' + esc(w.category) + ' · ' + esc(w.year) + '</span>' +
        '<h3>' + esc(w.title) + '</h3><p>' + esc(w.subtitle) + '</p>' +
        '<ul class="tags">' + (w.tags || []).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul></div></article>';
    }).join('');

    $('#filters').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      $$('#filters button').forEach(function (x) { x.setAttribute('aria-selected', x === b); });
      $$('#gallery .card').forEach(function (c) {
        c.classList.toggle('is-hidden', b.dataset.cat !== '全部' && c.dataset.cat !== b.dataset.cat);
      });
    });

    // 鼠标进入的位置作为"上色"的圆心
    $$('#gallery .card[data-work]').forEach(function (c) {
      var fr = $('.card__frame', c);
      c.addEventListener('pointerenter', function (e) {
        var b = fr.getBoundingClientRect();
        fr.style.setProperty('--cx', ((e.clientX - b.left) / b.width * 100) + '%');
        fr.style.setProperty('--cy', ((e.clientY - b.top) / b.height * 100) + '%');
      });
    });
    // 手机上没有悬停：滑到屏幕中间时自动上色
    if (touch && io) {
      var cio = new IntersectionObserver(function (es) {
        es.forEach(function (e) { e.target.classList.toggle('is-color', e.isIntersecting); });
      }, { rootMargin: '-35% 0px -35% 0px' });
      $$('#gallery .card[data-work]').forEach(function (c) { cio.observe(c); });
    }
  }

  /* ---------- 作品详情 ---------- */
  var sheet = $('#sheet'), sheetPaper = $('#sheetPaper'), lastFocus;
  function openWork(id, fromHash) {
    var real = WORKS.filter(function (w) { return !w.placeholder; });
    var idx = -1;
    real.forEach(function (w, i) { if (w.id === id) idx = i; });
    if (idx < 0) return;
    var w = real[idx], prev = real[(idx - 1 + real.length) % real.length], next = real[(idx + 1) % real.length];
    lastFocus = document.activeElement;

    sheetPaper.innerHTML =
      '<button class="sheet__x" data-sheet-close aria-label="关闭">×</button>' +
      '<header class="sheet__head">' +
      '<span class="card__no">No.' + esc(w.no) + ' · ' + esc(w.category) + '</span>' +
      '<h2>' + esc(w.title) + '</h2><p class="sheet__sub">' + esc(w.subtitle) + '</p>' +
      '<dl class="sheet__meta"><div><dt>年份</dt><dd>' + esc(w.year) + '</dd></div><div><dt>我的角色</dt><dd>' + esc(w.role) + '</dd></div>' +
      '<div><dt>关键词</dt><dd>' + esc((w.tags || []).join(' / ')) + '</dd></div></dl></header>' +
      '<p class="sheet__summary">' + esc(w.summary) + '</p>' +
      (w.images && w.images.length ? '<div class="sheet__imgs">' + w.images.map(function (src) {
        return '<figure><img src="' + esc(src) + '" alt="' + esc(w.title) + ' 作品图" loading="lazy"></figure>';
      }).join('') + '</div>' : '') +
      (w.case ? '<ol class="case">' + w.case.map(function (c, i) {
        return '<li><span class="case__k"><i>0' + (i + 1) + '</i>' + esc(c.k) + '</span><p>' + esc(c.v) + '</p></li>';
      }).join('') + '</ol>' : '') +
      '<footer class="sheet__foot">' +
      (w.link ? '<a class="btn" href="' + esc(w.link) + '" target="_blank" rel="noopener">在线体验 →</a>' : '') +
      (w.qr ? '<figure class="sheet__qr"><img src="' + esc(w.qr) + '" alt="' + esc(w.title) + ' 二维码"><figcaption>手机扫码体验</figcaption></figure>' : '') +
      '</footer>' +
      (real.length > 1 ? '<nav class="sheet__nav"><button data-work="' + esc(prev.id) + '">← ' + esc(prev.title) + '</button><button data-work="' + esc(next.id) + '">' + esc(next.title) + ' →</button></nav>' : '');

    sheet.setAttribute('aria-hidden', 'false');
    sheet.classList.add('is-open');
    document.body.classList.add('in-sheet');
    sheetPaper.scrollTop = 0;
    if (!fromHash) hist('replaceState', '#work/' + w.id);
    setTimeout(function () { $('.sheet__x', sheetPaper).focus({ preventScroll: true }); }, 50);
  }
  function closeWork() {
    if (!sheet.classList.contains('is-open')) return;
    sheet.classList.remove('is-open');
    sheet.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('in-sheet');
    hist('replaceState', current ? '#' + current : location.pathname + location.search);
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  /* ---------- 关于 ---------- */
  function buildAbout() {
    var e = P.education;
    $('#about').innerHTML =
      '<div class="about__side">' +
      '<figure class="polaroid rv">' + (P.photo ? '<img src="' + esc(P.photo) + '" alt="' + esc(P.name) + '">' :
        '<div class="polaroid__blank"><span>' + esc(P.name.slice(-1)) + '</span></div>') +
      '<figcaption>' + esc(P.name) + ' · ' + esc(P.nameEn) + '</figcaption></figure>' +
      '<p class="about__intro rv">' + esc(P.intro) + '</p>' +
      '<div class="edu rv"><h3>' + icon('pencil') + '教育</h3><p class="edu__school">' + esc(e.school) + '</p>' +
      '<p>' + esc(e.major) + '</p><p class="mono">' + esc(e.time) + '</p><p class="hl">' + esc(e.rank) + '</p>' +
      '<p class="edu__courses">' + esc(e.courses) + '</p></div>' +
      '</div>' +
      '<div class="about__main">' +
      '<div class="traits">' + P.traits.map(function (t, i) {
        return '<div class="trait rv"><b>' + esc(t.k) + '</b><p>' + esc(t.v) + '</p></div>';
      }).join('') + '</div>' +
      '<h3 class="sub">' + icon('plane') + '一路飞过来的地方</h3>' +
      '<ol class="timeline">' + P.timeline.map(function (t) {
        return '<li class="rv"><span class="timeline__time mono">' + esc(t.time) + '</span>' +
          '<h4>' + esc(t.org) + '<small>' + esc(t.title) + '</small></h4>' +
          '<ul>' + t.points.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul></li>';
      }).join('') + '</ol></div>';
  }

  /* ---------- 能力 ---------- */
  function buildStudio() {
    $('#studio').innerHTML =
      '<div class="stickies">' + P.skills.map(function (g, i) {
        return '<div class="sticky sticky--' + i + ' rv" style="--rot:' + [-2, 1.5, -1, 2.2][i % 4] + 'deg"><span class="tape tape--a"></span>' +
          '<h3>' + esc(g.group) + '</h3><ul>' + g.items.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul></div>';
      }).join('') + '</div>' +
      '<h3 class="sub">' + icon('star', 'ic--accent') + '奖状墙</h3>' +
      '<ul class="awards">' + P.awards.map(function (a) {
        var lv = a.level === '国家级' ? 'n' : a.level === '省级' ? 'p' : 's';
        return '<li class="rv"><span class="stamp stamp--' + lv + '">' + esc(a.level) + '</span><b>' + esc(a.name) + '</b><em>' + esc(a.prize) + '</em></li>';
      }).join('') + '</ul>' +
      '<h3 class="sub">' + icon('circle') + '证书</h3>' +
      '<ul class="tags tags--lg rv">' + P.certs.map(function (c) { return '<li>' + esc(c) + '</li>'; }).join('') + '</ul>';
  }

  /* ---------- 联系 ---------- */
  function buildLetter() {
    $('#letter').innerHTML =
      '<div class="letter__paper rv">' +
      '<span class="postmark"><b>杭州</b><i>HANGZHOU</i><i>2026</i></span>' +
      '<p class="letter__to">致 未来的同事：</p>' +
      '<p>谢谢你走完这条走廊。</p>' +
      '<p>我想找一份<strong>' + esc(P.role.replace(/ · /g, ' / ')) + '</strong>的工作，' + esc(P.city) + '。' +
      '如果你手上正好有一个需要洞察、文案和一点点手作感的项目，我很想听听。</p>' +
      '<ul class="contact">' +
      '<li><span>邮箱</span><a href="mailto:' + esc(P.email) + '">' + esc(P.email) + '</a><button data-copy="' + esc(P.email) + '">复制</button></li>' +
      '<li><span>电话</span><a href="tel:' + esc(P.phone.replace(/\s/g, '')) + '">' + esc(P.phone) + '</a><button data-copy="' + esc(P.phone.replace(/\s/g, '')) + '">复制</button></li>' +
      '<li><span>城市</span><em>' + esc(P.city) + '</em></li>' +
      '</ul>' +
      '<p class="letter__sign">' + esc(P.name) + '<small>' + esc(P.nameEn.toLowerCase()) + '</small></p>' +
      '</div>' +
      '<p class="credit">这个网站由周琳设计制作 · 走廊灵感来自 ITom 的纸上作品集</p>';
  }

  var toastT;
  function toast(msg) {
    var t = $('#toast'); t.textContent = msg; t.classList.add('is-on');
    clearTimeout(toastT); toastT = setTimeout(function () { t.classList.remove('is-on'); }, 1800);
  }
  function copy(text) {
    var done = function () { toast('已复制：' + text); };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { toast(text); }
      ta.remove();
    }
  }

  /* ---------- 打字机副标题 ---------- */
  function typeRole() {
    var el = $('#roleText'), words = P.role.split(' · '), wi = 0, ci = 0, del = false;
    if (reduce) { el.textContent = P.role; return; }
    (function tick() {
      var w = words[wi];
      ci += del ? -1 : 1;
      el.textContent = w.slice(0, ci);
      var wait = del ? 60 : 140;
      if (!del && ci === w.length) { del = true; wait = 1800; }
      else if (del && ci === 0) { del = false; wi = (wi + 1) % words.length; wait = 300; }
      setTimeout(tick, wait);
    })();
  }

  /* =============================================================
   * 4. 事件 & 路由
   * ============================================================= */
  document.addEventListener('click', function (e) {
    var t = e.target;
    var go = t.closest('[data-go]');
    if (go) {
      e.preventDefault();
      var g = go.dataset.go;
      if (g === 'home') { closeWork(); closeRoom().then(function () { scrollToCam(0); }); return; }
      if (go.classList.contains('door')) enterDoor(g);
      else if (current) openRoom(g); else enterDoor(g);
      return;
    }
    var w = t.closest('[data-work]');
    if (w) { openWork(w.dataset.work); return; }
    if (t.closest('[data-close]')) { closeRoom(); return; }
    if (t.closest('[data-sheet-close]')) { closeWork(); return; }
    var c = t.closest('[data-copy]');
    if (c) copy(c.dataset.copy);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (sheet.classList.contains('is-open')) closeWork(); else closeRoom(); }
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[role=button][data-go], [role=button][data-work]')) {
      e.preventDefault(); e.target.click();
    }
  });
  addEventListener('pointermove', function (e) {
    if (touch) return;
    mxT = e.clientX / innerWidth * 2 - 1; myT = e.clientY / innerHeight * 2 - 1;
  }, { passive: true });
  addEventListener('scroll', readScroll, { passive: true });
  var rT;
  addEventListener('resize', function () {
    clearTimeout(rT);
    rT = setTimeout(function () { measure(); buildWorld(); buildDoodles(); if (map) map.remove(); if (prompt) prompt.remove(); buildMap(); readScroll(); }, 150);
  });

  function route() {
    var h = location.hash.replace('#', '');
    if (h.indexOf('work/') === 0) {
      var id = h.slice(5);
      (current === 'works' ? Promise.resolve() : openRoom('works', true)).then(function () { openWork(id, true); });
    } else if (h && $('#room-' + h)) { closeWork(); openRoom(h, true); }
    else { closeWork(); closeRoom(true); }
  }
  addEventListener('popstate', route);

  /* =============================================================
   * 5. 启动：撕开纸
   * ============================================================= */
  function boot() {
    newTear();
    measure(); buildWorld(); buildDoodles(); buildMap();
    buildGallery(); buildAbout(); buildStudio(); buildLetter();
    typeRole(); readScroll();
    raf = requestAnimationFrame(frame);

    // 等字体和封面图加载，计数到 100% 再撕开
    var assets = WORKS.filter(function (w) { return w.cover; }).map(function (w) {
      return new Promise(function (res) { var i = new Image(); i.onload = i.onerror = res; i.src = w.cover; });
    });
    if (document.fonts && document.fonts.load) assets.push(document.fonts.load('40px CabinSketch').catch(function () {}));
    if (!assets.length) assets.push(Promise.resolve());
    var total = assets.length, loaded = 0, shown = 0, t0 = performance.now(), countEl = $('.tear__count');
    assets.forEach(function (p) { p.then(function () { loaded++; }); });
    var minMs = reduce ? 0 : 1300;
    (function count() {
      var target = Math.min(loaded / total, (performance.now() - t0) / minMs || 1) * 100;
      shown += (target - shown) * .12 + .3;
      shown = Math.min(shown, target, 100);
      countEl.textContent = Math.floor(shown);
      if (shown >= 99.6 || performance.now() - t0 > 3500) {
        countEl.textContent = '100';
        setTimeout(function () {
          document.body.classList.remove('is-loading');
          var h = location.hash.replace('#', '');
          // 带锚点打开（如 #works、#work/作品id）就直接进房间，纸撕开时已经在房间里
          if (h.indexOf('work/') === 0 || (h && $('#room-' + h))) route();
          else tearOpen();
        }, 260);
        return;
      }
      requestAnimationFrame(count);
    })();
  }
  boot();
})();
