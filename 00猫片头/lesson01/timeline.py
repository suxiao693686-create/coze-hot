"""根据每句配音的真实长度排时间轴，写出 timeline.js 给动画用。
用法: python3 timeline.py 配音文件夹"""
import json, sys, wave, os

voice_dir = sys.argv[1]
lines = json.load(open(os.path.join(os.path.dirname(__file__), 'script.json')))
t, prev = 0.6, None
out = []
for l in lines:
    with wave.open(os.path.join(voice_dir, l['id'] + '.wav')) as w:
        dur = w.getnframes() / w.getframerate()
    if prev is not None:
        if prev['scene'] == 'hook':           # 片头插在这里
            t = prev['end'] + 0.7 + 0.5
        elif l['scene'] != prev['scene']:
            t = prev['end'] + 0.9                # 换场景多停一下
        else:
            t = prev['end'] + 0.3
    item = {'id': l['id'], 'scene': l['scene'], 'say': l['say'], 'sub': l.get('sub', l['say']),
            'start': round(t, 3), 'end': round(t + dur, 3)}
    out.append(item); prev = item
splice = out[0]['end'] + 0.7
total = out[-1]['end'] + 1.6
js = 'window.TIMELINE = ' + json.dumps({'lines': out, 'splice': round(splice, 3), 'total': round(total, 3)}, ensure_ascii=False, indent=1) + ';\n'
open(os.path.join(os.path.dirname(__file__), 'timeline.js'), 'w').write(js)
print('splice', round(splice, 2), 'total', round(total, 2))
