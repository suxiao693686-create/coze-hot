"""正片的配音 + 背景音乐 + 音效混音。
用法: python3 audio_lesson.py 配音文件夹(44.1k) 音效时间点.json 输出.wav"""
import json, os, sys, wave
import numpy as np
from scipy.signal import lfilter

SR = 44100
here = os.path.dirname(os.path.abspath(__file__))
TL = json.loads(open(os.path.join(here, 'timeline.js')).read().split('=', 1)[1].strip().rstrip(';'))
voice_dir, cues_path, out_path = sys.argv[1:4]
DUR = TL['total']
N = int(DUR * SR) + SR
music, sfx, voice = np.zeros(N), np.zeros(N), np.zeros(N)
rng = np.random.default_rng(1)

def add(buf, sig, t, gain=1.0):
    i = int(t * SR); n = min(len(sig), len(buf) - i)
    if n > 0 and i >= 0: buf[i:i + n] += sig[:n] * gain
def tt(d): return np.arange(int(d * SR)) / SR
def env(d, a=0.004, r=None):
    t = tt(d); r = r or d
    return np.minimum(1, t / a) * np.exp(-t / (r / 4))
def freq(n):
    names = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    return 440 * 2 ** ((names[n[0]] + 12 * (int(n[-1]) + 1) - 69) / 12)
def sweep(f0, f1, d): return 2 * np.pi * np.geomspace(f0, f1, int(d * SR)).cumsum() / SR
def sq(f, d, duty=0.25): return np.where((tt(d) * f) % 1 < duty, 1.0, -1.0)
def tri(f, d): p = (tt(d) * f) % 1; return 4 * np.abs(p - 0.5) - 1
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def lp(x, k): return lfilter([k], [1, k - 1], x)
def hp(x, k): return x - lp(x, k)
def mixs(*xs):   # 不同长度的声音相加
    out = np.zeros(max(len(x) for x in xs))
    for x in xs: out[:len(x)] += x
    return out

# ---------- 背景音乐：轻快循环（112 BPM），只做伴奏不抢人声 ----------
BEAT = 60 / 112; E8 = BEAT / 2
prog = [('C3', ['C5', 'E5', 'G5', 'E5']), ('A2', ['C5', 'E5', 'A5', 'E5']), ('F2', ['C5', 'F5', 'A5', 'F5']), ('G2', ['B4', 'D5', 'G5', 'D5'])]
t, i = 0.0, 0
while t < DUR:
    bass, arp = prog[(i // 8) % 4]
    add(music, sq(freq(arp[i % 4]), E8 * 0.8, 0.125) * env(E8 * 0.8, 0.003, 0.25), t, 0.07)
    if i % 2 == 0: add(music, tri(freq(bass), E8 * 1.6) * env(E8 * 1.6, 0.004, 0.8), t, 0.3)
    if i % 4 == 0: add(music, np.sin(sweep(130, 45, 0.15)) * env(0.15, 0.001, 0.2), t, 0.35)
    if i % 4 == 2: add(music, hp(noise(0.08), 0.3) * env(0.08, 0.001), t, 0.08)
    add(music, hp(noise(0.025), 0.7) * env(0.025, 0.001), t + E8 / 2, 0.035)
    t += E8; i += 1

# ---------- 音效 ----------
def click(): d = 0.012; return np.sin(2 * np.pi * rng.uniform(2500, 5000) * tt(d)) * env(d, 0.0005, 0.012)
def S_pop():   return np.sin(sweep(500, 1400, 0.07)) * env(0.07, 0.001)
def S_thud():  return mixs(np.sin(sweep(120, 45, 0.25)) * env(0.25, 0.001, 0.3), lp(noise(0.08), 0.3) * env(0.08, 0.001) * 0.5)
def S_stamp(): return mixs(np.sin(sweep(110, 45, 0.35)) * env(0.35, 0.001, 0.4), lp(noise(0.2), 0.4) * env(0.2, 0.001) * 0.6)
def S_crack():
    s = np.zeros(int(0.3 * SR))
    for k in range(6): b = hp(noise(0.03), 0.5) * env(0.03, 0.0005); o = int(k * 0.04 * SR); s[o:o + len(b)] += b * (1 - k * 0.12)
    return s
def S_fire(): n = noise(0.9); return (lp(n, 0.05) * 3 + hp(n, 0.6) * 0.3 * (rng.random(len(n)) > 0.995)) * np.sin(np.pi * tt(0.9) / 0.9)
def S_whoosh(d=0.35):
    n = noise(d); k = np.linspace(0, 1, len(n)); x = lp(n, 0.02) * (1 - k) + lp(n, 0.4) * k
    return hp(x, 0.05) * np.sin(np.pi * k) ** 1.5 * 2
def S_drops():
    s = np.zeros(int(0.8 * SR))
    for _ in range(14): b = click(); o = int(rng.uniform(0, 0.75) * SR); s[o:o + len(b)] += b * rng.uniform(0.3, 0.8)
    return s
def S_ding(): return sum(np.sin(2 * np.pi * f * tt(0.8)) * a for f, a in ((1568, 1), (2093, 0.6), (3136, 0.25))) * env(0.8, 0.002, 0.9) * 0.6
def S_clink(): return sum(np.sin(2 * np.pi * f * tt(0.25)) for f in (2600, 3900, 5200)) / 3 * env(0.25, 0.001, 0.15)
def S_poof(): return lp(noise(0.4), 0.15) * env(0.4, 0.01, 0.3) * 2
def S_clank(): d = 0.3; return sum(np.sin(2 * np.pi * f * tt(d)) for f in (1180, 1730, 2540, 3390)) / 4 * env(d, 0.001, 0.25)
def S_boing(): return np.sign(np.sin(sweep(200, 600, 0.25) + 3 * np.sin(2 * np.pi * 12 * tt(0.25)))) * env(0.25) * 0.4
def S_bonk(): return mixs(np.sin(sweep(300, 120, 0.2)) * env(0.2, 0.001), S_clank()[:int(0.2 * SR)] * 0.4)
def S_machine(): d = 1.2; x = np.sign(np.sin(2 * np.pi * 55 * tt(d))) * 0.3 + lp(noise(d), 0.1); return x * np.sin(np.pi * tt(d) / d) * 0.6
def S_water(): d = 0.8; n = noise(d); return (hp(lp(n, 0.3), 0.08) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt(d)))) * np.sin(np.pi * tt(d) / d) * 1.5
def S_cut():
    s = np.zeros(int(0.8 * SR))
    for k in range(8): b = hp(noise(0.02), 0.6) * env(0.02, 0.0005); o = int(k * 0.09 * SR); s[o:o + len(b)] += b
    return s
