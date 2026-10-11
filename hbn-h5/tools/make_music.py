"""合成一段可循环的古风背景音乐（古筝 + 箫 + 碰铃），输出 assets/bgm.mp3。

全部由代码合成，无版权问题。D 宫五声调式（D E F# A B），72 拍/分，16 小节约 53 秒。
如果想换成自己的音乐，直接替换 assets/bgm.mp3 即可（建议 128kbps 以内、1 分钟左右）。

用法：python3 tools/make_music.py   （需要 numpy、scipy、ffmpeg）
"""
import os
import subprocess

import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
BPM = 72
BEAT = 60 / BPM
BARS = 16
LOOP = BARS * 4 * BEAT
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(2024)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def zheng(midi, dur, vel=1.0, slide=False, vib=None):
    """古筝拨弦：加法合成，高次泛音衰减更快，带轻微非谐性、拨弦噪声、揉弦和按音上滑。"""
    f0 = hz(midi)
    ring = min(4.5, dur + 2.2)
    n = int(ring * SR)
    t = np.arange(n) / SR
    freq = np.full(n, f0)
    if slide:  # 按音：从大二度下方滑上来
        k = int(0.14 * SR)
        freq[:k] = f0 * 2 ** (-2 / 12 * (1 - np.sin(np.linspace(0, np.pi / 2, k))))
    if vib is None:
        vib = dur >= BEAT * 0.99
    if vib:  # 揉弦
        depth = 0.006 * np.clip((t - 0.35) / 0.4, 0, 1)
        freq = freq * (1 + depth * np.sin(2 * np.pi * 5.2 * t))
    phase = 2 * np.pi * np.cumsum(freq) / SR
    out = np.zeros(n)
    base = 1.6 + 0.012 * max(0, f0 - 200) / 10
    for h in range(1, 14):
        inharm = np.sqrt(1 + 0.00025 * h * h)
        if f0 * h * inharm > 15000:
            break
        amp = abs(np.sin(np.pi * h * 0.19)) / h ** 1.05
        decay = base * (1 + 0.55 * (h - 1))
        out += amp * np.exp(-decay * t) * np.sin(h * inharm * phase + rng.uniform(0, 6.28))
    # 拨弦瞬态
    nk = int(0.012 * SR)
    noise = rng.normal(0, 1, nk) * np.linspace(1, 0, nk) ** 2
    out[:nk] += 0.25 * noise
    attack = np.clip(t / 0.003, 0, 1)
    rel = np.clip((ring - t) / 0.3, 0, 1)
    return out * attack * rel * vel * 0.22


