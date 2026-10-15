---
name: config-schema
description: Complete reference for config.toml, its @file references, and every field used by IRB form generators.
---

# Config Schema Reference

All study data lives in plain text with `config.toml` as the entry point; nothing is
hardcoded. `rech check` (`rec_helper/config.py`) resolves references, validates required
fields and prints a summary; `--json` prints the fully resolved config.
Institution facts (committee name, IRB-number label, submission address, page,
font) are **not** config: they live in `institutions/<id>/profile.toml`.

## File references (`@`)

Any string value `"@path"` or `"@path#key"` is replaced by that file's content. Paths are
relative to the file containing the reference; referenced files may reference others.

| Target | Result |
|---|---|
| `"@cv.toml#pi"` | the `[pi]` table of `cv.toml` |
| `"@cv.toml"` | the whole TOML document |
| `"@中文計畫摘要.md"` | Markdown with `## headings` → table of sections |
| `"@中文計畫摘要.md#研究背景"` | one section (by key or heading) |
| `"@修正說明.md"` | Markdown without `##` headings → plain text |
| `"@note.txt"` | plain text |

Markdown rules: `## 二、研究背景` → key `background` (numbering ignored, see table under
`proposal`; other headings are used verbatim as keys). A section consisting only of `-` /
`1.` items becomes a list; anything else becomes paragraphs (wrapped lines are joined —
no space next to CJK — and blank lines separate paragraphs). `<!-- comments -->` and the
`# title` line are dropped; `**bold**` / `` `code` `` markers are stripped.

Required (validated): `phase`, `study.title_zh`, `study.title_en`, `study.type`,
`study.review_type`, `pi.name`, `pi.dept`, `dates.study_start`, `dates.study_end`,
`subjects.planned_n`.

## `institution`

| Field | Type | Description | Example |
|---|---|---|---|
| `institution` | string | Folder under `institutions/` whose profile + form pack to use (default `ntuh`; `REC_INSTITUTION` env overrides). Top-level key, before the first `[table]`. | `"ntuh"` |

When onboarding a new institution needs a field that isn't listed here, add it
under the matching section below and document it in this file.

## `extra_forms` / `site` (optional, top level)

| Field | Type | Description | Example |
|---|---|---|---|
| `extra_forms` | list | Form ids to generate on top of what the pack routes for this phase | `["DSMP"]` |
| `site` | string | NTUH branch whose consent templates to use (`HCH` 新竹臺大分院, `BMH` 生醫醫院); default: from `pi.dept` | `"HCH"` |

## Study documents (optional, top level; plain paths relative to the study folder, no `@`)

| Field | Type | Description | Example |
|---|---|---|---|
| `protocol` | string | Markdown source of the protocol; `rech protocol` drafts it, `rech generate` renders 計畫書_v<版本>.docx | `"計畫書.md"` |
| `protocol_file` | string | An existing protocol (.docx/.pdf/.md) used only by the checks | `"計畫書.docx"` |
| `english_abstract` | string | Markdown English abstract → 英文摘要_v<版本>.docx | `"英文摘要.md"` |
| `reply` | string | Review comments and answers (`## <序號>` with 意見／回覆／修正 lines) → 審查意見回覆表 | `"審查意見.md"` |
| `guidelines` | list | Reporting guidelines for `rech guidelines` (default: chosen from the study) | `["STROBE", "CLAIM"]` |

## `version` (optional)

```toml
[version]
number = "1.0"
date   = "2026/10/14"   # default: today
計畫書  = "1.1"           # per document: a number or { number = "1.1", date = "…" }
```

Printed in the header of generated 計畫書 / 摘要 / 回覆表; `rech stamp` uses it for other files.

## `phase` (required)

