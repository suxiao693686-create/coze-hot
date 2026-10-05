// 逐帧渲染动画。
//   node render.js <输出文件夹>                 -> 渲染 intro.html 为 PNG 序列
//   node render.js <输出文件夹> 1.5,3.2          -> 只渲染这几个时间点（检查用）
//   PAGE=lesson01/lesson01.html node render.js out.mp4   -> 直接输出无声 MP4，并写出 out.mp4.cues.json（音效时间点）
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
(async () => {
  const out = process.argv[2] || 'frames';
  const only = process.argv[3] ? process.argv[3].split(',').map(Number) : null;
  const page_ = path.resolve(__dirname, process.env.PAGE || 'intro.html');
  const toMp4 = out.endsWith('.mp4') && !only;
  if (!toMp4) fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => { console.error('PAGE ERROR', e); process.exit(1); });
  await page.goto('file://' + page_ + '?render=1');
  await page.evaluate(() => window.ready);
  const fps = 30;
  const dur = await page.evaluate(() => window.DURATION);
  const times = only || Array.from({ length: Math.round(dur * fps) }, (_, i) => i / fps);
  let ff;
  if (toMp4) {
    const cues = await page.evaluate(() => window.CUES || []);
    fs.writeFileSync(out + '.cues.json', JSON.stringify(cues));
    ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  }
  for (let i = 0; i < times.length; i++) {
    const type = toMp4 ? 'image/jpeg' : 'image/png';
    const data = await page.evaluate(([t, type]) => { window.render(t); return document.getElementById('c').toDataURL(type, 0.95); }, [times[i], type]);
    const buf = Buffer.from(data.split(',')[1], 'base64');
    if (toMp4) { if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if (i % 300 === 0) console.log('frame', i, '/', times.length); }
    else fs.writeFileSync(path.join(out, only ? `t_${times[i].toFixed(2)}.png` : `f_${String(i).padStart(4, '0')}.png`), buf);
  }
  await browser.close();
  if (toMp4) { ff.stdin.end(); await new Promise(r => ff.on('close', r)); }
  console.log('rendered', times.length, 'frames to', out);
})();
