// dongdong.js：情歌 MV《咚咚咚》。分镜见 STORYBOARD.md，时间全部来自 src/song_data.js（SONG），
// 所以每一次底鼓 = 一次心跳 = 一次灯闪，每个字幕字在它被唱出的那一刻点亮。
(() => {
  // ---------------------------------------------------------------- 节拍 & 歌词时间
  const KICKS = SONG.kicks, CLAPS = SONG.claps, SYL = SONG.lyrics.flatMap(L => L.syl);
  const DONGS = SYL.filter(s => s.ch === '咚').map(s => s.t);
  const last = (list, t) => { let lo = 0, hi = list.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (list[m] <= t + 1e-6) { r = m; lo = m + 1; } else hi = m - 1; } return r; };
  const since = (list, t) => { const i = last(list, t); return i < 0 ? 99 : t - list[i]; };
  const kick = (t, k = 9) => Math.exp(-since(KICKS, t) * k);             // 1 on each kick (the heartbeat), then decays
  const clapK = (t, k = 10) => Math.exp(-since(CLAPS, t) * k);
  const dong = (t, k = 5) => Math.exp(-since(DONGS, t) * k);             // each sung 咚
  const sylHit = (t, from, to, k = 9) => { const s = SYL.filter(x => x.t >= from && x.t < to).map(x => x.t); return Math.exp(-since(s, t) * k); };
  const kickIndex = t => last(KICKS, t);

  // ---------------------------------------------------------------- palette
  const C = {
    night: '#1E2150', sky2: '#2C2F68', bldL: '#3A3266', bldR: '#2D3B6A', bldFar: '#4A5A8C', road: '#252043',
    warm: '#F7D58A', warmDk: '#E9A94E', roomDk: '#2B2146', curtain: '#E27A92', curtainDk: '#B4506E', sill: '#C8B59A',
    beam: '#FFD98A', rose: '#EF6F8E', heart: '#E2476E',
  };
  const BLU = { col: '#7DB4D8', dk: '#3F6E98', lt: '#C5E4F5', hat: 'bow' };
  // emotions() cross-fades body colours between keys, so Blu's colours ride along in every key (or she'd flash clay-orange)
  const bluEmotions = (t, keys, o) => emotions(t, keys.map(([a, b, c]) => [a, b, { ...BLU, ...(c || {}) }]), o);
  const WL = { x: 400, y: 560, w: 320, h: 290 }, WR = { x: 1520, y: 560, w: 320, h: 290 };
  const SILL = WL.y + WL.h / 2;                                            // the characters stand on the sill line

  // several glows with ONE flush (glow() flushes the brush every call, which is the slow part without a GPU)
  function glows(list) {
    list = list.filter(g => g[4] > .01 && g[2] > 1); if (!list.length) return;
    flushBrush(); push(); blendMode(ADD);
    for (const [x, y, r, col, a] of list) { const c = color(col), rr = r * (1 + jit(.03)); tint(red(c), green(c), blue(c), 150 * clamp(a)); image(glowTex, x - rr, y - rr, 2 * rr, 2 * rr); }
    noTint(); blendMode(BLEND); pop();
  }

  // ---------------------------------------------------------------- set pieces
  function sky(t, o = {}) {
    boilSeed('sky');
    paint(rectPts(-900, -700, W + 1800, H + 1400), { wash: C.night, ink: null });
    paint(ellPts(960, 820, 1300, 520, 30, 10), { fill: o.warm ? '#7B4E86' : C.sky2, fillOp: o.warm ? 120 : 110, bleed: .3, tex: .5, ink: null });
    // stars: in the intro/outro each music-box note (eighth notes) makes a different star flash
    const e = Math.floor(bpOf(t) * 2), ek = Math.exp(-frac(bpOf(t) * 2) * 5), box = o.box ?? 0;
    for (let i = 0; i < 34; i++) {
      boilSeed('star' + i);
      const x = hash(i) * 2600 - 340, y = hash(i + 50) * 520 - 120;
      let tw = .5 + .4 * Math.sin(t * (1.5 + 2 * hash(i + 9)) + i * 2);
      if (box && (e * 7) % 34 === i) tw += 1.6 * ek * box;
      paint(starPts(x, y, (3 + 5 * hash(i + 90)) * tw, .35, 4), { wash: PAL.cream, washOp: Math.min(255, 140 + 90 * tw), ink: null });
    }
    boilSeed('moon');
    paint(ellPts(960, 170, 62, 62, 24, 1.5), { wash: PAL.cream, fill: PAL.ochre, fillOp: 35, ink: PAL.ink, sw: .8 });
    paint(ellPts(942, 150, 15, 11, 10), { fill: mixCol(PAL.cream, PAL.ochre, .5), fillOp: 110, ink: null });
  }
  // a building with a grid of little windows; `lit` decides which of them glow
  function building(key, x, y, w, h, col, lit = () => 0, skip = null) {
    boilSeed('bld' + key);
    paint(rectPts(x, y, w, h, 2), { wash: col, ink: null });
    inkLine([[x, y + 2], [x + w / 2, y], [x + w, y + 2]], 1, PAL.ink, 'ink', .2);
    inkLine([[x + (x < 900 ? w : 0), y], [x + (x < 900 ? w : 0), y + h / 2], [x + (x < 900 ? w : 0), y + h]], 1, PAL.ink, 'ink', .1);
    paint(rectPts(x - 10, y - 26, w + 20, 28, 1), { wash: mixCol(col, PAL.ink, .35), ink: PAL.ink, sw: .8 });
    for (let i = 0; i < 12; i++) {
      const cx = x + 70 + (i % 4) * (w - 140) / 3, cy = y + 90 + Math.floor(i / 4) * 250;
      if (skip && Math.abs(cx - skip.x) < skip.w * .9 && Math.abs(cy - skip.y) < skip.h * .9) continue;
      boilSeed('bw' + key + i);
      const k = clamp(lit(i));
      paint(rrPts(cx - 34, cy - 44, 68, 88, 8, 1.5), { wash: mixCol(mixCol(col, PAL.ink, .45), C.warm, k), ink: PAL.ink, sw: .6 });
    }
  }
  function street(t, lampK = 0) {
    boilSeed('street');
    paint(rectPts(-900, 930, W + 1800, 700, 2), { wash: C.road, ink: null });
    inkLine([[-900, 932], [960, 928], [W + 900, 932]], 1, PAL.ink, 'ink', .3);
    for (let i = 0; i < 9; i++) paint(rectPts(-300 + i * 320, 1010, 150, 14, 2), { wash: mixCol(C.road, PAL.cream, .25), ink: null });
    boilSeed('lamppost');
    inkLine([[960, 935], [962, 760], [960, 640]], 2.2, PAL.ink, 'ink', .2);
    inkLine([[960, 640], [990, 616], [1030, 626]], 1.6, PAL.ink, 'ink', .6);
    paint(ellPts(1032, 640, 26, 16, 14), { wash: mixCol(C.warm, PAL.cream, .3), ink: PAL.ink, sw: .7 });
    return [1032, 650, 160 + 90 * lampK, C.warm, .55 + .45 * lampK];
  }
  // A window seen from the street: interior (dark or lit) and curtains behind the character; frame and sill in front.
  function windowBack(key, w, lit, o = {}) {
    boilSeed('win' + key);
    const x = w.x - w.w / 2, y = w.y - w.h / 2;
    paint(rectPts(x, y, w.w, w.h, 1.5), { wash: mixCol(C.roomDk, C.warm, clamp(lit)), ink: null });
    if (lit > .05) paint(ellPts(w.x, w.y + 20, w.w * .45, w.h * .4, 20, 3), { fill: mixCol(C.warm, PAL.cream, .4), fillOp: 120 * clamp(lit), bleed: .3, ink: null });
    for (const s of [-1, 1]) {   // tied-back curtains
      boilSeed('cur' + key + s);
      const cx = w.x + s * (w.w / 2 - 34), sway = Math.sin(T * 1.3 + s) * 4;
      paint([[cx - 34, y], [cx + 34, y], [cx + 20 + sway, y + w.h * .55], [cx + 30, y + w.h], [cx - 30, y + w.h], [cx - 20 + sway, y + w.h * .55]],
        { wash: o.curtain || C.curtain, ink: PAL.ink, sw: .7, curv: .3 });
    }
  }
  function windowFront(key, w, wallBelow = null) {
    boilSeed('wfr' + key);
    const x = w.x - w.w / 2, y = w.y - w.h / 2;
    if (wallBelow) paint(rectPts(x - 60, y + w.h, w.w + 120, 700, 1), { wash: wallBelow, ink: null });   // hides whatever ducks below the sill
    for (const [a, b] of [[[x, y], [x + w.w, y]], [[x, y], [x, y + w.h]], [[x + w.w, y], [x + w.w, y + w.h]]]) inkLine([a, b], 1.4, PAL.ink, 'ink', 0);
    paint(rectPts(x - 26, y + w.h - 2, w.w + 52, 32, 1.5), { wash: C.sill, ink: PAL.ink, sw: .9 });
  }
  // A desk lamp held at the arm tip (arm space: +x along the arm). on 0..1.
  const lampHook = on => (u, sw) => {
    paint(rectPts(-.2 * u, -.25 * u, .8 * u, .5 * u, u * .02), { wash: '#6D5A7A', ink: PAL.ink, sw: sw * .6 });
    paint([[.4 * u, -.45 * u], [1.9 * u, -1.05 * u], [1.9 * u, 1.05 * u], [.4 * u, .45 * u]], { wash: mixCol(PAL.ochre, '#FFE9A8', on), ink: PAL.ink, sw: sw * .7 });
    paint(ellPts(1.9 * u, 0, .32 * u, 1.0 * u, 14), { wash: mixCol('#C9B98F', PAL.cream, on), ink: PAL.ink, sw: sw * .5 });
  };
  // where the lamp's mouth is in the world, for a character at (x, y) holding it in the right arm at angle a
  const lampMouth = (x, y, u, a, flip, dy = 0) => [x + (flip ? -1 : 1) * (4.9 + 4.1 * Math.cos(a)) * u, y + dy * u - 4.5 * u - 4.1 * Math.sin(a) * u];
  // a light beam from p to q: a chain of glows that widens with distance
  function beam(p, q, k, list) {
    if (k < .02) return;
    const n = Math.max(6, Math.round(Math.hypot(q[0] - p[0], q[1] - p[1]) / 45));
    for (let i = 0; i <= n; i++) { const s = i / n; list.push([lerp(p[0], q[0], s), lerp(p[1], q[1], s), 46 + 90 * s, C.beam, k * (.8 - .3 * s)]); }
    list.push([p[0], p[1], 90, PAL.cream, k]);
  }
  function ringWave(x, y, age, r0, col = PAL.cream) {
    if (age < 0 || age > .7) return;
    const k = age / .7, r = r0 + 260 * easeOut(k);
    paint(ellPts(x, y, r, r, 30), { ink: col, sw: 2.2 * (1 - k) + .2 });
  }
  // a little heart painted on Clawd's body (body space), pumping with the kicks
  const chestHeart = (k, size = 1) => (u, sw) => { const r = u * .85 * size * (1 + .4 * k); paint(heartPts(0, -2.9 * u - r * .55, r), { wash: C.heart, ink: PAL.ink, sw: sw * .6 }); };
  // the string of lights between the two windows (n bulbs; shown 0..1 grows it out from the middle)
  const A0 = [WL.x + WL.w / 2 + 6, WL.y - WL.h / 2 + 10], A1 = [WR.x - WR.w / 2 - 6, WR.y - WR.h / 2 + 10];
  const wireAt = s => [lerp(A0[0], A1[0], s), lerp(A0[1], A1[1], s) + 120 * 4 * s * (1 - s)];
  function lightString(t, shown, flashK, list) {
    if (shown <= 0) return;
    boilSeed('wire');
    const P = []; for (let i = 0; i <= 16; i++) { const s = .5 + (i / 16 - .5) * shown; P.push(wireAt(s)); }
    inkLine(P, .9, PAL.ink, 'inkfine', .5);
    const cols = [C.warm, C.rose, '#9FD8E6', PAL.cream];
    for (let i = 0; i < 15; i++) {
      const s = (i + .5) / 15; if (Math.abs(s - .5) > shown / 2) continue;
      boilSeed('bulb' + i);
      const [bx, by] = wireAt(s), k = clamp(.45 + .55 * flashK + .2 * Math.sin(t * 3 + i * 1.7));
      paint(ellPts(bx, by + 12, 8, 11, 10), { wash: mixCol('#8C7A6A', cols[i % 4], k), ink: PAL.ink, sw: .45 });
      if (i % 2 === 0) list.push([bx, by + 12, 30 + 26 * flashK, cols[i % 4], .25 + .6 * flashK]);
    }
  }

  // ---------------------------------------------------------------- karaoke lyrics (screen space)
  const FONT = '"ZCOOL KuaiLe", "WenQuanYi Zen Hei", sans-serif';
  function karaoke(t) {
    const L = SONG.lyrics.find(L => t >= L.start - .45 && t < L.end - .15); if (!L) return;
    const a = seg(t, L.start - .45, L.start - .15) * (1 - seg(t, L.end - .45, L.end - .15));
    const size = 82, adv = 90, gap = L.brk ? 54 : 0, n = L.syl.length, total = n * adv + gap;
    L.syl.forEach((s, i) => {
      const x = 960 - total / 2 + adv * (i + .5) + (L.brk && i >= L.brk ? gap : 0);
      const age = t - s.t, on = age >= 0, hit = on ? Math.exp(-age * 7) : 0;
      const col = !on ? PAL.cream : s.ch === '咚' ? '#FFD45E' : '#FF9AB4';
      letter(s.ch, x, 990 - 18 * hit, size * (1 + .32 * hit), col,
        { screen: true, alpha: a, stroke: PAL.ink, font: `${(size * (1 + .32 * hit)).toFixed(1)}px ${FONT}`, rot: (on ? .06 : 0) * Math.sin(i * 2.1) * hit });
    });
  }

  // ---------------------------------------------------------------- A: intro, the dark street (0–9.6)
  function shotIntro(t, lt, dur) {
    const tLight = SONG.bar * 1, tPan = 4.4;
    const cx = kf(t, [[0, 960], [tPan, 960], [5.5, 400], [9.6, 400]]), cy = kf(t, [[0, 540], [tPan, 540], [5.5, 590], [8.6, 612], [9.6, 616]]);
    const z = kf(t, [[0, 1.0], [tPan, 1.04], [5.5, 2.1], [8.6, 2.7], [9.6, 3.6]], t > 8.6 ? easeIn : ease);
    camBegin(cx, cy, z);
    const G = [];
    sky(t, { box: 1 });
    const litR = t < tLight ? 0 : 1 - .25 * Math.exp(-(t - tLight) * 8);   // snaps on with a little flare
    building('L', -300, 250, 940, 1100, C.bldL, i => (i === 2 ? .7 : 0), WL);
    building('R', 1280, 220, 1000, 1100, C.bldR, i => (i === 9 ? .6 : 0), WR);
    G.push(street(t, 0));
    windowBack('L', WL, .08);
    windowBack('R', WR, litR);
    if (t >= tLight) G.push([WR.x, WR.y, 260 + 300 * Math.exp(-(t - tLight) * 4), C.warm, .6 + .6 * Math.exp(-(t - tLight) * 3)]);
    glows(G.splice(0));
    // Blu pops up into her window and hums
    if (t > tLight + .1) {
      const up = backOut(seg(t, tLight + .1, tLight + .55));
      clawd(WR.x, SILL, 16, { ...BLU, ...feel('happy', t, { emote: 'music', lookX: -.3 }), view: 'q', flip: true, dy: lerp(7, 0, up) + (feel('happy', t).dy || 0) * .5, boilKey: 'blu' });
    }
    // Clawd, gazing across from his dark window; love lands on a kick
    const mood = emotions(t, [[0, 'neutral', { lookX: .9, lookY: -.1 }], [6.0, 'love', { lookX: .8 }]], { take: 1.2 });
    const k = t > 4.8 ? kick(t) : 0;
    clawd(WL.x, SILL, 16, { ...mood, sq: (mood.sq || 0) + .07 * k, tintK: mood.tintK, boilKey: 'clawd',
      draw: t > 6.0 ? chestHeart(k, ease(seg(t, 6.0, 6.4)) * 1.2) : null });
    windowFront('L', WL); windowFront('R', WR);
    camEnd();
    glows(G);
    if (lt < 1.6) iris(960, 520, lerp(0, 1300, easeIn(seg(lt, .15, 1.6))));
    boilSeed('transition');
    if (lt > dur - .3) brushWipe((lt - (dur - .3)) / .6, [C.curtainDk, C.curtain]);
  }

  // ---------------------------------------------------------------- B: verse 1-2, Clawd at his window (9.6–19.2)
  function curtainWipe(p) {   // two curtains slide shut (p 0→1) in screen space
    if (p <= 0) return;
    for (const s of [-1, 1]) {
      boilSeed('cw' + s);
      const edge = 960 + s * lerp(1100, -20, easeOut(p)), outer = s < 0 ? -80 : W + 80;
      const P = []; for (let i = 0; i <= 8; i++) P.push([edge + Math.sin(i * 1.3 + s) * 14 * (1 - p), -60 + i * (H + 120) / 8]);
      paint([...P, [outer, H + 60], [outer, -60]], { wash: C.curtain, ink: PAL.ink, sw: 1.2 });
      for (let f = 1; f <= 4; f++) { const fx = lerp(edge, outer, f / 5); inkLine([[fx, -40], [fx + 12, H / 2], [fx - 6, H + 40]], .9, C.curtainDk, 'dry', .4); }
    }
  }
  function shotWindow(t, lt, dur) {
    const tWave = 15.0, tTurn = 16.2, tHide = 16.85;
    camBegin(kf(lt, [[0, 650], [dur, 780]]) + 6 * Math.sin(lt * .7), 545, kf(lt, [[0, 1.1], [dur, 1.0]]));
    const G = [];
    sky(t);
    // far side: Blu's building, paler and smaller (depth)
    building('far', 1180, 300, 900, 900, C.bldFar, i => (i === 11 ? .5 : 0), { x: 1480, y: 560, w: 200, h: 180 });
    const FW = { x: 1480, y: 560, w: 200, h: 180 };
    windowBack('far', FW, .95 + .05 * kick(t));
    G.push([FW.x, FW.y, 180 + 70 * kick(t) + 120 * sylHit(t, 14.4, 19.2, 4), C.warm, .55 + .3 * kick(t)]);
    glows(G.splice(0));
    const bluTurn = t < tTurn ? { view: 'q', flip: false } : turn(t, tTurn, tTurn + .25, .25, -.25);
    const bm = bluEmotions(t, [[0, 'happy', { emote: 'music', lookX: .5 }], [tTurn + .3, 'neutral', { lookX: .9 }], [17.4, 'confused', { lookX: .9 }]], { take: .6 });
    clawd(FW.x, FW.y + FW.h / 2, 9, { ...BLU, ...bm, ...bluTurn, boilKey: 'blu' });
    windowFront('far', FW);
    // near side: the wall around Clawd's window
    boilSeed('wall');
    paint(rectPts(-400, -300, 1420, 1500, 2), { wash: C.bldL, ink: null });
    inkLine([[1018, -300], [1020, 500], [1016, 1300]], 1.3, PAL.ink, 'ink', .1);
    const NW = { x: 515, y: 520, w: 780, h: 600 };
    windowBack('near', NW, .12, {});
    // Clawd: dreamy → waves → panics and ducks → peeks out, blushing
    const mood = emotions(t, [[0, 'hopeful', { lookX: 1, lookY: -.2 }], [tWave, 'happy', { lookX: 1 }], [tHide - .05, 'scared', { lookX: 1 }], [17.6, 'shy', { lookX: 1, lookY: -.3 }]]);
    const wave = t > tWave && t < tHide ? ease(seg(t, tWave, tWave + .25)) : 0;
    const duck = t < tHide ? 0 : t < 17.4 ? lerp(0, 6.2, easeIn(seg(t, tHide, tHide + .22))) : lerp(6.2, 4.3, backOut(seg(t, 17.6, 18.0)));
    const k = kick(t);
    clawd(NW.x, NW.y + NW.h / 2, 30, { ...mood, view: 'front', dy: (mood.dy || 0) * (duck ? .2 : 1) + duck, sq: (mood.sq || 0) + .05 * k,
      aR: wave ? lerp(mood.aR ?? .2, 1.3 + .45 * Math.sin((t - tWave) * 14), wave) : mood.aR, boilKey: 'clawd', noShadow: true,
      draw: chestHeart(k, .7) });
    if (t > tHide + .1 && t < 17.6) emote('sweat', NW.x + 190, NW.y + NW.h / 2 - 150, 30, seg(t, tHide + .1, tHide + .3), t - tHide);
    windowFront('near', NW, C.bldL);
    boilSeed('pot');   // a flower pot on the sill
    paint(rectPts(160, 790, 70, 60, 2), { wash: '#B4614A', ink: PAL.ink, sw: .9 });
    inkLine([[195, 792], [190 + 6 * Math.sin(t * 2), 735]], 1, PAL.sap, 'ink', .4);
    paint(starPts(190 + 6 * Math.sin(t * 2), 728, 20, .45, 5, t * .3), { wash: C.rose, ink: PAL.ink, sw: .7 });
    camEnd();
    boilSeed('transition');
    if (lt < .3) brushWipe(.5 + lt / .6, [C.curtainDk, C.curtain]);
    curtainWipe(seg(lt, dur - .7, dur));
    karaoke(t);
  }

  // ---------------------------------------------------------------- C: verse 3-4, Clawd's room (19.2–28.8)
  const DESK = { x: 1460, y: 760 };
  function deskLamp(x, y, on) {   // standing on the desk, shade pointing left-down
    boilSeed('desklamp');
    paint(ellPts(x, y - 8, 60, 14, 14), { wash: '#6D5A7A', ink: PAL.ink, sw: .9 });
    inkLine([[x, y - 12], [x + 30, y - 120], [x - 20, y - 190]], 2, PAL.ink, 'ink', .3);
    push(); translate(x - 20, y - 190); rotate(2.5);
    lampHook(on)(34, 1.4);
    pop();
  }
  function shotRoom(t, lt, dur) {
    const tIdea = 26.85, tGo = 27.25, tAt = 27.95, tGrab = 28.05;
    const shake = t > 26.4 ? shakeXY(t, 9 * seg(t, 26.4, 28.8) ** 2) : [0, 0];
    const cx = kf(t, [[19.2, 900], [24, 860], [26.4, 860], [28.1, 1180]]), cy = kf(t, [[19.2, 600], [24, 640], [25.8, 680], [26.4, 650], [28.1, 610]]);
    const z = kf(t, [[19.2, 1.0], [24, 1.0], [25.8, 1.4], [26.4, 1.4], [28.1, 1.08]]);
    camBegin(cx + shake[0], cy + shake[1], z * (1 + .02 * kick(t)));
    const G = [];
    boilSeed('room');
    paint(rectPts(-500, -400, W + 1000, 1300, 2), { wash: '#4A3A6C', ink: null });
    for (let i = 0; i < 40; i++) { boilSeed('wp' + i); const x = -300 + (i % 10) * 270 + (Math.floor(i / 10) % 2) * 135, y = 60 + Math.floor(i / 10) * 200; paint(heartPts(x, y, 9), { wash: '#5A4880', ink: null }); }
    boilSeed('floor');
    paint(rectPts(-500, 880, W + 1000, 600, 2), { wash: '#5E4038', ink: null });
    inkLine([[-500, 882], [960, 878], [W + 500, 882]], 1.2, PAL.ink, 'ink', .2);
    for (let i = 0; i < 7; i++) inkLine([[-400 + i * 420, 890], [-520 + i * 470, 1300]], .7, '#3E2A2A', 'inkfine', .1);
    // back window, curtains closed (the curtains from the end of shot B)
    boilSeed('bwin');
    paint(rectPts(330, 250, 380, 330, 1.5), { wash: C.roomDk, ink: PAL.ink, sw: 1.1 });
    for (const s of [-1, 1]) { boilSeed('bcur' + s); paint([[520 + s * 2, 250], [520 + s * 200, 240], [520 + s * 190, 600], [520 + s * 10, 600]], { wash: C.curtain, ink: PAL.ink, sw: .8, curv: .2 }); }
    // a framed heart doodle on the wall
    boilSeed('frame');
    paint(rectPts(1080, 330, 150, 120, 1), { wash: PAL.cream, ink: PAL.ink, sw: 1 });
    paint(heartPts(1155, 392, 34 * (1 + .1 * kick(t))), { wash: C.rose, ink: PAL.ink, sw: .6 });
    // desk
    boilSeed('desk');
    paint(rectPts(1260, DESK.y, 420, 34, 1.5), { wash: '#8A5A44', ink: PAL.ink, sw: 1 });
    for (const lx of [1290, 1630]) paint(rectPts(lx, DESK.y + 30, 24, 150, 1), { wash: '#6E4433', ink: PAL.ink, sw: .8 });
    if (t < tGrab) deskLamp(DESK.x, DESK.y, 0);
    // Clawd: thinks → tries to speak → tongue-tied scribble → hand-on-heart, heart pumping → sees the lamp → idea → trots over, grabs it
    const u = 34, gy = 905;
    const walk = stroll(t, tGo, tAt, 840, 1190, u);
    const x = t < tGo ? 840 : walk.x;
    const mood = emotions(t, [[19.2, 'thinking'], [21.5, 'determined', { lookX: .2 }], [22.35, 'surprised', { mouth: 'O', emote: null }],
      [22.9, 'nervous', { emote: 'scribble' }], [24.0, 'shy', { lookY: .4, lookX: 0 }], [26.4, 'neutral', { lookX: 1, lookY: .2 }],
      [tIdea, 'idea', { lookX: 1 }], [tAt, 'determined', { lookX: 1 }]]);
    const k = kick(t), heartSize = t < 24 ? .8 : lerp(.8, 2.1, ease(seg(t, 24.0, 24.6)));
    let pose = {};
    if (t >= 24 && t < 26.4) pose = { aL: -.9, aR: -.9 };                                    // paws over the heart
    if (t >= tGo && t < tAt) pose = { view: 'side', walk: walk.walk, dy: walk.dy };
    if (t >= tAt) pose = { aR: lerp(.2, 1.15, backOut(seg(t, tGrab, tGrab + .35))), armR: t >= tGrab ? lampHook(0) : null };
    clawd(x, gy, u, { ...mood, ...pose, sq: (mood.sq || 0) + .06 * k * (t > 24 ? 1.6 : 1), dy: (mood.dy || 0) * (pose.walk != null ? .3 : 1) + (pose.dy || 0),
      boilKey: 'clawd', draw: pose.view === 'side' ? null : chestHeart(k, heartSize) });
    if (t > 24 && t < 26.4) glows([[x, gy - 5 * u * 1.0, 120 + 120 * k, C.rose, .35 + .4 * k]]);
    camEnd();
    boilSeed('transition');
    if (lt < .7) { const p = 1 - seg(lt, 0, .7); curtainWipe(p); }
    flash(seg(t, 28.45, 28.8) ** 2, PAL.cream);
    karaoke(t);
  }

  // ---------------------------------------------------------------- D-E-F: chorus & outro on the street (28.8–60)
  function shotStreet(t, lt, dur) {
    const c1 = 28.8, whip0 = 33.25, whip1 = 33.65, two = 38.4, heartT = 43.2, stringT = 45.0, outro = 48.0, irisT = 55.8;
    const chorus = t < outro;
    const k = kick(t, chorus ? 8 : 6), dk = dong(t);
    // camera: on Clawd → rides the beam → whips to Blu → two-shot → pull back wide → push to the lantern
    const cx = kf(t, [[c1, 520], [32.4, 560], [whip0, 760], [whip1, 1440], [37.6, 1470], [39.0, 960], [46.8, 960], [48, 960], [52.8, 960], [57.4, 960]]);
    const cy = kf(t, [[c1, 580], [whip0, 570], [whip1, 580], [37.6, 590], [39.0, 545], [46.8, 545], [48, 520], [52.8, 520], [57.4, 560]]);
    const z = kf(t, [[c1, 1.75], [32.4, 1.7], [whip0, 1.55], [whip1, 1.75], [37.6, 1.8], [39.0, 1.12], [46.8, 1.12], [48, 1.0], [52.8, 1.0], [57.4, 1.55]]);
    camBegin(cx, cy, z * (1 + (chorus ? .035 : .015) * k + .03 * dk));
    const G = [];
    sky(t, { warm: t > heartT, box: t > outro ? 1 : 0 });
    const lit = i => (chorus ? (hash(i * 3 + Math.floor(last(CLAPS, t) / 2)) > .6 ? .7 : .15) : hash(i) > .55 ? .75 : .1);
    building('L', -300, 250, 940, 1100, C.bldL, lit, WL);
    building('R', 1280, 220, 1000, 1100, C.bldR, i => lit(i + 20), WR);
    G.push(street(t, k));
    // windows: Clawd's lit by his own lamp from now on; Blu's flashes when his beam hits it
    const clawdLamp = t < two ? .45 + .55 * k : t < 40.2 ? .5 : t < heartT ? (beatN(t) % 2 === 0 ? .45 + .55 * k : .5) : .75 + .25 * k;
    const bluLampOn = t > 38.0;
    const bluLamp = !bluLampOn ? 0 : t < 40.2 ? .3 + .7 * dk : t < heartT ? (beatN(t) % 2 === 1 ? .45 + .55 * k : .5) : .75 + .25 * k;
    windowBack('L', WL, .55 + .25 * clawdLamp);
    windowBack('R', WR, .6 + .35 * (t < two ? clawdLamp : bluLamp));
    glows(G.splice(0));

    // ----- Clawd
    const cm = emotions(t, [[c1, 'determined', { lookX: 1 }], [30.6, 'excited', { lookX: 1 }], [40.2, 'starstruck', { lookX: 1 }], [heartT + .1, 'love', { lookX: .8 }], [outro, 'love', { lookX: .9 }]], { take: .7 });
    const bob = move(chorus ? 'bounce' : 'sway', t, 0);
    const jmp = jump(t, 45.6, 46.05, 2.2), jmp2 = jump(t, 46.8, 47.25, 1.8);
    const lean = t > 50.4 && t < 53.2 ? ease(seg(t, 50.4, 50.9)) * (1 - ease(seg(t, 52.6, 53.2))) : 0;
    const aC = t < heartT + 2.4 ? .25 + .06 * Math.sin(t * 3) : lerp(.25, -.5, ease(seg(t, heartT + 2.4, heartT + 2.9)));
    const holdLampC = t < heartT + 2.9;
    clawd(WL.x, SILL, 16, { ...cm, dy: (cm.dy || 0) * .4 + bob.dy * .5 + jmp.dy + jmp2.dy, sq: (cm.sq || 0) + .08 * k + jmp.sq + jmp2.sq,
      rot: (bob.rot || 0) * .6 + .12 * lean, dx: (bob.dx || 0) * .25 + .8 * lean, aR: holdLampC ? aC : cm.aR, aL: t > 30.6 && t < 31.9 ? -.9 : cm.aL,
      armR: holdLampC ? lampHook(clawdLamp) : null, boilKey: 'clawd', draw: chestHeart(k, t > 30.6 && t < 31.9 ? 1.4 : .8) });
    const mC = lampMouth(WL.x, SILL, 16, aC, false, (cm.dy || 0) * .4 + bob.dy * .5);

    // ----- Blu
    const bm = bluEmotions(t, [[c1, 'happy', { emote: 'music', lookX: -.4 }], [34.3, 'surprised', { lookX: 1 }], [35.3, 'shy', { lookX: 1 }], [36.0, 'love', { lookX: 1 }],
      [37.2, 'idea', { lookX: .2, lookY: .3 }], [38.0, 'determined', { lookX: 1 }], [40.2, 'happy', { lookX: 1 }], [heartT + .1, 'love', { lookX: .8 }], [outro, 'love', { lookX: .9 }]], { take: .8 });
    const bob2 = move(chorus ? 'bounce' : 'sway', t + .08, 1);
    const aB = !bluLampOn ? null : t < heartT + 2.9 ? lerp(-.6, .25, backOut(seg(t, 37.6, 38.0))) + .06 * Math.sin(t * 3.3) : lerp(.25, -.5, ease(seg(t, heartT + 2.9, heartT + 3.4)));
    const holdLampB = bluLampOn && t < heartT + 3.4;
    clawd(WR.x, SILL, 16, { ...BLU, ...bm, flip: true, dy: (bm.dy || 0) * .4 + bob2.dy * .5 + jmp.dy + jmp2.dy, sq: (bm.sq || 0) + .06 * k + jmp.sq + jmp2.sq,
      rot: (bob2.rot || 0) * .6 + .12 * lean, dx: (bob2.dx || 0) * .25 + .8 * lean, aR: holdLampB ? aB : bm.aR, armR: holdLampB ? lampHook(bluLamp) : null, boilKey: 'blu' });
    if (t > 37.2 && t < 37.6) {   // her lamp waiting on the sill, before she grabs it
      push(); translate(WR.x - 130, SILL - 18); rotate(Math.PI - .2); lampHook(0)(16, .8); pop();
    }
    const mB = lampMouth(WR.x, SILL, 16, aB || 0, true, (bm.dy || 0) * .4 + bob2.dy * .5);
    windowFront('L', WL); windowFront('R', WR);

    // ----- light: beams, rings, the heart of light, the string of lights
    const yi = sylHit(t, 33.6, 34.8, 10);   // 一闪一闪: four blinks
    if (t < two) beam(mC, [WR.x, WR.y], clamp(.25 + .75 * Math.max(k, yi)) * seg(t, c1, c1 + .1), G);
    else if (t < heartT) {
      beam(mC, [WR.x, WR.y], clawdLamp * .9, G);
      if (bluLampOn) beam(mB, [WL.x, WL.y], bluLamp * .9, G);
    } else if (t < heartT + 1.2) {
      const m = ease(seg(t, heartT - .3, heartT));
      beam(mC, [lerp(WR.x, 960, m), lerp(WR.y, 470, m)], 1 - seg(t, heartT + .6, heartT + 1.2), G);
      beam(mB, [lerp(WL.x, 960, m), lerp(WL.y, 470, m)], 1 - seg(t, heartT + .6, heartT + 1.2), G);
    }
    if (t >= two - .6 && t < two) G.push([WR.x, WR.y, 200, C.warm, .5]);
    // ring waves on every sung 咚
    DONGS.forEach(d => {
      if (t < d || t > d + .7) return;
      boilSeed('ring' + d);
      const src = d < two ? mC : d < outro ? mB : [960, 545];
      ringWave(src[0], src[1], t - d, 30, d < two ? C.warm : d < outro ? '#9FD8E6' : C.rose);
      G.push([src[0], src[1], 220, d < two ? C.beam : '#BFE8F2', .9 * Math.exp(-(t - d) * 5)]);
    });
    // the heart of light (on 我喜欢你), then it settles into a heart lantern hanging from the string
    if (t > heartT - .05) {
      const bloom = backOut(seg(t, heartT, heartT + .5)), settle = ease(seg(t, stringT + .4, 47.2));
      const hk = sylHit(t, heartT, heartT + 1.4, 7) + .6 * k * (t > outro ? 1 : .5) + .5 * dk;
      const hx = 960, hy = lerp(440, wireAt(.5)[1] + 52, settle), hr = lerp(150, 46, settle) * bloom * (1 + .12 * hk);
      G.push([hx, hy, hr * 2.4, C.rose, .7 + .4 * hk]);
      glows(G.splice(0));
      if (settle > .02) { boilSeed('lanternline'); inkLine([wireAt(.5), [hx, hy - hr * .7]], .8, PAL.ink, 'inkfine', 0); }
      boilSeed('bigheart');
      paint(heartPts(hx, hy, hr), { wash: mixCol(C.heart, '#FF9AB4', .3 + .3 * clamp(hk)), ink: PAL.ink, sw: clamp(hr / 80, .5, 1.3) });
      if (t < stringT + .2) for (let i = 0; i < 8; i++) {   // sparkles burst out of the heart
        const q = seg(t, heartT + i * .02, heartT + .7 + i * .02), a = i / 8 * TAU;
        if (q > 0 && q < 1) paint(starPts(hx + Math.cos(a) * 260 * easeOut(q), hy + Math.sin(a) * 200 * easeOut(q), 22 * (1 - q * .7), .3, 4, q * 3), { wash: PAL.cream, washOp: 255 * (1 - q * q), ink: null });
      }
    }
    // 就在今晚: the string pops out bulb by bulb from the middle; later it blinks with the heartbeat
    const shown = t < stringT ? 0 : clamp(seg(t, stringT, stringT + 1.25) * 1.05);
    lightString(t, shown, t < outro ? sylHit(t, stringT, stringT + 2, 8) : Math.max(k, dk), G);
    camEnd();
    glows(G.splice(0));
    if (t > 46.4 && t < 47.6) {   // hearts drift up from both of them after the jump
      for (let i = 0; i < 2; i++) { const p = toScreen(i ? WR.x : WL.x, SILL - 150); emote('hearts', p[0], p[1], 26, seg(t, 46.3, 46.6) * (1 - seg(t, 47.3, 47.6)), t - 46.3); }
    }
    boilSeed('transition');
    if (t < c1 + .5) flash(1 - easeOut(seg(t, c1, c1 + .5)), PAL.cream);
    if (t > whip0 && t < whip1) {   // whip-pan smear lines
      const p = seg(t, whip0, whip1), s = Math.sin(p * Math.PI);
      for (let i = 0; i < 9; i++) { boilSeed('whip' + i); const y = 80 + i * 115 + 30 * hash(i); inkLine([[-100, y], [W + 100, y + jit(10)]], 3 * s * (.5 + hash(i + 7)), mixCol(C.night, PAL.cream, .25), 'dry', .2); }
    }
    if (t > irisT) {   // a heart-shaped iris closes onto the lantern, holds a beat, then shuts
      const lp = toScreen(960, wireAt(.5)[1] + 52, { cx: cx, cy: cy, zoom: z, rot: 0 });
      const r = t < 57.4 ? lerp(1500, 150, ease(seg(t, irisT, 57.4))) : t < 58.0 ? 150 * (1 + .12 * Math.sin((t - 57.4) * 10)) : lerp(150, 0, easeIn(seg(t, 58.0, 58.5)));
      if (r < 6) paint(rectPts(-60, -60, W + 120, H + 120), { wash: PAL.ink, ink: null }); else irisShape(heartPts(lp[0], lp[1] + r * .05, r, 30), PAL.ink);
    }
    karaoke(t);
  }

  shots([[0, shotIntro], [9.6, shotWindow], [19.2, shotRoom], [28.8, shotStreet]]);
})();
