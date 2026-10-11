(function () {
  'use strict';

  var A = window.ASSETS, CFG = window.CONFIG || {};
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var app = $('#app');

  // ---------- 坐标工具（全部用设计稿原图像素） ----------
  function dims(n) { return A.bg[n]; }
  function pos(n, x, y, w, h) {
    var d = dims(n), s = 'left:' + (x / d.w * 100) + '%;top:' + (y / d.h * 100) + '%;width:' + (w / d.w * 100) + '%;';
    if (h != null) s += 'height:' + (h / d.h * 100) + '%;';
    return s;
  }
  function sp(name, wrap, img, delay, imgDelay) {
    var m = A.sprites[name];
    return '<div class="sp ' + (wrap || '') + '" data-sp="' + name + '" style="' + pos(m.bg, m.x, m.y, m.w) +
      (delay != null ? 'animation-delay:' + delay + 's;' : '') + '">' +
      '<img class="' + (img || '') + '" src="assets/' + name + '.png" alt=""' +
      (imgDelay != null ? ' style="animation-delay:' + imgDelay + 's"' : '') + '></div>';
  }
  function hot(n, x, y, w, h, act) {
    return '<div class="hot" data-act="' + act + '" style="' + pos(n, x, y, w, h) + '"></div>';
  }
  function hotOn(name, act, pad) {
    var m = A.sprites[name]; pad = pad || 0;
    return hot(m.bg, m.x - pad, m.y - pad, m.w + pad * 2, m.h + pad * 2, act);
  }
  function wipe(n, x, y, w, h, t, d, paper) {
    return '<div class="wipe" style="' + pos(n, x, y, w, h) + '--t:' + t + 's;--d:' + (d || .8) + 's;--paper:' + (paper || dims(n).paper) + '"></div>';
  }
  // 漫画分格：points 为原图坐标 [[x,y],...]
  function panel(n, pts, cls, delay) {
    var d = dims(n);
    var poly = pts.map(function (p) { return (p[0] / d.w * 100) + '% ' + (p[1] / d.h * 100) + '%'; }).join(',');
    return '<div class="panel in ' + cls + '" style="-webkit-clip-path:polygon(' + poly + ');clip-path:polygon(' + poly + ');animation-delay:' + delay + 's">' +
      '<img src="assets/bg' + n + '.jpg" alt=""></div>';
  }
  function spark(n, x, y, delay, size) {
    return '<i class="spark" style="' + pos(n, x, y) + 'animation-delay:' + delay + 's;' + (size ? 'font-size:' + size + 'em' : '') + '"></i>';
  }

  // ---------- 场景定义 ----------
  var S = {
    cover: {
      bg: 1, petals: true,
      html: function () {
        return '<div class="inner zoom"><img class="bg" src="assets/bg1.jpg" alt="">' +
          sp('cover_title', 'in a-ink', '', .3) +
          sp('cover_seal', 'in a-stamp', '', 1.6) +
          sp('cover_start', 'in a-pop', 'pulse', 2.1) +
          '</div>' + hotOn('cover_start', 'start', 40);
      },
      enter: function () { later(1600, sfx.stamp); }
    },
    load: {
      bg: 2,
      html: function () {
        return '<div class="inner"><img class="bg" src="assets/bg2.jpg" alt="">' +
          sp('load_head', 'in a-pop', 'bob', .1) +
          '<div class="bar" style="' + pos(2, 392, 1104, 316, 62) + '"><i></i></div>' +
          '<div class="bar-bottle" style="' + pos(2, 360, 975, 82) + '"><img src="assets/rule_bottle.png" alt=""></div>' +
          '<div class="pct" style="top:' + (1215 / 2000 * 100) + '%">0%</div></div>';
      }
    },
    story1: {
      bg: 3, tap: true, ready: 3900,
      html: function () {
        return '<div class="inner">' +
          panel(3, [[0, 0], [1414, 0], [1414, 563], [0, 563]], 'a-down', .2) +
          panel(3, [[0, 563], [1414, 563], [1414, 1065], [0, 722]], 'a-right', 1.1) +
          panel(3, [[0, 722], [1414, 1065], [1414, 1228], [0, 1566]], 'a-left', 2.0) +
          panel(3, [[0, 1566], [1414, 1228], [1414, 2000], [0, 2000]], 'a-up', 2.9) +
          '</div>';
      },
      enter: function () {
        [200, 1100, 2000, 2900].forEach(function (t, i) { later(t, function () { sfx.pluck(i); }); });
      }
    },
    story2: {
      bg: 4, tap: true, ready: 3300,
      html: function () {
        return '<div class="inner">' +
          '<div class="shk">' + panel(4, [[0, 0], [1414, 0], [1414, 1018], [0, 1018]], 'a-fade', .2) + '</div>' +
          panel(4, [[0, 1018], [1414, 1018], [1414, 2000], [0, 2000]], 'a-up', 2.3) +
          '</div>';
      },
      enter: function () { later(1300, sfx.gasp); later(2300, function () { sfx.pluck(1); }); }
    },
    rule: {
      bg: 5,
      html: function () {
        var p = '#fefefa', lines = [[825, 900], [906, 986], [986, 1066], [1068, 1150], [1182, 1268]];
        return '<div class="inner"><img class="bg" src="assets/bg5.jpg" alt="">' +
          sp('rule_bottle', 'in a-drop', 'sway', .1) +
          wipe(5, 302, 362, 535, 170, .3, .9, '#fefdf9') +
          lines.map(function (l, i) { return wipe(5, 236, l[0], 648, l[1] - l[0], .9 + i * .6, .65, p); }).join('') +
          sp('rule_btn', 'in a-stamp', 'pulse', 3.9) +
          '</div>' + hotOn('rule_btn', 'rule', 30);
      },
      enter: function () { later(3900, sfx.stamp); }
    },
    pick: {
      bg: 6, cls: 'pick',
      html: function () {
        return '<div class="inner"><img class="bg" src="assets/bg6.jpg" alt="">' +
          '<div class="ask in a-fade" style="top:' + (1312 / 2000 * 100) + '%;animation-delay:.6s">请为贵妃择一焕颜之物</div>' +
          sp('pick_lead', 'in a-up', 'glow', .3, 0) +
          sp('pick_toner', 'in a-up', 'glow', .45, .3) +
          sp('pick_hbn', 'in a-up', 'glow', .6, .6) +
          '</div>' +
          hot(6, 200, 1420, 280, 320, 'pick:lead') +
          hot(6, 520, 1350, 180, 390, 'pick:toner') +
          hot(6, 750, 1380, 180, 360, 'pick:hbn');
      }
    },
    fail1: { bg: 7, html: function () { return failHtml(7, 'fail1'); }, enter: function () { later(300, sfx.bad); } },
    fail2: { bg: 8, html: function () { return failHtml(8, 'fail2'); }, enter: function () { later(300, sfx.bad); } },
    reveal: {
      bg: 9, tap: true, ready: 3000,
      html: function () {
        return '<div class="inner">' +
          panel(9, [[0, 0], [1124, 0], [1124, 705], [0, 705]], 'a-left', .2) +
          panel(9, [[0, 705], [1124, 705], [1124, 1190], [0, 1190]], 'a-burst', 1.2) +
          panel(9, [[0, 1190], [1124, 1190], [1124, 2000], [0, 2000]], 'a-up', 2.2) +
          spark(9, 560, 250, 1.4, 3) + spark(9, 360, 420, 1.9) + spark(9, 160, 880, 1.6, 2.4) +
          spark(9, 990, 860, 2.0, 2.4) + spark(9, 1000, 1290, 2.6) + spark(9, 120, 1300, 2.9) +
          '</div>';
      },
      enter: function () { later(200, function () { sfx.pluck(2); }); later(1200, sfx.good); }
    },
    win: {
      bg: 10, petals: true, tap: true, swipe: true, ready: 1800, noTip: true,
      html: function () {
        var b = A.sprites.win_bottle;
        return '<div class="inner"><img class="bg" src="assets/bg10.jpg" alt="">' +
          sp('win_title', 'in a-pop', '', .2) +
          sp('win_head', 'in a-pop', 'bob', .5) +
          sp('win_hand', 'in a-fade', 'wave', .9) +
          '<div class="sp in a-left" style="' + pos(10, b.x, b.y, b.w) + 'animation-delay:1.2s">' +
          '<div class="shine" style="position:relative;-webkit-mask-image:url(assets/win_bottle.png);mask-image:url(assets/win_bottle.png);-webkit-mask-size:100% 100%;mask-size:100% 100%">' +
          '<img src="assets/win_bottle.png" alt="" style="width:100%"></div></div>' +
          wipe(10, 312, 1428, 712, 116, 1.4, 1.1) +
          sp('win_arrow', 'in a-fade', 'upbeat', 2) +
          spark(10, 300, 560, .9) + spark(10, 880, 640, 1.3) + spark(10, 820, 1120, 1.7, 2.2) +
          '</div>';
      },
      enter: function () { later(200, sfx.good); }
    },
    end: {
      bg: 11, petals: true,
      html: function () {
        return '<div class="inner"><img class="bg" src="assets/bg11.jpg" alt="">' +
          wipe(11, 92, 132, 300, 175, .2, .5, '#f6f1ee') +
          wipe(11, 380, 132, 450, 175, .55, .7, '#f6f1ee') +
          wipe(11, 250, 300, 600, 150, 1.1, .9, '#f6f1ee') +
          sp('end_girl', 'in a-up', 'sway', .3) +
          spark(11, 190, 900, 1.2, 2.4) + spark(11, 340, 1080, 1.8) + spark(11, 880, 860, 2.2) +
          sp('end_retry', 'in a-stamp', 'pulse', 1.9, 0) +
          sp('end_buy', 'in a-stamp', 'pulse', 2.2, .8) +
          '</div>' + hotOn('end_retry', 'retry', 30) + hotOn('end_buy', 'buy', 30);
      },
      enter: function () { later(1900, sfx.stamp); later(2200, sfx.stamp); }
    }
  };

  function failHtml(n, k) {
    var lines = [[1376, 1460], [1460, 1544], [1544, 1630]];
    return '<div class="inner"><img class="bg" src="assets/bg' + n + '.jpg" alt="">' +
      sp(k + '_crow', 'in a-left', 'hop', .2) +
      sp(k + '_head', 'in a-pop', 'sob', .3) +
      '<i class="tear" style="' + pos(n, 400, 1185) + 'font-size:2.2em;animation-delay:.9s"></i>' +
      '<i class="tear" style="' + pos(n, 626, 1185) + 'font-size:2.2em;animation-delay:1.5s"></i>' +
      lines.map(function (l, i) { return wipe(n, 172, l[0], 810, l[1] - l[0], 1 + i * .6, .7, '#fcf7f3'); }).join('') +
      sp(k + '_btn', 'in a-stamp', 'pulse', 2.9) +
      '</div>' + hotOn(k + '_btn', 'retry', 30);
  }

  // ---------- 构建 DOM ----------
  Object.keys(S).forEach(function (id) {
    var s = S[id], el = document.createElement('section');
    el.className = 'screen ' + (s.cls || '');
    el.dataset.id = id;
    el.innerHTML = '<div class="stage">' + s.html() + '</div>';
    app.appendChild(el);
    s.el = el; s.stage = el.firstChild; s.d = dims(s.bg);
  });

  function layout() {
    var vw = window.innerWidth, vh = window.innerHeight;
    Object.keys(S).forEach(function (id) {
      var s = S[id], k = Math.min(vw / s.d.w, vh / s.d.h), w = s.d.w * k;
      s.stage.style.setProperty('--sw', w + 'px');
      s.stage.style.setProperty('--sh', s.d.h * k + 'px');
      s.stage.style.setProperty('--u', w / 100 + 'px');
    });
    petals.resize();
  }

  // ---------- 计时器（离开场景时清掉） ----------
  var timers = [];
  function later(ms, fn) { timers.push(setTimeout(fn, ms)); }
  function clearTimers() { timers.forEach(clearTimeout); timers = []; }

  // ---------- 场景切换 ----------
  var cur = null, busy = false, readyAt = 0;
  var tip = $('#tip');

  function go(id, o) {
    o = o || {};
    if (busy || id === cur) return;
    busy = true;
    var from = cur && S[cur], to = S[id];
    clearTimers();
    tip.classList.remove('show');
    var el = to.el;
    el.classList.remove('on', 'ff', 'chosen');
    [].forEach.call(el.querySelectorAll('.sel'), function (n) { n.classList.remove('sel'); });
    void el.offsetWidth; // 重置动画
    el.classList.add('show', 'on');
    el.style.zIndex = 2;
    if (from) from.el.style.zIndex = 1;
    document.body.style.backgroundColor = to.d.paper;
    document.documentElement.style.backgroundColor = to.d.paper;
    petals.set(!!to.petals);
    cur = id;
    readyAt = Infinity;
    if (to.enter) to.enter();
    if (to.tap) later(to.ready || 0, function () { readyAt = 0; if (!to.noTip) tip.classList.add('show'); });

    var dur = 0, outAnim = null;
    if (from && el.animate) {
      if (o.ink && supportsClip) {
        var x = o.x != null ? o.x : innerWidth / 2, y = o.y != null ? o.y : innerHeight / 2;
        var R = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + 20;
        var c0 = 'circle(0px at ' + x + 'px ' + y + 'px)', c1 = 'circle(' + R + 'px at ' + x + 'px ' + y + 'px)';
        dur = 950;
        el.animate([{ clipPath: c0, webkitClipPath: c0, opacity: .4 }, { clipPath: c1, webkitClipPath: c1, opacity: 1 }],
          { duration: dur, easing: 'cubic-bezier(.65,0,.35,1)' });
        outAnim = from.el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: dur, easing: 'ease-in', fill: 'forwards' });
      } else {
        dur = 750;
        el.animate([{ opacity: 0, transform: 'scale(1.035)' }, { opacity: 1, transform: 'none' }],
          { duration: dur, easing: 'cubic-bezier(.2,.8,.2,1)' });
        outAnim = from.el.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'scale(.985)' }],
          { duration: dur * .8, easing: 'ease', fill: 'forwards' });
      }
    }
    setTimeout(function () {
      if (from) {
        from.el.classList.remove('show', 'on', 'ff', 'chosen');
        from.el.style.zIndex = '';
        if (outAnim) outAnim.cancel();
      }
      el.style.zIndex = '';
      busy = false;
    }, dur);
  }
  var supportsClip = window.CSS && CSS.supports &&
    (CSS.supports('clip-path', 'circle(1px at 1px 1px)') || CSS.supports('-webkit-clip-path', 'circle(1px at 1px 1px)'));

  // ---------- 交互 ----------
  function point(e) {
    var t = e.changedTouches ? e.changedTouches[0] : e;
    return { x: t.clientX, y: t.clientY };
  }
  app.addEventListener('click', function (e) {
    unlockAudio();
    if (busy) return;
    var p = point(e), h = e.target.closest('.hot'), s = S[cur];
    if (h) {
      act(h.dataset.act, p);
    } else if (s && s.tap) {
      if (Date.now() < readyAt || readyAt === Infinity) { // 动画未播完：先快进
        s.el.classList.add('ff');
        clearTimers();
        readyAt = Date.now() + 350;
        later(350, function () { if (!s.noTip) tip.classList.add('show'); });
        return;
      }
      sfx.tap();
      next(cur, p);
    }
  });

  var touchY = null;
  app.addEventListener('touchstart', function (e) { touchY = e.touches[0].clientY; }, { passive: true });
  app.addEventListener('touchend', function (e) {
    if (touchY == null) return;
    var dy = e.changedTouches[0].clientY - touchY;
    touchY = null;
    if (dy < -50 && S[cur] && S[cur].swipe && !busy && readyAt !== Infinity) { sfx.tap(); next(cur); }
  }, { passive: true });

  function next(id, p) {
    var order = { story1: 'story2', story2: 'rule', reveal: 'win', win: 'end' };
    if (order[id]) go(order[id], p ? { ink: id === 'reveal', x: p.x, y: p.y } : {});
  }

  function act(a, p) {
    if (a === 'start') { sfx.stamp(); playBgm(); go('load', { ink: true, x: p.x, y: p.y }); startLoading(); return; }
    if (a === 'rule') { sfx.stamp(); go('pick', { ink: true, x: p.x, y: p.y }); return; }
    if (a === 'retry') { sfx.stamp(); go('pick', { ink: true, x: p.x, y: p.y }); return; }
    if (a === 'buy') { sfx.stamp(); buy(); return; }
    if (a.indexOf('pick:') === 0) {
      var k = a.slice(5), s = S.pick;
      if (s.el.classList.contains('chosen')) return;
      sfx.tap();
      s.el.classList.add('chosen');
      s.el.querySelector('[data-sp="pick_' + k + '"]').classList.add('sel');
      busy = true;
      setTimeout(function () {
        busy = false;
        go({ lead: 'fail1', toner: 'fail2', hbn: 'reveal' }[k], { ink: true, x: p.x, y: p.y });
      }, 750);
    }
  }

  function buy() {
    var url = CFG.buyUrl;
    if (/MicroMessenger/i.test(navigator.userAgent) && /taobao|tmall|tb\.cn/i.test(url)) {
      $('#wxGuide').hidden = false; // 微信内无法直接打开淘宝/天猫链接
      return;
    }
    setTimeout(function () { location.href = url; }, 250);
  }
  $('#wxClose').addEventListener('click', function () { $('#wxGuide').hidden = true; });

  // ---------- 预加载 ----------
  function loadImg(src) {
    return new Promise(function (res) {
      var i = new Image();
      i.onload = i.onerror = function () { (i.decode ? i.decode().catch(function () {}) : Promise.resolve()).then(res); };
      i.src = src;
    });
  }
  function allAssets() {
    var list = [];
    for (var n = 1; n <= 11; n++) list.push('assets/bg' + n + '.jpg');
    Object.keys(A.sprites).forEach(function (k) { list.push('assets/' + k + '.png'); });
    return list;
  }
  var loadPromise = null, loaded = 0;
  function preloadAll() {
    if (loadPromise) return loadPromise;
    var list = allAssets();
    loadPromise = Promise.all(list.map(function (s) { return loadImg(s).then(function () { loaded++; }); }));
    return loadPromise;
  }
  function startLoading() {
    var list = allAssets(), t0 = Date.now(), shown = 0, MIN = 2600;
    var bar = $('.bar i', S.load.el), bottle = $('.bar-bottle', S.load.el), pct = $('.pct', S.load.el);
    var b0 = 392 - 41, bw = 316;
    preloadAll();
    (function tick() {
      var real = loaded / list.length, timeP = Math.min(1, (Date.now() - t0) / MIN);
      var target = Math.min(real, timeP);
      shown += (target - shown) * .18;
      if (target >= 1 && shown > .995) shown = 1;
      bar.style.width = shown * 100 + '%';
      bottle.style.left = ((b0 + bw * shown) / 1124 * 100) + '%';
      pct.textContent = Math.round(shown * 100) + '%';
      if (shown < 1) requestAnimationFrame(tick);
      else setTimeout(function () { go('story1'); }, 450);
    })();
  }

  // ---------- 背景音乐 ----------
  var bgm = $('#bgm'), musicBtn = $('#music'), musicOn = CFG.music !== false;
  bgm.volume = .7;
  function playBgm() {
    if (!musicOn) return;
    var p = bgm.play();
    if (p && p.catch) p.catch(function () {});
  }
  bgm.addEventListener('play', function () { musicBtn.classList.add('playing'); });
  bgm.addEventListener('pause', function () { musicBtn.classList.remove('playing'); });
  musicBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    unlockAudio();
    musicOn = !musicOn;
    if (musicOn) playBgm(); else bgm.pause();
  });
  // 微信内可在 JSBridge 就绪时自动播放
  document.addEventListener('WeixinJSBridgeReady', function () {
    if (window.WeixinJSBridge) WeixinJSBridge.invoke('getNetworkType', {}, playBgm);
    else playBgm();
  }, false);
  // 其他浏览器：第一次触摸时开始播放
  document.addEventListener('touchstart', function first() {
    document.removeEventListener('touchstart', first, true);
    if (bgm.paused) playBgm();
  }, true);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) bgm.pause(); else playBgm();
  });
  try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {}

  // ---------- 音效（Web Audio 合成） ----------
  var ctx = null;
  function unlockAudio() {
    if (!ctx) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ctx = new AC();
    }
    if (ctx.state === 'suspended') ctx.resume();
  }
  function hz(m) { return 440 * Math.pow(2, (m - 69) / 12); }
  function pluck(m, at, gain, len) {
    if (!ctx) return;
    var t = ctx.currentTime + (at || 0), f = hz(m), out = ctx.createGain();
    out.gain.value = gain || .18;
    out.connect(ctx.destination);
    [1, 2, 3, 4].forEach(function (h) {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = f * h;
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(1 / (h * h * .8), t + .004);
      g.gain.exponentialRampToValueAtTime(.0001, t + (len || 1.2) / h);
      o.connect(g); g.connect(out);
      o.start(t); o.stop(t + (len || 1.2) + .05);
    });
  }
  function thump(f0, f1, dur, gain) {
    if (!ctx) return;
    var t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(f0, t);
    o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(gain, t);
    g.gain.exponentialRampToValueAtTime(.0001, t + dur);
    o.connect(g); g.connect(ctx.destination);
    o.start(t); o.stop(t + dur + .02);
  }
  var PENTA = [74, 76, 78, 81, 83, 86];
  var sfx = {
    tap: function () { pluck(81, 0, .12, .6); },
    stamp: function () { thump(170, 60, .22, .5); pluck(62, .01, .08, .5); },
    pluck: function (i) { pluck(PENTA[i % PENTA.length] - 12, 0, .12, 1.4); },
    gasp: function () { thump(900, 260, .4, .22); thump(140, 50, .35, .45); },
    good: function () { PENTA.forEach(function (m, i) { pluck(m, i * .07, .13, 1.5); }); },
    bad: function () { pluck(69, 0, .16, 1.2); pluck(66, .28, .16, 1.2); pluck(62, .56, .18, 1.8); thump(120, 45, .5, .35); }
  };

  // ---------- 花瓣飘落 ----------
  var petals = (function () {
    var cv = $('#petals'), c = cv.getContext('2d'), list = [], on = false, raf = 0, W = 0, H = 0, dpr = 1, fade = 0;
    function mk(initial) {
      return {
        x: Math.random() * W, y: initial ? Math.random() * H : -20 - Math.random() * 80,
        r: 5 + Math.random() * 6, vx: -.3 + Math.random() * .6, vy: .5 + Math.random() * .8,
        a: Math.random() * 6.28, va: -.03 + Math.random() * .06, f: Math.random() * 6.28, vf: .02 + Math.random() * .04,
        hue: Math.random() < .7 ? 350 : 20
      };
    }
    function frame() {
      c.clearRect(0, 0, W, H);
      fade = Math.max(0, Math.min(1, fade + (on ? .03 : -.04)));
      c.globalAlpha = fade * .85;
      list.forEach(function (p) {
        p.x += p.vx + Math.sin(p.f) * .5; p.y += p.vy; p.a += p.va; p.f += p.vf;
        if (p.y > H + 20) Object.assign(p, mk(false));
        c.save();
        c.translate(p.x, p.y); c.rotate(p.a); c.scale(1, Math.abs(Math.cos(p.f)) * .7 + .3);
        var g = c.createRadialGradient(-p.r * .3, 0, 0, 0, 0, p.r);
        g.addColorStop(0, 'hsla(' + p.hue + ',90%,94%,1)');
        g.addColorStop(1, 'hsla(' + p.hue + ',75%,78%,1)');
        c.fillStyle = g;
        c.beginPath();
        c.moveTo(0, -p.r);
        c.quadraticCurveTo(p.r * .9, -p.r * .2, 0, p.r);
        c.quadraticCurveTo(-p.r * .9, -p.r * .2, 0, -p.r);
        c.fill();
        c.restore();
      });
      if (on || fade > 0) raf = requestAnimationFrame(frame);
      else { raf = 0; c.clearRect(0, 0, W, H); }
    }
    return {
      resize: function () {
        dpr = Math.min(2, window.devicePixelRatio || 1);
        W = innerWidth; H = innerHeight;
        cv.width = W * dpr; cv.height = H * dpr;
        c.setTransform(dpr, 0, 0, dpr, 0, 0);
        if (!list.length) for (var i = 0; i < 22; i++) list.push(mk(true));
      },
      set: function (v) {
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) v = false;
        on = v;
        if ((on || fade > 0) && !raf) raf = requestAnimationFrame(frame);
      }
    };
  })();

  // ---------- 启动 ----------
  layout();
  window.addEventListener('resize', layout);
  window.addEventListener('orientationchange', function () { setTimeout(layout, 300); });

  var first = ['assets/bg1.jpg', 'assets/cover_title.png', 'assets/cover_seal.png', 'assets/cover_start.png'];
  Promise.all(first.map(loadImg)).then(function () {
    $('#boot').classList.add('hide');
    musicBtn.classList.add('ready');
    go('cover');
    preloadAll(); // 封面展示期间后台继续加载其余素材
  });
})();
