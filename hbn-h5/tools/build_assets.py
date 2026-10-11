"""把 source/ 里的 11 张设计稿处理成 H5 用的素材。

- 背景图：等比缩放 + 压缩，输出 assets/bg{n}.jpg
- 精灵图：把按钮、人物等元素抠成透明 PNG，单独做动画
    cut     按与纸色的差异抠图，并在背景里把原位置“擦掉”，元素可以自由移动
    hull    同 cut，但取外轮廓凸包（脸部等内部接近纸色的元素用这个，避免抠出洞）
    feather 矩形裁切 + 羽化边缘，背景保留原图，只适合做轻微缩放/发光
    item    托盘上的物品：GrabCut 抠图，不擦背景（只做原地放大/变暗）
    erase   只擦除背景，不输出精灵（用于替换成代码绘制的元素，如进度条）
- 生成 assets/manifest.js，记录每张图尺寸和精灵在原图上的坐标

用法：python3 tools/build_assets.py   （在 hbn-h5 目录下运行）
"""
import json
import os

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "source")
OUT = os.path.join(ROOT, "assets")
SCALE = 0.8          # 原图高 2000 → 1600
JPG_QUALITY = 82

# name: (图号, x0, y0, x1, y1, 模式)   坐标均为原图像素
SPRITES = {
    "cover_title":  (1, 80, 70, 735, 505, "cut"),
    "cover_seal":   (1, 915, 168, 1118, 628, "cut"),
    "cover_start":  (1, 428, 1688, 702, 1996, "cut"),
    "load_head":    (2, 400, 668, 692, 1015, "hull"),
    "load_bar":     (2, 378, 1028, 722, 1200, "erase"),
    "rule_bottle":  (5, 160, 222, 300, 552, "cut"),
    "rule_btn":     (5, 390, 1545, 716, 1858, "cut"),
    "pick_lead":    (6, 210, 1435, 465, 1715, "item"),
    "pick_toner":   (6, 535, 1365, 678, 1725, "item"),
    "pick_hbn":     (6, 770, 1400, 905, 1715, "item"),
    "fail1_crow":   (7, 110, 80, 285, 222, "cut"),
    "fail1_head":   (7, 318, 548, 792, 1232, "hull"),
    "fail1_btn":    (7, 408, 1668, 732, 1972, "cut"),
    "fail2_crow":   (8, 110, 80, 285, 222, "cut"),
    "fail2_head":   (8, 318, 548, 792, 1232, "hull"),
    "fail2_btn":    (8, 408, 1668, 732, 1972, "cut"),
    "win_title":    (10, 228, 205, 945, 385, "cut"),
    "win_head":     (10, 358, 505, 892, 1145, "hull"),
    "win_hand":     (10, 72, 868, 288, 1102, "hull"),
    "win_bottle":   (10, 118, 1318, 242, 1592, "cut"),
    "win_arrow":    (10, 498, 1910, 628, 2000, "cut"),
    "end_girl":     (11, 178, 478, 912, 1535, "hull"),
    "end_retry":    (11, 112, 1582, 412, 1862, "cut"),
    "end_buy":      (11, 652, 1582, 952, 1862, "cut"),
    "end_music":    (11, 960, 0, 1046, 82, "erase"),
}


def bg_color(rgb, box):
    x0, y0, x1, y1 = box
    crop = rgb[y0:y1, x0:x1]
    border = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    return np.median(border, axis=0)


def cut_mask(rgb, box, hull=False, ref=None, largest=False):
    x0, y0, x1, y1 = box
    crop = rgb[y0:y1, x0:x1].astype(np.int16)
    if ref is None:
        ref = bg_color(rgb, box)
    diff = np.abs(crop - ref).max(axis=2)
    fg = diff > (18 if hull else 26)
    fg = ndimage.binary_closing(fg, iterations=3)
    fg = ndimage.binary_fill_holes(fg)
    # 去掉零星噪点
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes >= 60
        fg = keep[lab]
    if largest and fg.any():
        lab, n = ndimage.label(fg)
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        fg = lab == (1 + int(np.argmax(sizes)))
    if hull and fg.any():
        pts = cv2.findNonZero(fg.astype(np.uint8))
        hm = np.zeros(fg.shape, np.uint8)
        cv2.fillConvexPoly(hm, cv2.convexHull(pts), 1)
        fg = hm.astype(bool)
    fg = ndimage.binary_dilation(fg, iterations=2)
    alpha = cv2.GaussianBlur(fg.astype(np.float32), (5, 5), 0)
    return fg, alpha


