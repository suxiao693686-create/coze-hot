// 用法: node render.js <输出文件夹> [只渲染的时间点,逗号分隔]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const out = process.argv[2] || 'frames';
  const only = process.argv[3] ? process.argv[3].split(',').map(Number) : null;
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => { console.error('PAGE ERROR', e); process.exit(1); });
  await page.goto('file://' + path.resolve(__dirname, 'intro.html') + '?render=1');
  await page.evaluate(() => window.ready);
  const fps = 30;
  const dur = await page.evaluate(() => window.DURATION);
  const times = only || Array.from({ length: Math.round(dur * fps) }, (_, i) => i / fps);
  for (let i = 0; i < times.length; i++) {
    const data = await page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, times[i]);
    const name = only ? `t_${times[i].toFixed(2)}.png` : `f_${String(i).padStart(4, '0')}.png`;
    fs.writeFileSync(path.join(out, name), Buffer.from(data.split(',')[1], 'base64'));
  }
  await browser.close();
  console.log('rendered', times.length, 'frames to', out);
})();
