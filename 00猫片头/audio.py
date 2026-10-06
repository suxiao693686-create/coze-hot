"""合成片头的背景音乐 + 音效，并混入配音。
用法: python3 audio.py 开模.wav 标题.wav 输出.wav
节拍: 150 BPM，一拍 0.4 秒，从 0.05 秒起算；开模 2.05 秒正好落在拍子上。"""
import os, sys, wave
import numpy as np

SR = 44100
DUR = 6.2
T_OPEN, T_WIPE, T_SWAP = 2.05, 4.75, 5.05
BEAT, E8, E16 = 0.4, 0.2, 0.1
rng = np.random.default_rng(3)
mix = np.zeros(int(SR * DUR) + SR)    # 音效
music = np.zeros_like(mix)            # 音乐（会被配音压低）

def add(buf, sig, t, gain=1.0):
    i = int(t * SR); n = min(len(sig), len(buf) - i)
    if n > 0: buf[i:i + n] += sig[:n] * gain

def tt(d): return np.arange(int(d * SR)) / SR
def env(d, a=0.004, r=None):
    t = tt(d); r = r or d
    return np.minimum(1, t / a) * np.exp(-t / (r / 4))
def freq(note):
    names = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    return 440 * 2 ** ((names[note[0]] + 12 * (int(note[-1]) + 1) - 69) / 12)
def sweep(f0, f1, d): return 2 * np.pi * np.geomspace(f0, f1, int(d * SR)).cumsum() / SR
def square(f, d, duty=0.25, vib=0.0):
    t = tt(d); ph = (t * f + vib * np.sin(2 * np.pi * 6 * t) * np.minimum(1, t / 0.15)) % 1
    return np.where(ph < duty, 1.0, -1.0)
def tri(f, d): p = (tt(d) * f) % 1; return 4 * np.abs(p - 0.5) - 1
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def onepole(x, k):
    from scipy.signal import lfilter
    return lfilter([k], [1, k - 1], x)
def hp(x, k): return x - onepole(x, k)

# ---------- 乐器 ----------
def kick():  return np.sin(sweep(160, 42, 0.18)) * env(0.18, 0.001, 0.25)
def clap():
    s = np.zeros(int(0.16 * SR))
    for k, o in enumerate((0, 0.008, 0.016)):
        b = hp(noise(0.14), 0.3) * env(0.14, 0.001, 0.08 if k < 2 else 0.2); s[int(o * SR):int(o * SR) + len(b)] += b
    return s
def hat(open_=False): d = 0.12 if open_ else 0.03; return hp(noise(d), 0.7) * env(d, 0.001)
def crash(): return hp(noise(1.4), 0.6) * env(1.4, 0.001, 1.6)
def boom():  return np.sin(sweep(90, 30, 0.9)) * env(0.9, 0.002, 1.0)
def pop():   return np.sin(sweep(500, 1400, 0.07)) * env(0.07, 0.001)
def whoosh(d, up=True):
    n = noise(d); lo = onepole(n, 0.02 if up else 0.5); hi = onepole(n, 0.5 if up else 0.02)
    k = np.linspace(0, 1, len(n)); x = lo * (1 - k) + hi * k
    return hp(x, 0.05) * np.sin(np.pi * k) ** 1.5
def click():
    d = 0.012; return np.sin(2 * np.pi * rng.uniform(2500, 5000) * tt(d)) * env(d, 0.0005, 0.012)
def lead(n, d, g=1.0):  # 明亮的主旋律（两层方波 + 颤音）
    return (square(freq(n), d, 0.25, vib=0.15) * 0.8 + square(freq(n) * 2, d, 0.5) * 0.25) * env(d, 0.003, d * 2.5) * g
def pluck(n, d): return square(freq(n), d, 0.125) * env(d, 0.002, 0.12)

