#!/usr/bin/env python3
"""把作品图片转成作品集网页用的格式。

两种用法（在仓库根目录运行）：

1. 一组图片 → 逐页翻阅（和 PPT 一样的翻阅器，横版竖版都行）
       python3 portfolio/tools/img2web.py 文旅宣传文/ zhaoyanming
   按文件名顺序排页，输出 slide-01.webp … 和缩略图 thumb-01.webp …

2. 长图（公众号长文、长海报、网页截图）→ 从上往下阅读
       python3 portfolio/tools/img2web.py 长图.jpg jiehou --long
       python3 portfolio/tools/img2web.py 网页截图/ web --long --width 1366 --names "首页,介绍,制作流程"
   每张长图切成几段 long-01.webp …（网页里无缝拼起来，边读边加载），再截第一张的顶部做 4:5 封面 cover.webp。
   给文件夹时，里面每张长图按文件名顺序成为文章的一个部分。

输出到 portfolio/works/<id>/，最后打印出要写进 js/data.js 的字段。
需要：Pillow。
"""
import argparse
import glob
import os
import sys

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
WORKS = os.path.join(SITE, 'works')
EXT = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')


def load(path):
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert('RGB')


def fit(im, longest):
    w, h = im.size
    s = min(1.0, longest / max(w, h))
    return im.resize((round(w * s), round(h * s)), Image.LANCZOS) if s < 1 else im


def clean(out_dir, patterns):
    for p in patterns:
        for f in glob.glob(os.path.join(out_dir, p)):
            os.remove(f)


def deck(files, out_dir, rel_dir, longest, quality):
    clean(out_dir, ['slide-*', 'thumb-*'])
    digits = max(2, len(str(len(files))))
    total, ratio = 0, None
    for i, f in enumerate(files, 1):
        im = load(f)
        if ratio is None:
            ratio = im.width / im.height
        name = str(i).zfill(digits)
        big = os.path.join(out_dir, 'slide-%s.webp' % name)
        fit(im, longest).save(big, 'WEBP', quality=quality, method=6)
        small = os.path.join(out_dir, 'thumb-%s.webp' % name)
        fit(im, 480).save(small, 'WEBP', quality=70, method=6)
        total += os.path.getsize(big) + os.path.getsize(small)
        print('  第 %d 页  %s  %d KB' % (i, os.path.basename(f), os.path.getsize(big) // 1024))
    print('\n完成：%d 页，共 %.1f MB，放在 %s' % (len(files), total / 1024 / 1024, rel_dir))
    print('在 js/data.js 的作品里写上：')
    print("  deck: { dir: '%s', count: %d, ratio: %s }," % (rel_dir, len(files), round(ratio, 4)))


def long_image(files, out_dir, rel_dir, width, seg, quality, names):
    """长图切段。多张长图（比如网页的几个页面）会按顺序拼成一篇，每张是一个部分。"""
    clean(out_dir, ['long-*', 'cover.webp'])
    parts, total = [], 0
    for k, path in enumerate(files, 1):
        im = load(path)
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        w, h = im.size
        prefix = 'long-' if len(files) == 1 else 'long-%d-' % k
        n = -(-h // seg)
        for i in range(n):
            part = im.crop((0, i * seg, w, min(h, (i + 1) * seg)))
            p = os.path.join(out_dir, '%s%02d.webp' % (prefix, i + 1))
            part.save(p, 'WEBP', quality=quality, method=6)
            total += os.path.getsize(p)
        if k == 1:
            cover = im.crop((0, 0, w, min(h, round(w * 5 / 4))))
            cp = os.path.join(out_dir, 'cover.webp')
            fit(cover, 1000).save(cp, 'WEBP', quality=quality, method=6)
            total += os.path.getsize(cp)
        name = names[k - 1] if k <= len(names) else os.path.splitext(os.path.basename(path))[0]
        parts.append((name, prefix, n, w, h))
        print('  %s：%d×%d，切成 %d 段' % (name, w, h, n))
    print('\n完成：共 %.1f MB，放在 %s' % (total / 1024 / 1024, rel_dir))
    print('在 js/data.js 的作品里写上：')
    print("  cover: '%scover.webp'," % rel_dir)
    if len(parts) == 1:
        name, prefix, n, w, h = parts[0]
        print("  article: { dir: '%s', count: %d, segment: %d, width: %d, height: %d }," % (rel_dir, n, seg, w, h))
    else:
        print("  article: { dir: '%s', segment: %d, parts: [" % (rel_dir, seg))
        for name, prefix, n, w, h in parts:
            print("    { name: '%s', prefix: '%s', count: %d, width: %d, height: %d }," % (name, prefix, n, w, h))
        print('  ] },')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='图片文件夹，或者一张图片')
    ap.add_argument('id', help='作品 id（英文），输出到 portfolio/works/<id>/')
    ap.add_argument('--long', action='store_true', help='长图模式：从上往下阅读')
    ap.add_argument('--longest', type=int, default=1920, help='翻阅模式：大图最长边，默认 1920')
    ap.add_argument('--width', type=int, default=1080, help='长图模式：宽度，默认 1080')
    ap.add_argument('--segment', type=int, default=2400, help='长图模式：每段高度，默认 2400')
    ap.add_argument('--quality', type=int, default=82, help='WebP 质量，默认 82')
    ap.add_argument('--names', default='', help='长图模式：每个部分的名字，用逗号隔开，比如 "首页,介绍,制作流程"')
    args = ap.parse_args()

    if os.path.isdir(args.src):
        files = sorted(f for f in glob.glob(os.path.join(args.src, '*')) if f.lower().endswith(EXT))
    else:
        files = [args.src] if args.src.lower().endswith(EXT) else []
    if not files:
        sys.exit('没有找到图片：' + args.src)

    out_dir = os.path.join(WORKS, args.id)
    os.makedirs(out_dir, exist_ok=True)
    rel_dir = os.path.relpath(out_dir, SITE).replace(os.sep, '/') + '/'
    if args.long:
        names = [x.strip() for x in args.names.split(',') if x.strip()]
        long_image(files, out_dir, rel_dir, args.width, args.segment, args.quality, names)
    else:
        deck(files, out_dir, rel_dir, args.longest, args.quality)


if __name__ == '__main__':
    main()
