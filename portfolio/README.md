# 周琳 · 作品集网站（纸上走廊）

一条用铅笔画出来的走廊：向下滚动往里走，推开门进入房间。灵感来自 [ITom 的 3D 作品集](https://github.com/ITomPoland/portfolio-itom)，这里用纯 HTML / CSS / JS（CSS 3D）重新做了一版，不需要安装或构建，直接放到 GitHub Pages 就能访问，手机也能流畅打开。

线上地址：**https://suxiao693686-create.github.io/coze-hot/portfolio/**

`qrcode.png` 是指向这个网址的二维码（可以放进简历），`qrcode-card.png` 是带名字的卡片版（可以单独发给别人）。二维码是静态的，不会过期。

## 发布

GitHub Pages 从仓库的 `gh-pages` 分支发布。改完作品后把改动推到 `gh-pages`，1～2 分钟后线上就会更新：

```bash
git push origin <改动所在的分支>:gh-pages
```

仓库根目录的 `.nojekyll` 让 Pages 直接发布静态文件，不要删除。国内部分网络访问 github.io 会慢，偶尔打不开；需要更稳的话，可以把整个仓库的静态文件传到腾讯云 COS、阿里云 OSS 这类静态网站托管，再用 `python3 portfolio/tools/make_qr.py 新网址` 重新生成二维码（作品集里的 H5 和网页作品引用了仓库里的 `hbn-h5/`、`youzhisan/`，要一起传）。

## 页面结构

| 位置 | 内容 |
| --- | --- |
| 撕纸加载 | 纸张从中间撕开，进入走廊；切换房间时也用同样的撕纸转场 |
| 走廊入口 | 手绘大字「周琳」、打字机副标题、漂浮涂鸦（跟随鼠标视差） |
| 走廊墙面 | 左右三扇门（作品 / 关于 / 能力），挂着两个作品画框（有作品时显示黑白线稿、悬停上色；没有时是「待落笔」空框），贴着关键数据便利贴 |
| 走廊尽头 | 「联系」的门 |
| Room 01 作品 | 按模块分区（目前有「PPT 设计」「文字」「视觉设计」三个模块）。画框悬停时从鼠标位置开始上色；点开是案例详情，PPT 作品可以全屏逐页翻阅（键盘 ← →、手机左右滑动、底部缩略图跳页） |
| Room 02 关于 | 拍立得照片位、自我介绍、教育、三个关键词、经历时间线 |
| Room 03 工作室 | 技能便利贴、奖状墙（国家级 / 省级 / 校级印章）、证书 |
| 联系 | 一封撕边信纸：邮箱、电话、城市，可一键复制 |

右侧的小地图可以直接跳到某扇门，顶部导航可以直接进入任意房间，按 `Esc` 返回。每个房间都有自己的链接：`#works`、`#about`、`#skills`、`#contact`，作品详情页是 `#work/作品id`，可以单独发给别人。

## 怎么加作品

作品内容都在 `js/data.js`：`MODULES` 是作品模块（按顺序显示），`WORKS` 是作品，每件作品用 `module` 指定属于哪个模块。

### PPT 作品

PPT 不直接放进网页（几十 MB，打开慢，手机也打不开），而是每页转成一张压缩过的图片，在网页里像放映一样翻阅：

1. 用 PowerPoint / WPS 把 PPT **导出为 PDF**（字体和排版和原稿一模一样）
2. 在仓库根目录运行：
   ```bash
   python3 portfolio/tools/ppt2web.py 塔山石榴.pdf tashan
   ```
   图片会生成到 `portfolio/works/tashan/`（每页一张大图 + 一张缩略图），最后打印出一行 `deck: { ... }`
3. 在 `data.js` 里把对应作品的 `placeholder: true` 去掉，填上标题、简介，再粘贴那行 `deck`

封面默认用 PPT 第一页，想换就写 `cover`。

### 图片作品（文案排版、海报、长图）

用 `tools/img2web.py`：

- 一组图片 → 逐页翻阅（按文件名排序，横版竖版都行）：
  ```bash
  python3 portfolio/tools/img2web.py 文旅宣传文/ zhaoyanming
  ```
- 一张长图（公众号长文、长海报）→ 从上往下阅读，像在手机上读公众号：
  ```bash
  python3 portfolio/tools/img2web.py 长图.jpg jiehou --long
  ```
- 几张长图拼成一篇（网页的几个页面、几张信息图），每张是一个部分，详情页里可以点某个部分直接跳过去：
  ```bash
  python3 portfolio/tools/img2web.py 网页截图/ youzhisan-web --long --width 1366 --names "首页,介绍,制作流程,保护创新,IP 形象"
  ```

脚本最后会打印出 `deck` 或 `article` 字段，粘贴到 `data.js` 的作品里。横版图片做竖版卡片封面时，可以用 `coverPos: '12% 50%'` 指定露出哪一块。

### 视频

```bash
python3 portfolio/tools/vid2web.py 宣传片.mov xunwei
```

转成 1080p、码率不超过 3 Mbps 的 H.264 MP4（手机拍的 HEVC、4K、60 帧都能转），再截一帧做封面。把打印出来的 `video` 字段写进作品，详情页里就能直接播放。

### H5 小游戏

作品里写 `play: { src: '../hbn-h5/' }`，详情页会出现一个手机框，点「在这里试玩」就在框里加载游戏。只在作品集自己的网站上（和游戏同一个域名）显示；在别处预览时只留「在线体验」按钮。

### 其他作品

把一个 `placeholder: true` 的「待落笔」空框，换成 `data.js` 注释里的作品模板，填好 `id`、`title`、`cover`、`images`、`case` 等字段。新的作品类型就在 `MODULES` 里加一个模块。走廊墙上的两个画框会从不同模块里各取第一件作品。

## 其他可以改的

- **照片**：在 `data.js` 的 `PROFILE` 里加 `photo: 'covers/me.jpg'`，关于页的拍立得就会显示照片
- **文字**：个人简介、经历、技能、奖项都在 `PROFILE` 里
- **走廊布局**：`js/main.js` 顶部的 `LAYOUT`（门、画框、便利贴的位置，`d` 是离入口的深度）
- **颜色 / 字体**：`css/style.css` 开头的 `:root` 变量（纸色、墨色、朱红）

## 文件

```
portfolio/
├── index.html
├── css/style.css
├── js/data.js        ← 内容（主要改这个）
├── js/main.js        ← 走廊、转场、房间逻辑
├── covers/           ← 作品封面和作品图
├── works/            ← 作品转出来的网页图片和视频（每件作品一个文件夹）
├── tools/ppt2web.py  ← PPT / PDF 转网页图片（含 PPT 里的视频）
├── tools/img2web.py  ← 图片 / 长图转网页格式
├── tools/vid2web.py  ← 视频转网页格式
├── tools/make_qr.py  ← 生成作品集二维码
├── qrcode.png / qrcode-card.png  ← 作品集二维码
└── fonts/CabinSketch-Bold.ttf   ← 手绘英文字体（SIL OFL 开源授权）
```

本地预览：在仓库根目录运行 `python3 -m http.server`，打开 `http://localhost:8000/portfolio/`。
