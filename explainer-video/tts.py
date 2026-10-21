"""配音：把每个场景的旁白合成语音，并算出每一句字幕在语音里的起止时间。

引擎（--tts）：
  edge    微软 Edge 朗读（免费，声音最好，支持很多中文音色）。需要能访问 speech.platform.bing.com
  google  谷歌翻译朗读（免费，女声，音质一般）。edge 用不了时的备选
  none    不配音，按语速估算字幕时间（只用来快速预览画面）
  auto    默认：edge → google → none，哪个能用用哪个
"""

import asyncio
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

import numpy as np

SR = 44100
PUNCT = "，。、；：？！,.;:?!…—“”‘’\"'（）()《》【】 　"
PAUSE = {"，": 2, ",": 2, "、": 1.5, "；": 3, ";": 3, "：": 2, ":": 2, "。": 3.5, "？": 3.5, "?": 3.5, "！": 3.5, "!": 3.5}


def spoken_len(text):
    """会被念出来的字数（标点不算）。英文单词按 2 个字算。"""
    text = re.sub(r"[A-Za-z]+", "字字", text)
    text = re.sub(r"\d", "字", text)
    return sum(1 for ch in text if ch not in PUNCT)


def scene_text(lines):
    """把一场戏的几句旁白拼成一段话，句尾没标点就补逗号，最后一句补句号。"""
    out = []
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if ln and ln[-1] not in "，。？！,.?!；;：:…":
            ln += "。" if i == len(lines) - 1 else "，"
        out.append(ln)
    return "".join(out)


def decode(path, tempo=1.0):
    """任意音频 → 44.1kHz 单声道 float32"""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if abs(tempo - 1) > 1e-3:
        cmd += ["-af", f"atempo={tempo:.3f}"]
    cmd += ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def trim(audio, thresh=0.012, pad=0.03):
    """去掉首尾静音，返回 (音频, 去掉的开头秒数)"""
    idx = np.where(np.abs(audio) > thresh)[0]
    if not len(idx):
        return audio, 0.0
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(audio), idx[-1] + int(pad * SR))
    return audio[a:b], a / SR


# ---------------- 各家引擎 ----------------

def _edge(text, voice, rate, mp3):
    import edge_tts

    async def run():
        kw = {"rate": rate, "boundary": "WordBoundary"}
        if os.environ.get("HTTPS_PROXY"):
            kw["proxy"] = os.environ["HTTPS_PROXY"]
        com = edge_tts.Communicate(text, voice, **kw)
        bounds = []
        with open(mp3, "wb") as f:
            async for msg in com.stream():
                if msg["type"] == "audio":
                    f.write(msg["data"])
                elif msg["type"] == "WordBoundary":
                    bounds.append((msg["offset"] / 1e7, msg["duration"] / 1e7, msg["text"]))
        return bounds

    return asyncio.run(asyncio.wait_for(run(), timeout=60))


