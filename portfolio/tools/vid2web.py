#!/usr/bin/env python3
"""把视频转成作品集网页里能流畅播放的格式。

用法（在仓库根目录运行）：
    python3 portfolio/tools/vid2web.py 宣传片.mov xunwei
    python3 portfolio/tools/vid2web.py 宣传片.mov xunwei --poster 2

输出到 portfolio/works/<id>/：
    <id>.mp4      H.264 + AAC，最高 1080p / 30 帧，码率不超过 3 Mbps，边下边播
    poster.webp   封面帧（默认取第 1 秒），也用作作品卡片的封面

手机拍的 HEVC（.mov）、4K、60 帧的视频，很多浏览器放不了或者太大，转完就都能放了。
最后会打印出要写进 js/data.js 的 video 字段。需要：ffmpeg、Pillow。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
WORKS = os.path.join(SITE, 'works')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='视频文件')
    ap.add_argument('id', help='作品 id（英文），输出到 portfolio/works/<id>/')
    ap.add_argument('--poster', type=float, default=1.0, help="封面取第几秒，默认 1.0")
    args = ap.parse_args()
    if not os.path.isfile(args.src):
        sys.exit('找不到视频：' + args.src)

    out_dir = os.path.join(WORKS, args.id)
    os.makedirs(out_dir, exist_ok=True)
    rel_dir = os.path.relpath(out_dir, SITE).replace(os.sep, '/') + '/'
    mp4 = os.path.join(out_dir, args.id + '.mp4')

    info = json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
         '-of', 'json', args.src], check=True, capture_output=True).stdout)['streams'][0]
    w, h = info['width'], info['height']
    landscape = w >= h
    scale = "scale='min(1920,iw)':-2" if landscape else "scale=-2:'min(1920,ih)'"

    print('转视频（4K 的源文件可能要几分钟）…')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', args.src,
                    '-vf', scale + ",fps='min(30,source_fps)'",
                    '-c:v', 'libx264', '-crf', '24', '-maxrate', '3000k', '-bufsize', '6000k',
                    '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', mp4], check=True)

    print('截封面 …')
    tmp = tempfile.mkdtemp()
    png = os.path.join(tmp, 'poster.png')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(args.poster), '-i', mp4,
                    '-frames:v', '1', png], check=True)
    Image.open(png).convert('RGB').save(os.path.join(out_dir, 'poster.webp'), 'WEBP', quality=82, method=6)

    ratio = round(w / h, 4)
    print('\n完成：%.1f MB，放在 %s' % (os.path.getsize(mp4) / 1024 / 1024, rel_dir))
    print('在 js/data.js 的作品里写上：')
    print("  video: { src: '%s%s.mp4', poster: '%sposter.webp', ratio: %s }," % (rel_dir, args.id, rel_dir, ratio))


if __name__ == '__main__':
    main()
