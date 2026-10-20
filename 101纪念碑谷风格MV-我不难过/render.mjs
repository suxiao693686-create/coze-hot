// 逐帧离线渲染《我不难过》纪念碑谷风格 MV —— 画面不掉帧、和音乐严格同步
//
// 准备（只需一次）：
//   npm i playwright && npx playwright install chromium
//   并安装 ffmpeg（命令行能运行 ffmpeg / ffprobe）
//
// 用法：
//   node render.mjs --audio 我不难过.mp3 --lrc 我不难过.lrc
//   node render.mjs --audio 我不难过.mp3 --lrc 我不难过.lrc --ar 9:16 --out 竖屏.mp4
//   node render.mjs --from 150 --to 190            # 只渲染一段（不给音乐 = 无声预览）
//
// 参数：
//   --audio  音乐文件            --lrc   歌词文件（带时间轴的 LRC）
//   --ar     16:9 | 9:16          --fps   帧率，默认 30
//   --out    输出文件，默认 mv.mp4
//   --from / --to                 只渲染这段时间（秒）
//   --offset 歌词整体延后多少秒（可为负）
//   --sections 0,18,50,...        手动指定 9 个段落起点（自动对齐不理想时使用）
//   --three  本地 three.module.js 路径（离线时使用）
import { chromium } from 'playwright';
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv[i + 1] : d; };
const audio = arg('audio'), lrc = arg('lrc'), ar = arg('ar', '16:9'), fps = Number(arg('fps', 30));
const outFile = arg('out', 'mv.mp4'), offset = arg('offset'), sections = arg('sections'), three = arg('three');

const here = path.dirname(fileURLToPath(import.meta.url));
const query = new URLSearchParams({ render: '1', ar });
if (offset) query.set('offset', offset);
if (sections) query.set('sections', sections);
const url = `${pathToFileURL(path.join(here, 'index.html')).href}?${query}`;

let audioDur = null;
if (audio) {
  audioDur = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio]).toString().trim());
}

const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
const browser = await chromium.launch({ proxy, args: ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const [w, h] = ar === '9:16' ? [1080, 1920] : [1920, 1080];
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
page.on('pageerror', e => console.error('页面错误：', e.message));
if (three) {
  const body = fs.readFileSync(three);
  await page.route('https://cdn.jsdelivr.net/**', r => r.fulfill({ body, contentType: 'application/javascript' }));
}
await page.goto(url);
await page.waitForFunction(() => window.MV, null, { timeout: 60000 });
await page.evaluate(() => window.MV.ready);
if (lrc) await page.evaluate(t => window.MV.loadLRC(t), fs.readFileSync(lrc, 'utf8'));
if (audioDur) await page.evaluate(d => window.MV.setDuration(d), audioDur);
const tl = await page.evaluate(() => window.MV.timeline());
console.log(`段落（${tl.mode}）：`);
for (const s of tl.sections) console.log(`  ${s.key.padEnd(7)} ${s.start.toFixed(1).padStart(6)}s – ${s.end.toFixed(1).padStart(6)}s  歌词 ${s.lines} 行`);

const from = Number(arg('from', 0)), to = Math.min(Number(arg('to', tl.duration)), tl.duration);
const frames = Math.floor((to - from) * fps);
const ff = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-'];
if (audio) ff.push('-ss', String(from), '-t', String(to - from), '-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k');
ff.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-s', `${w}x${h}`, '-movflags', '+faststart', '-shortest', outFile);
const enc = spawn('ffmpeg', ff, { stdio: ['pipe', 'inherit', 'inherit'] });

const t0 = Date.now();
for (let i = 0; i < frames; i++) {
  const t = from + i / fps;
  const data = await page.evaluate(t => { window.MV.renderFrame(t); return document.getElementById('out').toDataURL('image/jpeg', .95); }, t);
  if (!enc.stdin.write(Buffer.from(data.slice(data.indexOf(',') + 1), 'base64'))) await new Promise(r => enc.stdin.once('drain', r));
  if (i % fps === 0) {
    const el = (Date.now() - t0) / 1000, eta = el / (i + 1) * (frames - i - 1);
    process.stdout.write(`\r渲染中 ${(100 * i / frames).toFixed(1)}%  第 ${t.toFixed(0)} 秒  剩余约 ${Math.ceil(eta / 60)} 分钟   `);
  }
}
enc.stdin.end();
await new Promise(r => enc.on('close', r));
await browser.close();
console.log(`\n完成：${outFile}`);
