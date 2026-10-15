---
name: rec-helper
description: 臺大醫院研究倫理委員會（NTUH REC）送審資料助手 — turns one study folder (config.toml + cv.toml + 中文計畫摘要.md + 線上填寫.md + 附件填寫.md) into e-REC copy-paste sheets, the committee's official Word attachments filled in, PDFs and a layout gate, for every submission (新案 簡審/一般/免審, 變更, 持續審查, 結案, SAE, 偏差, 其他事項, 恩慈). Use when the user mentions 臺大/NTUH REC, e-REC, IRB/REC submissions, ethics review paperwork, or filling the committee's forms.
---

# REC Helper

One study folder → everything a 臺大醫院 REC submission needs:

- `output/online/*.html|md` — e-REC web pages as copy-paste sheets (● from the Markdown,
  ◆ derived from config — confirm, ✎ still to answer)
- `output/*.docx|pdf` — the committee's official blanks, filled
- `output/layout_report.md` — layout gate; **0 Errors before submission**

User guide (Traditional Chinese): `docs/NTUH.md`. Config reference:
[config-schema.md](references/config-schema.md).

## Running it

All commands run in the **study folder** (the one holding `config.toml`) via `rech`
(`python -m rec_helper` when `rech` is not on PATH). `rech doctor` reports what's missing
(LibreOffice, poppler, font, blanks).

```bash
rech init ntuh-chart-review   # start from the example (refuses to overwrite)
rech templates                # download the committee's blanks once (or set REC_TEMPLATES)
rech all                      # attachments + online sheets + PDF + gate + dashboard
rech online --skeleton        # list unanswered web questions → 線上填寫.md
rech attachments --skeleton   # append the study's attachment questions → 附件填寫.md
rech closure                  # any phase: new amendment continuing closure suspension sae deviation other import
rech protocol                 # draft 計畫書.md from the study (then protocol = "計畫書.md")
rech consistency              # cross-document facts → output/consistency_report.md
rech precheck                 # AF-063 pre-review → output/precheck_report.md
rech guidelines               # STROBE/SPIRIT/CLAIM/TRIPOD-LLM coverage → output/guidelines_report.md
rech refs                     # verify references online + acronyms (--offline: acronyms only)
rech reply                    # 審查意見.md template → 審查意見回覆表 (+ 修正前後對照表 rows)
rech stamp FILE…              # version-date stamped copies in output/stamped/ + 版本紀錄.md
```

## Workflow when the user gives free text

1. Save the raw text, then distill it into `config.toml` / `cv.toml` / `中文計畫摘要.md`
   ([distill.md](references/distill.md)); run `rech check`.
2. Decide the routing facts with the user: `study.type`, `study.review_type`
   (exempt / expedited / full_board), `subjects.consent_waiver`.
3. `rech online --skeleton` and `rech attachments --skeleton`; draft answers in
   `線上填寫.md` / `附件填寫.md`, marking drafted prose with an HTML comment so the user reviews it.
4. `rech protocol`, then write the 【待寫】 chapters of `計畫書.md` with the user (their facts, your
   drafting; never invent results, references or numbers). Set `protocol = "計畫書.md"`.
5. `rech all` (includes consistency, precheck, guidelines) and `rech refs`; report ✎ items still to
   answer, ◆ derived answers to confirm, ✗ inconsistencies, □ 待補 pre-review items, and layout errors.
6. After review: paste the comments into `審查意見.md` (`rech reply`), draft each 回覆 and 修正 line with
   the user, and bump `[version]` for the revised documents.

## Rules

- Study facts live in plain text (config + `@` files); never hardcode them in code.
- Institution facts live in the pack (`rec_helper/institutions/ntuh/profile.toml`, `forms.py`).
- Official blanks in `templates/` are never edited; generators fill copies.
- Browsing the e-REC system is read-only unless the user explicitly asks otherwise:
  never press 儲存 / 送出 / 刪除 on a real case.
- Signatures, e-REC-only fields (研究領域 dropdown, team accounts, 審查費, 利益申報) and the
  protocol itself stay with the user.

## Another committee

The engine is institution-agnostic: a new committee is a new pack under `institutions/<id>/`.
See [onboard-institution.md](references/onboard-institution.md).
