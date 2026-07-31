#!/usr/bin/env node
/**
 * Forbidden-terminology lint (PRD 7.2, 12).
 *
 * Runs before every production build and fails it. The rule the PRD sets out is
 * that no screen may assert a diagnosis, a confirmed aspiration, or a pneumonia
 * risk - the system reports signal indices and observations, nothing more.
 *
 * The research-use notice is the single exception, because it has to name the
 * thing it is disclaiming. It is allowlisted by key, and the allowlisted strings
 * are themselves checked to be negations - so a notice cannot be quietly edited
 * into an assertion and keep its exemption.
 *
 * Usage: node lint-terms.mjs <dir> [<dir>...]
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { extname, join, relative } from 'node:path';

const BANNED = [
  // Traditional Chinese
  { term: '診斷', why: 'asserts a diagnosis' },
  { term: '確診', why: 'asserts a confirmed diagnosis' },
  { term: '吸入性肺炎', why: 'names a clinical condition as a finding' },
  { term: '肺炎風險', why: 'asserts a pneumonia risk' },
  { term: '吸入風險', why: 'asserts an aspiration risk' },
  { term: '確認吸入', why: 'asserts a confirmed aspiration' },
  { term: '病患', why: 'use 受試者 (subject) - this is a research system' },
  { term: '治療建議', why: 'implies a treatment decision' },
  // English
  { term: 'diagnosis', why: 'asserts a diagnosis' },
  { term: 'diagnose', why: 'asserts a diagnosis' },
  { term: 'diagnostic', why: 'asserts a diagnosis' },
  { term: 'aspiration risk', why: 'asserts an aspiration risk' },
  { term: 'pneumonia risk', why: 'asserts a pneumonia risk' },
  { term: 'aspiration pneumonia', why: 'names a clinical condition as a finding' },
  { term: 'confirmed aspiration', why: 'asserts a confirmed aspiration' },
];

// Keys permitted to contain banned terms, and the negation each must keep.
const NOTICE_KEYS = new Set(['ruo.notice', 'ruo.short']);
const REQUIRED_NEGATION = [/不得/, /並非/, /not a/i, /must not/i, /研究用途/, /research use/i];

const SKIP_DIRS = new Set(['node_modules', 'dist', '.vite', 'coverage', '.git']);
const EXTS = new Set(['.ts', '.tsx', '.js', '.jsx', '.html']);

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) walk(path, out);
    else if (EXTS.has(extname(path))) out.push(path);
  }
  return out;
}

/**
 * True when this line, or one just above it, declares an allowlisted notice key.
 * The lookback matters: a long notice is usually wrapped onto the line after its
 * key, and checking only the current line would flag every one of them.
 */
const LOOKBACK = 2;

function isAllowlistedNotice(lines, index) {
  for (let i = Math.max(0, index - LOOKBACK); i <= index; i += 1) {
    for (const key of NOTICE_KEYS) {
      if (lines[i].includes(`'${key}'`) || lines[i].includes(`"${key}"`)) return true;
    }
  }
  return false;
}

const roots = process.argv.slice(2);
if (roots.length === 0) {
  console.error('usage: lint-terms.mjs <dir> [<dir>...]');
  process.exit(2);
}

const violations = [];
const noticeLines = [];
let scanned = 0;

for (const root of roots) {
  for (const file of walk(root)) {
    scanned += 1;
    const lines = readFileSync(file, 'utf8').split('\n');
    lines.forEach((line, i) => {
      if (line.includes('lint-terms-allow')) return;
      const allowlisted = isAllowlistedNotice(lines, i);
      for (const { term, why } of BANNED) {
        if (!line.toLowerCase().includes(term.toLowerCase())) continue;
        if (allowlisted) {
          noticeLines.push({ file, line: i + 1, text: line.trim() });
          continue;
        }
        violations.push({
          file: relative(process.cwd(), file),
          line: i + 1,
          term,
          why,
          text: line.trim().slice(0, 120),
        });
      }
    });
  }
}

// An allowlisted notice must still read as a disclaimer.
for (const notice of noticeLines) {
  if (!REQUIRED_NEGATION.some((re) => re.test(notice.text))) {
    violations.push({
      file: relative(process.cwd(), notice.file),
      line: notice.line,
      term: '(allowlisted notice)',
      why: 'a research-use notice must state the disclaimer, not assert the thing it names',
      text: notice.text.slice(0, 120),
    });
  }
}

if (violations.length > 0) {
  console.error(`\nForbidden terminology (PRD 2.1 R3) - ${violations.length} violation(s):\n`);
  for (const v of violations) {
    console.error(`  ${v.file}:${v.line}`);
    console.error(`    ${v.term}  -  ${v.why}`);
    console.error(`    ${v.text}\n`);
  }
  console.error('Describe the signal and the action, not a clinical conclusion.\n');
  process.exit(1);
}

console.log(`lint:terms - ${scanned} files scanned, no forbidden terminology found.`);
