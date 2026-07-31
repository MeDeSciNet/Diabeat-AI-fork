# SomnoSwallow

夜間吞嚥訊號監測與照護建議系統 — 研究用原型（Research Use Only）。

> **本系統為研究用途，不得作為診斷或治療決策依據。**
> 本 repo 的任何軟體皆不得用於臨床診斷或病人管理決策。

## 這條分支

`claude/somnoswallow-mvp-52t8p0` 是一條 **orphan branch**，與 `main`（Diabeat-AI Flutter app）沒有共同歷史。
SomnoSwallow 是獨立的 monorepo，因此從空白的檔案樹開始。

目前只有這份 placeholder。實作尚未開始。

## 規劃中的結構

| 代號 | 子系統 | 一句話 |
| --- | --- | --- |
| SIM | 裝置模擬器 | 生理參數化的合成訊號產生器，同時輸出 ground truth |
| ING | 擷取與分析服務 | 收訊號 → 偵測吞嚥事件 → 算夜間訊號指標 → 產生警訊 |
| CARE | 照護者 Dashboard | 手機優先，昨晚摘要 + 可執行的照護建議 |
| STATION | 護理站中央 Dashboard | 桌機大螢幕，多床位總覽 + 班別摘要 |
| PAM | 體位輔助床墊控制器 | 床頭抬高 / 側臥翻身，建議—確認制，不自動觸發 |

實作順序：`shared-schemas/` → SIM → ING → CARE / STATION → PAM。
SIM 必須先於 ING，因為沒有 ground truth 就無法驗收偵測演算法。

## 三條紅線（優先於所有功能需求）

任何與此節衝突的功能需求都應被拒絕，並在 PR 中標明。

1. **不做即時生命警報** — 夜間分析在睡眠結束後批次執行，警訊於隔日晨間送達。
2. **不做自動電刺激閉環** — PAM 只做體位介入，且必須經人工確認。
3. **不輸出診斷結論** — UI 一律用「訊號指標」「觀察建議」，所有畫面須有 RUO 常駐標示。
