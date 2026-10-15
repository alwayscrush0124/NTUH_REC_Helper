# Changelog

## 0.2.0 — 撰寫與送件前檢查

- `rech consistency`：跨文件一致性檢查（收案數、年齡、日期與資料期間、計畫名稱、保存年限、與設定矛盾的用字；處理「不含兒童」這類否定句）。
- `rech precheck`：依 AF-063〈臨床研究案件審查重點〉逐項模擬預審。
- `rech protocol`：依現有資料擬計畫書（`計畫書.md`），`rech generate` 產生 Word；英文摘要同樣支援。
- `rech reply`：審查意見回覆表，修正行自動帶入變更案修正前後對照表。
- `rech refs`：參考文獻核對（Crossref／PubMed／DataCite-arXiv）與縮寫定義檢查。
- `[version]`、`rech stamp`、`rech versions`：版本日期設定、蓋章複本與版本紀錄。
- `rech guidelines`：研究報告指引檢核（SPIRIT、STROBE、STARD、CLAIM、TRIPOD+AI、TRIPOD-LLM）。
- `rech all` 一併執行一致性、預審與指引檢核。新增相依套件 `pypdf`；PDF 蓋章為選用 `rec-helper[pdf]`。

## 0.1.0 — 第一版

臺大醫院研究倫理委員會（NTUH REC）送審資料助手。

- **e-REC 線上申請書對照填寫單**（`rech online`）：新案（簡審、一般審查、免審）、變更案、持續審查、
  結案/終止/撤案、嚴重不良事件、試驗偏差、其他事項；依前一題答案顯示追問題。
- **官方 Word 附件自動填寫**（`rech generate`）：自評表、使用病歷資料進行研究申請表、保密聲明切結書、
  計畫中文摘要，以及 43 份逐題填寫的官方表單（同意書含新竹/生醫院區版、DSMP、易受傷害族群說明表、
  網路研究、FDA、藥品、NGS、修正前後對照表、SAE 清單、研究授權表、恩慈療法…），依研究內容自動判斷要送哪些。
- **官方空白表單下載**（`rech templates`）：自動抓倫委會九個「表單下載」頁。
- **送件前檢查**：紙張、邊界、字型與官方範本一致；檔名符合 e-REC 上傳規定。
- 範例研究 `ntuh-chart-review`；使用說明 `docs/NTUH.md`。
