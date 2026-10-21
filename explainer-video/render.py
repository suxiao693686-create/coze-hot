"""出画面：用无头浏览器打开 renderer/index.html，逐帧截图，交给 ffmpeg 压成视频。"""

import asyncio
import base64
import glob
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = (HERE / "renderer" / "index.html").as_uri()
FONT_DIR = HERE / ".cache" / "fonts"
FONT_CSS = "https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@500;900"


def ensure_fonts():
    """第一次运行时下载思源黑体（Noto Sans SC）到 .cache/fonts。下载不了就用系统自带中文字体。"""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    want = {w: FONT_DIR / f"NotoSansSC-{w}.ttf" for w in (500, 900)}
    if all(p.exists() and p.stat().st_size > 100_000 for p in want.values()):
        return want
    try:
        # 旧版浏览器的 UA 会拿到完整的 ttf，而不是切片的 woff2
        req = urllib.request.Request(FONT_CSS, headers={"User-Agent": "Mozilla/4.0"})
        css = urllib.request.urlopen(req, timeout=15).read().decode()
        blocks = css.split("@font-face")[1:]
        for b in blocks:
            w = int(b.split("font-weight:")[1].split(";")[0])
            url = b.split("url(")[1].split(")")[0]
            if w in want and not want[w].exists():
                print(f"  下载字体 Noto Sans SC {w} …")
                tmp = want[w].with_suffix(".part")
                with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                    shutil.copyfileobj(r, f)
                tmp.rename(want[w])
        return want
    except Exception as e:
        print(f"  ! 字体下载失败（{type(e).__name__}），改用系统中文字体")
        return {w: p for w, p in want.items() if p.exists()}


def _chromium_path():
    """云端环境的 Chromium 在 /opt/pw-browsers；本机用 playwright 自己装的那个"""
    if os.environ.get("CHROMIUM_PATH"):
        return os.environ["CHROMIUM_PATH"]
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "/opt/pw-browsers"]
    for root in roots:
        if not root:
            continue
        hits = sorted(glob.glob(os.path.join(root, "chromium-*/chrome-linux*/chrome")))
        if hits:
            return hits[-1]
    return None


async def _launch(pw):
    try:
        return await pw.chromium.launch()
    except Exception:
        path = _chromium_path()
        if not path:
            raise SystemExit("找不到浏览器，请先运行：python3 -m playwright install chromium")
        return await pw.chromium.launch(executable_path=path)


async def _open(browser, video, fonts):
    page = await browser.new_page(viewport={"width": video["width"], "height": video["height"]}, device_scale_factor=1)
    await page.goto(PAGE)
    await page.evaluate(
        """async fonts => {
          for (const [w, url] of fonts) {
            const f = new FontFace('VS', `url(${url})`, { weight: String(w) });
            await f.load(); document.fonts.add(f);
          }
          await document.fonts.ready;
        }""",
        [[w, p.as_uri()] for w, p in fonts.items()],
    )
    await page.evaluate("v => init(v)", video)
    cdp = await page.context.new_cdp_session(page)
    return page, cdp


async def _shot(page, cdp, t, fmt="jpeg"):
    await page.evaluate("t => seek(t)", t)
    opts = {"format": fmt, "optimizeForSpeed": True}
    if fmt == "jpeg":
        opts["quality"] = 92
    res = await cdp.send("Page.captureScreenshot", opts)
    return base64.b64decode(res["data"])


async def _worker(browser, video, fonts, frames, out, fps):
    page, cdp = await _open(browser, video, fonts)
    ff = await asyncio.create_subprocess_exec(
        "ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out),
        stdin=asyncio.subprocess.PIPE,
    )
    for i in frames:
        ff.stdin.write(await _shot(page, cdp, i / fps))
        await ff.stdin.drain()
    ff.stdin.close()
    if await ff.wait() != 0:
        raise RuntimeError("ffmpeg 编码失败")
    await page.close()


async def _render(video, out_dir, fps, workers, on_progress=None):
    from playwright.async_api import async_playwright

    fonts = ensure_fonts()
    total = int(round(video["duration"] * fps))
    n = max(1, min(workers, total // fps or 1))
    chunk = -(-total // n)
    segs = [out_dir / f"seg{k}.mp4" for k in range(n)]
    async with async_playwright() as pw:
        browser = await _launch(pw)
        await asyncio.gather(*[
            _worker(browser, video, fonts, range(k * chunk, min(total, (k + 1) * chunk)), segs[k], fps)
            for k in range(n)
        ])
        await browser.close()
    return segs


def render_video(video, audio_wav, out_mp4, fps=30, workers=4):
    out_dir = Path(out_mp4).parent
    segs = asyncio.run(_render(video, out_dir, fps, workers))
    lst = out_dir / "segments.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio_wav),
        "-c:v", "copy", "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", "44100", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(out_mp4),
    ], check=True)
    for s in segs:
        s.unlink()
    lst.unlink()


async def _stills(video, times, out_pngs, cover_png):
    from playwright.async_api import async_playwright

    fonts = ensure_fonts()
    async with async_playwright() as pw:
        browser = await _launch(pw)
        page, cdp = await _open(browser, video, fonts)
        for t, p in zip(times, out_pngs):
            Path(p).write_bytes(await _shot(page, cdp, t, "png"))
        if cover_png:
            await page.evaluate("() => showCover()")
            res = await cdp.send("Page.captureScreenshot", {"format": "png"})
            Path(cover_png).write_bytes(base64.b64decode(res["data"]))
        await browser.close()


def render_stills(video, times, out_pngs, cover_png=None):
    asyncio.run(_stills(video, times, out_pngs, cover_png))


def contact_sheet(pngs, out_png, cols=4):
    """把多张截图拼成一张总览图，方便一眼检查每个画面"""
    w = 360
    filt = f"scale={w}:-1,tile={cols}x{-(-len(pngs) // cols)}:padding=8:margin=8:color=0x222222"
    tmp = Path(out_png).parent / "_still_%03d.png"
    for i, p in enumerate(pngs):
        shutil.copy(p, str(tmp) % i)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-vf", filt, "-frames:v", "1", str(out_png)], check=True)
    for i in range(len(pngs)):
        os.remove(str(tmp) % i)
