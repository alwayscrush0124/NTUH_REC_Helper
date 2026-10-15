# 臺大醫院（NTUH REC）使用說明

這個工具幫你準備送臺大醫院研究倫理委員會的資料：

- **線上申請書（e-REC 系統）**：產生「對照填寫單」，每一題都寫好答案，開網頁照著貼。
- **Word 附件**：直接填在倫委會官方空白表單上（病歷申請表、自評表、切結書、同意書、DSMP…），另存 PDF。
- **送件前檢查**：紙張、邊界、字型和官方表單一致；檔名符合 e-REC 上傳規定。

研究資料只寫一次（`config.toml` 和幾個 Markdown 檔），新案、變更、持續審查、結案都從同一份資料產生。

---

## 1. 安裝（每台電腦一次）

1. 安裝 **Python 3.11 以上**（python.org，安裝時勾 *Add python to PATH*）。
2. 安裝 **LibreOffice**（轉 PDF、檢查版面用）。
3. 安裝本工具，三選一：
   ```bash
   pip install rec-helper                     # 已發布到 PyPI 時
   pip install <下載的 rec_helper-*.whl>        # 同事給你的安裝檔
   pip install <本專案資料夾路徑>                 # 直接從原始碼
   ```
4. 確認環境：`rech doctor`

> 有 `uv` 的人也可以 `uv tool install rec-helper`。

## 2. 開始一個研究（每個研究一個資料夾）

```bash
mkdir 我的研究 && cd 我的研究
rech init ntuh-chart-review     # 複製臺大範例（回溯性病歷研究、簡審、免除知情同意）
rech templates                  # 下載倫委會官方空白表單到 templates/ntuh/
```

範例檔案換成自己的研究：

| 檔案 | 寫什麼 |
|---|---|
| `config.toml` | 計畫名稱、研究類型、審查方式、日期、人數、是否免除同意 |
| `cv.toml` | 主持人、協同主持人（`dept` 寫「單位／職稱」） |
| `中文計畫摘要.md` | 研究背景、目的、納入排除、方法、統計（也帶入線上申請書） |
| `線上填寫.md` | 線上申請書中 config 推不出來的題目，`## <題號>` 一題一段 |
| `附件填寫.md` | Word 附件的文字與勾選，`## <題號>` 一題一段 |

`config.toml` 裡最重要的三個欄位決定要送哪些東西：

- `study.type`：`retrospective`（回溯）、`prospective`（前瞻）、`clinical_trial`（臨床試驗）
- `study.review_type`：`exempt`（免審）、`expedited`（簡審）、`full_board`（一般審查）
- `subjects.consent_waiver`：是否申請免除知情同意

## 3. 產生資料

```bash
rech all
```

產出在 `output/`：

- `output/online/01_新案申請書.html` …：線上填寫單。用瀏覽器打開，每題有「複製」鈕。
  - ● 來自你的 Markdown　◆ 依 config 推定（請確認）　✎ 待填　－ 視情況
- `output/*.docx`、`*.pdf`：Word 附件與 PDF。
- `output/layout_report.md`：版面檢查。**Errors 要是 0 才送件。**
- `output/consistency_report.md`、`precheck_report.md`、`guidelines_report.md`：送件前檢查（見第 5 節）。

還沒答的題目：

```bash
rech online --skeleton          # 列出線上申請書還沒答的題目 → 線上填寫.md
rech attachments --skeleton     # 把本案 Word 附件的題目附加到 附件填寫.md
```

`附件填寫.md` 的題號像 `DSMP-5`、`AF127-4`，寫法：

| 題型 | 寫法 |
|---|---|
| 是／否（含理由欄） | `是` 或 `否：理由` |
| 勾選 | `- 選項開頭`，可多行複選；`- 選項：說明` 會填到該選項的 ＿＿ |
| 文字 | 直接寫；一列一行。會取代範本裡的說明文字 |
| 清單表（修正前後對照表、SAE 清單、授權表） | 一列一行，欄位用 `｜` 分隔 |

沒答的題目：病歷申請表寫【待填】，其他附件保留範本原文。

## 4. 哪些附件會自動產生

依 `config.toml` 和你在 `線上填寫.md` 的答案自動判斷（和 e-REC「上傳文件」頁一致）：

| 情況 | 附件 |
|---|---|
| 新案（簡審、一般審查） | 臨床研究計畫申請人自評表、計畫中文摘要 |
| 回溯性病歷研究＋免除同意 | 使用病歷資料進行研究申請表、保密聲明切結書（主持人版） |
| H1／H2 知情同意 | 受試者同意書（臨床試驗）或研究受訪者說明及同意書 |
| 主持人單位在新竹臺大分院／生醫醫院 | 自動改用該院區版本同意書（或 `config.toml` 寫 `site = "HCH"`） |
| E4 有 DSMP，或藥品/醫材臨床試驗 | 資料及安全性監測計畫 |
| G21-1 易受傷害族群 | 對應的說明表（未成年人、孕婦、受拘禁人…） |
| G33 網路研究、A3-1 FDA、B2 藥品、C6 自行管理 | 網路研究自評表、FDA 確認事項表、藥品資料表、用藥自行管理自評表 |
| 基因研究 | NGS 告知方式說明表、NGS 同意書 |
| 免審 | 只有計畫中文摘要（計畫書須含中文摘要） |

自動判斷沒選到、但你要送的表單：在 `config.toml` 最上面加 `extra_forms = ["DSMP"]`。

## 5. 計畫書、送件前檢查、版本日期

### 寫計畫書

計畫書沒有官方範本。先讓工具依你已寫的資料擬稿，再自己補寫：

```bash
rech protocol                   # 產生 計畫書.md（各章已帶入摘要、線上填寫、附件內容；缺的寫【待寫】）
```

