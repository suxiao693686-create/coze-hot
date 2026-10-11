"""生成油纸伞网站二维码（静态二维码，本身永不过期；只要网址能访问就能一直扫）。

用法：
  python3 tools/make_qr.py                       # 默认 GitHub Pages 网址
  python3 tools/make_qr.py https://你的网址/      # 换了托管地址时重新生成
输出：qrcode.png（纯二维码）和 qrcode-poster.png（带标题的海报版）
需要：pip install qrcode pillow
"""
import os
import sys

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1] if len(sys.argv) > 1 else "https://suxiao693686-create.github.io/coze-hot/youzhisan/"
RED = (168, 49, 43)
PAPER = (240, 230, 212)


def font(size):
    for p in ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
              "/System/Library/Fonts/STHeiti Medium.ttc", "C:/Windows/Fonts/simkai.ttf", "C:/Windows/Fonts/msyh.ttc"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=2)
    qr.add_data(URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color=(60, 30, 26), back_color="white").convert("RGB")
    img.save(os.path.join(ROOT, "qrcode.png"))

    # 海报版
    W, H = 900, 1200
    poster = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(poster)
    d.rectangle([30, 30, W - 30, H - 30], outline=RED, width=6)
    d.rectangle([44, 44, W - 44, H - 44], outline=RED, width=2)
    title = "油纸伞"
    f1, f2, f3 = font(96), font(40), font(30)
    tw = d.textlength(title, font=f1)
    d.text(((W - tw) / 2, 110), title, font=f1, fill=(120, 100, 90))
    sub = "非遗文化主题网站 · 一竹一纸一桐油"
    d.text(((W - d.textlength(sub, font=f2)) / 2, 240), sub, font=f2, fill=RED)
    q = img.resize((560, 560), Image.NEAREST)
    poster.paste(q, ((W - 560) // 2, 330))
    tip = "扫码浏览 · 电脑端观看效果更佳"
    d.text(((W - d.textlength(tip, font=f3)) / 2, 930), tip, font=f3, fill=(90, 60, 50))
    # 印章
    sx, sy, s = W // 2 - 60, 1000, 120
    d.rectangle([sx, sy, sx + s, sy + s], fill=RED)
    d.text((sx + 36, sy + 6), "非", font=font(48), fill="white")
    d.text((sx + 36, sy + 60), "遺", font=font(48), fill="white")
    poster.save(os.path.join(ROOT, "qrcode-poster.png"))
    print("QR ->", URL)


if __name__ == "__main__":
    main()