def _google(text, mp3):
    # 一次最多约 200 字，长了就按标点切开
    parts, buf = [], ""
    for piece in re.split(r"(?<=[，。？！；,.?!;])", text):
        if len(buf) + len(piece) > 180 and buf:
            parts.append(buf)
            buf = ""
        buf += piece
    if buf:
        parts.append(buf)
    data = b""
    for p in parts:
        q = urllib.parse.urlencode({"ie": "UTF-8", "client": "gtx", "tl": "zh-CN", "q": p})
        req = urllib.request.Request(
            "https://translate.googleapis.com/translate_tts?" + q,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data += r.read()
    with open(mp3, "wb") as f:
        f.write(data)


def _rate_factor(rate):
    m = re.match(r"([+-]?\d+)%", str(rate or "+0%"))
    return 1 + (int(m.group(1)) / 100 if m else 0)


# ---------------- 字幕时间 ----------------

def line_times_from_bounds(lines, bounds, total):
    """用 edge 返回的逐词时间，算出每句字幕的开始时间。对不上时返回 None。"""
    if not bounds:
        return None
    starts_char, c = [], 0
    for ln in lines:
        starts_char.append(c)
        c += spoken_len(ln)
    starts = [None] * len(lines)
    cum = 0
    for off, _dur, word in bounds:
        li = max(i for i, sc in enumerate(starts_char) if sc <= cum)
        if starts[li] is None:
            starts[li] = off
        cum += spoken_len(word)
    if any(s is None for s in starts) or abs(cum - c) > max(2, c * 0.1):
        return None
    starts[0] = 0.0
    return [(starts[i], starts[i + 1] if i + 1 < len(lines) else total) for i in range(len(lines))]


def line_times_estimate(lines, total):
    """没有逐词时间时，按字数 + 标点停顿按比例分配"""
    w = []
    for i, ln in enumerate(lines):
        ln = ln.strip()
        tail = ln[-1] if ln else ""
        pause = PAUSE.get(tail, 2 if i < len(lines) - 1 else 0)
        w.append(max(1, spoken_len(ln)) + pause)
    tot = sum(w)
    out, acc = [], 0.0
    for x in w:
        a = acc / tot * total
        acc += x
        out.append((a, acc / tot * total))
    return out


# ---------------- 对外 ----------------

class TTS:
    def __init__(self, engine="auto", voice="zh-CN-YunxiNeural", rate="+5%", cache_dir="tts"):
        self.engine = engine
        self.voice = voice
        self.rate = rate
        self.cache = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.used = "none" if engine == "none" else None  # 实际用上的引擎

    def _try(self, engine, text, base):
        mp3 = base + ".mp3"
        bounds = None
        if engine == "edge":
            bounds = _edge(text, self.voice, self.rate, mp3)
            audio = decode(mp3)
        elif engine == "google":
            _google(text, mp3)
            audio = decode(mp3, tempo=1.12 * _rate_factor(self.rate))
        else:
            raise ValueError(engine)
        if len(audio) < SR * 0.2:
            raise RuntimeError("合成结果太短")
        return audio, bounds

    def say(self, lines):
        """返回 (音频, 时长, [(句开始, 句结束), ...])，时间都相对语音开头。"""
        text = scene_text(lines)
        if self.engine == "none" or self.used == "none":
            total = max(1.2, spoken_len(text) / 4.6 + 0.25 * len(lines))
            return np.zeros(int(total * SR), np.float32), total, line_times_estimate(lines, total)

        order = [self.used] if self.used else (["edge", "google"] if self.engine == "auto" else [self.engine])
        last_err = None
        for eng in order:
            key = hashlib.md5(json.dumps([eng, self.voice, self.rate, text]).encode()).hexdigest()[:16]
            base = os.path.join(self.cache, key)
            try:
                if os.path.exists(base + ".npy"):
                    audio = np.load(base + ".npy")
                    meta = json.load(open(base + ".json"))
                    bounds = meta["bounds"]
                else:
                    audio, bounds = self._try(eng, text, base)
                    np.save(base + ".npy", audio)
                    json.dump({"text": text, "bounds": bounds}, open(base + ".json", "w"), ensure_ascii=False)
                self.used = eng
                audio, cut = trim(audio)
                total = len(audio) / SR
                if bounds:
                    bounds = [(o - cut, d, w) for o, d, w in bounds]
                times = line_times_from_bounds(lines, bounds, total) or line_times_estimate(lines, total)
                return audio, total, times
            except Exception as e:  # 换下一个引擎
                last_err = e
                print(f"  ! {eng} 配音失败：{type(e).__name__}: {str(e)[:120]}")
        if self.engine != "auto":
            raise RuntimeError(f"配音失败：{last_err}")
        print("  ! 所有配音引擎都不可用，改为无配音预览（按语速估算字幕时间）")
        self.used = "none"
        return self.say(lines)
