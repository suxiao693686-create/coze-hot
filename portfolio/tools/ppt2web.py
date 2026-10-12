#!/usr/bin/env python3
"""把 PPT / PDF 转成作品集网页里能流畅翻阅的图片（PPT 里的视频也会一起转出来）。

用法（在仓库根目录运行）：
    python3 portfolio/tools/ppt2web.py 塔山石榴.pptx tashan
    python3 portfolio/tools/ppt2web.py 塔山石榴.pdf tashan --width 1920

输出到 portfolio/works/<id>/：
    slide-01.webp ...  每页大图（默认宽 1920，网页里全屏看）
    thumb-01.webp ...  每页缩略图（宽 400，翻阅器底部和详情页用）
    video-11.mp4 ...   PPT 里嵌的视频（压到 720p），网页里在原来的位置播放

最后会打印出要写进 js/data.js 的 deck 字段。

给 .pptx 时脚本会做三件事，让排版尽量和 PowerPoint 一致：
  1. 取出 PPT 里嵌入的字体，按 PPT 引用的名字装到本机（需要 fontTools）
  2. 关掉 LibreOffice 默认的「中文和英文/数字之间自动加空格」，否则标题会被挤得换行
  3. 用 LibreOffice 转 PDF，再逐页渲染
PPT 引用了但没有嵌入（或嵌入格式读不了）的字体，可以用 --alias 指定替代：
    --alias "字由点字典黑 Bold=字由点字典黑 1 Bold"
给 PowerPoint / WPS 自己导出的 PDF 则直接渲染，排版和原稿完全一致，但没有视频。

需要：pdftoppm（poppler-utils）、Pillow；.pptx 还需要 LibreOffice、fontTools、ffmpeg（有视频时）。
"""
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
WORKS = os.path.join(SITE, 'works')
PPT_EXT = ('.ppt', '.pptx', '.key', '.odp')


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def soffice(src, fmt, out_dir):
    run(['soffice', '--headless', '--convert-to', fmt, '--outdir', out_dir, src])
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(out_dir, base + '.' + fmt)
    if not os.path.exists(out):
        sys.exit('LibreOffice 转换失败：%s → %s' % (src, fmt))
    return out


# ---------- 1. 嵌入字体 ----------
def install_fonts(pptx, work_id, aliases):
    """取出 .pptx 里的嵌入字体（EOT 格式，未压缩的才能取），改名成 PPT 引用的字体名后装到本机。"""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print('  没装 fontTools（pip install fonttools），跳过嵌入字体，排版可能走样')
        return
    z = zipfile.ZipFile(pptx)
    pres = z.read('ppt/presentation.xml').decode('utf8')
    rels = z.read('ppt/_rels/presentation.xml.rels').decode('utf8')
    targets = {}
    for rel in re.findall(r'<Relationship [^>]+>', rels):
        rid = re.search(r'Id="([^"]+)"', rel).group(1)
        targets[rid] = re.search(r'Target="([^"]+)"', rel).group(1)

    fonts = {}  # PPT 引用的字体名 → TTF 字节
    for block in re.findall(r'<p:embeddedFont>.*?</p:embeddedFont>', pres, re.S):
        name = re.search(r'typeface="([^"]+)"', block).group(1)
        rid = re.search(r'<p:regular r:id="([^"]+)"', block)
        if not rid or rid.group(1) not in targets:
            continue
        data = z.read('ppt/' + targets[rid.group(1)])
        eot_size, font_size, _ver, flags = struct.unpack('<IIII', data[:16])
        if flags & 0x4 or flags & 0x10000000:
            print('  嵌入字体「%s」是压缩格式，读不了' % name)
            continue
        fonts[name] = data[eot_size - font_size:eot_size]
    if not fonts and not aliases:
        return

    # 读不了或没嵌入的字体：--alias 指定的优先，否则找同系列、同为 Bold 的字体顶上
    used = set()
    for n in z.namelist():
        if n.startswith('ppt/slides/slide') and n.endswith('.xml'):
            used.update(re.findall(r'<a:(?:latin|ea) typeface="([^"+][^"]*)"', z.read(n).decode('utf8', 'ignore')))
    for name, src in aliases.items():
        if src in fonts:
            fonts[name] = fonts[src]
    for name in sorted(used - set(fonts)):
        if name.endswith(' Bold'):
            same = [k for k in fonts if k.endswith(' Bold') and k[:4] == name[:4]]
            if same:
                fonts[name] = fonts[same[0]]
                print('  「%s」没有可用的嵌入字体，用「%s」代替' % (name, same[0]))

    font_dir = os.path.expanduser('~/.fonts/ppt2web-' + work_id)
    shutil.rmtree(font_dir, ignore_errors=True)
    os.makedirs(font_dir)
    tmp = tempfile.mkdtemp()
    for i, (name, data) in enumerate(sorted(fonts.items())):
        raw = os.path.join(tmp, 'raw.ttf')
        with open(raw, 'wb') as fh:
            fh.write(data)
        f = TTFont(raw)
        table = f['name']
        for nid in (1, 4, 16, 21):
            table.removeNames(nameID=nid)
        for lang in (0x409, 0x804):  # 英文、简体中文两套名字都写成 PPT 里的名字
            table.setName(name, 1, 3, 1, lang)
            table.setName(name, 4, 3, 1, lang)
            table.setName('Regular', 2, 3, 1, lang)
        f.save(os.path.join(font_dir, 'font%d.ttf' % i))
        print('  装好字体：%s' % name)
    shutil.rmtree(tmp, ignore_errors=True)
    run(['fc-cache', '-f', font_dir])


