#!/usr/bin/env bash
# 一键生成片头视频：bash build.sh   （每期改 intro.html 顶部的 CONFIG 即可）
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-build}
OUT=${OUT:-00猫片头.mp4}
export TTS_MODEL=${TTS_MODEL:-$WORK/kokoro-multi-lang-v1_1}
mkdir -p "$WORK"

# 1) 离线配音模型（首次运行自动下载）
if [ ! -f "$TTS_MODEL/model.onnx" ]; then
  curl -sSL -o "$WORK/kokoro.tar.bz2" https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2
  tar xjf "$WORK/kokoro.tar.bz2" -C "$WORK"
fi

# 2) 配音：压缩 + 提亮，让声音更有精神
hype() { ffmpeg -y -loglevel error -i "$1" -af "aresample=44100,highpass=f=100,equalizer=f=3200:t=q:w=1.2:g=3,acompressor=threshold=-18dB:ratio=3:attack=8:release=100:makeup=3" -ar 44100 -ac 1 "$2"; }
python3 tts.py "喵喵！" "$WORK/raw0.wav" 1.4 >/dev/null
python3 tts.py "开模！" "$WORK/raw1.wav" 1.3 >/dev/null
python3 tts.py "零零猫塑料小课堂，开课啦！" "$WORK/raw2.wav" 1.4 >/dev/null
for i in 0 1 2; do hype "$WORK/raw$i.wav" "$WORK/voice$i.wav"; done

# 3) 音乐 + 音效 + 配音混音
python3 audio.py "$WORK/voice0.wav" "$WORK/voice1.wav" "$WORK/voice2.wav" "$WORK/audio.wav"

# 4) 逐帧渲染画面
rm -rf "$WORK/frames"
NODE_PATH=$(npm root -g) node render.js "$WORK/frames"

# 5) 合成 MP4（抖音竖屏 1080x1920, 30fps）
ffmpeg -y -loglevel error -framerate 30 -i "$WORK/frames/f_%04d.png" -i "$WORK/audio.wav" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "完成: $OUT"
