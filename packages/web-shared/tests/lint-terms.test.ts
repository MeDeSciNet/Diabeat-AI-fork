import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { DICT } from '../src/lib/i18n';

const SCRIPT = fileURLToPath(new URL('../scripts/lint-terms.mjs', import.meta.url));

function runLint(dir: string): { code: number; output: string } {
  try {
    const output = execFileSync('node', [SCRIPT, dir], { encoding: 'utf8' });
    return { code: 0, output };
  } catch (err: any) {
    return { code: err.status ?? 1, output: `${err.stdout ?? ''}${err.stderr ?? ''}` };
  }
}

function fixture(contents: string): string {
  const dir = mkdtempSync(join(tmpdir(), 'lint-terms-'));
  writeFileSync(join(dir, 'sample.tsx'), contents);
  return dir;
}

describe('forbidden terminology lint', () => {
  it('passes on wording that describes the signal', () => {
    const dir = fixture(`export const copy = { title: '夜間吞嚥訊號指標', hint: 'Signal index' };`);
    expect(runLint(dir).code).toBe(0);
  });

  it('fails the build on a Chinese diagnostic claim', () => {
    const dir = fixture(`export const copy = { title: '系統診斷結果' };`);
    const { code, output } = runLint(dir);
    expect(code).toBe(1);
    expect(output).toContain('asserts a diagnosis');
  });

  it('fails the build on an English aspiration-risk claim', () => {
    const dir = fixture(`export const copy = { title: 'Overnight aspiration risk' };`);
    const { code, output } = runLint(dir);
    expect(code).toBe(1);
    expect(output).toContain('asserts an aspiration risk');
  });

  it('fails on pneumonia risk wording', () => {
    const dir = fixture(`export const copy = { title: '肺炎風險偏高' };`);
    expect(runLint(dir).code).toBe(1);
  });

  it('allows the research-use notice, which has to name what it disclaims', () => {
    const dir = fixture(
      `export const copy = { 'ruo.notice': '本系統為研究用途，不得作為診斷或治療決策依據。' };`,
    );
    expect(runLint(dir).code).toBe(0);
  });

  it('rejects a notice edited into an assertion', () => {
    const dir = fixture(`export const copy = { 'ruo.notice': '本系統提供診斷結論。' };`);
    const { code, output } = runLint(dir);
    expect(code).toBe(1);
    expect(output).toContain('must state the disclaimer');
  });

  it('keeps the shipped vocabulary clean in both languages', () => {
    for (const lang of Object.keys(DICT) as (keyof typeof DICT)[]) {
      for (const [key, value] of Object.entries(DICT[lang])) {
        if (key.startsWith('ruo.')) continue;
        expect(String(value).toLowerCase()).not.toContain('diagnos');
        expect(String(value)).not.toContain('診斷');
        expect(String(value)).not.toContain('吸入性肺炎');
      }
    }
  });

  it('never labels the index as a clinical risk', () => {
    expect(DICT['zh-Hant']['index.name']).toContain('訊號指標');
    expect(DICT.en['index.name']).toContain('signal index');
  });
});
