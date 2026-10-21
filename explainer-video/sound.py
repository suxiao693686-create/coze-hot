"""声音：配音做人声处理，和配乐、音效混成一条立体声音轨。

配乐两种来源：
  - 默认：music.py 按段落现场编曲（真钢琴 + 鼓 + 铺底），换场卡在节拍上
  - 脚本里写 "bgm": "某首歌.mp3"：用你自己的音乐（剪映、Suno 生成的都行），自动循环、淡入淡出、说话时压低
"""

import subprocess
import wave

import numpy as np

import assets
import music

SR = 44100
SFX = {  # 种类: (采样名, 音量)
    "boom": ("misc_cineboom", 0.75),
    "swoosh": ("perc_swoosh", 0.32),
    "pop": ("elec_pop", 0.16),
    "ping": ("elec_ping", 0.22),
}


def _ff(x, filt, ch=1):
    """用 ffmpeg 滤镜处理一段 float32 音频"""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-i", "-", "-af", filt,
         "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"],
        input=x.astype(np.float32).tobytes(), capture_output=True, check=True,
    ).stdout
    y = np.frombuffer(out, np.float32).copy()
    return y if ch == 1 else y.reshape(-1, ch).T


def process_voice(v):
    """人声：去低频轰鸣、去浑浊、提清晰度、压缩让音量稳定"""
    return _ff(v, "highpass=f=75,equalizer=f=280:t=q:w=1.2:g=-2.5,equalizer=f=3500:t=q:w=1.0:g=3,"
                  "acompressor=threshold=-22dB:ratio=3:attack=4:release=70:makeup=4dB,alimiter=limit=0.9")[: len(v)]


def load_bgm(path, total):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy()
    n = int(total * SR)
    out = np.zeros((2, n), np.float32)
    xf = min(int(1.5 * SR), x.shape[1] // 3)
    pos = 0
    while pos < n:   # 不够长就循环，接缝处交叉淡化
        start = pos - xf if pos else 0
        seg = x[:, : n - start].copy()
        if pos:
            ramp = np.linspace(0, 1, xf, dtype=np.float32)
            seg[:, :xf] *= ramp
            out[:, start:pos] *= 1 - ramp
        out[:, start: start + seg.shape[1]] += seg
        pos = start + seg.shape[1]
    t = np.arange(n) / SR
    return out * np.clip(t / 1.0, 0, 1) * np.clip((total - t) / 2.5, 0, 1)


def smooth(x, w):
    """滑动平均（用累加和算，长音频也很快）"""
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    h = w // 2
    i = np.arange(len(x))
    a, b = np.clip(i - h, 0, len(x)), np.clip(i + h, 0, len(x))
    return ((c[b] - c[a]) / np.maximum(b - a, 1)).astype(np.float32)


def rms(x):
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9)


def mix(total, voices, sfx, sections, music_mode="chill", bgm=None):
    """voices: [(开始秒, 单声道音频)]，sfx: [(开始秒, 种类)]，返回 (2, n) 立体声"""
    n = int(total * SR)
    voice = np.zeros(n, np.float32)
    for at, a in voices:
        i = int(at * SR)
        j = min(n, i + len(a))
        if j > i:
            voice[i:j] += a[: j - i]
    talking = np.abs(voice) > 0.01
    if talking.any():
        voice = process_voice(voice)
        voice *= 10 ** (-16 / 20) / rms(voice[talking])          # 说话部分的音量统一到 -16 dB
    out = np.stack([voice, voice])

    bed = None
    if bgm:
        bed = load_bgm(bgm, total)
    elif music_mode:
        bed = music.compose(total, sections, music_mode if isinstance(music_mode, str) else "chill")
    if bed is not None:
        bed = bed[:, :n]
        bed = _ff(bed.T.reshape(-1), "equalizer=f=350:t=q:w=1:g=-3", ch=2)[:, :n]   # 给人声让出中低频
        bed *= 10 ** (-28 / 20) / rms(bed)                       # 配乐整体比人声低 12 dB 左右
        env = smooth(talking.astype(np.float32), int(0.25 * SR))
        bed *= 1 - 0.3 * np.clip(env * 1.5, 0, 1)                # 说话时再压低一点
        if not talking.any():
            bed *= 10 ** (10 / 20)
        out[:, : bed.shape[1]] += bed

    for at, kind in sfx:
        name, g = SFX[kind]
        music.put(out, assets.load("sonic", name), at, g)
    peak = np.abs(out).max()
    if peak > 0.97:
        out *= 0.97 / peak
    return out


def write_wav(path, audio):
    a = audio if audio.ndim == 2 else np.stack([audio, audio])
    pcm = (np.clip(a.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
