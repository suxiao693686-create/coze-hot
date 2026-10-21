#!/usr/bin/env python3
"""黑底白线讲解视频 · 一条命令出片

用法：
  python3 make_video.py 脚本.json                 生成完整视频（配音 + 字幕 + 音效 + 封面）
  python3 make_video.py 脚本.json --preview       只出每个画面的截图总览，几秒钟，用来检查排版
  python3 make_video.py check 脚本.json           只检查脚本有没有写错
  python3 make_video.py icons 关键词 [关键词…]      查图标（英文关键词，如 brain phone money）

常用选项：
  --tts auto|edge|google|none   配音引擎，默认 auto
  --voice zh-CN-YunxiNeural      音色（edge 才有效），也可以写在脚本里
  --no-music                     不要背景氛围音
  --out 目录                      输出目录，默认 output/<脚本名>
"""

import argparse
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TYPES = {
    "headline": [], "question": [], "number": ["value"], "icon": [], "draw": ["svg"],
    "icons": ["items"], "compare": ["left", "right"], "flow": ["steps"], "cycle": ["steps"],
    "list": ["items"], "bars": ["items"], "quote": ["text"], "cta": [],
}
ITEM_SCENES = {"icons", "flow", "cycle", "list", "bars", "compare"}
SUB_MAX = 16          # 每条字幕最多字数
LEAD = 0.12           # 镜头先到，配音稍后开口
TAIL = 0.25           # 一场戏说完后留一口气
LAST_TAIL = 1.8       # 最后一场多停一会儿


def load_icons():
    s = (HERE / "renderer" / "icons.js").read_text(encoding="utf-8")
    return set(json.loads(s[s.index("=") + 1: s.rindex(";")]).keys())


def find_icons(words, limit=12):
    names = load_icons()
    tags = json.loads((HERE / "renderer" / "icon-tags.json").read_text(encoding="utf-8"))
    for w in words:
        w = w.lower()
        hits = [n for n in sorted(names) if w in n]
        hits += [n for n in sorted(names) if w not in n and any(w in t.lower() for t in tags.get(n, []))]
        print(f"{w}: " + (", ".join(hits[:limit]) if hits else "（没找到，换个英文词试试）"))


def norm_say(sc):
    say = sc.get("say", [])
    if isinstance(say, str):
        say = [x for x in re.split(r"[|\n]", say) if x.strip()]
    return [x.strip() for x in say]


def disp_len(s):
    return sum(0.55 if ord(c) < 256 else 1 for c in s)


def sub_text(line):
    return line.strip().rstrip("，。、；：,.;:")


def iter_scenes(script):
    for si, sec in enumerate(script["sections"]):
        for sc in sec.get("scenes", []):
            yield si, sec, sc


def check(script):
    """检查脚本，返回 (错误列表, 提醒列表)"""
    errs, warns = [], []
    icons = load_icons()
    if not script.get("sections"):
        errs.append("缺少 sections（钩子 / 解释 / 结尾）")
        return errs, warns

    def chk_icon(name, where):
        if name and name not in icons:
            near = difflib.get_close_matches(name, icons, n=4, cutoff=0.5)
            errs.append(f"{where}: 没有叫 \"{name}\" 的图标" + (f"，可能是：{', '.join(near)}" if near else "（用 icons 命令查）"))

    n = 0
    for si, sec, sc in iter_scenes(script):
        n += 1
        where = f"第{n}个场景({sec.get('name', si + 1)}/{sc.get('type')})"
        t = sc.get("type")
        if t not in TYPES:
            errs.append(f"{where}: 不认识的类型 {t}，可用：{', '.join(TYPES)}")
            continue
        for f in TYPES[t]:
            if f not in sc:
                errs.append(f"{where}: 缺少字段 {f}")
        say = norm_say(sc)
        if not say:
            errs.append(f"{where}: say（旁白）不能为空")
        for ln in say:
            if disp_len(sub_text(ln)) > SUB_MAX:
                warns.append(f"{where}: 这句太长（>{SUB_MAX}字），字幕会变小：{ln}")
        chk_icon(sc.get("icon"), where)
        for key in ("items", "steps"):
            for it in sc.get(key, []) if isinstance(sc.get(key), list) else []:
                if isinstance(it, dict):
                    chk_icon(it.get("icon"), where)
        for side in ("left", "right"):
            if isinstance(sc.get(side), dict):
                chk_icon(sc[side].get("icon"), where)
        if t in ("icons", "flow") and not (2 <= len(sc.get("items", sc.get("steps", []))) <= 6):
            errs.append(f"{where}: 需要 2~6 项")
        if t == "cycle" and not (3 <= len(sc.get("steps", [])) <= 6):
            errs.append(f"{where}: 循环需要 3~6 步")
        if t in ("list", "bars") and not (1 <= len(sc.get("items", [])) <= 5):
            errs.append(f"{where}: 需要 1~5 项")
    first = script["sections"][0].get("scenes", [])
    if first:
        chars = sum(len(sub_text(x)) for x in norm_say(first[0]))
        if chars > 32:
            warns.append(f"钩子第一场有 {chars} 个字，开头太长留不住人，建议 3 秒内说完（约 15 字）")
    return errs, warns