def feather_alpha(h, w, edge=0.14):
    ey, ex = max(2, int(h * edge)), max(2, int(w * edge))
    ry = np.clip(np.minimum(np.arange(h), np.arange(h)[::-1]) / ey, 0, 1)
    rx = np.clip(np.minimum(np.arange(w), np.arange(w)[::-1]) / ex, 0, 1)
    a = np.outer(ry, rx)
    return a * a * (3 - 2 * a)  # smoothstep


def grabcut_alpha(rgb, box):
    x0, y0, x1, y1 = box
    crop = np.ascontiguousarray(rgb[y0:y1, x0:x1])
    h, w = crop.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), mask, (6, 6, w - 12, h - 12), bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    fg = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        fg = lab == (1 + int(np.argmax(sizes)))
    fg = ndimage.binary_fill_holes(ndimage.binary_closing(fg, iterations=2))
    return cv2.GaussianBlur(fg.astype(np.float32), (5, 5), 0)


def fill_paper(rgb, hole):
    """用周围纸色平滑填充被擦掉的区域（归一化卷积），再加一点纸纹噪声。"""
    img = rgb.astype(np.float32)
    paper = np.median(img[~hole], axis=0)
    # 只从“纸”上取色，避开周围的文字和线稿，否则会糊出灰影
    is_paper = np.abs(img - paper).max(axis=2) < 14
    valid = (~hole & is_paper).astype(np.float32)
    fill = np.broadcast_to(paper, img.shape).copy()
    # 由粗到细：大半径保证洞中心有颜色，小半径保留周边纸色的细微变化
    for sigma in (200, 80, 30):
        num = cv2.GaussianBlur(img * valid[..., None], (0, 0), sigma)
        den = cv2.GaussianBlur(valid, (0, 0), sigma)[..., None]
        w = np.clip(den / 0.3, 0, 1)
        fill = fill * (1 - w) + num / np.maximum(den, 1e-4) * w
    rng = np.random.default_rng(7)
    fill += rng.normal(0, 1.2, fill.shape)
    soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 3)[..., None]
    out = img * (1 - soft) + fill * soft
    return np.clip(out, 0, 255).astype(np.uint8)


def save_png(rgba, path):
    img = Image.fromarray(rgba, "RGBA")
    img = img.resize((max(1, round(img.width * SCALE)), max(1, round(img.height * SCALE))), Image.LANCZOS)
    img.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE).save(path, optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {"scale": SCALE, "bg": {}, "sprites": {}}
    images = {n: np.array(Image.open(os.path.join(SRC, f"{n}.jpg")).convert("RGB")) for n in range(1, 12)}
    erase_masks = {n: np.zeros(im.shape[:2], np.uint8) for n, im in images.items()}

    for name, (n, x0, y0, x1, y1, mode) in SPRITES.items():
        rgb = images[n]
        box = (x0, y0, x1, y1)
        h, w = y1 - y0, x1 - x0
        if mode == "erase":
            erase_masks[n][y0:y1, x0:x1] = 255
            continue
        if mode in ("cut", "hull"):
            fg, alpha = cut_mask(rgb, box, hull=(mode == "hull"))
            em = ndimage.binary_dilation(fg, iterations=10)
            erase_masks[n][y0:y1, x0:x1] |= (em * 255).astype(np.uint8)
        elif mode == "item":
            alpha = grabcut_alpha(rgb, box)
        else:
            alpha = feather_alpha(h, w)
        rgba = np.dstack([rgb[y0:y1, x0:x1], (alpha * 255).astype(np.uint8)])
        save_png(rgba, os.path.join(OUT, f"{name}.png"))
        manifest["sprites"][name] = {"bg": n, "x": x0, "y": y0, "w": w, "h": h}

    for n, rgb in images.items():
        H, W = rgb.shape[:2]
        mask = erase_masks[n]
        if mask.any():
            rgb = fill_paper(rgb, mask > 0)
        img = Image.fromarray(rgb).resize((round(W * SCALE), round(H * SCALE)), Image.LANCZOS)
        img.save(os.path.join(OUT, f"bg{n}.jpg"), quality=JPG_QUALITY, optimize=True, progressive=True)
        paper = np.median(np.concatenate([rgb[:8].reshape(-1, 3), rgb[-8:].reshape(-1, 3)]), axis=0)
        manifest["bg"][n] = {"w": W, "h": H, "paper": "#%02x%02x%02x" % tuple(int(c) for c in paper)}

    with open(os.path.join(OUT, "manifest.js"), "w", encoding="utf-8") as f:
        f.write("// 由 tools/build_assets.py 生成，请勿手改\nwindow.ASSETS = ")
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    print("done")


if __name__ == "__main__":
    main()
