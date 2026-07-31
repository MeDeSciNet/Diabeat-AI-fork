import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
const body = readFileSync('somnoswallow-demo.html', 'utf8');
writeFileSync('wrapped.html', `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${body}</body></html>`);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const errs = [];
for (const theme of ['dark','light']) {
  const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
  p.on('console', m => { if (m.type()==='error') errs.push(`[${theme}] ${m.text()}`); });
  p.on('pageerror', e => errs.push(`[${theme}] ${e.message}`));
  await p.goto('file://' + process.cwd() + '/wrapped.html');
  await p.evaluate(t => document.documentElement.setAttribute('data-theme', t), theme);
  await p.waitForTimeout(6000);   // let the night sweep run
  const clock = await p.textContent('#clock');
  const cnt = await p.textContent('#cCount');
  const supine = await p.textContent('#cSupine');
  const gap = await p.textContent('#cGap');
  await p.waitForTimeout(9500);   // finish the night
  const clockEnd = await p.textContent('#clock');
  const cntEnd = await p.textContent('#cCount');
  const gapEnd = await p.textContent('#cGap');
  const turn = await p.getAttribute('#turnMark', 'opacity');

  await p.click('#mRisk');
  await p.evaluate(() => { const s=document.getElementById('scrub'); s.value=1600; s.dispatchEvent(new Event('input')); });
  await p.waitForTimeout(250);
  const lung = await p.textContent('#lungLabel');

  // PSG co-registration model
  await p.evaluate(() => document.getElementById('psg').scrollIntoView({ block: 'center' }));
  await p.waitForTimeout(12500);           // auto sweep: mode A through to the end
  const pgA = (await p.textContent('#pgTxt')).trim();
  const pgTagA = (await p.textContent('#pgTag')).trim();
  await p.waitForTimeout(13500);           // auto-switches to mode B and replays
  const pgB = (await p.textContent('#pgTxt')).trim();
  const pgTagB = (await p.textContent('#pgTag')).trim();
  const pressed = await p.getAttribute('#pgOn', 'aria-pressed');
  await p.click('#pgOff'); await p.waitForTimeout(150);
  const pgBack = (await p.textContent('#pgTag')).trim();
  await p.click('#psgPlay'); await p.waitForTimeout(400);
  const playLabel = (await p.textContent('#psgPlay')).trim();
  await p.click('#psgPlay');

  await p.click('#confirmBtn'); await p.waitForTimeout(4200);
  const angle = await p.textContent('#sAngle');
  await p.click('#simDetect'); await p.click('#occToggle'); await p.click('#confirmBtn');
  await p.waitForTimeout(200);
  const refusal = (await p.textContent('.bedlog div')).trim();
  const ovf = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

  console.log(`--- ${theme} ---`);
  console.log(' 6s :', clock, cnt.trim(), '仰躺', supine.trim(), '空白', gap.trim());
  console.log(' end:', clockEnd, cntEnd.trim(), '空白', gapEnd.trim(), 'turnMark', turn);
  console.log(' lung:', lung, '| bed:', angle, '| overflow:', ovf);
  console.log(' refusal:', refusal.slice(0,40));
  console.log(' psg A:', pgTagA, '|', pgA);
  console.log(' psg B:', pgTagB, '|', pgB, '| pgOn pressed:', pressed);
  console.log(' psg toggle back:', pgBack, '| play btn:', playLabel);
  await p.close();
}
const m = await b.newPage({ viewport: { width: 390, height: 844 } });
m.on('pageerror', e => errs.push(`[mobile] ${e.message}`));
await m.goto('file://' + process.cwd() + '/wrapped.html');
await m.waitForTimeout(1500);
console.log('--- mobile --- overflow:', await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth));
await m.close();
await b.close();
console.log(errs.length ? '\nERRORS:\n' + errs.join('\n') : '\nno errors');
