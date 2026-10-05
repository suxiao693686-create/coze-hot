// 00猫 公用绘图库：片头和每期正片共用
const W = 1080, H = 1920;
const FONT = '"WenQuanYi Zen Hei", "PingFang SC", "Microsoft YaHei", sans-serif';

const C = {
  outline: '#4a2518', cream: '#fdfbee', shade: '#d3d1cc', shade2: '#efe9d2',
  pinkEar: '#f6b08f', nose: '#f6c3ac', eye: '#111111', mouthIn: '#7a1f24', tongue: '#ff8a8a',
  steel1: '#8693a2', steel2: '#5a6574', steelDark: '#3d4651', steelLight: '#b4bfcc',
  blue: '#2f6fde', orange: '#ff8a3d', red: '#e8432f', yellow: '#ffd54a',
};

// ---------- helpers ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const easeOut = k => 1 - Math.pow(1 - k, 3);
const easeIn = k => k * k * k;
const easeInOut = k => k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const easeOutBack = k => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const PELLET_COLORS = ['#f4f1e6', '#2b2b2b', '#2f6fde', '#e8432f', '#ffd54a', '#3bb273', '#ff8a3d', '#9b6bd6'];
function shadeHex(hex, f) {
  const n = parseInt(hex.slice(1), 16); let r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  r = clamp(Math.round(r * f), 0, 255); g = clamp(Math.round(g * f), 0, 255); b = clamp(Math.round(b * f), 0, 255);
  return `rgb(${r},${g},${b})`;
}

// ---------- 00猫 sprite (grid 33 x 38, bottom row 37) ----------
const GW = 33, GH = 38;
function inTri(px, py, a, b, c) {
  const d = (p1, p2, p3) => (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1]);
  const p = [px, py], d1 = d(p, a, b), d2 = d(p, b, c), d3 = d(p, c, a);
  return !(((d1 < 0) || (d2 < 0) || (d3 < 0)) && ((d1 > 0) || (d2 > 0) || (d3 > 0)));
}
function shrinkTri(t, k) {
  const cx = (t[0][0] + t[1][0] + t[2][0]) / 3, cy = (t[0][1] + t[1][1] + t[2][1]) / 3;
  return t.map(p => [cx + (p[0] - cx) * k, cy + (p[1] - cy) * k]);
}
const EAR_L = [[6.5, 0.2], [3.8, 9], [13.8, 4.2]];
const EAR_R = [[25.5, 0.2], [28.2, 9], [18.2, 4.2]];
function headMask(c, r, earL = 0, earR = 0) {
  const x = c + 0.5, y = r + 0.5;
  const ex = (x - 16.5) / 13.6, ey = (y - 12.2) / 9.4;
  if (ex * ex + ey * ey <= 1) return 1;
  const el = EAR_L.map(p => [p[0] - earL * 0.6, p[1] + earL]);
  const er = EAR_R.map(p => [p[0] + earR * 0.6, p[1] + earR]);
  if (inTri(x, y, ...el)) return 2;
  if (inTri(x, y, ...er)) return 3;
  return 0;
}
function bodyMask(c, r) {
  const x = c + 0.5, y = r + 0.5;
  const rr = (x0, y0, x1, y1, rad) => {
    if (x < x0 || x > x1 || y < y0 || y > y1) return false;
    const cx = clamp(x, x0 + rad, x1 - rad), cy = clamp(y, y0 + rad, y1 - rad);
    return (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad;
  };
  return rr(1.5, 15, 31.5, 34.5, 6) || rr(6.5, 30, 14.5, 38, 2) || rr(18.5, 30, 26.5, 38, 2);
}
function ellMask(cx, cy, rx, ry) { return (c, r) => { const x = (c + 0.5 - cx) / rx, y = (r + 0.5 - cy) / ry; return x * x + y * y <= 1; }; }

// draw a mask: fill + 1-cell outline; colorFn(c,r) for fill colour
function drawMask(g, S, ox, oy, c0, r0, c1, r1, mask, colorFn) {
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) {
    if (!mask(c, r)) continue;
    const edge = !mask(c - 1, r) || !mask(c + 1, r) || !mask(c, r - 1) || !mask(c, r + 1);
    g.fillStyle = edge ? C.outline : colorFn(c, r);
    g.fillRect(Math.round(ox + c * S), Math.round(oy + r * S), Math.ceil(S), Math.ceil(S));
  }
}
function cells(g, S, ox, oy, list, color) {
  g.fillStyle = color;
  for (const [c, r] of list) g.fillRect(Math.round(ox + c * S), Math.round(oy + r * S), Math.ceil(S), Math.ceil(S));
}
const EYES = {
  open:    [[1,0],[2,0],[0,1],[1,1],[2,1],[3,1],[0,2],[1,2],[2,2],[3,2],[1,3],[2,3]],
  blink:   [[0,2],[1,2],[2,2],[3,2]],
  happy:   [[1,1],[2,1],[0,2],[3,2],[0,3],[3,3]],
  angryL:  [[0,0],[1,1],[2,1],[3,2],[1,3],[2,3],[0,4]],
  angryR:  [[3,0],[2,1],[1,1],[0,2],[2,3],[1,3],[3,4]],
};

