# REC Helper

臺大醫院研究倫理委員會（NTUH REC）送審資料助手, packaged as `rec-helper` (command `rech`):
study facts (`config.toml` + `@` files) + the NTUH pack (`rec_helper/institutions/ntuh/`) →
e-REC copy-paste sheets + the committee's official Word blanks filled in → PDF → layout gate.
The engine stays institution-agnostic (another committee = another pack).
User guide (zh-TW): `docs/NTUH.md`.

## Quick Start

The repo root doubles as a study folder (a copy of the `ntuh-chart-review` example).
`make <x>` = `uv run rech <x>`; without uv: `python -m rec_helper <x>` (or `make <x> RUN="python -m"`):

```bash
# Edit config.toml (facts, `institution = "<id>"`), cv.toml (team), 中文計畫摘要.md (prose)
make check                        # Resolve @references + validate
make templates                    # Once: download the committee's blank forms
make all                          # Attachments + e-REC sheets + PDF + layout gate + dashboard
make closure                      # = make all PHASE=closure (any phase; file untouched)
make set-phase PHASE=closure      # Persist the phase in config.toml (keeps comments)
make onboard INST=<id>            # New institution: blanks in templates/<id>/ → draft pack
uv run rech doctor                # LibreOffice, poppler, form font, config, blanks
```

Installed users run the same commands as `rech <x>` in any study folder
(`rech init <example>` starts one and copies `.claude/skills/rec/` into it).

## Conventions

- **Python**: Managed by `uv` (pyproject.toml, hatchling build), run via `uv run rech` or `make`
- **Package**: all code lives in `rec_helper/` (import `rec_helper.*`, never path hacks);
  data shipped in the wheel (packs, examples, `fonts.conf`) sits inside it, and the skill is
  force-included as `rec_helper/skill`. Paths for study data are relative to the **cwd**
  (the study folder), never to `__file__`
- **New CLI command**: add it to `rec_helper/cli.py` (and a Makefile target if contributors use it)
- **Three kinds of data, never mixed**:
  - study facts → `config.toml` (+ the files it `@`-references)
  - institution facts (names, IRB-no label, submission address, page, margins, font, blank locations) → `<pack>/profile.toml`
  - form list + routing → `<pack>/forms.py`
- **No institution literals in code**: generators read `institution()` (`rec_helper.docx_utils`); shared modules read `rec_helper.institution.current()`
- **Active institution**: `REC_INSTITUTION` env → `institution` in config.toml → `ntuh`
- **Pack lookup** (first wins): `<cwd>/institutions/<id>/` (local, from `rech onboard`) →
  `rec_helper.institutions` entry points (installed packages) → bundled `rec_helper/institutions/<id>/`
- **Web-system forms** (NTUH): never DOCX — `rech online` writes copy-paste sheets; field ids/options mirror the web pages
- **Generators**: prefer `template_fill.blank_generator` (fill the official blank); rebuild with python-docx only when a blank can't be filled
- **Font**: the profile's `font` (NTUH: 標楷體 / DFKai-SB); no theme fonts (`pin_form_font`); fonts the official blank itself uses are notes, not errors
- **Checkbox**: ■ (U+25A0) = checked, □ (U+25A1) = unchecked, via `check()`
- **Config (SSOT)**: All study data in plain text, never hardcoded. `config.toml` holds
  structured fields; `"@file"` / `"@file#key"` values inline other files (`@cv.toml#pi`,
  `@中文計畫摘要.md`). Long prose goes in Markdown (`## 標題` → section key), not TOML strings.
  Loader + validation: `rec_helper/config.py`. Never re-dump config.toml — use `PHASE=` for a
  one-off run, or `set_phase.py` (edits only the `phase =` line) to persist it
- **Output**: DOCX → `output/`, PDF → `output/`, PNG previews → `output/preview/`
- **Page**: profile page size + per-form margins, applied by `generate_all`
- **Blanks**: `templates/<id>/` in the study folder (gitignored; `$REC_TEMPLATES/<id>/` to share), the gate's ground truth, never edited, never packaged
- **Layout gate**: `make validate` must show 0 errors before submission; PDF is the submission copy

## Project Structure

