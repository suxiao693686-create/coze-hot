# 黑底白线讲解视频 · 一句话出片

给一个主题，自动做出一条讲解短视频：

- **画风固定**：黑底星空，白色线条图标一笔一笔画出来，重点词紫色发光，底部大字幕，顶部标题和进度条
- **一镜到底**：所有画面排在一张大画布上，镜头顺着一条发光的线滑到下一个画面，不是一页一页翻
- **配乐**：真钢琴采样 + 鼓 + 铺底，按"钩子 / 解释 / 结尾"现场编曲，换场卡在节拍上；也可以换成你自己的音乐
- **结构固定**：钩子（3 秒抓住人）→ 解释（一二三讲清楚）→ 结尾（金句 + 关注 + 下期预告）
- **全自动**：查资料、写稿、配音、字幕、音效、封面一次出齐

样片脚本：[`examples/刷短视频停不下来.json`](examples/刷短视频停不下来.json)

---

## 怎么用（最简单）

在 Claude Code 里打开这个仓库，直接说：

> 做一条讲解视频，主题：为什么熬夜之后反而不困

Claude 会按 [`.claude/skills/explainer-video/SKILL.md`](../.claude/skills/explainer-video/SKILL.md) 里的流程，自己查资料、写稿、检查画面、出片，最后把视频和封面发给你。80 秒左右的片子，几分钟就能做好。

不满意就接着说，比如：

- "开头再狠一点" / "第三点换个例子"
- "换成女声" / "语速快一点"
- "改成横屏" / "强调色换成金色" / "背景换成点阵"
- "账号名写 @我的账号"
- "先给我看稿子，我确认了再出片"

## 每次会得到什么

都在 `output/<主题>/` 里：

| 文件 | 是什么 |
|---|---|
| `video.mp4` | 成片，1080×1920，30 帧，自带配音、字幕、音效 |
| `cover.png` | 封面图（大标题 + 重点词发光） |
| `subtitles.srt` | 字幕文件，可以导入剪映再改 |
| `contact.png` | 每个画面的截图总览，一眼检查排版 |
| `narration.txt` | 旁白全文 |

## 风格：哪些固定，哪些能改

| 固定（保证每条视频风格统一） | 能改（写在脚本里，或者直接跟 Claude 说） |
|---|---|
| 黑底、白色线条、一笔一笔画出 | 强调色：紫 / 青 / 金 / 红 / 绿 |
| 重点词发光、故障风闪入 | 背景：星空 / 点阵波浪 / 纯黑 |
| 字幕大字白色黑描边 | 竖屏 9:16 / 横屏 16:9 |
| 钩子 → 解释 → 结尾 | 账号名、音色、语速 |
| 一镜到底的镜头 | 配乐：舒缓 / 悬疑 / 轻快 / 你自己的音乐 |

建议同一个账号固定一套账号名、强调色、背景和音色，看多了观众一眼就能认出你。

## 关于配音（重要）

| 配音 | 效果 | 什么时候用 |
|---|---|---|
| 微软 Edge 朗读（edge） | 最好听，免费，男女声都有（云希、云健、晓晓…） | 默认优先用它 |
| 谷歌翻译朗读（google） | 女声，音质一般 | 微软用不了时自动换成它 |
| 不配音（none） | 没声音，只有字幕 | 想自己在剪映里配音时 |

**在云端用（Claude 网页 / App）**：云端环境默认的网络设置挡住了微软配音的地址 `speech.platform.bing.com`，所以会自动换成谷歌女声。想用微软的声音，在云端环境设置里把这个地址加进允许名单：会话标题栏的环境菜单 → Edit → Network access → Allowed domains 加上 `speech.platform.bing.com`（[官方步骤](https://code.claude.com/docs/en/cloud-environments#network-access)）。

**在自己电脑上用**：一般直接就能用微软的声音。

## 关于配乐

默认每条视频现场编一段曲子：真钢琴（Salamander 大钢琴采样）+ 鼓 + 合成铺底和贝斯。开场有电影感的重低音，进正文前一个反向镲，正文鼓和贝斯进来，结尾鼓停只留钢琴。跟 Claude 说"配乐换成悬疑的 / 轻快的"就行。

**想要更好听**：用你自己的音乐。剪映曲库、Suno 生成的都可以，把文件放进仓库，跟 Claude 说"配乐用 music/xxx.mp3"。程序会自动循环、淡入淡出，说话时把音乐压低。

## 在自己电脑上运行

需要先装好 Python 3.9+ 和 ffmpeg（Mac：`brew install ffmpeg`；Windows：`winget install ffmpeg`），然后：

```bash
cd explainer-video
pip install -r requirements.txt
python3 -m playwright install chromium     # 装一个给程序用的浏览器，只需一次
python3 make_video.py examples/刷短视频停不下来.json
```

Windows 上把 `python3` 换成 `python`。第一次运行会自动下载思源黑体（约 20MB）和乐器采样（约 40MB），以后就不用再下载了。字体下载不了会用系统自带的中文字体。

## 手动命令

```bash
python3 make_video.py check   scripts/主题.json      # 只检查脚本有没有写错
python3 make_video.py scripts/主题.json --preview   # 几秒钟出截图总览，先看排版
python3 make_video.py scripts/主题.json             # 出成片
python3 make_video.py icons brain money sleep       # 查图标（英文关键词）
```

常用选项：`--tts edge|google|none`（配音引擎）、`--voice zh-CN-XiaoxiaoNeural`（音色）、`--no-music`（不要背景音）、`--out 目录`。

脚本怎么写（场景类型、字段、写稿规则）都在 [SKILL.md](../.claude/skills/explainer-video/SKILL.md)。

## 原理（白话版）

画面不是 AI"生成"的，而是用网页代码"画"出来的：浏览器按时间把每一帧摆好，每秒拍 30 张照片，再用 ffmpeg 拼成视频。所以：

- 文字一个都不会错，同一份脚本每次出来都一样
- 不花钱（除了 Claude 本身），也没有版权问题，音效和背景音都是代码合成的
- 做不了真人、实拍这类画面。这种还是用即梦、可灵

## 文件说明

```
explainer-video/
├── make_video.py      主程序：检查脚本 → 配音 → 时间轴 → 截图 → 混音 → 出片
├── tts.py             配音（edge / google / none）和字幕对时
├── music.py           配乐：按段落编曲（钢琴 / 鼓 / 贝斯 / 铺底）
├── sound.py           人声处理、音效、混音
├── assets.py          第一次运行时下载乐器采样
├── render.py          用无头浏览器逐帧截图、压成视频
├── renderer/          画面引擎（HTML + JS），所有场景类型都在 engine.js
├── examples/          示例脚本
├── scripts/           你的视频脚本放这里
└── output/            成片输出（不提交到 git）
```

## 致谢

- 图标：[Lucide](https://lucide.dev)（ISC 许可，见 `renderer/LICENSE-lucide.txt`）
- 字体：思源黑体 Noto Sans SC（SIL OFL 许可），运行时自动下载
- 钢琴：Salamander Grand Piano V3，作者 Alexander Holm（CC BY 3.0），运行时自动下载
- 鼓和音效：Sonic Pi 采样库（CC0 公有领域），运行时自动下载
- 风格参考了 [anything2explainer](https://github.com/Vincentwei1021/anything2explainer) 的黑底白线讲解风，这里的代码是重新写的、更轻量的版本
