#!/usr/bin/env python3
"""把 PPT / PDF 转成作品集网页里能流畅翻阅的图片。

用法（在仓库根目录运行）：
    python3 portfolio/tools/ppt2web.py 塔山石榴.pdf tashan
    python3 portfolio/tools/ppt2web.py 塔山石榴.pptx tashan --width 1920

输出到 portfolio/works/<id>/：
    slide-01.webp ...  每页大图（默认宽 1920，网页里全屏看）
    thumb-01.webp ...  每页缩略图（宽 400，翻阅器底部和详情页用）

最后会打印出要写进 js/data.js 的 deck 字段。

建议优先用 PowerPoint / WPS 自己导出的 PDF：字体和排版和原稿完全一致。
直接给 .pptx 也可以，脚本会用 LibreOffice 转，但电脑上没有原稿字体时排版可能走样。
需要：pdftoppm（poppler-utils）、Pillow；转 .pptx 还需要 LibreOffice。
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WORKS = os.path.join(os.path.dirname(HERE), 'works')


def to_pdf(src, tmp):
    ext = os.path.splitext(src)[1].lower()
    if ext == '.pdf':
        return src
    if ext not in ('.ppt', '.pptx', '.key', '.odp'):
        sys.exit('只支持 .pdf / .ppt / .pptx / .key / .odp：' + src)
    print('用 LibreOffice 把 PPT 转成 PDF …')
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, src],
                   check=True, stdout=subprocess.DEVNULL)
    out = glob.glob(os.path.join(tmp, '*.pdf'))
    if not out:
        sys.exit('PPT 转 PDF 失败')
    return out[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='PPT 或 PDF 文件')
    ap.add_argument('id', help='作品 id（英文），图片会放到 portfolio/works/<id>/')
    ap.add_argument('--width', type=int, default=1920, help='大图宽度，默认 1920')
    ap.add_argument('--quality', type=int, default=82, help='WebP 质量，默认 82')
    args = ap.parse_args()

    out_dir = os.path.join(WORKS, args.id)
    tmp = tempfile.mkdtemp(prefix='ppt2web-')
    try:
        pdf = to_pdf(os.path.abspath(args.src), tmp)
        print('把每一页渲染成图片 …')
        subprocess.run(['pdftoppm', '-png', '-scale-to-x', str(args.width), '-scale-to-y', '-1',
                        pdf, os.path.join(tmp, 'p')], check=True)
        pages = sorted(glob.glob(os.path.join(tmp, 'p-*.png')),
                       key=lambda p: int(p.rsplit('-', 1)[1].split('.')[0]))
        if not pages:
            sys.exit('没有渲染出任何页面')

        if os.path.isdir(out_dir):
            for f in glob.glob(os.path.join(out_dir, 'slide-*.webp')) + glob.glob(os.path.join(out_dir, 'thumb-*.webp')):
                os.remove(f)
        os.makedirs(out_dir, exist_ok=True)

        width = max(2, len(str(len(pages))))
        total = 0
        for i, page in enumerate(pages, 1):
            im = Image.open(page).convert('RGB')
            name = str(i).zfill(width)
            big = os.path.join(out_dir, 'slide-%s.webp' % name)
            im.save(big, 'WEBP', quality=args.quality, method=6)
            th = im.copy()
            th.thumbnail((400, 400 * im.height // im.width), Image.LANCZOS)
            small = os.path.join(out_dir, 'thumb-%s.webp' % name)
            th.save(small, 'WEBP', quality=70, method=6)
            total += os.path.getsize(big) + os.path.getsize(small)
            print('  第 %d 页  %d KB' % (i, os.path.getsize(big) // 1024))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    rel = os.path.relpath(out_dir, os.path.dirname(HERE)).replace(os.sep, '/') + '/'
    print('\n完成：%d 页，共 %.1f MB，放在 %s' % (len(pages), total / 1024 / 1024, rel))
    print('在 js/data.js 的作品里写上：')
    print("  deck: { dir: '%s', count: %d }," % (rel, len(pages)))


if __name__ == '__main__':
    main()
