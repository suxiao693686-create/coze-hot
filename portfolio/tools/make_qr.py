"""生成作品集二维码（静态二维码，本身不会过期；只要网址能访问就能一直扫）。

用法（在仓库根目录运行）：
  python3 portfolio/tools/make_qr.py                      # 默认 GitHub Pages 网址
  python3 portfolio/tools/make_qr.py https://你的新网址/   # 换了托管地址时重新生成
输出到 portfolio/：
  qrcode.png       纯二维码，可以放进简历
  qrcode-card.png  带名字和网址的卡片版，可以单独发给别人
需要：pip install qrcode pillow
"""
import os
import sys

import qrcode
from PIL import Image, ImageDraw, ImageFont

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1] if len(sys.argv) > 1 else 'https://suxiao693686-create.github.io/coze-hot/portfolio/'
PAPER = (243, 239, 230)
INK = (29, 28, 26)
GRAPHITE = (87, 83, 76)
SEAL = (192, 57, 43)


def font(size, serif=True):
    paths = (['/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc', '/System/Library/Fonts/Songti.ttc',
              'C:/Windows/Fonts/simsun.ttc'] if serif else []) + [
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc', 'C:/Windows/Fonts/msyh.ttc']
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def center(d, y, text, f, fill, W):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def main():
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=20, border=2)
    qr.add_data(URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color=INK, back_color='white').convert('RGB')
    img.save(os.path.join(SITE, 'qrcode.png'))

    # 卡片版：宣纸底色、朱红印章，和作品集网站一个调子
    W, H = 900, 1260
    card = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(card)
    d.rectangle([34, 34, W - 34, H - 34], outline=INK, width=3)
    s = 132  # 印章
    sx, sy = (W - s) // 2, 96
    d.rectangle([sx, sy, sx + s, sy + s], fill=SEAL)
    d.rectangle([sx + 9, sy + 9, sx + s - 9, sy + s - 9], outline=(251, 238, 230), width=3)
    f_seal = font(46)
    for i, ch in enumerate('周琳'):
        d.text((sx + (s - d.textlength(ch, font=f_seal)) / 2, sy + 14 + i * 52), ch, font=f_seal, fill=(251, 238, 230))
    center(d, 266, '周琳 · 作品集', font(64), INK, W)
    center(d, 356, '广告策划 · 创意文案 · 品牌策划', font(32, serif=False), GRAPHITE, W)
    q = img.resize((560, 560), Image.NEAREST)
    card.paste(q, ((W - 560) // 2, 440))
    d.rectangle([(W - 560) // 2 - 2, 438, (W + 560) // 2 + 1, 1001], outline=INK, width=2)
    center(d, 1040, '扫码查看作品集', font(34, serif=False), INK, W)
    center(d, 1100, URL.replace('https://', ''), font(24, serif=False), GRAPHITE, W)
    card.save(os.path.join(SITE, 'qrcode-card.png'))
    print('QR ->', URL)


if __name__ == '__main__':
    main()
