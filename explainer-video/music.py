"""配乐：真钢琴采样 + 鼓采样 + 合成铺底和贝斯，按视频的"钩子 / 解释 / 结尾"编曲。

- 钩子：电影感重低音开场，钢琴零星几个音，结尾一个反向镲把人"吸"进正文
- 解释：鼓和贝斯进来，lofi 律动，钢琴分解和弦 + 小旋律
- 结尾：鼓停、镲一响，只留钢琴和铺底，最后一个长和弦收尾
整首曲子的小节线对齐"解释"开始的那一拍，换场都落在节拍上。
"""

import numpy as np
from scipy import signal as sg

import assets

SR = 44100

MOODS = {
    # 名称: (BPM, 和弦[(贝斯, [钢琴和弦音])], 旋律音阶)
    "chill": (88, [(41, [53, 57, 60, 64]), (40, [52, 55, 59, 62]), (38, [50, 53, 57, 60]), (36, [52, 55, 59, 60])],
              [72, 74, 76, 79, 81]),
    "tension": (92, [(45, [57, 60, 64]), (41, [57, 60, 65]), (38, [57, 62, 65]), (40, [56, 59, 64])],
                [69, 72, 74, 76, 79]),
    "uplift": (100, [(36, [55, 60, 64]), (43, [55, 59, 62]), (45, [57, 60, 64]), (41, [57, 60, 65])],
               [72, 74, 76, 79, 81]),
}


def bpm_of(mood):
    return MOODS.get(mood, MOODS["chill"])[0]


# ---------------- 乐器 ----------------

_piano_map = None


def _piano_samples():
    global _piano_map
    if _piano_map is None:
        names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
        _piano_map = {}
        for p in assets.ensure("piano").glob("*.mp3"):
            stem = p.stem.replace("v8", "")
            pitch, octv = stem[:-1], int(stem[-1])
            _piano_map[12 * (octv + 1) + names[pitch]] = p.stem
    return _piano_map


def piano(note, dur, vel=0.5):
    m = _piano_samples()
    root = min(m, key=lambda k: abs(k - note))
    x = assets.load("piano", m[root])
    ratio = 2 ** ((note - root) / 12)
    n = int((dur + 1.0) * SR)
    pos = np.arange(n) * ratio
    pos = pos[pos < x.shape[1] - 1]
    y = np.stack([np.interp(pos, np.arange(x.shape[1]), x[c]) for c in range(2)]).astype(np.float32)
    t = np.arange(y.shape[1]) / SR
    env = np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.22))
    return y * env * vel


def _saw(f, t, phase=0.0):
    return 2 * ((f * t + phase) % 1.0) - 1


def pad(notes, dur, bright=1400):
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n), np.float32)
    for note in notes:
        f = 440 * 2 ** ((note - 69) / 12)
        for ch, det in ((0, -0.006), (1, 0.006)):
            out[ch] += _saw(f * (1 + det), t, 0.13 * ch) + _saw(f * (1 - det * 0.6), t, 0.41) * 0.7
    sos = sg.butter(4, bright, "low", fs=SR, output="sos")
    out = sg.sosfilt(sos, out, axis=1).astype(np.float32)
    env = np.clip(t / 0.9, 0, 1) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.5))
    return out * env / (len(notes) * 2.4)


def bass(note, dur):
    f = 440 * 2 ** ((note - 69) / 12)
    n = int((dur + 0.2) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.18 * np.sin(6 * np.pi * f * t)
    env = np.minimum(t / 0.006, 1) * (0.55 + 0.45 * np.exp(-t / 0.25)) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.06))
    return (x * env * 0.5).astype(np.float32)


def smp(name, rev=False):
    x = assets.load("sonic", name)
    return x[:, ::-1].copy() if rev else x


# ---------------- 混音小工具 ----------------

def put(buf, clip, at, gain=1.0, pan=0.0):
    a = int(round(at * SR))
    if clip.ndim == 1:
        clip = np.stack([clip * (1 - max(0, pan)), clip * (1 + min(0, pan))])
    if a < 0:
        clip, a = clip[:, -a:], 0
    b = min(buf.shape[1], a + clip.shape[1])
    if b > a:
        buf[:, a:b] += clip[:, : b - a] * gain