One of: `new`, `amendment`, `continuing`, `closure`, `suspension`, `sae`, `deviation`, `other`, `import`
(limited to the phases the institution's form pack routes).

Top-level key (must appear before the first `[table]`). Override per run without editing
the file: `rech closure` or `rech all --phase closure`.
To persist a switch, `rech set-phase closure` (`rec_helper/set_phase.py`) rewrites only
the value on the `phase =` line, keeping its comment and the rest of the file.

## Validation

`rec_helper/config.py` validates the resolved config on load and lists every problem at
once: missing required fields, an unknown `institution`, a `phase` the institution's form
pack doesn't route, unknown `study.type` / `study.review_type`,
sections of the wrong shape (e.g. `pi` resolving to text instead of a table), co-PIs
without a `name`, and quoted booleans (`"false"` is a non-empty string and would count
as true — write `false`). Optional sections (`co_pi`, `closure`, `amendment`,
`continuing_review`) may be omitted entirely; they and optional fields generators index
directly are filled with neutral defaults (`DEFAULTS` / `BOOL_FIELDS` in `rec_helper/config.py`).

## `study` (required)

| Field | Type | Description | Example |
|---|---|---|---|
| `irb_no` | string | IRB case number | `"202701001RINA"` |
| `project_no` | string | Project number (or "不適用") | `"不適用"` |
| `title_zh` | string | Chinese title | `"第二型糖尿病患者使用 SGLT2 抑制劑…"` |
| `title_en` | string | English title | `"SGLT2 Inhibitor Use and…"` |
| `type` | string | Study type | `retrospective`, `prospective`, `clinical_trial`, `genetic` |
| `design` | `研究設計` | 五、研究設計 (appended after the generated sentence) |
| `review_type` | string | IRB review type | `exempt`, `expedited`, `full_board` |
| `drug_device` | bool | Drug or device trial | `false` |
| `genetic` | bool | Involves genetic data | `false` |
| `multicenter` | bool | Multi-center study | `false` |

## `pi` (required) — usually `pi = "@cv.toml#pi"`

| Field | Type | Description | Example |
|---|---|---|---|
| `name` | string | PI Chinese name | `"王小明"` |
| `name_en` | string | PI English name | `"Hsiao-Ming Wang"` |
| `dept` | string | Department and title | `"內科部／主治醫師"` |
| `phone` | string | Contact phone | `"02-23123456 分機 00000"` |
| `email` | string | Contact email | `"example@ntuh.gov.tw"` |

## `co_pi` (optional, list) — usually `co_pi = "@cv.toml#co_pi"`

Each `[[co_pi]]` entry in `cv.toml`:

| Field | Type | Description |
|---|---|---|
| `name` | string | Co-PI Chinese name |
| `name_en` | string | Co-PI English name |
| `dept` | string | Department and title |

## `dates` (required)

| Field | Type | Description | Example |
|---|---|---|---|
| `study_start` | string | Study start date | `"2027年01月01日"` |
| `study_end` | string | Study end date | `"2026年05月31日"` |
| `data_period` | string | Data collection period | `"2020年1月至2024年12月"` |
| `irb_approval_date` | string | IRB approval date | `"2025年07月20日"` |

## `subjects` (required)

| Field | Type | Description | Example |
|---|---|---|---|
| `planned_n` | int | Planned enrollment number | `300` |
| `actual_n` | int | Actual enrolled (for closure/continuing) | `1180` |
| `consent_waiver` | bool | Waiver of informed consent | `true` |
| `vulnerable_population` | bool | Includes vulnerable subjects | `false` |
| `groups` | list | Subject groups with `name` and `n` | see below |

### `subjects.groups` (optional, list)

Array of inline tables:

```toml
groups = [
  { name = "SGLT2 抑制劑組", n = 600 },
  { name = "DPP-4 抑制劑組", n = 600 },
]
```

## `proposal` (optional) — usually `proposal = "@中文計畫摘要.md"`

Free text for the 中文計畫摘要, one `##` section per key. A missing section keeps the
form's placeholder. Lists render as `1. … 2. …`. Keep the whole summary within 2 pages.
Full example: `rech init ntuh-chart-review` copies one (`rec_helper/examples/ntuh-chart-review/中文計畫摘要.md`).

| Key | Markdown heading | Form section |
|---|---|---|
| `background` | `研究背景` | 二、研究背景 |
| `objectives` | `研究目的` | 三、研究目的 (string or list) |
| `design` | `研究設計` | 五、研究設計 (appended after the generated sentence) |
| `inclusion` / `exclusion` | `納入條件` / `排除條件` | 六、研究參與者 (string or list) |
| `data_source` | `資料來源` | 七、研究方法 (retrospective; default: the profile's `ehr_name`) |
| `variables` / `endpoints` | `資料收集項目` / `研究終點` | 七、研究方法 (retrospective) |
| `methods` | `研究方法` | 七、研究方法 (prospective / trials) |
| `statistics` | `統計分析` | 九、統計分析 |
| `attachments` | `附件` | 十一、附件 (string or list) |

## `online` (optional) — usually `online = "@線上填寫.md"`

Answers for institutions whose application is a web system (NTUH: `online_module` in the
pack's profile). `rech online` writes one copy-paste sheet per web page to `output/online/`
(`.md` + `.html` with 複製 buttons), deriving what it can from the rest of config.toml;
`rech online --skeleton` writes 線上填寫.md listing every field it couldn't derive.

One `## <題號> <標題>` section per answer; only the first word (the field id as printed on
the page, e.g. `A7`, `G29-1`, `研究領域`) matters, and it overrides the derived value.
Choice questions take the option text (a unique prefix is enough: `否`, `3-2-4`);
multi-choice questions take a `-` list. Follow-up questions the web page only reveals after an
earlier answer (NTUH: `C3` → `C3-1`, `H` route → its block, `B2` 藥品 → tab C) are listed
once that earlier answer is written here. NTUH picks the application by `study.review_type`:
`expedited` / `full_board` → 新案申請書 (+ 簡審範圍評核表 for expedited), `exempt` →
新案免審申請書 (field ids `免審1` … `免審11-2-1`); every type also gets 上傳文件 (which uploads
this study needs), 計畫主持人聲明書, 審查費 and 利益申報.

```markdown
## 研究領域
腫瘤學
## A7 經費贊助來源
- 自籌
## G1-1 醫療院所地點
- 新竹臺大分院
```

## `attachments` (optional) — usually `attachments = "@附件填寫.md"`

Prose and choices for DOCX attachments that config.toml can't hold. Same format as `online`:
one `## <key> …` per answer, first word is the key.

- 使用病歷資料進行研究申請表: keys in `ANSWER_KEYS` (`rec_helper/institutions/ntuh/attachments.py`);
  unanswered fields are written as 【待填】. `closure.data_safety.retention_years` fills the
  研究結束後 N 年銷毀 line.
- Every other official blank is filled row by row (`rec_helper/form_rows.py`): keys are
  `<FORM>-<n>` (`DSMP-5`, `AF127-4`); `rech attachments --skeleton` appends the study's
  questions to 附件填寫.md. Answers: `是` / `否：理由` (是否 rows), a `- option` list (checkboxes,
  `- option：說明` also fills its ＿＿), text (replaces the guidance), or one line per row with
  cells split by `｜` (log tables). Unanswered rows keep the blank's text.

## `closure` (when phase=closure)

| Field | Type | Description |
|---|---|---|
| `extensions` | int | Number of extensions granted |
| `amendments` | int | Number of amendments |
| `sae_count` | int | Number of SAEs during study |
| `specimens` | bool | Biological specimens collected |
| `data_safety.deidentified` | bool | Data is de-identified |
| `data_safety.encrypted` | bool | Data is encrypted |
| `data_safety.retention_years` | int | Years to retain data |
| `data_safety.authorized_personnel` | string | Who can access data |

## `amendment` (when phase=amendment)

| Field | Type | Description |
|---|---|---|
| `change_description` | string | Description of changes (or `"@修正說明.md"`) |
| `affects_consent` | bool | Changes affect consent form |
| `affects_risk` | bool | Changes affect risk level |

## `continuing_review` (when phase=continuing)

| Field | Type | Description |
|---|---|---|
| `enrollment_status` | string | Current enrollment status |
| `deviations` | int | Number of protocol deviations |
| `extension_requested` | bool | Requesting study extension |
