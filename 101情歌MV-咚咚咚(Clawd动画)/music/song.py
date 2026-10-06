# song.py: 情歌《咚咚咚》— 作曲、作词、编曲、合成演唱，全部由代码生成。
#   python3 music/song.py            → assets/song.wav + src/song_data.js（给画面用的节拍/歌词时间表）
# 100 BPM，C 大调，一小节 2.4 秒。副歌的每个“咚”都落在底鼓上，画面里的灯、心跳、镜头冲击都读同一张时间表。
import json, math, os
import numpy as np
from scipy.signal import lfilter, fftconvolve, butter
from pypinyin import lazy_pinyin, Style

SR = 44100
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
DUR = 60.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def midi_hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def bt(bar, beat=0.0): return bar * BAR + beat * BEAT          # 小节 + 拍 → 秒
def idx(t): return int(round(t * SR))

def add(buf, sig, t, gain=1.0):
    i = idx(t)
    if i >= len(buf): return
    sig = sig[: len(buf) - i].copy()
    f = min(len(sig), idx(.004)); sig[len(sig) - f:] *= np.linspace(1, 0, f)   # 尾部淡出，避免爆音
    buf[i:i + len(sig)] += sig * gain

# ---------------------------------------------------------------- 结构 & 和声
# 0-3 前奏 | 4-11 主歌 | 12-19 副歌 | 20-23 尾声（最后一个和弦延到 60 秒）
CH = {'C': [48, 52, 55, 60, 64], 'Am': [45, 52, 57, 60, 64], 'F': [41, 53, 57, 60, 65], 'G': [43, 55, 59, 62, 67],
      'Em': [40, 52, 55, 59, 64]}
PROG = (['C', 'Am', 'F', 'G'] + ['C', 'Am', 'F', 'G'] * 2 + ['F', 'G', 'Em', 'Am', 'F', 'G', 'C', 'C'] + ['F', 'G', 'C', 'C'])
SECTION = lambda b: 'intro' if b < 4 else 'verse' if b < 12 else 'chorus' if b < 20 else 'outro'

# ---------------------------------------------------------------- 歌词 & 旋律
# 每句两小节：(起始小节, 歌词, [(拍位, 时值拍, midi), ...])
LINES = [
    (4,  '隔着一条街的窗',   [(0, .5, 64), (.5, .5, 67), (1, .5, 69), (1.5, 1, 67), (2.5, .5, 64), (3, .5, 62), (3.5, 2.5, 64)]),
    (6,  '亮着你的微光',     [(0, .5, 69), (.5, .5, 67), (1, 1, 65), (2, .5, 64), (2.5, .5, 65), (3, 3, 67)]),
    (8,  '我想说的那句话',   [(0, .5, 64), (.5, .5, 67), (1, .5, 72), (1.5, 1, 71), (2.5, .5, 69), (3, .5, 67), (3.5, 2.5, 69)]),
    (10, '卡在心跳中央',     [(0, .5, 69), (.5, .5, 69), (1, 1, 67), (2, .5, 65), (2.5, .5, 64), (3, 3, 67)]),
    (12, '咚咚咚是我的心跳', [(0, .5, 72), (1, .5, 72), (2, .5, 72), (3, .5, 69), (3.5, .5, 67), (4, .5, 69), (4.5, .5, 71), (5, 2, 74)]),
    (14, '一闪一闪向你报到', [(0, .5, 71), (.5, .5, 71), (1, .5, 67), (1.5, 1, 67), (2.5, .5, 69), (3, .5, 71), (3.5, .5, 72), (4, 3, 69)]),
    (16, '咚咚咚你听见了吗', [(0, .5, 72), (1, .5, 72), (2, .5, 72), (3, .5, 71), (3.5, .5, 69), (4, .5, 67), (4.5, .5, 69), (5, 2, 71)]),
    (18, '我喜欢你就在今晚', [(0, .5, 67), (.5, .5, 69), (1, .5, 72), (1.5, 1.5, 74), (3, .5, 76), (3.5, .5, 74), (4, .5, 74), (4.5, 3, 72)]),
    (20, '咚咚咚我喜欢你',   [(0, .5, 72), (1, .5, 72), (2, .5, 72), (4, .5, 67), (4.5, .5, 69), (5, .5, 71), (5.5, 2.5, 72)]),
]
# 字幕分句（显示用）：在哪儿断开
BREAK = {'咚咚咚是我的心跳': 3, '一闪一闪向你报到': 4, '咚咚咚你听见了吗': 3, '我喜欢你就在今晚': 4, '咚咚咚我喜欢你': 3}