# ---------- A 段 0 ~ 2.05：俏皮踮脚走 ----------
sneak = ['G4', None, 'C5', None, 'E5', 'D5', 'C5', None, 'G4', None, 'C5', 'E5']   # 八分音符
for i, n in enumerate(sneak):
    t = 0.05 + i * E8
    if n: add(music, pluck(n, 0.16), t, 0.22)
    add(music, tri(freq('C3') if (i // 2) % 2 == 0 else freq('G2'), 0.1) * env(0.1), t, 0.4 if i % 2 == 0 else 0.0)
    add(music, hat(), t + E16, 0.08)
    if i % 4 == 2: add(music, clap(), t, 0.15)
# 舔爪子“啵啵”
for k in range(4): add(mix, np.sin(sweep(800, 1500, 0.05)) * env(0.05), 0.3 + k * 2 / 7, 0.14)
# “！” 弹出
add(mix, pop(), 1.0, 0.3)
add(mix, square(freq('E6'), 0.08, 0.5) * env(0.08), 1.05, 0.08); add(mix, square(freq('A6'), 0.1, 0.5) * env(0.1), 1.11, 0.08)
# 起跳 boing
add(mix, np.sign(np.sin(sweep(250, 950, 0.2))) * env(0.2), 1.45, 0.12)
# 链条哗啦 + 抓住
for t in (1.65, 1.78, 1.9):
    d = 0.22; s = sum(np.sin(2 * np.pi * f * tt(d)) for f in (1180, 1730, 2540, 3390)) / 4
    add(mix, s * env(d, 0.001, 0.2), t, 0.25)
# 1.45 ~ 2.05 蓄力：升调 + 军鼓加花
add(mix, whoosh(0.6, True), 1.45, 0.25)
add(music, square(1, 0.6) * 0 + np.sign(np.sin(sweep(200, 800, 0.6))) * np.linspace(0, 1, int(0.6 * SR)) ** 2, 1.45, 0.06)
for k in range(6): add(music, clap(), 1.45 + k * E16, 0.08 + k * 0.03)

# ---------- 开模：重低音 + 镲 + 液压 + 粒子 ----------
add(mix, boom(), T_OPEN, 1.0)
add(mix, onepole(noise(0.12), 0.3) * env(0.12, 0.001), T_OPEN, 0.6)
add(mix, crash(), T_OPEN, 0.25)
add(mix, hp(onepole(noise(0.8), 0.5), 0.05) * np.sin(np.pi * tt(0.8) / 0.8) ** 2, T_OPEN + 0.02, 0.35)
for _ in range(80): add(mix, click(), T_OPEN + 0.05 + rng.uniform(0, 0.9) ** 1.6, rng.uniform(0.1, 0.3))

# ---------- B 段 2.05 ~ 5.05：欢快主歌 ----------
chords = [('C3', ['C4', 'E4', 'G4']), ('G2', ['B3', 'D4', 'G4']), ('A2', ['C4', 'E4', 'A4']), ('F2', ['C4', 'F4', 'A4'])]
hook = ['E5', None, 'G5', 'C6', None, 'G5', 'A5', 'G5',
        'D5', None, 'G5', 'B5', None, 'D6', 'B5', 'G5',
        'C5', None, 'E5', 'A5', None, 'C6', 'B5', 'A5',
        'F5', 'A5', 'C6', None, 'D6', None, 'E6', None]
n8 = int(round((T_SWAP - T_OPEN) / E8))
for i in range(n8):
    t = T_OPEN + i * E8
    bass, triad = chords[(i // 8) % 4]
    if hook[i % 32]: add(music, lead(hook[i % 32], E8 * 0.95), t, 0.11)
    add(music, tri(freq(bass) * (2 if i % 2 else 1), E8 * 0.9) * env(E8 * 0.9, 0.003, 0.6), t, 0.38)
    if i % 2 == 1:   # 反拍和弦“嚓”
        for n in triad: add(music, square(freq(n) * 2, 0.08, 0.5) * env(0.08), t, 0.035)
    if i % 2 == 0: add(music, kick(), t, 0.7)
    if i % 4 == 2: add(music, clap(), t, 0.3)
    add(music, hat(open_=(i % 2 == 1)), t + (0 if i % 2 else E16), 0.07)
# 标题三连击：00猫(2.45) 弹出、蓝条(2.65) 飞入、开课啦(2.85) 盖章
add(mix, pop(), 2.45, 0.35)
for k, n in enumerate(['C6', 'E6', 'G6', 'C7']): add(mix, square(freq(n), 0.12, 0.5) * env(0.12), 2.45 + k * 0.035, 0.07)
add(mix, whoosh(0.22, True), 2.55, 0.5)
add(mix, boom()[:int(0.4 * SR)], 2.85, 0.8)
add(mix, onepole(noise(0.2), 0.4) * env(0.2, 0.001), 2.85, 0.6)
add(mix, crash(), 2.85, 0.18)
for _ in range(30): add(mix, click(), rng.uniform(2.8, 4.7), rng.uniform(0.04, 0.1))

# ---------- 转场：粒子倾泻 ----------
add(mix, whoosh(0.5, True), T_WIPE - 0.2, 0.35)
pour = hp(onepole(noise(0.75), 0.6), 0.08)
add(mix, pour * np.sin(np.pi * tt(0.75) / 0.75), T_WIPE, 0.35)
for _ in range(170): add(mix, click(), T_WIPE + rng.uniform(0, 0.7), rng.uniform(0.08, 0.25))

# ---------- C 段：叮～ 收尾 ----------
add(music, kick(), T_SWAP + 0.2, 0.8)
add(music, crash(), T_SWAP + 0.2, 0.15)
for k, n in enumerate(['C5', 'E5', 'G5', 'C6']):
    add(music, lead(n, 0.9 - k * 0.05, 0.9), T_SWAP + 0.2 + k * 0.05, 0.08)
add(music, tri(freq('C3'), 1.0) * env(1.0, 0.003, 1.5), T_SWAP + 0.2, 0.4)
for k, n in enumerate(['G6', 'C7']): add(mix, np.sin(2 * np.pi * freq(n) * tt(0.6)) * env(0.6, 0.002, 0.8), T_SWAP + 0.6 + k * 0.08, 0.12)

# ---------- 配音（音乐自动让路）----------
def load(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR, w.getframerate()
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
voice = np.zeros_like(mix)
for path, t in ((sys.argv[1], 1.45), (sys.argv[2], 2.45)):
    v = load(path); v = v / np.max(np.abs(v)) * 0.75
    i0 = int(t * SR); voice[i0:i0 + len(v)] += v[:len(voice) - i0]
NO_VOICE = os.environ.get('NO_VOICE') == '1'   # 只要音乐+音效，不要人声
if NO_VOICE: voice[:] = 0
duck = onepole((np.abs(voice) > 0.01).astype(float), 0.0008)
duck = np.clip(duck * 3, 0, 1)
out = 0.45 * music * (1 - 0.75 * duck) + mix * (1 - 0.7 * duck) + voice * 1.8
out = out[:int(SR * DUR)]
fade = int(0.3 * SR); out[-fade:] *= np.linspace(1, 0, fade)
out = np.tanh(out / np.max(np.abs(out)) * 0.8) / np.tanh(0.8) * 0.9   # 轻微饱和，听着更饱满
if NO_VOICE: out *= 0.55   # 给后配的人声留出音量空间
with wave.open(sys.argv[3], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print('wrote', sys.argv[3])
