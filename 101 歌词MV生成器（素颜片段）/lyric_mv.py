#!/usr/bin/env python3
"""
歌词 MV 生成器 —— 按 LRC 时间轴把歌词逐字卡拉OK高亮，合成竖屏/横屏 MV。

用法示例（截取 01:02 ~ 01:40 的片段）:
    python3 lyric_mv.py --audio 素颜.mp3 --lrc 素颜.lrc \
        --start 62 --end 100 --title 素颜 --artist 许嵩 \
        --bg ./bg_images --out suyan_mv.mp4

依赖: Python3, Pillow, numpy, ffmpeg (命令行)
"""
import argparse
import math
import os
import random
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

# 「素颜」风格：干净、柔和的粉蓝渐变 + 漂浮光斑
PALETTE_TOP = [(236, 196, 208), (190, 208, 238)]
PALETTE_BOTTOM = [(168, 178, 222), (226, 182, 200)]
TEXT_BASE = (255, 255, 255)
TEXT_HIGHLIGHT = (255, 120, 150)
TEXT_SHADOW = (90, 70, 100)


# ---------------------------------------------------------------- 解析 LRC
TIME_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
OFFSET_RE = re.compile(r"\[offset:\s*([+-]?\d+)\]", re.I)


def parse_lrc(path):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    offset = 0.0
    m = OFFSET_RE.search(text)
    if m:
        offset = int(m.group(1)) / 1000.0
    items = []
    for raw in text.splitlines():
        stamps = TIME_RE.findall(raw)
        if not stamps:
            continue
        lyric = TIME_RE.sub("", raw).strip()
        for mm, ss in stamps:
            t = int(mm) * 60 + float(ss) - offset
            items.append((t, lyric))
    items.sort(key=lambda x: x[0])
    lines = []
    for i, (t, lyric) in enumerate(items):
        end = items[i + 1][0] if i + 1 < len(items) else t + 5.0
        if lyric:
            lines.append({"start": t, "end": end, "text": lyric})
    return lines


def clip_lines(lines, start, end):
    out = []
    for ln in lines:
        if ln["end"] <= start or ln["start"] >= end:
            continue
        out.append({
            "start": ln["start"] - start,
            "end": min(ln["end"], end) - start,
            "text": ln["text"],
        })
    return out


# ---------------------------------------------------------------- 音频
def probe_duration(audio):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", audio],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def audio_envelope(audio, start, dur, fps):
    """每帧一个 0~1 的响度值，用来让光斑跟着节奏呼吸。"""
    sr = 8000
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", audio,
         "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True, check=True)
    pcm = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    hop = sr / fps
    n = int(math.ceil(dur * fps))
    env = np.zeros(n, dtype=np.float32)
    for i in range(n):
        seg = pcm[int(i * hop):int((i + 1) * hop)]
        if len(seg):
            env[i] = math.sqrt(float(np.mean(seg * seg)))
    if env.max() > 0:
        env /= np.percentile(env, 98) + 1e-6
    env = np.clip(env, 0, 1)
    # 平滑
    k = np.ones(5) / 5
    return np.convolve(env, k, mode="same")