- `rec_helper/cli.py` — `rech` command (init, check, generate, online, attachments, consistency, precheck, guidelines, refs, protocol, reply, stamp, versions, pdf, templates, onboard, validate, all, dashboard, set-phase, institutions, skill, doctor; `rech <phase>` = `all --phase`)
- `rec_helper/institutions/<id>/` — bundled packs: profile.toml, forms.py (registered as entry points in pyproject.toml)
- `rec_helper/examples/` — Complete example studies (`rech init <name>` / `make init EXAMPLE=<name>`)
- `rec_helper/institution.py` — Pack lookup (local → installed → bundled) + active profile loader
- `rec_helper/config.py` — config.toml loader (`@` references, Markdown sections, `rech check`) + validation: required fields, enums, real booleans, defaults for optional sections
- `rec_helper/template_fill.py` — Generic fill-the-blank generator (labels → values, □ → ■)
- `rec_helper/onboard.py` — Blank forms → draft profile + forms.py + inventory in `<cwd>/institutions/<id>/`
- `rec_helper/docx_utils.py` — Shared DOCX helpers (profile-aware; `form_filename` for output names)
- `rec_helper/form_selector.py` — Phase + study type → required forms (active pack); shared `PHASE_NAMES`
- `rec_helper/generators/` — Rebuild generators for forms without an official blank (`proposal.py`: 中文計畫摘要; `generators.*` in a FORM_REGISTRY)
- `rec_helper/generate_all.py` — Main orchestrator
- `rec_helper/set_phase.py` — Persist `phase = "..."` in config.toml without losing comments
- `rec_helper/online_forms.py` — Copy-paste sheets (`output/online/*.md|html`) for forms filled in an IRB web system; pack declares them in `online_module` (NTUH: `institutions/ntuh/online.py` new case, `online_phases.py` later submissions), answers from config + `online = "@線上填寫.md"`
- `rec_helper/form_rows.py` — Generic filler for question-per-row official blanks (header / 是否 / checkbox / text / log-table rows, keys `<FORM>-<n>`); `rech attachments --skeleton` lists the questions. A pack lists such blanks in its generator module's `ROW_FORMS` (NTUH: `attachments.py`)
- `docs/NTUH.md` — User guide for NTUH colleagues (Traditional Chinese)
- `rec_helper/study_text.py` — Everything a study says (config, summary, web answers incl. derived, attachment answers, protocol from `protocol` / `protocol_file`), for the checks below
- `rec_helper/consistency.py` — `rech consistency`: cross-document facts (counts, ages, dates, title, retention, wording vs settings; negation-aware)
- `rec_helper/precheck.py` — `rech precheck`: pre-review against NTUH AF-063 審查重點 (■ □ ？ －)
- `rec_helper/guidelines.py` — `rech guidelines`: reporting-guideline coverage (SPIRIT, STROBE, STARD, CLAIM, TRIPOD+AI, TRIPOD-LLM; paraphrased items)
- `rec_helper/refs.py` — `rech refs`: reference lookup (Crossref, PubMed, DataCite/arXiv) + acronym definitions
- `rec_helper/generators/protocol.py` + `markdown_doc.py` — `rech protocol` drafts 計畫書.md; PROTOCOL / ABSTRACT_EN render Markdown to DOCX
- `rec_helper/reply.py` — `rech reply`: 審查意見.md → REPLY 審查意見回覆表; its 修正 lines feed AMENDTABLE
- `rec_helper/versions.py` — `[version]` in config, version headers, `rech stamp` copies + 版本紀錄.md ledger
- `rec_helper/checklist.py` — ■/□ checklist generator
- `rec_helper/dashboard.py` — Submission status dashboard
- `rec_helper/convert.py` — DOCX→PDF→PNG pipeline
- `rec_helper/fetch_templates.py` — Scrape or index official blanks → `templates/<id>/`
- `rec_helper/validate_layout.py` — Layout/font safety gate → `output/layout_report.md`
- `.claude/skills/rec/` — Claude Code skill set, shipped in the wheel (onboarding: `references/onboard-institution.md`)
- `.github/workflows/release.yml` — tag `vX.Y.Z` (= pyproject version) → GitHub Release (+ PyPI when `PUBLISH_PYPI=true`)

## Testing

```bash
make init FORCE=1 && make templates && make all
make test   # NTUH example × every phase, form routing, row filler, layout gate, CLI
            # (DOCX tests skip when templates/ntuh/ isn't downloaded, as in CI)
make lint   # ruff; CI runs both on every PR, plus a wheel smoke test outside the repo
make build  # sdist + wheel; install dist/*.whl in a fresh venv to try it as a user
```

New official blank: map it in `profile.toml` (`named_forms` / `templates.files`), add it to
`ROW_FORMS` in `attachments.py` (registered automatically) and route it in `forms.py`. New config field: document it in
`.claude/skills/rec/references/config-schema.md`, and add it to `DEFAULTS` /
`BOOL_FIELDS` in `rec_helper/config.py` if generators index it directly.