def reverb(x, seconds=2.4, wet=0.3):
    n = int(seconds * SR)
    rng = np.random.default_rng(7)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)).astype(np.float32) * np.exp(-6.9 * t / seconds)
    ir = sg.sosfilt(sg.butter(2, 5000, "low", fs=SR, output="sos"), ir, axis=1)
    ir[:, : int(0.015 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    wetsig = np.stack([sg.fftconvolve(x[c], ir[c])[: x.shape[1]] for c in range(2)])
    return x + wetsig.astype(np.float32) * wet


# ---------------- 编曲 ----------------

def compose(total, sections, mood="chill"):
    """sections: [(名字, 开始, 结束)]，按"钩子 / 解释 / 结尾"排"""
    bpm, prog, scale = MOODS.get(mood, MOODS["chill"])
    beat = 60 / bpm
    bar = 4 * beat
    n = int((total + 3) * SR)
    keys, pads, drums, low = (np.zeros((2, n), np.float32) for _ in range(4))
    rng = np.random.default_rng(11)

    sec = {name: (a, b) for name, a, b in sections}
    hook_end = sec.get("钩子", (0, 0))[1]
    end_start = sec.get("结尾", (total, total))[0]
    origin = hook_end                       # 小节线对齐"解释"开始
    first_bar = -int(np.ceil(origin / bar))
    last_bar = int(np.ceil((total - origin) / bar))

    for k in range(first_bar, last_bar + 1):
        t0 = origin + k * bar
        if t0 >= total:
            break
        root, chord = prog[k % len(prog)]
        chord = [c + 12 for c in chord]
        part = "hook" if t0 < hook_end - 1e-6 else ("end" if t0 >= end_start - 1e-6 else "body")
        # 铺底：全程都有，开头和结尾更亮一点
        put(pads, pad(chord[:3], bar, 2600 if part == "body" else 3200), t0, 0.5)
        # 钢琴
        if part == "hook":
            for i, c in enumerate(chord):
                put(keys, piano(c, bar * 0.9, 0.22), t0 + i * 0.03)
            put(keys, piano(scale[k % len(scale)] + 12, beat * 2, 0.16), t0 + beat * 2, pan=0.2)
        else:
            vel = 0.4 if part == "body" else 0.34
            for i, c in enumerate(chord):
                put(keys, piano(c, bar * 0.8, vel), t0 + i * 0.035)
            for c in chord[-2:]:
                put(keys, piano(c, beat, vel * 0.55), t0 + 2.5 * beat)
            # 小旋律：每两小节一句，音从和弦音附近挑
            if k % 2 == 0:
                for pos in (1.0, 1.5, 3.0):
                    note = scale[int(rng.integers(0, len(scale)))]
                    put(keys, piano(note, beat * 0.9, vel * 0.5), t0 + pos * beat, pan=0.25)
        # 贝斯和鼓只在正文
        if part == "body":
            put(low, bass(root + 12, beat * 1.6), t0)
            put(low, bass(root + 12, beat * 0.8), t0 + 2.5 * beat)
            put(low, bass(root + 19 if root + 19 < 60 else root + 7, beat * 0.5), t0 + 3.5 * beat)
            for pos in (0, 2.5):
                put(drums, smp("bd_pure"), t0 + pos * beat, 0.4)
                put(drums, smp("bd_fat"), t0 + pos * beat, 0.45)
            for pos in (1, 3):
                put(drums, smp("drum_snare_soft"), t0 + pos * beat, 0.8)
                put(drums, smp("perc_snap"), t0 + pos * beat + 0.01, 0.12, pan=-0.2)
            for i in range(8):
                swing = 0.09 * beat if i % 2 else 0
                put(drums, smp("drum_cymbal_closed"), t0 + i * beat / 2 + swing, 0.5 if i % 2 else 0.7, pan=0.3)

    # 钩子开场：低音钢琴（重低音在音效里）
    put(keys, piano(prog[0][0] + 12, bar * 1.5, 0.35), 0)
    put(keys, piano(prog[0][0] + 24, bar * 1.5, 0.35), 0)
    put(keys, piano(prog[0][0] + 36, bar * 1.5, 0.25), 0.02)
    # 进入正文前一个反向镲，正文第一拍落一个镲
    rc = smp("drum_cymbal_open", rev=True)
    put(drums, rc, hook_end - rc.shape[1] / SR, 0.45)
    put(drums, smp("drum_splash_soft"), hook_end, 0.35)
    # 进入结尾：鼓停，镲一响
    if end_start < total:
        put(drums, smp("drum_splash_soft"), end_start, 0.45)
        put(drums, smp("ambi_swoosh"), end_start - 0.9, 0.3)

    # 侧链：底鼓一响，铺底和贝斯让一让
    kick_env = np.zeros(n, np.float32)
    for k in range(first_bar, last_bar + 1):
        t0 = origin + k * bar
        if hook_end <= t0 < end_start:
            for pos in (0, 2.5):
                a = int((t0 + pos * beat) * SR)
                L = int(0.25 * SR)
                if 0 <= a < n:
                    seg = np.exp(-np.arange(min(L, n - a)) / (0.08 * SR))
                    kick_env[a:a + len(seg)] = np.maximum(kick_env[a:a + len(seg)], seg)
    duck = 1 - 0.45 * kick_env
    pads *= duck
    low *= duck

    keys = reverb(keys, 2.6, 0.32)
    pads = reverb(pads, 3.0, 0.35)
    drums = reverb(drums, 1.2, 0.08)
    low = sg.sosfilt(sg.butter(2, 300, "low", fs=SR, output="sos"), low, axis=1).astype(np.float32)
    mix = keys * 1.0 + pads * 0.7 + drums * 0.6 + low * 0.35
    mix = sg.sosfilt(sg.butter(2, 45, "high", fs=SR, output="sos"), mix, axis=1).astype(np.float32)
    mix = np.tanh(mix * 1.2) / 1.2
    t = np.arange(n) / SR
    mix *= np.clip((total + 0.2 - t) / 2.5, 0, 1)
    return mix[:, : int(total * SR)]
