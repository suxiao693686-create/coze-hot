#!/usr/bin/env bash
# 一键生成片头视频：bash build.sh   （每期改 intro.html 顶部的 CONFIG 即可）
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-build}
OUT=${OUT:-00猫片头.mp4}
mkdir -p "$WORK"

# 1) 配音模型（首次运行自动下载）
export MODELS=${MODELS:-$WORK}
get() { [ -e "$MODELS/$2" ] || { curl -sSL -o "$MODELS/dl.tar.bz2" "$1" && tar xjf "$MODELS/dl.tar.bz2" -C "$MODELS" && rm "$MODELS/dl.tar.bz2"; }; }
R=https://github.com/k2-fsa/sherpa-onnx/releases/download
get $R/tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2 sherpa-onnx-zipvoice-distill-int8-zh-en-emilia
get $R/asr-models/sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2 sherpa-onnx-paraformer-zh-small-2024-03-09
[ -e "$MODELS/vocos_24khz.onnx" ] || curl -sSL -o "$MODELS/vocos_24khz.onnx" $R/vocoder-models/vocos_24khz.onnx

# 2) 配音：ZipVoice 按 00猫声音模板 的语气念；标题那句稍微压快一点，卡进 2.25 秒
fx="highpass=f=100,equalizer=f=3200:t=q:w=1.2:g=3,acompressor=threshold=-18dB:ratio=3:attack=8:release=100:makeup=3"
python3 tts_zip.py "开模！" "$WORK/raw1.wav" 1.0 8 >/dev/null
python3 tts_zip.py "零零猫塑料小课堂，开课啦！" "$WORK/raw2.wav" 1.0 8 >/dev/null
ffmpeg -y -loglevel error -i "$WORK/raw1.wav" -af "aresample=44100,$fx" -ar 44100 -ac 1 "$WORK/voice1.wav"
ffmpeg -y -loglevel error -i "$WORK/raw2.wav" -af "atempo=1.08,aresample=44100,$fx" -ar 44100 -ac 1 "$WORK/voice2.wav"

# 3) 音乐 + 音效 + 配音混音
python3 audio.py "$WORK/voice1.wav" "$WORK/voice2.wav" "$WORK/audio.wav"

# 4) 逐帧渲染画面
rm -rf "$WORK/frames"
NODE_PATH=$(npm root -g) node render.js "$WORK/frames"

# 5) 合成 MP4（抖音竖屏 1080x1920, 30fps）
ffmpeg -y -loglevel error -framerate 30 -i "$WORK/frames/f_%04d.png" -i "$WORK/audio.wav" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "完成: $OUT"