/**
 * pose: { eyes, mouth: 'smile'|'open'|'tongue', armL:[dx,dy], armR:[dx,dy], armsUp, sx, sy, headDx, headDy, earL, earR, lookUp }
 * (x, y) = bottom centre of the feet
 */
function drawCat(g, x, y, S, pose = {}) {
  const sx = pose.sx || 1, sy = pose.sy || 1;
  g.save();
  g.translate(x, y);
  g.scale(sx, sy);
  const ox = -GW * S / 2, oy = -GH * S;
  // shadow
  if (pose.shadowY !== undefined) {
    g.fillStyle = 'rgba(60,30,10,0.18)';
    g.beginPath(); g.ellipse(0, (pose.shadowY - y) / sy, 15 * S / sx, 2.2 * S, 0, 0, Math.PI * 2); g.fill();
  }

  // arms behind body when raised
  const armL = pose.armL || [0, 0], armR = pose.armR || [0, 0];
  const armColor = (c, r) => C.cream;
  // body
  drawMask(g, S, ox, oy, 0, 13, 32, 38, bodyMask, (c, r) => {
    if (r >= 19 && r <= 21 && c > 5 && c < 28 && Math.abs(c - 16.5) < 12 - (r - 19) * 3) return C.shade;
    if (c >= 27 && r >= 18 && r <= 31) return C.shade;
    if (c <= 4 && r >= 26 && r <= 31) return C.shade;
    if (r >= 32 && (c === 13 || c === 19)) return C.shade;
    return C.cream;
  });
  // toes
  cells(g, S, ox, oy, [[9, 36], [9, 37], [11, 36], [11, 37], [21, 36], [21, 37], [23, 36], [23, 37]], C.outline);
  if (pose.apron) {  // 奶茶店围裙
    drawMask(g, S, ox, oy, 8, 20, 25, 34, (c, r) => c >= 9 && c <= 23 && r >= 21 && r <= 33 && !(r > 31 && (c === 9 || c === 23)), (c, r) =>
      (r === 27 && c >= 13 && c <= 19) ? '#ffd9b0' : (r >= 26 && r <= 29 && c >= 13 && c <= 19 && (c === 13 || c === 19 || r === 29)) ? '#c25f1c' : C.orange);
    cells(g, S, ox, oy, [[10, 19], [10, 20], [22, 19], [22, 20]], C.orange);
  }

  // head
  const hdx = pose.headDx || 0, hdy = pose.headDy || 0;
  const hox = ox + hdx * S, hoy = oy + hdy * S;
  const eL = pose.earL || 0, eR = pose.earR || 0;
  const triL = shrinkTri(EAR_L.map(p => [p[0] - eL * 0.6, p[1] + eL]), 0.5);
  const triR = shrinkTri(EAR_R.map(p => [p[0] + eR * 0.6, p[1] + eR]), 0.5);
  drawMask(g, S, hox, hoy, 0, -2, 32, 23, (c, r) => headMask(c, r, eL, eR), (c, r) => {
    const x = c + 0.5, y = r + 0.5;
    if (inTri(x, y, ...triL)) return C.shade;
    if (inTri(x, y, ...triR)) return C.pinkEar;
    if (c >= 27 && r >= 9 && r <= 17) return C.shade2;
    return C.cream;
  });
  // blush
  for (const bx of [9.2, 23.8]) {
    const gx = hox + bx * S, gy = hoy + 15.2 * S;
    const grd = g.createRadialGradient(gx, gy, 0, gx, gy, 3 * S);
    grd.addColorStop(0, 'rgba(255,135,115,0.55)'); grd.addColorStop(1, 'rgba(255,135,115,0)');
    g.fillStyle = grd; g.fillRect(gx - 3 * S, gy - 3 * S, 6 * S, 6 * S);
  }
  // eyes
  const ey = pose.lookUp ? 9 : 10;
  const eyes = pose.eyes || 'open';
  const EL = eyes === 'angry' ? EYES.angryL : eyes === 'sad' ? EYES.angryR : EYES[eyes], ER = eyes === 'angry' ? EYES.angryR : eyes === 'sad' ? EYES.angryL : EYES[eyes];
  cells(g, S, hox, hoy, EL.map(([c, r]) => [8 + c, ey + r]), C.eye);
  cells(g, S, hox, hoy, ER.map(([c, r]) => [21 + c, ey + r]), C.eye);
  if (eyes === 'open') cells(g, S, hox, hoy, [[9, ey + 1], [22, ey + 1]], '#ffffff');
  if (pose.hat === 'helmet') {  // 工厂安全帽
    drawMask(g, S, hox, hoy, 5, -3, 28, 8, (c, r) => {
      const x = c + 0.5, y = r + 0.5;
      if (r === 5 && c >= 6 && c <= 26) return true;
      const ex = (x - 16.5) / 10, ey = (y - 5.5) / 7.5;
      return y <= 5.5 && ex * ex + ey * ey <= 1;
    }, (c, r) => (c === 16 && r < 5) ? '#ffe680' : (c < 11 && r < 3) ? '#fff2a8' : C.yellow);
  }
  // nose + mouth
  cells(g, S, hox, hoy, [[16, 14]], C.nose);
  cells(g, S, hox, hoy, [[15, 14], [17, 14]], '#f9d9cb');
  const mouth = pose.mouth || 'smile';
  if (mouth === 'open') {
    cells(g, S, hox, hoy, [[15, 15], [16, 15], [17, 15], [14, 16], [18, 16], [14, 17], [18, 17], [15, 18], [16, 18], [17, 18]], C.eye);
    cells(g, S, hox, hoy, [[15, 16], [16, 16], [17, 16], [15, 17], [17, 17]], C.mouthIn);
    cells(g, S, hox, hoy, [[16, 17]], C.tongue);
  } else {
    cells(g, S, hox, hoy, [[16, 15], [15, 16], [14, 16], [17, 16], [18, 16]], C.eye);
    if (mouth === 'tongue') cells(g, S, hox, hoy, [[15, 17], [16, 17], [15, 18]], C.tongue);
  }
  // arms in front
  if (pose.armsUp) {
    drawMask(g, S, ox, oy, 6, -10, 16, 16, ellMask(12.5 + armL[0], 1.5 + armL[1], 2.6, 4.2), armColor);
    drawMask(g, S, ox, oy, 16, -10, 27, 16, ellMask(20.5 + armR[0], 1.5 + armR[1], 2.6, 4.2), armColor);
    cells(g, S, ox, oy, [[11, -1], [13, -1], [19, -1], [21, -1]], C.outline);
    cells(g, S, ox, oy, [[12, 0], [20, 0]], C.pinkEar);
  } else {
    drawMask(g, S, ox, oy, -6, 12, 18, 36, ellMask(3.6 + armL[0], 26 + armL[1], 3.2, 4.6), armColor);
    drawMask(g, S, ox, oy, 15, 12, 39, 36, ellMask(29.4 + armR[0], 26 + armR[1], 3.2, 4.6), armColor);
  }
  g.restore();
}

