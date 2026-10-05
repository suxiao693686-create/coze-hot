"""合成片头的背景音乐 + 音效，并混入配音。用法: python3 audio.py voice_kaimo.wav voice_title.wav out.wav"""
import sys, wave
import numpy as np

SR = 44100
DUR = 6.2
T_OPEN, T_WIPE, T_SWAP = 2.05, 4.75, 5.05
rng = np.random.default_rng(3)
mix = np.zeros(int(SR * DUR) + SR)

def add(sig, t, gain=1.0):
    i = int(t * SR); n = min(len(sig), len(mix) - i)
    if n > 0: mix[i:i + n] += sig[:n] * gain

def tt(d): return np.arange(int(d * SR)) / SR
def env(d, a=0.005, r=None):
    t = tt(d); r = r or d
    return np.minimum(1, t / a) * np.exp(-t / (r / 4))
def freq(note):  # 'C5' -> Hz
    names = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    return 440 * 2 ** ((names[note[0]] + 12 * (int(note[-1]) + 1) - 69) / 12)
def square(f, d, duty=0.25):
    return np.where((tt(d) * f) % 1 < duty, 1.0, -1.0)
def tri(f, d):
    p = (tt(d) * f) % 1; return 4 * np.abs(p - 0.5) - 1
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def lowpass(x, k=0.1):
    y = np.zeros_like(x); acc = 0.0
    for i, v in enumerate(x): acc += k * (v - acc); y[i] = acc
    return y

E8 = 0.2  # eighth note at 150 BPM

# ---- phase A: sneaky intro (0 - T_OPEN) ----
for i in range(int(T_OPEN / E8)):
    t = i * E8
    add(tri(freq('C3') if i % 2 == 0 else freq('G2'), 0.12) * env(0.12), t, 0.35)
    add(noise(0.03) * env(0.03), t + 0.1, 0.06)
# lick blips
for k in range(5):
    t = 0.3 + k * 2 / 7
    add(np.sin(2 * np.pi * np.linspace(900, 1400, int(0.05 * SR)).cumsum() / SR) * env(0.05), t, 0.18)
# "!" pop
add(square(1, 0.12) * 0 + np.sign(np.sin(2 * np.pi * np.geomspace(500, 1600, int(0.12 * SR)).cumsum() / SR)) * env(0.12), 1.12, 0.12)
# jump boing
add(np.sign(np.sin(2 * np.pi * np.geomspace(250, 900, int(0.2 * SR)).cumsum() / SR)) * env(0.2), 1.55, 0.12)
# chain clank x2
for t in (1.75, 1.9):
    d = 0.25; s = sum(np.sin(2 * np.pi * f * tt(d)) for f in (1180, 1730, 2540, 3390)) / 4
    add(s * env(d, 0.002, 0.25), t, 0.35)
# mold open: heavy clunk + hydraulic hiss
d = 0.5; ph = 2 * np.pi * np.geomspace(110, 40, int(d * SR)).cumsum() / SR
add(np.sin(ph) * env(d, 0.002, 0.5), T_OPEN, 0.9)
add(lowpass(noise(0.12), 0.3) * env(0.12, 0.001), T_OPEN, 0.6)
hiss = lowpass(noise(0.8), 0.5) - lowpass(noise(0.8), 0.05)
add(hiss * np.sin(np.pi * tt(0.8) / 0.8) ** 2, T_OPEN + 0.02, 0.35)

def click(): 
    d = 0.012; return np.sin(2 * np.pi * rng.uniform(2500, 5000) * tt(d)) * env(d, 0.0005, 0.012)
# pellet burst rattle
for _ in range(70): add(click(), T_OPEN + 0.05 + rng.uniform(0, 0.9) ** 1.6, rng.uniform(0.1, 0.3))

# ---- phase B: main chiptune (T_OPEN - T_SWAP) ----
chords = [('C', ['E5', 'G5', 'C6', 'G5'], 'C3'), ('G', ['D5', 'G5', 'B5', 'G5'], 'G2'),
          ('Am', ['C5', 'E5', 'A5', 'E5'], 'A2'), ('F', ['C5', 'F5', 'A5', 'C6'], 'F2')]
i = 0; t = T_OPEN
while t < T_SWAP - 0.01:
    _, mel, bass = chords[(i // 4) % 4]
    n = mel[i % 4]
    add(square(freq(n), E8 * 0.9) * env(E8 * 0.9, 0.003, 0.5), t, 0.11)
    add(square(freq(n) * 2, E8 * 0.5, 0.5) * env(E8 * 0.5, 0.003, 0.15), t, 0.025)
    bf = freq(bass) * (2 if i % 2 else 1)
    add(tri(bf, E8 * 0.9) * env(E8 * 0.9, 0.003, 0.6), t, 0.32)
    if i % 2 == 0:  # kick
        add(np.sin(2 * np.pi * np.geomspace(150, 45, int(0.15 * SR)).cumsum() / SR) * env(0.15), t, 0.55)
    if i % 4 == 2:  # snare
        add(noise(0.12) * env(0.12, 0.001), t, 0.22)
    add(noise(0.03) * env(0.03, 0.001), t + E8 / 2, 0.06)
    i += 1; t += E8
# title ding arpeggio + stamp bam
for k, n in enumerate(['C6', 'E6', 'G6', 'C7']): add(square(freq(n), 0.12, 0.5) * env(0.12), 2.6 + k * 0.04, 0.08)
add(np.sin(2 * np.pi * np.geomspace(120, 50, int(0.35 * SR)).cumsum() / SR) * env(0.35), 2.95, 0.8)
add(lowpass(noise(0.2), 0.4) * env(0.2, 0.001), 2.95, 0.5)
# rain clicks
for _ in range(30): add(click(), rng.uniform(2.8, 4.7), rng.uniform(0.04, 0.1))

# ---- wipe: pellet pour ----
pour = lowpass(noise(0.75), 0.6) - lowpass(noise(0.75), 0.08)
add(pour * np.sin(np.pi * tt(0.75) / 0.75), T_WIPE, 0.35)
for _ in range(160): add(click(), T_WIPE + rng.uniform(0, 0.7), rng.uniform(0.08, 0.25))

# ---- phase C: resolve ----
for k, n in enumerate(['C5', 'E5', 'G5', 'C6']):
    add(square(freq(n), 0.9 - k * 0.05) * env(0.9 - k * 0.05, 0.003, 1.2), T_SWAP + 0.2 + k * 0.06, 0.07)
add(tri(freq('C3'), 1.0) * env(1.0, 0.003, 1.5), T_SWAP + 0.2, 0.35)
add(square(freq('G6'), 0.25, 0.5) * env(0.25), T_SWAP + 0.55, 0.06)

# ---- voices (duck music underneath) ----
def load(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        assert w.getframerate() == SR, w.getframerate()
    return x
music = mix.copy(); voice = np.zeros_like(mix)
for path, t in ((sys.argv[1], 1.75), (sys.argv[2], 2.6)):
    v = load(path); v = v / np.max(np.abs(v)) * 0.6; i0 = int(t * SR); voice[i0:i0 + len(v)] += v[:len(voice) - i0]
duck = lowpass((np.abs(voice) > 0.01).astype(float), 0.0008)
out = music * (1 - 0.55 * np.clip(duck * 3, 0, 1)) + voice
out = out[:int(SR * DUR)]
fade = int(0.3 * SR); out[-fade:] *= np.linspace(1, 0, fade)
out = out / np.max(np.abs(out)) * 0.89
with wave.open(sys.argv[3], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
print('wrote', sys.argv[3])