# ---------------------------------------------------------------- 乐器
def env_ad(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)

def kick(vel=1.0):
    n = idx(.45); t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5) + .35 * np.sin(ph * 2) * np.exp(-t * 30)
    s[:idx(.004)] += rng.standard_normal(idx(.004)) * .3
    return np.tanh(s * 1.6) * vel

def clap():
    n = idx(.35); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    b, a = butter(2, [900 / (SR / 2), 4200 / (SR / 2)], 'band'); nz = lfilter(b, a, nz)
    e = np.zeros(n)
    for k, off in enumerate([0, .011, .022]):
        i = idx(off); e[i:] += np.exp(-(t[: n - i]) * 90) * (1 - k * .15)
    e += .55 * np.exp(-t * 14) * (t > .028)
    return nz * e * .9

def hat(open_=False):
    n = idx(.2 if open_ else .05); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    b, a = butter(2, 7000 / (SR / 2), 'high'); nz = lfilter(b, a, nz)
    return nz * np.exp(-t * (14 if open_ else 80)) * .35

def snare_hit(vel=1.0):
    n = idx(.18); t = np.arange(n) / SR
    nz = rng.standard_normal(n); b, a = butter(2, [1500 / (SR / 2), 8000 / (SR / 2)], 'band'); nz = lfilter(b, a, nz)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35)
    return (nz * np.exp(-t * 28) * .7 + tone * .4) * vel

def epiano(m, dur, vel=1.0):
    n = idx(dur + .6); t = np.arange(n) / SR; f = midi_hz(m)
    idxm = 2.2 * np.exp(-t * 6)
    s = np.sin(2 * np.pi * f * t + idxm * np.sin(2 * np.pi * f * t))
    s += .25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    e = np.minimum(1, t / .004) * np.exp(-t / .9) * np.clip((dur + .25 - t) / .25, 0, 1)
    return s * e * vel

def bell(m, vel=1.0):
    n = idx(1.6); t = np.arange(n) / SR; f = midi_hz(m)
    s = np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6) + .15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12)
    return s * np.minimum(1, t / .002) * np.exp(-t * 2.6) * vel

def saw(f, n, detune=0.0):
    ph = np.cumsum(np.full(n, f * (1 + detune)) / SR) + rng.random()
    return 2 * (ph % 1) - 1

def bass(m, dur, vel=1.0):
    n = idx(dur + .05); t = np.arange(n) / SR; f = midi_hz(m)
    s = saw(f, n) * .6 + np.sin(2 * np.pi * f * t) * .8
    b, a = butter(2, 520 / (SR / 2), 'low'); s = lfilter(b, a, s)
    e = np.minimum(1, t / .005) * (.55 + .45 * np.exp(-t * 7)) * np.clip((dur - t) / .04, 0, 1)
    return s * e * vel

def pad(notes, dur):
    n = idx(dur + .4); t = np.arange(n) / SR; s = np.zeros(n)
    for m in notes[1:]:
        for d in (-.004, .004): s += saw(midi_hz(m), n, d)
    b, a = butter(2, 1400 / (SR / 2), 'low'); s = lfilter(b, a, s)
    e = np.minimum(1, t / .35) * np.clip((dur + .4 - t) / .4, 0, 1)
    return s * e / len(notes)

