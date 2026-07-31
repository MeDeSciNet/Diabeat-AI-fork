import { chromium } from 'playwright';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const theme of ['dark', 'light']) {
  const p = await b.newPage({ viewport: { width: 1180, height: 1200 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + process.cwd() + '/wrapped.html');
  await p.evaluate(t => document.documentElement.setAttribute('data-theme', t), theme);
  await p.waitForTimeout(400);
  const panel = p.locator('#psg').locator('xpath=ancestor::div[contains(@class,"model")][1]');
  await panel.scrollIntoViewIfNeeded();
  await p.waitForTimeout(26000);           // let the auto A -> B sequence finish
  await panel.screenshot({ path: `psg-${theme}-B.png` });
  console.log(theme, 'B:', (await p.textContent('#pgTag')).trim(), (await p.textContent('#pgTxt')).trim());
  await p.click('#pgOff'); await p.waitForTimeout(300);
  await panel.screenshot({ path: `psg-${theme}-A.png` });
  console.log(theme, 'A:', (await p.textContent('#pgTag')).trim(), (await p.textContent('#pgTxt')).trim());
  await p.close();
}
const m = await b.newPage({ viewport: { width: 390, height: 844 } });
await m.goto('file://' + process.cwd() + '/wrapped.html');
await m.locator('#psg').scrollIntoViewIfNeeded();
await m.waitForTimeout(26000);
await m.locator('#psg').locator('xpath=ancestor::div[contains(@class,"panel")][1]').screenshot({ path: 'psg-mobile.png' });
await m.close();
await b.close();