在 `config.toml` 最上面加 `protocol = "計畫書.md"`，之後 `rech all` 會產生 `output/計畫書_v1.0.docx`（頁首有版本日期，【待寫】以黃底標出）。
已經有自己寫好的 Word/PDF 計畫書：改寫 `protocol_file = "計畫書.docx"`，工具只拿來檢查，不會重新產生。
英文摘要同理：`english_abstract = "英文摘要.md"`。

### 送件前檢查（`rech all` 會一起跑）

| 指令 | 檢查什麼 | 報告 |
|---|---|---|
| `rech consistency` | 摘要、線上申請書、附件、計畫書之間的收案數、年齡、日期、資料期間、計畫名稱、保存年限是否一致；有沒有出現與設定矛盾的字（例如未納入未成年人卻寫「兒科」） | `consistency_report.md` |
| `rech precheck` | 依倫委會 AF-063〈臨床研究案件審查重點〉逐項預審：■ 符合　□ 待補　？ 人工確認　－ 不適用 | `precheck_report.md` |
| `rech guidelines` | 計畫書是否涵蓋研究報告指引的項目（觀察性 STROBE、臨床試驗 SPIRIT、影像 AI CLAIM、LLM 研究 TRIPOD-LLM…，自動依研究判斷；或 `guidelines = ["STROBE"]` 指定） | `guidelines_report.md` |
| `rech refs` | 參考文獻是否真實存在、年份與題名是否相符（Crossref／PubMed／arXiv）；縮寫是否在首次出現時定義全名。`--offline` 只查縮寫 | `refs_report.md` |

這些是依文字自動比對，提醒你可能漏掉的地方，不代表委員會判斷。`rech refs` 只會把參考文獻字串送到文獻資料庫查詢，不送研究內容。

### 回覆審查意見

```bash
rech reply                      # 產生 審查意見.md 範本
```

把委員意見貼進去，每則寫「回覆：」，有改文件就加「修正：文件｜頁碼｜章節｜修正前｜修正後｜原因」。
`config.toml` 加 `reply = "審查意見.md"` 後，`rech all` 產生 `審查意見回覆表.docx`；變更案的修正前後對照表也會自動帶入這些修正行。

### 版本日期

在 `config.toml` 設一次：

```toml
[version]
number = "1.0"
date   = "2026/10/14"     # 不寫就是今天
計畫書  = "1.1"            # 個別文件可不同
```

工具產生的計畫書、摘要、回覆表會自動印在頁首。自己做的檔案用：

```bash
rech stamp 計畫書.pdf 英文摘要.pdf     # 蓋好版本日期的複本放在 output/stamped/，原檔不動
rech versions                          # 看 版本紀錄.md（每次蓋章都記下檔名、版本、日期、檔案指紋）
```

蓋 PDF 需要 `pip install rec-helper[pdf]`；Word 檔不用。

## 6. 核准之後

同一個資料夾，換階段就好：

```bash
rech amendment      # 變更案：變更案申請書填寫單＋修正前後對照表
rech continuing     # 持續審查：申請書填寫單＋（有 SAE 時）SAE 摘要報告清單
rech closure        # 結案：結案/終止/撤案申請書填寫單
rech sae            # 嚴重不良事件及非預期問題通報
rech deviation      # 試驗偏差通報（重大偏差附根本原因分析報告）
rech other          # 其他事項通報
rech import         # 恩慈療法／專案進口（紙本表單）
```

一個 `線上填寫.md` 可以放所有階段的答案；後續階段的題號有前綴，例如 `## 變更二`、`## 持續7-1`、`## 結案1`。
要長期換階段：`rech set-phase continuing`（只改 `config.toml` 的 phase 那一行）。

## 7. 一定要自己做的事

- **簽名**：切結書（主持人及每位研究人員各一份）、新案申請書（行政審查後由系統列印，主持人及科／部主任簽章後掃描）。
- **e-REC 才能選的欄位**：研究領域下拉選單、團隊成員帳號、審查費繳費方式、利益申報。
- **計畫書內容**：`rech protocol` 只會擬稿，研究內容要由你撰寫與確認；【待寫】都要補完。
- **確認 ◆ 推定的答案**：工具依研究類型推定的答案（例如 G28 風險相當）都要看過一次。

## 8. 上傳 e-REC 前注意

- 檔名不可含 `(` `)` `--` `"` `'` `<` `>` `|`。本工具產生的檔名已避開。
- 計畫書、摘要、同意書、問卷、文宣品都要註明**版本日期**。
- 上傳的是 `output/` 裡的 **PDF**（或依系統要求的 Word）。

## 9. 常見問題

**Q：`rech templates` 有一兩個表單下載失敗？**
倫委會網站偶爾有失效連結（例如舊版 AF-020）。其他表單照常可用；需要的話到「表單下載」頁手動下載放進 `templates/ntuh/`。

**Q：版面檢查說字型是新細明體？**
若註明「沿用自官方空白表單」，代表官方範本本來就這樣，不用處理。只有 Errors 要改。

**Q：多個研究共用表單？**
設定環境變數 `REC_TEMPLATES=<共用資料夾>`，`rech templates` 一次，所有研究共用。

**Q：兒童版同意書？**
官方兒童版使用注音排版，工具不自動填寫；請下載空白表單（`templates/ntuh/CHILD_HCH.docx` 等）自行編修。

---

給維護者：NTUH 表單包在 `rec_helper/institutions/ntuh/`
（`online.py` 新案線上頁、`online_phases.py` 後續階段、`attachments.py` + `rec_helper/form_rows.py` Word 附件、`forms.py` 路由、`profile.toml` 表單下載與邊界）。
e-REC 改版時，對照倫委會「申請書(含填寫說明)」PDF 更新題號與選項。