# ---------------------------------------------------------------- 合成歌声（共振峰合成）
# 每个字 = 一个音符：辅音（噪声/爆破/鼻音）+ 元音轨迹（共振峰随韵母滑动）+ 颤音。
VOW = {  # F1 F2 F3 F4
    'a': (850, 1250, 2800, 3600), 'o': (520, 880, 2650, 3500), 'e': (560, 1250, 2700, 3500), 'E': (560, 1900, 2700, 3600),
    'i': (300, 2450, 3200, 3900), 'u': (330, 780, 2600, 3400), 'v': (300, 2000, 2700, 3500), 'r': (400, 1500, 2300, 3400),
    'n': (260, 1700, 2600, 3400), 'N': (280, 1100, 2600, 3400), 'm': (260, 1100, 2500, 3300), 'l': (380, 1200, 2700, 3400),
}
FINALS = {'a': 'a', 'o': 'o', 'e': 'e', 'i': 'i', 'u': 'u', 'v': 'v', 'ai': 'ai', 'ei': 'Ei', 'ao': 'au', 'ou': 'ou',
          'an': 'an', 'en': 'en', 'ang': 'aN', 'eng': 'eN', 'ong': 'uN', 'ia': 'ia', 'ie': 'iE', 'iao': 'iau', 'iu': 'iou',
          'ian': 'iEn', 'in': 'in', 'iang': 'iaN', 'ing': 'iN', 'iong': 'iuN', 'ua': 'ua', 'uo': 'uo', 'uai': 'uai',
          'ui': 'uEi', 'uan': 'uan', 'un': 'uen', 'uang': 'uaN', 've': 'vE', 'van': 'vEn', 'vn': 'vn', 'er': 'r'}
