"""声音：把配音、背景氛围音、转场音效混成一条音轨。音效全部用代码合成，没有版权问题。"""

import wave

import numpy as np

SR = 44100


def _noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def _band(x, lo, hi):
    """用 FFT 做一个简单的带通滤波"""
    f = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    f[(fr < lo) | (fr > hi)] = 0
    return np.fft.irfft(f, len(x)).astype(np.float32)


def whoosh(seed=0, dur=0.42):
    n = int(dur * SR)
    t = np.linspace(0, 1, n, dtype=np.float32)
    x = _band(_noise(n, seed), 300, 4500)
    env = np.sin(np.pi * t ** 0.6) ** 2
    x = x * env
    return x / (np.abs(x).max() + 1e-9) * 0.16


def boom(dur=0.9):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    freq = 38 + 90 * np.exp(-t * 9)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    x = np.sin(phase) * np.exp(-t * 4.2)
    click = _band(_noise(n, 3), 800, 6000) * np.exp(-t * 60) * 0.25
    x = x + click
    return (x / (np.abs(x).max() + 1e-9) * 0.5).astype(np.float32)


def tick(dur=0.09):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    x = np.sin(2 * np.pi * 1350 * t) * np.exp(-t * 55) + 0.4 * np.sin(2 * np.pi * 2700 * t) * np.exp(-t * 80)
    return (x * 0.07).astype(np.float32)


def pad(total):
    """很轻的氛围铺底：Am - F - C - G 慢慢循环"""
    n = int(total * SR)
    t = np.arange(n, dtype=np.float32) / SR
    chords = [[110.0, 164.8, 220.0, 261.6], [87.3, 130.8, 174.6, 220.0],
              [130.8, 196.0, 261.6, 329.6], [98.0, 146.8, 196.0, 246.9]]
    bar = 4.0
    out = np.zeros(n, np.float32)
    for k in range(int(total // bar) + 2):
        a, b = int(k * bar * SR), int((k + 1) * bar * SR + 1.5 * SR)
        a, b = max(0, a), min(n, b)
        if a >= n:
            break
        tt = t[a:b] - k * bar
        env = np.clip(tt / 1.2, 0, 1) * np.clip((bar + 1.5 - tt) / 1.5, 0, 1)
        seg = np.zeros(b - a, np.float32)
        for f in chords[k % 4]:
            seg += np.sin(2 * np.pi * f * tt) + 0.6 * np.sin(2 * np.pi * f * 1.003 * tt + 1.0)
            seg += 0.12 * np.sin(2 * np.pi * f * 2 * tt)
        out[a:b] += seg * env
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * t / 7.0)
    out *= lfo
    fade = np.clip(t / 2.0, 0, 1) * np.clip((total - t) / 2.5, 0, 1)
    out *= fade
    return out / (np.abs(out).max() + 1e-9) * 0.055


def place(track, clip, at):
    a = int(at * SR)
    if a >= len(track):
        return
    b = min(len(track), a + len(clip))
    track[a:b] += clip[: b - a]


def mix(total, voices, sfx, music=True):
    """voices: [(开始秒, 音频)]，sfx: [(开始秒, 种类)]"""
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    for at, a in voices:
        place(voice, a, at)
    out = voice.copy()
    if music:
        bg = pad(n / SR)
        # 说话时把背景压低
        env = np.convolve(np.abs(voice), np.ones(4410) / 4410, mode="same")
        env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
        out += bg * (1 - 0.5 * env)
    for i, (at, kind) in enumerate(sfx):
        clip = {"whoosh": lambda: whoosh(i), "boom": boom, "tick": tick}[kind]()
        place(out, clip, at)
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    return out[: int(total * SR)]


def write_wav(path, audio):
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
