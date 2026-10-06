#!/usr/bin/env bash
# 一键生成第01课成片：bash lesson01/build.sh
# 结构：开头钩子 → 00猫片头 → 正片
set -euo pipefail
cd "$(dirname "$0")"
WORK=${WORK:-../build}
OUT=${OUT:-第01课_什么是改性塑料.mp4}
export MODELS=${MODELS:-$WORK}
mkdir -p "$WORK/l2raw" "$WORK/l1"

# 1) 片头（没有就先生成）
[ -f ../00猫片头.mp4 ] || (cd .. && WORK="$WORK" bash build.sh)

# 2) 配音：ZipVoice 每句生成几遍挑最准的（已经生成过的会跳过）
python3 - <<PY
import json, subprocess, os
for l in json.load(open('script.json')):
    raw = f"$WORK/l2raw/{l['id']}.wav"
    if not os.path.exists(raw):
        subprocess.run(['python3', '../tts_zip.py', l['say'], raw, '1.0', '3'], check=True, capture_output=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', raw, '-af',
        'aresample=44100,highpass=f=100,equalizer=f=3200:t=q:w=1.2:g=3,acompressor=threshold=-18dB:ratio=3:attack=8:release=100:makeup=3',
        '-ar', '44100', '-ac', '1', f"$WORK/l1/{l['id']}.wav"], check=True)
PY

# 3) 按配音长度排时间轴
python3 timeline.py "$WORK/l1"

# 4) 渲染画面（无声）+ 导出音效时间点
(cd .. && PAGE=lesson01/lesson01.html NODE_PATH=$(npm root -g) node render.js "$WORK/lesson_video.mp4")

# 5) 混音
python3 audio_lesson.py "$WORK/l1" "$WORK/lesson_video.mp4.cues.json" "$WORK/lesson_audio.wav"

# 6) 合成：钩子 + 片头 + 正片
SPLICE=$(python3 -c "import json;print(json.loads(open('timeline.js').read().split('=',1)[1].strip().rstrip(';'))['splice'])")
ffmpeg -y -loglevel error -i "$WORK/lesson_video.mp4" -i "$WORK/lesson_audio.wav" -i ../00猫片头.mp4 -filter_complex "
  [0:v]split[v0][v1]; [1:a]asplit[a0][a1];
  [v0]trim=0:$SPLICE,setpts=PTS-STARTPTS[hv]; [a0]atrim=0:$SPLICE,asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=mono[ha];
  [v1]trim=start=$SPLICE,setpts=PTS-STARTPTS[mv]; [a1]atrim=start=$SPLICE,asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=mono[ma];
  [2:v]setpts=PTS-STARTPTS,fps=30[iv]; [2:a]aresample=44100,aformat=sample_rates=44100:channel_layouts=mono[ia];
  [hv][ha][iv][ia][mv][ma]concat=n=3:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -crf 18 -preset medium -c:a aac -b:a 192k -movflags +faststart "$OUT"
echo "完成: lesson01/$OUT"