// ---------- pixel text ----------
const textCache = {};
function pixelText(text, fontPx, scale, fill, outline = C.outline, shadow = true) {
  const key = [text, fontPx, scale, fill, outline, shadow].join('|');
  if (textCache[key]) return textCache[key];
  const t = document.createElement('canvas'), tg = t.getContext('2d');
  tg.font = `bold ${fontPx}px ${FONT}`;
  const tw = Math.ceil(tg.measureText(text).width) + 6, th = fontPx + 8;
  t.width = tw; t.height = th;
  tg.font = `bold ${fontPx}px ${FONT}`; tg.textBaseline = 'middle'; tg.fillStyle = '#000';
  tg.fillText(text, 3, th / 2 + 1);
  const d = tg.getImageData(0, 0, tw, th).data;
  const on = (x, y) => x >= 0 && y >= 0 && x < tw && y < th && d[(y * tw + x) * 4 + 3] > 110;
  const pad = 2, out = document.createElement('canvas');
  out.width = (tw + pad * 2) * scale; out.height = (th + pad * 2 + 1) * scale;
  const og = out.getContext('2d');
  const put = (x, y, col) => { og.fillStyle = col; og.fillRect((x + pad) * scale, (y + pad) * scale, scale, scale); };
  for (let y = -1; y <= th; y++) for (let x = -1; x <= tw; x++) {
    if (on(x, y)) continue;
    let near = false;
    for (let dy = -1; dy <= 1 && !near; dy++) for (let dx = -1; dx <= 1; dx++) if (on(x + dx, y + dy)) { near = true; break; }
    if (near) { if (shadow) put(x, y + 1, outline); put(x, y, outline); }
  }
  for (let y = 0; y < th; y++) for (let x = 0; x < tw; x++) if (on(x, y)) put(x, y, fill);
  textCache[key] = out;
  return out;
}
function drawCentered(g, img, cx, cy, s = 1, rot = 0) {
  g.save(); g.translate(cx, cy); g.rotate(rot); g.scale(s, s);
  g.drawImage(img, -img.width / 2, -img.height / 2); g.restore();
}

// ---------- pellets ----------
function pellet(g, x, y, size, color, rot = 0) {
  g.save(); g.translate(x, y); g.rotate(rot);
  const s = size, h = s * 0.8;
  g.fillStyle = shadeHex(color, 0.55); g.fillRect(-s / 2, -h / 2, s, h);
  g.fillStyle = color; g.fillRect(-s / 2 + 3, -h / 2 + 3, s - 6, h - 6);
  g.fillStyle = 'rgba(255,255,255,0.65)'; g.fillRect(-s / 2 + 5, -h / 2 + 5, s * 0.25, h * 0.25);
  g.restore();
}
