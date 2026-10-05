#!/usr/bin/env bash
# 一键生成片头视频：bash build.sh   （每期改 intro.html 顶部的 CONFIG 即可）
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-build}
OUT=${OUT:-00猫片头.mp4}
export TTS_MODEL=${TTS_MODEL:-$WORK/vits-melo-tts-zh_en}
mkdir -p "$WORK"

# 1) 离线配音模型（首次运行自动下载）
if [ ! -f "$TTS_MODEL/model.onnx" ]; then
  curl -sSL -o "$WORK/melo.tar.bz2" https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-zh_en.tar.bz2
  tar xjf "$WORK/melo.tar.bz2" -C "$WORK"
fi

# 2) 配音（再调高一点音调，更像小猫）
cute() { ffmpeg -y -loglevel error -i "$1" -af "asetrate=44100*1.12,aresample=44100,atempo=1/1.12" -ar 44100 -ac 1 "$2"; }
python3 tts.py "开模！" "$WORK/raw1.wav" 1.0 >/dev/null
python3 tts.py "零零猫塑料小课堂，开课啦！" "$WORK/raw2.wav" 1.15 >/dev/null
cute "$WORK/raw1.wav" "$WORK/voice1.wav"
cute "$WORK/raw2.wav" "$WORK/voice2.wav"

# 3) 音乐 + 音效 + 配音混音
python3 audio.py "$WORK/voice1.wav" "$WORK/voice2.wav" "$WORK/audio.wav"

# 4) 逐帧渲染画面
rm -rf "$WORK/frames"
NODE_PATH=$(npm root -g) node render.js "$WORK/frames"

# 5) 合成 MP4（抖音竖屏 1080x1920, 30fps）
ffmpeg -y -loglevel error -framerate 30 -i "$WORK/frames/f_%04d.png" -i "$WORK/audio.wav" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "完成: $OUT"