def music_mode(script):
    m = script.get("music", "chill")
    return "chill" if m is True else (m or None)


def build_timeline(script, tts, fps=30):
    """配音 → 每场戏的时长、每句字幕的时间、音效位置。换场时间卡在配乐的节拍上。"""
    import music
    mode = music_mode(script)
    bpm = script.get("bgm_bpm") if script.get("bgm") else (music.bpm_of(mode) if mode else None)
    beat = 60 / bpm if bpm else None
    W, H = (1080, 1920) if script.get("format", "9:16") == "9:16" else (1920, 1080)
    scenes, subs, sections, voices, sfx = [], [], [], [], []
    keywords = script.get("keywords", [])
    t = 0.0
    all_sc = list(iter_scenes(script))
    for idx, (si, sec, sc) in enumerate(all_sc):
        say = norm_say(sc)
        print(f"  配音 {idx + 1}/{len(all_sc)}：{''.join(say)[:24]}…")
        audio, dur, times = tts.say(say)
        last = idx == len(all_sc) - 1
        hold = sc.get("hold", LAST_TAIL if last else TAIL)
        end = t + max(1.6, LEAD + dur + hold)
        if beat and not last:
            # 段落之间卡整拍，其余卡半拍
            q = beat if all_sc[idx + 1][0] != si else beat / 2
            end = np.ceil(end / q - 0.15) * q
        length = round((end - t) * fps) / fps
        lines = [{"text": sub_text(x), "start": LEAD + a, "end": LEAD + b} for x, (a, b) in zip(say, times)]
        item = dict(sc, start=t, end=t + length, lines=lines, section=si)
        item.pop("say", None)
        scenes.append(item)
        voices.append((t + LEAD, audio))
        hl = [w for w in (sc.get("highlight") if isinstance(sc.get("highlight"), list) else [sc.get("highlight")]) if w] + keywords
        for i, ln in enumerate(lines):
            end = lines[i + 1]["start"] if i + 1 < len(lines) else min(length - 0.12, ln["end"] + 0.6)
            subs.append({"text": ln["text"], "start": t + ln["start"], "end": t + end, "hl": hl})
        # 音效：开场重击 / 镜头移动时嗖一声 / 列表逐项出现时轻点
        if idx == 0 or sc.get("impact"):
            sfx.append((t, "boom"))
        if idx > 0:
            sfx.append((max(0, t - 0.22), "swoosh"))
        if sc.get("type") in ITEM_SCENES:
            for ln in lines[1:]:
                sfx.append((t + ln["start"] - 0.05, "pop"))
        if sc.get("type") == "number":
            sfx.append((t + 1.35, "ping"))
        t += length
    for si, sec in enumerate(script["sections"]):
        mine = [s for s in scenes if s["section"] == si]
        if mine:
            sections.append({"name": sec.get("name", ""), "label": sec.get("label", ""), "start": mine[0]["start"], "end": mine[-1]["end"]})
    video = {
        "width": W, "height": H, "fps": fps, "duration": t,
        "title": script.get("title", ""), "hudTitle": script.get("hud_title", script.get("title", "")),
        "brand": script.get("brand", ""), "accent": script.get("accent", "#A78BFA"),
        "bg": script.get("bg", "stars"), "hud": script.get("hud", True),
        "cover": script.get("cover", {}), "sections": sections, "scenes": scenes, "subtitles": subs,
    }
    return video, voices, sfx