def S_coin(): a = sq(freq('B6'), 0.07, 0.5) * env(0.07); b = sq(freq('E7'), 0.3, 0.5) * env(0.3); return np.concatenate([a, b]) * 0.4
def S_click(): return hp(noise(0.015), 0.5) * env(0.015, 0.0005)
SFX = {k[2:]: v for k, v in globals().items() if k.startswith('S_')}
GAIN = {'pop': 0.35, 'thud': 0.7, 'stamp': 0.8, 'crack': 0.5, 'fire': 0.4, 'whoosh': 0.35, 'drops': 0.5, 'ding': 0.35, 'clink': 0.35,
        'poof': 0.5, 'clank': 0.35, 'boing': 0.5, 'bonk': 0.6, 'machine': 0.35, 'water': 0.4, 'cut': 0.4, 'coin': 0.4, 'click': 0.5}
for c in json.load(open(cues_path)):
    add(sfx, SFX[c['type']](), c['t'], GAIN[c['type']] * c.get('gain', 1))

# ---------- 配音 ----------
for l in TL['lines']:
    with wave.open(os.path.join(voice_dir, l['id'] + '.wav')) as w:
        assert w.getframerate() == SR
        v = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    add(voice, v / np.max(np.abs(v)) * 0.8, l['start'])

# 说话时音乐和音效自动让路；片头插入点前后音乐淡出淡入
NO_VOICE = os.environ.get('NO_VOICE') == '1'   # 只要音乐+音效，不要人声
if NO_VOICE: voice[:] = 0
duck = np.clip(lp((np.abs(voice) > 0.01).astype(float), 0.0005) * 3, 0, 1)
gate = np.ones(N); sp = int(TL['splice'] * SR); fade = int(0.4 * SR)
gate[sp - fade:sp] = np.linspace(1, 0, fade); gate[sp:sp + fade] = np.linspace(0, 1, fade)
out = music * gate * (1 - 0.75 * duck) * 0.8 + sfx * (1 - 0.4 * duck) + voice * 1.3
out = out[:int(DUR * SR)]
f = int(0.8 * SR); out[-f:] *= np.linspace(1, 0, f)
out = np.tanh(out / np.max(np.abs(out)) * 1.0) / np.tanh(1.0) * 0.9
if NO_VOICE: out *= 0.55   # 给后配的人声留出音量空间
with wave.open(out_path, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print('wrote', out_path, round(DUR, 1), 's')