def xiao(midi, dur, vel=1.0):
    """箫：正弦为主 + 少量泛音 + 气声，慢起慢收，带颤音。"""
    f0 = hz(midi)
    n = int((dur + 0.35) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.005 * np.clip((t - 0.3) / 0.5, 0, 1) * np.sin(2 * np.pi * 4.8 * t)
    phase = 2 * np.pi * np.cumsum(f0 * vib) / SR
    tone = np.sin(phase) + 0.22 * np.sin(2 * phase) + 0.06 * np.sin(3 * phase)
    sos = butter(2, [f0 * 0.8, min(f0 * 4, 12000)], btype="band", fs=SR, output="sos")
    breath = sosfilt(sos, rng.normal(0, 1, n)) * 0.35
    env = np.clip(t / 0.14, 0, 1) * np.clip((dur + 0.35 - t) / 0.35, 0, 1)
    return (tone + breath) * env * vel * 0.10


def bell(midi, vel=1.0):
    """碰铃：非谐泛音的金属声。"""
    f0 = hz(midi)
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for r, a, d in [(1, 1, 1.4), (2.76, 0.5, 2.2), (5.4, 0.3, 3.5), (8.9, 0.15, 5)]:
        out += a * np.exp(-d * t) * np.sin(2 * np.pi * f0 * r * t)
    return out * np.clip(t / 0.002, 0, 1) * vel * 0.05


def place(buf, sig, start_sec, pan=0.0):
    if start_sec < 0:  # 开头之前的音（如第一小节的刮奏）放到曲尾，循环时正好接上
        start_sec += LOOP
    i = int(start_sec * SR)
    j = min(len(buf), i + len(sig))
    if j <= i:
        return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[: j - i] * l
    buf[i:j, 1] += sig[: j - i] * r


# 旋律：(小节内拍位, 时值, 音高, 是否按音上滑)
D4, E4, Fs4, A4, B4, D5, E5, Fs5, A5 = 62, 64, 66, 69, 71, 74, 76, 78, 81
MELODY = [
    [(0, 1, A4), (1, .5, B4), (1.5, .5, A4), (2, 1, Fs4), (3, 1, E4)],
    [(0, 1.5, D4), (1.5, .5, E4), (2, 2, Fs4, True)],
    [(0, 1, A4), (1, 1, D5), (2, .5, B4), (2.5, .5, A4), (3, 1, Fs4)],
    [(0, 3, E4, True)],
    [(0, 1, Fs4), (1, .5, A4), (1.5, .5, B4), (2, 1, D5), (3, 1, E5)],
    [(0, 1.5, Fs5, True), (1.5, .5, E5), (2, 1, D5), (3, 1, B4)],
    [(0, 1, A4), (1, .5, B4), (1.5, .5, A4), (2, .5, Fs4), (2.5, .5, E4), (3, 1, D4)],
    [(0, 3, D4)],
    [(0, 1, D5), (1, 1, E5), (2, 1, Fs5), (3, 1, A5)],
    [(0, 1.5, Fs5), (1.5, .5, E5), (2, 2, D5)],
    [(0, 1, B4), (1, .5, D5), (1.5, .5, B4), (2, 1, A4), (3, 1, Fs4)],
    [(0, 3, A4)],
    [(0, 1, B4), (1, .5, A4), (1.5, .5, Fs4), (2, 1, E4), (3, 1, Fs4)],
    [(0, 1.5, A4, True), (1.5, .5, B4), (2, 2, D5)],
    [(0, 1, E5), (1, .5, D5), (1.5, .5, B4), (2, 1, A4), (2.5, .5, Fs4), (3, .5, E4)],
    [(0, 4, D4)],
]
# 每小节和声根音（低音区）
ROOTS = [50, 47, 50, 45, 50, 47, 45, 50, 50, 47, 52, 45, 47, 50, 45, 50]
XIAO_BARS = range(8, 12)   # 第 9-12 小节由箫主奏


def main():
    buf = np.zeros((int((LOOP + 5) * SR), 2))
    for bar in range(BARS):
        t0 = bar * 4 * BEAT
        root = ROOTS[bar]
        # 低音
        place(buf, zheng(root - 12, 4 * BEAT, 0.45, vib=False), t0, -0.2)
        # 分解和弦：根-五-八-五，八分音符
        arp = [root, root + 7, root + 12, root + 7] * 2
        for k, m in enumerate(arp):
            v = 0.24 if k % 2 else 0.3
            place(buf, zheng(m, BEAT / 2, v, vib=False), t0 + k * BEAT / 2 + rng.uniform(0, 0.012), -0.35)
        # 旋律
        for note in MELODY[bar]:
            beat, dur, m = note[:3]
            slide = len(note) > 3 and note[3]
            start = t0 + beat * BEAT + rng.uniform(0, 0.01)
            if bar in XIAO_BARS:
                place(buf, xiao(m, dur * BEAT, 1.0), start, 0.25)
                place(buf, zheng(m - 12, dur * BEAT, 0.25), start, 0.3)
            else:
                place(buf, zheng(m, dur * BEAT, 0.95, slide=slide), start, 0.25)
        # 刮奏和碰铃，用于段落开头
        if bar in (0, 8):
            scale = [62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86]
            for k, m in enumerate(scale):
                place(buf, zheng(m, 0.4, 0.22 + 0.02 * k, vib=False), t0 - 0.45 + k * 0.04, 0.4 - k * 0.07)
            place(buf, bell(93), t0, 0.5)
        if bar in (4, 12):
            place(buf, bell(88, 0.7), t0, -0.5)

    # 混响：衰减噪声脉冲响应，两声道去相关
    ir_len = int(2.6 * SR)
    t = np.arange(ir_len) / SR
    sos = butter(1, 4500, fs=SR, output="sos")
    wet = np.zeros_like(buf)
    for ch in range(2):
        ir = sosfilt(sos, rng.normal(0, 1, ir_len)) * np.exp(-t / 0.55)
        ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        ir /= np.sqrt(np.sum(ir ** 2))
        wet[:, ch] = fftconvolve(buf[:, ch], ir)[: len(buf)]
    mix = buf * 0.8 + wet * 0.45
    mix = sosfilt(butter(2, 70, btype="high", fs=SR, output="sos"), mix, axis=0)  # 去掉低频轰鸣

    # 首尾衔接：把尾音叠回开头，保证循环无缝
    n = int(LOOP * SR)
    tail = mix[n:]
    mix = mix[:n].copy()
    mix[: len(tail)] += tail
    mix /= np.max(np.abs(mix)) / 0.85

    pcm = (mix * 32767).astype("<i2").tobytes()
    out = os.path.join(ROOT, "assets", "bgm.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-codec:a", "libmp3lame", "-b:a", "112k", out],
        input=pcm, check=True)
    print(out, f"{LOOP:.1f}s")


if __name__ == "__main__":
    main()