INITS = ['zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's']

def parse(py):
    ini = next((i for i in INITS if py.startswith(i)), '')
    fin = py[len(ini):]
    if not ini and py[0] in 'yw':
        fin = {'yi': 'i', 'wu': 'u', 'yu': 'v', 'yue': 've', 'yuan': 'van', 'yun': 'vn', 'you': 'iu', 'ye': 'ie', 'yin': 'in',
               'ying': 'ing', 'wei': 'ui', 'wen': 'un', 'weng': 'ong'}.get(py) or (('i' if py[0] == 'y' else 'u') + py[1:])
    if ini in ('j', 'q', 'x') and fin.startswith('u'): fin = 'v' + fin[1:]
    if fin == 'i' and ini in ('zh', 'ch', 'sh', 'r', 'z', 'c', 's'): fin = 'er'
    return ini, FINALS.get(fin, 'a')

def biquad_bp(f, bw):
    r = math.exp(-math.pi * bw / SR); th = 2 * math.pi * f / SR
    return [1 - r, 0, -(1 - r) * r], [1, -2 * r * math.cos(th), r * r]

def formant_filter(src, F, gains=(1, .55, .32, .2), block=128):
    """src 逐块通过 4 个并联共振峰滤波器；F[i] 是每块的 (F1..F4)。"""
    out = np.zeros_like(src); zi = [np.zeros(2) for _ in range(4)]
    for bi in range(0, len(src), block):
        seg = src[bi:bi + block]; f = F[min(bi // block, len(F) - 1)]
        for k in range(4):
            b, a = biquad_bp(f[k], [80, 110, 160, 220][k])
            y, zi[k] = lfilter(b, a, seg, zi=zi[k]); out[bi:bi + block] += y * gains[k]
    return out

def sing(ch, m, dur, prev_m=None):
    ini, traj = parse(lazy_pinyin(ch, style=Style.NORMAL)[0])
    cons = {'': 0, 'b': .03, 'd': .03, 'g': .035, 'p': .06, 't': .06, 'k': .065, 'm': .06, 'n': .055, 'l': .05,
            'f': .07, 'h': .06, 's': .09, 'sh': .09, 'x': .09, 'z': .06, 'zh': .07, 'j': .06, 'c': .09, 'ch': .09, 'q': .09, 'r': .05}[ini]
    n = idx(dur); nc = idx(cons); nv = n - nc
    t = np.arange(n) / SR
    # pitch: 滑音 + 渐入颤音
    f0 = np.full(n, midi_hz(m))
    if prev_m is not None and prev_m != m:
        g = np.clip(t / .07, 0, 1); f0 = midi_hz(prev_m) * (1 - g) + f0 * g
    vib = 1 + .012 * np.sin(2 * np.pi * 5.6 * t) * np.clip((t - .18) / .25, 0, 1)
    ph = np.cumsum(f0 * vib) / SR
    src = (2 * (ph % 1) - 1) * .6 + np.sin(2 * np.pi * ph) * .5            # 声门源
    src = lfilter([1], [1, -.75], src) * .25 + rng.standard_normal(n) * .025   # 柔化 + 气声
    # 元音轨迹：介音快、主元音长、韵尾在最后 25%
    vs = list(traj)
    keys = [VOW[v] for v in vs]
    if len(keys) == 1: pos = [0.0]
    elif len(keys) == 2 and vs[0] in 'iuv': pos = [0, .18]
    elif len(keys) == 2: pos = [0, .72]
    else: pos = [0, .16, .75]
    nb = (n + 127) // 128; F = np.zeros((nb, 4))
    for bi in range(nb):
        s = bi * 128; x = 0 if s < nc else (s - nc) / max(1, nv)
        k = max(i for i, p in enumerate(pos) if p <= x)
        if k + 1 < len(keys):
            g = min(1, (x - pos[k]) / .12); F[bi] = np.array(keys[k]) * (1 - g) + np.array(keys[k + 1]) * g
        else: F[bi] = keys[k]
        if s < nc and ini in ('m', 'n', 'l'): F[bi] = VOW[ini]
    voiced = formant_filter(src, F)
    # 声门包络
    amp = np.ones(n)
    if ini in ('p', 't', 'k', 'f', 'h', 's', 'sh', 'x', 'c', 'ch', 'q', 'z', 'zh', 'j'): amp[:nc] = 0
    elif ini in ('b', 'd', 'g'): amp[:nc] = np.linspace(0, .3, nc)
    elif ini in ('m', 'n', 'l', 'r'): amp[:nc] = .45
    rel = min(idx(.06), n // 3); amp[-rel:] *= np.linspace(1, 0, rel)
    att = idx(.012); amp[nc:nc + att] *= np.linspace(0, 1, min(att, n - nc))
    if traj[-1] in 'nN': amp[int(n * .8):] *= .7
    y = voiced * amp
    # 辅音噪声
    if nc:
        nz = rng.standard_normal(nc)
        band = {'s': (5000, 10000), 'c': (5000, 10000), 'z': (4500, 9000), 'sh': (2500, 6500), 'ch': (2500, 6500), 'zh': (2500, 6500),
                'x': (3500, 8000), 'q': (3500, 8000), 'j': (3500, 8000), 'f': (1500, 8000), 'h': (600, 3000), 'r': (2000, 5000),
                'p': (500, 4000), 't': (2500, 7000), 'k': (1200, 4000), 'b': (300, 2500), 'd': (2000, 6000), 'g': (900, 3000)}.get(ini)
        if band:
            b, a = butter(2, [band[0] / (SR / 2), min(band[1], 20000) / (SR / 2)], 'band'); nz = lfilter(b, a, nz)
            te = np.arange(nc) / SR
            if ini in ('b', 'd', 'g', 'p', 't', 'k'): e = np.exp(-te * 120) * (2.2 if ini in 'ptk' else 1.2) + (np.exp(-te * 30) * .35 if ini in 'ptk' else 0)
            else: e = np.sin(np.pi * np.clip(te / cons, 0, 1)) * (.9 if ini in ('s', 'c', 'x', 'q', 'sh', 'ch') else .5)
            y[:nc] += nz * e * .35
    return y

# ---------------------------------------------------------------- 编曲
drums = np.zeros(N); keys = np.zeros(N); bassb = np.zeros(N); padb = np.zeros(N); box = np.zeros(N); voc = np.zeros(N); lead = np.zeros(N); fx = np.zeros(N)
KICKS, CLAPS = [], []

for b in range(24):
    sec, chord = SECTION(b), CH[PROG[b]]
    t0 = bt(b)
    # --- 鼓：前奏/主歌是“咚-咚”心跳（拍1+后半拍），副歌四拍底鼓
    if sec == 'chorus':
        kb = [0, 1, 2, 3]
    elif sec == 'intro':
        kb = [] if b < 2 else [0, .5]
    elif sec == 'outro':
        kb = [0, .5, 2, 2.5] if b < 23 else [0, .5]
    else:
        kb = [0, .5, 2, 2.5]
    for k in kb:
        vel = 1.0 if k in (0, 2) else .78 if sec != 'chorus' else .95
        add(drums, kick(vel), bt(b, k)); KICKS.append(round(bt(b, k), 4))
    if sec in ('verse', 'chorus') or (sec == 'outro' and b < 22):
        for k in (1, 3):
            add(drums, clap(), bt(b, k), .8 if sec == 'chorus' else .6); CLAPS.append(round(bt(b, k), 4))
    if sec == 'verse':
        for e in range(8): add(drums, hat(), bt(b, e * .5), .55 if e % 2 else .3)
    if sec == 'chorus':
        for e in range(16): add(drums, hat(), bt(b, e * .25), .5 if e % 2 else .3)
        for e in range(4): add(drums, hat(True), bt(b, e + .5), .45)
    if b == 11:   # 进副歌前的军鼓滚奏 + 噪声上扬
        for e in range(16): add(drums, snare_hit(.25 + .75 * e / 15), bt(b, e * .25), .7)
        n = idx(BAR); tt = np.arange(n) / SR; nz = rng.standard_normal(n)
        bb, aa = butter(2, 3000 / (SR / 2), 'high'); add(fx, lfilter(bb, aa, nz) * (tt / BAR) ** 2 * .35, t0)
    if b in (12, 20):   # 段落落点：反向吸气 + 镲
        n = idx(.9); tt = np.arange(n) / SR; nz = rng.standard_normal(n); bb, aa = butter(2, 5000 / (SR / 2), 'high')
        add(fx, lfilter(bb, aa, nz) * np.exp(-tt * 3) * .5, t0)
    # --- 贝斯
    root = chord[0] - 12 + (12 if chord[0] < 43 else 0)
    if sec == 'chorus':
        for e in range(8): add(bassb, bass(root + (12 if e % 4 == 3 else 0), BEAT * .45), bt(b, e * .5), .9)
    elif sec == 'verse' or (sec == 'outro' and b < 23) or (sec == 'intro' and b >= 2):
        for k, d in ((0, .9), (1.5, .4), (2, .9), (3.5, .4)): add(bassb, bass(root, BEAT * d), bt(b, k), .85)
    elif sec == 'outro':
        add(bassb, bass(root, BAR * 1.6), t0, .8)
    # --- 电钢琴和弦
    vo = chord[1:]
    if sec == 'chorus':
        for e in range(8):
            if e % 2: [add(keys, epiano(m, BEAT * .4, .5), bt(b, e * .5)) for m in vo]
        [add(keys, epiano(m, BEAT * 1.5, .35), t0) for m in vo]
    elif sec == 'verse':
        for k, d in ((0, 1.4), (1.5, .4), (2.5, 1.4)): [add(keys, epiano(m, BEAT * d, .45), bt(b, k)) for m in vo]
    elif sec == 'outro':
        [add(keys, epiano(m, BAR * (2.4 if b == 23 else 1), .4), t0) for m in vo]
    add(padb, pad(chord, BAR * (2.4 if b == 23 else 1)), t0, .5 if sec != 'chorus' else .7)
    # --- 八音盒（前奏、尾声）：分解和弦
    if sec in ('intro', 'outro'):
        arp = [chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[4] + 12, chord[3] + 12, chord[2] + 12, chord[3] + 12, chord[4] + 12]
        for e, m in enumerate(arp if b < 23 else arp[:1]): add(box, bell(m, .55), bt(b, e * .5))
    if sec == 'chorus':
        for e, m in enumerate([chord[4] + 12, chord[3] + 12]): add(box, bell(m, .25), bt(b, e * 2 + 1.5))

# --- 人声
LYRICS = []
prev = None
for bar, text, notes in LINES:
    syl = []
    for ch, (b, d, m) in zip(text, notes):
        t = bt(bar, b); dur = d * BEAT * .96
        add(voc, sing(ch, m, dur, prev), t)
        n = idx(dur); tt = np.arange(n) / SR
        add(lead, np.sin(2 * np.pi * midi_hz(m + 12) * tt) * np.minimum(1, tt / .01) * np.exp(-tt * 2.5), t, .12)
        syl.append({'ch': ch, 't': round(t, 4), 'd': round(d * BEAT, 4)})
        prev = m
    LYRICS.append({'text': text, 'bar': bar, 'start': round(bt(bar), 4), 'end': round(bt(bar + 2), 4), 'brk': BREAK.get(text, 0), 'syl': syl})
    prev = None

# ---------------------------------------------------------------- 混音
def reverb(x, secs=1.8, wet=.25):
    n = idx(secs); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 3.2 / secs * 2)
    b, a = butter(1, 5000 / (SR / 2), 'low'); ir = lfilter(b, a, ir); ir /= np.sqrt(np.sum(ir ** 2))
    return fftconvolve(x, ir)[:len(x)] * wet

# 侧链：底鼓压低和弦/贝斯/铺底，制造“心跳”泵感
duck = np.ones(N)
for k in KICKS:
    i = idx(k); n = min(idx(.35), N - i); tt = np.arange(n) / SR
    duck[i:i + n] = np.minimum(duck[i:i + n], 1 - .55 * np.exp(-tt * 12))
sung = np.abs(voc) > 1e-4
voc_mix = voc * (.21 / np.sqrt(np.mean(voc[sung] ** 2)))          # 人声放到伴奏前面：唱的部分 RMS ≈ 底鼓轨的水平
music = drums * .85 + bassb * .55 * duck + keys * .13 * duck + padb * .16 * duck + box * .22 + fx * .5 + lead
wetbus = reverb(voc_mix * .45 + keys * .1 + box * .25)
L = music + voc_mix + wetbus
R = music + voc_mix + reverb(voc_mix * .45 + keys * .1 + box * .25)
st = np.stack([L + box * .05 - keys * .03, R - box * .05 + keys * .03], 1)
fade = np.clip((DUR - np.arange(N) / SR) / 2.0, 0, 1)[:, None]
st *= fade
# 主总线：按 RMS 定响度，再用 tanh 软限幅压住辅音/底鼓的尖峰
st = st / np.sqrt(np.mean(st[:idx(56)] ** 2)) * .2
st = np.tanh(st * 1.15) * .92
os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
import wave
if os.environ.get('STEMS'):
    for nm, x in (('voc', voc), ('drums', drums), ('keys', keys)):
        with wave.open(os.path.join(HERE, nm + '.wav'), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x / np.max(np.abs(x)) * 30000).astype('<i2').tobytes())
with wave.open(os.path.join(ROOT, 'assets', 'song.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())

import subprocess   # 同时导出一份 mp3（提交到仓库的是它）
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(ROOT, 'assets', 'song.wav'), '-b:a', '192k', os.path.join(ROOT, 'assets', 'song.mp3')], check=False)
data = {'bpm': BPM, 'beat': BEAT, 'bar': BAR, 'duration': DUR, 'kicks': KICKS, 'claps': CLAPS, 'lyrics': LYRICS,
        'sections': [[0, 'intro'], [bt(4), 'verse'], [bt(12), 'chorus'], [bt(20), 'outro']]}
with open(os.path.join(ROOT, 'src', 'song_data.js'), 'w', encoding='utf-8') as f:
    f.write('// 由 music/song.py 生成：歌曲的节拍、底鼓、拍手和逐字歌词时间。画面全部从这里取时间，所以声画严格同步。\n')
    f.write('const SONG = ' + json.dumps(data, ensure_ascii=False) + ';\n')
print('kicks', len(KICKS), 'lines', len(LYRICS), 'peak ok')