# ---------------------------------------------------------------- 背景
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_bg(w, h, t):
    phase = (math.sin(t * 0.25) + 1) / 2
    top = lerp(PALETTE_TOP[0], PALETTE_TOP[1], phase)
    bot = lerp(PALETTE_BOTTOM[0], PALETTE_BOTTOM[1], phase)
    col = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    arr = np.array(top, np.float32) * (1 - col) + np.array(bot, np.float32) * col
    arr = np.repeat(arr[:, None, :], w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


class ImageBackground:
    """用户提供的图片：每张缓慢推拉（Ken Burns），交叉淡化切换。"""

    def __init__(self, folder, w, h, total):
        exts = (".jpg", ".jpeg", ".png", ".webp")
        files = sorted(
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(exts))
        if not files:
            raise SystemExit(f"背景目录 {folder} 里没有图片")
        self.w, self.h = w, h
        self.imgs = [self._cover(Image.open(p).convert("RGB")) for p in files]
        self.seg = max(total / len(self.imgs), 1.0)

    def _cover(self, img):
        # 放大 1.15 倍，留出推拉空间
        sw, sh = self.w * 1.15, self.h * 1.15
        s = max(sw / img.width, sh / img.height)
        return img.resize((int(img.width * s) + 1, int(img.height * s) + 1),
                          Image.LANCZOS)

    def _frame(self, idx, local):
        img = self.imgs[idx % len(self.imgs)]
        z = 1.0 + 0.12 * (1 - local) if idx % 2 else 1.0 + 0.12 * local
        cw = img.width / z
        ch = cw * self.h / self.w
        if ch > img.height:
            ch = img.height
            cw = ch * self.w / self.h
        x = (img.width - cw) / 2
        y = (img.height - ch) / 2
        return img.resize((self.w, self.h), Image.BILINEAR,
                          box=(x, y, x + cw, y + ch))

    def get(self, t):
        idx = int(t // self.seg)
        local = (t % self.seg) / self.seg
        cur = self._frame(idx, local)
        fade = 0.8
        rem = self.seg - (t % self.seg)
        if rem < fade and idx + 1 < len(self.imgs):
            nxt = self._frame(idx + 1, 0.0)
            cur = Image.blend(cur, nxt, 1 - rem / fade)
        # 轻微柔光 + 压暗，保证白字可读
        soft = cur.filter(ImageFilter.GaussianBlur(6))
        cur = Image.blend(cur, soft, 0.35)
        dark = Image.new("RGB", cur.size, (40, 30, 50))
        return Image.blend(cur, dark, 0.28)


class Bokeh:
    def __init__(self, w, h, n=28, seed=7):
        rnd = random.Random(seed)
        self.w, self.h = w, h
        self.dots = [{
            "x": rnd.uniform(0, w), "y": rnd.uniform(0, h),
            "r": rnd.uniform(w * 0.015, w * 0.07),
            "vx": rnd.uniform(-12, 12), "vy": rnd.uniform(-35, -10),
            "a": rnd.uniform(0.25, 0.6), "ph": rnd.uniform(0, 6.28),
        } for _ in range(n)]

    def draw(self, base, t, energy):
        # 半分辨率画光斑再放大模糊，省时且更柔
        sw, sh = self.w // 2, self.h // 2
        layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for p in self.dots:
            x = (p["x"] + p["vx"] * t) % (self.w + 200) - 100
            y = (p["y"] + p["vy"] * t) % (self.h + 200) - 100
            r = p["r"] * (1 + 0.25 * energy)
            a = p["a"] * (0.6 + 0.4 * math.sin(t * 1.3 + p["ph"])) * (0.7 + 0.6 * energy)
            alpha = int(255 * min(a, 1))
            x, y, r = x / 2, y / 2, r / 2
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(6)).resize(
            (self.w, self.h), Image.BILINEAR)
        base = base.convert("RGBA")
        base.alpha_composite(layer)
        return base


# ---------------------------------------------------------------- 文字
def load_font(path, size):
    paths = [path] if path else FONT_CANDIDATES
    for p in paths:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise SystemExit("找不到中文字体，请用 --font 指定一个 .ttf/.ttc 文件")


def wrap(text, font, max_w):
    rows, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) > max_w and cur:
            rows.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        rows.append(cur)
    return rows


