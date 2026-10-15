# REC Helper（rec-helper）

臺大醫院研究倫理委員會（NTUH REC）送審資料助手。

研究資料只寫一次，從新案到結案的送審資料都由同一份資料產生：

- **e-REC 線上申請書對照填寫單**：每一題都寫好答案，開網頁照著貼（含「複製」鈕）。
- **官方 Word 附件**：直接填在倫委會官方空白表單上，另存 PDF。
- **送件前檢查**：版面與字型、跨文件一致性、依 AF-063 模擬預審、研究報告指引、參考文獻核對。
- **計畫書與回覆**：依現有資料擬計畫書、產生審查意見回覆表、管理版本日期。

涵蓋新案（簡審、一般審查、免審）、變更案、持續審查、結案/終止/撤案、嚴重不良事件、試驗偏差、其他事項與恩慈療法。

## 快速開始

需要 Python 3.11 以上與 LibreOffice。

```bash
pip install git+https://github.com/alwayscrush0124/NTUH_REC_Helper
mkdir 我的研究 && cd 我的研究
rech init ntuh-chart-review     # 複製範例研究
rech templates                  # 下載倫委會官方空白表單
rech all                        # 產生線上填寫單、Word/PDF 附件、版面檢查
```

完整說明（研究資料怎麼寫、各階段、哪些要自己做、上傳注意事項）：**[docs/NTUH.md](docs/NTUH.md)**。

## 指令

| 指令 | 用途 |
|---|---|
| `rech init <範例>` | 開始一個研究資料夾 |
| `rech templates` | 下載官方空白表單（每台電腦或每個研究一次；`REC_TEMPLATES` 可共用） |
| `rech check` | 檢查研究資料 |
| `rech all` | 全部產生：附件 + 線上填寫單 + PDF + 版面檢查 + 進度 |
| `rech online [--skeleton]` | 線上填寫單；`--skeleton` 列出還沒答的題目 |
| `rech attachments [--skeleton]` | 附件題目；`--skeleton` 附加到 `附件填寫.md` |
| `rech <階段>` | `amendment`、`continuing`、`closure`、`sae`、`deviation`、`other`、`import`… |
| `rech protocol` | 依現有資料擬計畫書（`計畫書.md`），補完後產生 Word |
| `rech consistency` | 跨文件一致性檢查（收案數、年齡、日期、名稱…） |
| `rech precheck` | 依 AF-063 審查重點模擬預審 |
| `rech guidelines` | 研究報告指引檢核（STROBE、SPIRIT、CLAIM、TRIPOD-LLM…） |
| `rech refs [--offline]` | 參考文獻核對（Crossref／PubMed／arXiv）與縮寫檢查 |
| `rech reply` | 審查意見回覆表（並帶入修正前後對照表） |
| `rech stamp 檔案…` / `rech versions` | 蓋版本日期（複本）與版本紀錄 |
| `rech doctor` | 檢查環境（LibreOffice、字型、表單） |

沒有 `rech` 指令時可用 `python -m rec_helper <指令>`。

## 研究資料夾

| 檔案 | 內容 |
|---|---|
| `config.toml` | 計畫名稱、研究類型、審查方式、日期、人數、是否免除同意 |
| `cv.toml` | 主持人、協同主持人 |
| `中文計畫摘要.md` | 背景、目的、納入排除、方法、統計 |
| `線上填寫.md` | 線上申請書中推不出來的答案（`## <題號>`） |
| `附件填寫.md` | Word 附件的文字與勾選（`## <題號>`） |

## 開發

```bash
python -m pytest          # 測試（沒下載官方表單時，Word 附件相關測試會略過）
python -m ruff check .    # 程式風格
```

程式結構與慣例：[CLAUDE.md](CLAUDE.md)。臺大表單包：`rec_helper/institutions/ntuh/`。
引擎與機構無關，其他醫院可用 `rech onboard <id>` 從空白表單建立新的表單包。

## 授權

MIT，見 [LICENSE](LICENSE)。