# ---------- 2. PPT → PDF ----------
def pptx_to_pdf(src, tmp):
    """先转成 ODP，关掉中西文之间的自动空格，再转 PDF。"""
    odp = soffice(src, 'odp', tmp)
    x = os.path.join(tmp, 'odp')
    with zipfile.ZipFile(odp) as z:
        z.extractall(x)
    for fn in ('styles.xml', 'content.xml'):
        p = os.path.join(x, fn)
        with open(p, encoding='utf8') as fh:
            s = fh.read()
        s = s.replace('style:text-autospace="ideograph-alpha"', 'style:text-autospace="none"')
        with open(p, 'w', encoding='utf8') as fh:
            fh.write(s)
    fixed = os.path.join(tmp, 'fixed.odp')
    with zipfile.ZipFile(fixed, 'w') as z:
        z.write(os.path.join(x, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)
        for root, _dirs, files in os.walk(x):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, x)
                if arc != 'mimetype':
                    z.write(full, arc, compress_type=zipfile.ZIP_DEFLATED)
    return soffice(fixed, 'pdf', tmp)


# ---------- 3. 视频 ----------
def extract_videos(pptx, out_dir, rel_dir):
    """找出每页里的视频和它在页面上的位置，压成 720p 的网页视频。"""
    if not shutil.which('ffmpeg'):
        print('  没有 ffmpeg，跳过 PPT 里的视频')
        return []
    z = zipfile.ZipFile(pptx)
    pres = z.read('ppt/presentation.xml').decode('utf8')
    cx, cy = map(int, re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', pres).groups())
    rels = z.read('ppt/_rels/presentation.xml.rels').decode('utf8')
    targets = {}
    for rel in re.findall(r'<Relationship [^>]+>', rels):
        targets[re.search(r'Id="([^"]+)"', rel).group(1)] = re.search(r'Target="([^"]+)"', rel).group(1)
    order = [targets[r] for r in re.findall(r'<p:sldId [^>]*r:id="([^"]+)"', pres)]

    videos = []
    for page, slide in enumerate(order, 1):
        xml = z.read('ppt/' + slide).decode('utf8')
        if 'videoFile' not in xml:
            continue
        rel_path = 'ppt/slides/_rels/' + os.path.basename(slide) + '.rels'
        srels = z.read(rel_path).decode('utf8')
        smap = {}
        for rel in re.findall(r'<Relationship [^>]+>', srels):
            smap[re.search(r'Id="([^"]+)"', rel).group(1)] = re.search(r'Target="([^"]+)"', rel).group(1)
        for k, pic in enumerate(re.findall(r'<p:pic>.*?</p:pic>', xml, re.S)):
            m = re.search(r'<a:videoFile r:link="([^"]+)"', pic)
            pos = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>', pic)
            if not m or not pos or m.group(1) not in smap:
                continue
            media = os.path.normpath(os.path.join('ppt/slides', smap[m.group(1)])).replace(os.sep, '/')
            name = 'video-%d%s.mp4' % (page, '' if k == 0 else '-%d' % k)
            raw = os.path.join(out_dir, '_raw' + os.path.splitext(media)[1])
            with open(raw, 'wb') as fh:
                fh.write(z.read(media))
            print('  转视频：第 %d 页 → %s' % (page, name))
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw,
                            '-vf', "scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))'",
                            '-c:v', 'libx264', '-crf', '27', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart',
                            os.path.join(out_dir, name)], check=True)
            os.remove(raw)
            x, y, w, h = map(int, pos.groups())
            videos.append({'page': page, 'src': rel_dir + name,
                           'x': round(x / cx * 100, 2), 'y': round(y / cy * 100, 2),
                           'w': round(w / cx * 100, 2), 'h': round(h / cy * 100, 2)})
    return videos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='PPT 或 PDF 文件')
    ap.add_argument('id', help='作品 id（英文），图片会放到 portfolio/works/<id>/')
    ap.add_argument('--width', type=int, default=1920, help='大图宽度，默认 1920')
    ap.add_argument('--quality', type=int, default=82, help='WebP 质量，默认 82')
    ap.add_argument('--alias', action='append', default=[], metavar='缺的字体=用哪个字体代替',
                    help='PPT 引用但没有嵌入的字体，用另一个嵌入字体代替（可写多次）')
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    ext = os.path.splitext(src)[1].lower()
    if ext != '.pdf' and ext not in PPT_EXT:
        sys.exit('只支持 .pdf / .ppt / .pptx / .key / .odp：' + src)
    aliases = dict(a.split('=', 1) for a in args.alias)

    out_dir = os.path.join(WORKS, args.id)
    rel_dir = os.path.relpath(out_dir, SITE).replace(os.sep, '/') + '/'
    if os.path.isdir(out_dir):
        for f in glob.glob(os.path.join(out_dir, 'slide-*')) + glob.glob(os.path.join(out_dir, 'thumb-*')) + \
                glob.glob(os.path.join(out_dir, 'video-*')):
            os.remove(f)
    os.makedirs(out_dir, exist_ok=True)

    tmp = tempfile.mkdtemp(prefix='ppt2web-')
    videos = []
    try:
        if ext == '.pdf':
            pdf = src
        else:
            if ext == '.pptx':
                print('准备字体 …')
                install_fonts(src, args.id, aliases)
            print('用 LibreOffice 把 PPT 转成 PDF …')
            pdf = pptx_to_pdf(src, tmp)
            if ext == '.pptx':
                videos = extract_videos(src, out_dir, rel_dir)

        print('把每一页渲染成图片 …')
        run(['pdftoppm', '-png', '-scale-to-x', str(args.width), '-scale-to-y', '-1', pdf, os.path.join(tmp, 'p')])
        pages = sorted(glob.glob(os.path.join(tmp, 'p-*.png')),
                       key=lambda p: int(p.rsplit('-', 1)[1].split('.')[0]))
        if not pages:
            sys.exit('没有渲染出任何页面')

        digits = max(2, len(str(len(pages))))
        total = 0
        for i, page in enumerate(pages, 1):
            im = Image.open(page).convert('RGB')
            name = str(i).zfill(digits)
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

    for v in videos:
        total += os.path.getsize(os.path.join(SITE, v['src']))
    print('\n完成：%d 页%s，共 %.1f MB，放在 %s' % (
        len(pages), '、%d 个视频' % len(videos) if videos else '', total / 1024 / 1024, rel_dir))
    print('在 js/data.js 的作品里写上：')
    if videos:
        print("  deck: { dir: '%s', count: %d, videos: [" % (rel_dir, len(pages)))
        for v in videos:
            print("    { page: %d, src: '%s', x: %s, y: %s, w: %s, h: %s }," % (
                v['page'], v['src'], v['x'], v['y'], v['w'], v['h']))
        print('  ] },')
    else:
        print("  deck: { dir: '%s', count: %d }," % (rel_dir, len(pages)))


if __name__ == '__main__':
    main()