def draw_line(canvas, text, font, cx, cy, max_w, alpha=1.0, progress=None,
              scale=1.0):
    """在 (cx, cy) 居中绘制一句歌词。progress∈[0,1] 时做逐字卡拉OK填色。"""
    if alpha <= 0.01 or not text:
        return
    rows = wrap(text, font, max_w)
    asc, desc = font.getmetrics()
    lh = int((asc + desc) * 1.25)
    pad = 30
    tw = int(max(font.getlength(r) for r in rows)) + pad * 2
    th = lh * len(rows) + pad * 2

    total_chars = sum(len(r) for r in rows)
    lit_chars = (progress or 0) * total_chars

    shadow = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    base = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    hi = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    mask = Image.new("L", (tw, th), 0)
    ds, db, dh, dm = (ImageDraw.Draw(x) for x in (shadow, base, hi, mask))

    used = 0
    for i, row in enumerate(rows):
        rw = font.getlength(row)
        x0 = (tw - rw) / 2
        y0 = pad + i * lh
        ds.text((x0, y0), row, font=font, fill=TEXT_SHADOW + (200,))
        db.text((x0, y0), row, font=font, fill=TEXT_BASE + (255,),
                stroke_width=2, stroke_fill=TEXT_SHADOW + (120,))
        if progress is not None:
            dh.text((x0, y0), row, font=font, fill=TEXT_HIGHLIGHT + (255,),
                    stroke_width=2, stroke_fill=(255, 255, 255, 230))
            n_lit = min(max(lit_chars - used, 0), len(row))
            full = int(n_lit)
            px = font.getlength(row[:full])
            if full < len(row):
                px += (font.getlength(row[:full + 1]) - px) * (n_lit - full)
            if px > 0:
                dm.rectangle((0, y0 - 10, x0 + px, y0 + lh), fill=255)
        used += len(row)

    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    out.alpha_composite(shadow)
    out.alpha_composite(base)
    if progress is not None:
        hi_a = Image.fromarray(np.minimum(np.array(hi.getchannel("A")),
                                          np.array(mask)))
        hi.putalpha(hi_a)
        out.alpha_composite(hi)
    if scale != 1.0:
        out = out.resize((max(1, int(tw * scale)), max(1, int(th * scale))),
                         Image.LANCZOS)
    if alpha < 1:
        a = out.getchannel("A").point(lambda v: int(v * alpha))
        out.putalpha(a)
    canvas.alpha_composite(out, (int(cx - out.width / 2), int(cy - out.height / 2)))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- 主流程
