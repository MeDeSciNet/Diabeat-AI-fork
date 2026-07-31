# Pitch demo

`somnoswallow-demo.html` is a **single self-contained page** — no build step, no
external requests, no dependencies. It is the pitch artifact, not part of the
product. Open it in a browser, or publish it as an artifact.

It is written as a *fragment*: no `<!doctype>`, `<html>`, `<head>` or `<body>`
of its own, because the artifact host wraps it. To open it locally you need the
wrapper, which `smoke.mjs` writes as `wrapped.html`.

Published at
<https://claude.ai/code/artifact/8b704163-01ae-4bc9-905a-66abfb335774>
(republish the same file path from a conversation that owns it, or pass that URL
as `url`, to keep the link).

---

## The four models

Deliberately almost no prose — the animations carry the argument.

| # | Title | What it shows |
|---|---|---|
| 01 | 一次吞嚥，兩種結局 | Schematic throat forking to 肺 / 胃. Toggle 吞完吐氣 / 吞完吸氣. In the risk mode residue rides the inspiratory flow into the lung, with no cough and nothing observed. The respiration trace below shows the ≈1 s swallow apnea and which direction breathing resumes in. |
| 02 | 同一段 PSG，多一個通道 | 90 s of six-lane PSG. Mode A (現有 PSG) has an empty dashed slot where the swallow channel would be, and reads out 「低通氣事件 · 血氧下降 6%，歸因於呼吸事件」. Mode B (＋吞嚥通道) fills the slot and the same signal reads 吞嚥 32.4 s → +4.0 s 咳嗽 → +9.6 s 血氧下降. Auto-plays A then B on first scroll-into-view. Below it, the three claim tiers. |
| 03 | 一整夜，每一次都算 | The whole night as a strip: sleep stages, every swallow, posture, and the longest swallow-free interval — the point being that the gap matters more than the count. |
| 04 | 當晚偵測到，當晚就處理 | The mattress. A suggestion appears, a person confirms, only then does the bed move; refuses to move an empty bed; writes to a tamper-evident audit log. |

## Verifying it

```bash
cd pitch
npm i                 # playwright only
node smoke.mjs        # wraps the fragment, drives both themes + mobile
node shots4.mjs       # screenshots of model 02 (needs wrapped.html from smoke)
```

`smoke.mjs` checks: no console or page errors, no horizontal overflow at
1280×1000 and 390×844, both themes, and every interaction in all four models.

Chromium is pre-installed in this environment at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, which is what both scripts
pass as `executablePath`. The installed playwright expects build 1234 and would
otherwise try to download it. **On another machine, delete that option** and let
playwright find its own browser.

## Constraints the page has to keep

The same three that constrain the product — see
[docs/regulatory.md](../docs/regulatory.md):

- no claim of real-time life-safety alerting;
- no closed-loop stimulation, nothing moves without a person confirming;
- no diagnostic language anywhere (診斷 / 確診 / 吸入性肺炎風險 …), and the RUO
  badge stays in the header.

`make lint-terms` does **not** scan this directory — it lints `src` under the two
web packages, which is where product copy lives. The page does use 吸入性肺炎, but
only inside the 「還不能說」 column, as a negation. That is the same exemption the
lint grants the RUO notices by key. Do not move that wording into product copy.

Model 02's caveat line is load-bearing and must survive any edit: the device can
establish *that* a swallow happened and the physiological context around it. It
cannot establish that saliva entered the airway, or that silent aspiration
occurred.