def srt_time(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(subs, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(subs, 1):
            f.write(f"{i}\n{srt_time(s['start'])} --> {srt_time(s['end'])}\n{s['text']}\n\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "icons":
        find_icons(sys.argv[2:] or ["star"])
        return
    only_check = len(sys.argv) > 1 and sys.argv[1] == "check"
    argv = sys.argv[2:] if only_check else sys.argv[1:]
    ap = argparse.ArgumentParser(description="黑底白线讲解视频")
    ap.add_argument("script")
    ap.add_argument("--preview", action="store_true", help="只出截图总览")
    ap.add_argument("--tts", default=None, choices=["auto", "edge", "google", "none"])
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", default=None)
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2))))
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    script = json.loads(Path(a.script).read_text(encoding="utf-8"))
    errs, warns = check(script)
    for w in warns:
        print("提醒：" + w)
    if errs:
        for e in errs:
            print("错误：" + e)
        sys.exit(1)
    if only_check:
        print("脚本检查通过 ✓")
        return

    from tts import TTS
    import sound
    import render

    out = Path(a.out) if a.out else HERE / "output" / Path(a.script).stem
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    engine = a.tts or script.get("tts", "auto")
    if a.preview and not a.tts:
        engine = "none"
    tts = TTS(engine, a.voice or script.get("voice", "zh-CN-YunxiNeural"), a.rate or script.get("rate", "+5%"), str(out / "tts"))

    print("① 配音和时间轴")
    video, voices, sfx = build_timeline(script, tts, a.fps)
    print(f"   配音引擎：{tts.used}，总时长 {video['duration']:.1f} 秒")
    (out / "timeline.json").write_text(json.dumps(video, ensure_ascii=False, indent=1), encoding="utf-8")
    write_srt(video["subtitles"], out / "subtitles.srt")
    (out / "narration.txt").write_text("\n".join(s["text"] for s in video["subtitles"]), encoding="utf-8")

    print("② 截图总览 + 封面")
    times = [max(s["start"] + 0.6, s["end"] - 0.55) for s in video["scenes"]]
    stills = [out / f"_s{i:02d}.png" for i in range(len(times))]
    render.render_stills(video, times, stills, out / "cover.png")
    render.contact_sheet(stills, out / "contact.png")
    for p in stills:
        p.unlink()
    if a.preview:
        print(f"预览完成：{out / 'contact.png'}  （{time.time() - t0:.0f} 秒）")
        return

    print("③ 配乐和混音")
    bgm = script.get("bgm")
    if bgm and not Path(bgm).is_absolute():
        bgm = str(Path(a.script).resolve().parent / bgm)
    secs = [(s["name"], s["start"], s["end"]) for s in video["sections"]]
    audio = sound.mix(video["duration"], voices, sfx, secs, None if a.no_music else music_mode(script), bgm)
    sound.write_wav(out / "audio.wav", audio)

    print(f"④ 渲染画面（{int(video['duration'] * a.fps)} 帧，{a.workers} 路并行）")
    render.render_video(video, out / "audio.wav", out / "video.mp4", a.fps, a.workers)
    (out / "audio.wav").unlink()
    print(f"\n完成 ✓ 用时 {time.time() - t0:.0f} 秒")
    print(f"  视频：{out / 'video.mp4'}")
    print(f"  封面：{out / 'cover.png'}")
    print(f"  字幕：{out / 'subtitles.srt'}")
    print(f"  总览：{out / 'contact.png'}")
    if tts.used != "edge":
        print(f"  注意：本次配音用的是 {tts.used}，不是微软 edge 声音")


if __name__ == "__main__":
    main()