def render(args):
    w, h = map(int, args.size.lower().split("x"))
    fps = args.fps
    audio_len = probe_duration(args.audio)
    start = args.start
    end = args.end if args.end else audio_len
    end = min(end, audio_len)
    dur = end - start
    if dur <= 0:
        raise SystemExit("--end 必须大于 --start")

    lines = clip_lines(parse_lrc(args.lrc), start, end)
    if not lines:
        raise SystemExit("这个时间段里没有歌词，检查 --start/--end 和 LRC 时间")
    print(f"片段 {start:.2f}s ~ {end:.2f}s，共 {len(lines)} 句歌词")

    env = audio_envelope(args.audio, start, dur, fps)
    big = load_font(args.font, int(w * 0.075))
    small = load_font(args.font, int(w * 0.048))
    title_font = load_font(args.font, int(w * 0.1))
    max_w = w * 0.86

    bg_img = ImageBackground(args.bg, w, h, dur) if args.bg else None
    bokeh = Bokeh(w, h)

    fade_in, fade_out = 0.6, 0.8
    tmp_video = args.out + ".noaudio.mp4"
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", tmp_video],
        stdin=subprocess.PIPE)

    n_frames = int(math.ceil(dur * fps))
    cy = h * 0.62 if h > w else h * 0.55
    gap = big.size * 1.9
    for fi in range(n_frames):
        t = fi / fps
        e = float(env[min(fi, len(env) - 1)])
        frame = bg_img.get(t) if bg_img else gradient_bg(w, h, t)
        frame = bokeh.draw(frame, t, e)

        # 片头标题
        if args.title and t < 3.5:
            a = ease(t / 0.8) * (1 - ease((t - 2.6) / 0.9))
            draw_line(frame, args.title, title_font, w / 2, h * 0.3, max_w, a)
            if args.artist:
                draw_line(frame, args.artist, small, w / 2,
                          h * 0.3 + title_font.size * 1.3, max_w, a * 0.9)

        # 当前句索引
        cur = -1
        for i, ln in enumerate(lines):
            if ln["start"] <= t:
                cur = i
        nxt_i = cur + 1

        # 换句时的滑动过渡
        trans = 0.35
        k = 1.0
        if cur >= 0:
            k = ease((t - lines[cur]["start"]) / trans)
        shift = (1 - k) * gap

        # 当前句换行时，上下句让出空间
        extra = 0
        if cur >= 0:
            n_rows = len(wrap(lines[cur]["text"], big, max_w))
            extra = (n_rows - 1) * big.size * 0.65
        if cur >= 0:
            ln = lines[cur]
            sing = max((ln["end"] - ln["start"]) * 0.88, 0.3)
            prog = min((t - ln["start"]) / sing, 1.0)
            draw_line(frame, ln["text"], big, w / 2, cy + shift, max_w,
                      alpha=1.0, progress=prog, scale=0.82 + 0.18 * k)
            if cur - 1 >= 0:
                draw_line(frame, lines[cur - 1]["text"], small, w / 2,
                          cy - gap - extra + shift, max_w, alpha=0.7 * k + (1 - k) * 0.9)
        if nxt_i < len(lines):
            # 第一句开始前提前出现
            pre = 1.0 if cur >= 0 else ease((t - (lines[0]["start"] - 1.5)) / 0.6)
            draw_line(frame, lines[nxt_i]["text"], small, w / 2,
                      cy + gap + extra + shift, max_w, alpha=0.7 * pre)

        # 进度条
        d = ImageDraw.Draw(frame)
        bw = int(w * 0.6)
        bx, by = (w - bw) // 2, int(h * 0.9)
        d.rounded_rectangle((bx, by, bx + bw, by + 6), 3, fill=(255, 255, 255, 90))
        d.rounded_rectangle((bx, by, bx + int(bw * t / dur), by + 6), 3,
                            fill=TEXT_HIGHLIGHT + (230,))

        # 整体淡入淡出
        rgb = frame.convert("RGB")
        fade = min(ease(t / fade_in), ease((dur - t) / fade_out))
        if fade < 1:
            rgb = Image.blend(Image.new("RGB", rgb.size, (0, 0, 0)), rgb, fade)
        enc.stdin.write(rgb.tobytes())
        if fi % fps == 0:
            print(f"\r渲染 {fi}/{n_frames} 帧", end="", flush=True)
    enc.stdin.close()
    enc.wait()
    print(f"\r渲染完成 {n_frames} 帧        ")

    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", tmp_video,
         "-ss", str(start), "-t", str(dur), "-i", args.audio,
         "-af", f"afade=t=in:d={fade_in},afade=t=out:st={max(dur - fade_out, 0)}:d={fade_out}",
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-shortest", args.out], check=True)
    os.remove(tmp_video)
    print("输出:", args.out)


def main():
    ap = argparse.ArgumentParser(description="按 LRC 歌词生成卡拉OK风格 MV")
    ap.add_argument("--audio", required=True, help="歌曲音频 mp3/wav/flac/m4a")
    ap.add_argument("--lrc", required=True, help="带时间轴的 LRC 歌词文件")
    ap.add_argument("--start", type=float, default=0, help="片段开始秒数")
    ap.add_argument("--end", type=float, default=None, help="片段结束秒数")
    ap.add_argument("--out", default="mv.mp4")
    ap.add_argument("--bg", default=None, help="背景图片目录（不填用渐变+光斑）")
    ap.add_argument("--title", default="")
    ap.add_argument("--artist", default="")
    ap.add_argument("--size", default="1080x1920", help="竖屏 1080x1920 / 横屏 1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--font", default=None, help="中文字体文件路径")
    args = ap.parse_args()
    render(args)


if __name__ == "__main__":
    sys.exit(main())
