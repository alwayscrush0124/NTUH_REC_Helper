"""研究計畫書 and English abstract: drafted from the study, rendered from Markdown.

The protocol is the one required document with no official blank. Its source is
plain Markdown in the study folder, `protocol = "計畫書.md"` in config.toml:

    rech protocol --skeleton   →  計畫書.md, every chapter the committee expects,
                                  pre-filled from config / 中文計畫摘要 / 線上填寫 /
                                  附件填寫; gaps are 【待寫】 with a hint
    rech generate              →  output/計畫書_v<版本>.docx (version in the header)

The chapter list follows what NTUH asks a protocol to cover (收案對象、執行地點、
樣本數、納入及排除條件、執行步驟及方法、研究設計、統計方法、研究對象權益之保障、
預期成果及效益) plus data protection and AI use. `english_abstract = "英文摘要.md"`
renders the optional English abstract the same way.
"""
import os

from rec_helper.generators.markdown_doc import TODO_MARK, render

TYPE_ZH = {"retrospective": "回溯性", "prospective": "前瞻性", "clinical_trial": "臨床試驗", "genetic": "基因"}
DESIGN_ZH = {"cohort": "世代研究", "case_control": "病例對照研究", "cross_sectional": "橫斷面研究",
             "rct": "隨機對照試驗", "single_arm": "單臂試驗"}
NL2 = "\n\n"


def _todo(hint):
    return f"{TODO_MARK}{hint}"


def _text(value):
    if isinstance(value, list):
        return "\n".join(f"{i}. {v}" for i, v in enumerate(value, 1))
    return str(value or "").strip()


def _items(value):
    if isinstance(value, list):
        return "\n".join(f"- {v}" for v in value)
    return _text(value)


def _or_todo(value, hint):
    return _text(value) or _todo(hint)


def _zh_number(n):
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    return ("十" if n < 20 else digits[n // 10] + "十") + (digits[n % 10] if n % 10 else "")


def _sub(title, body):
    return f"### {title}{NL2}{body}"


def skeleton(config):
    """Markdown draft of the protocol from everything the study already states."""
    from rec_helper import study_text
    s, subj, dates = config["study"], config["subjects"], config.get("dates", {})
    p = config.get("proposal") if isinstance(config.get("proposal"), dict) else {}
    online = study_text.online_answers(config)
    att = study_text.attachment_answers(config)
    ds = (config.get("closure", {}) or {}).get("data_safety") or {}

    groups = [g for g in subj.get("groups") or [] if isinstance(g, dict)]
    group_lines = "\n".join(f"- {g['name']}：{g.get('n', '')}" for g in groups)
    site = online.get("G2") or ("、".join(online["G1-1"]) if isinstance(online.get("G1-1"), list) else None)
    design = f"本研究為{TYPE_ZH.get(s.get('type'), '')}{DESIGN_ZH.get(s.get('design'), '')}"
    if s.get("type") == "retrospective" and dates.get("data_period"):
        design += f"，回溯分析{dates['data_period']}之既有資料"
    design += "，為多中心研究。" if s.get("multicenter") else "，為單一中心研究。"
    if p.get("design"):
        design += NL2 + _text(p["design"])

    if subj.get("consent_waiver"):
        consent = "本研究申請免除知情同意，理由如下：" + NL2 + _or_todo(online.get("H3-1"), "免除知情同意之理由")
    else:
        consent = _todo("說明知情同意程序：由誰、何時、何地說明並取得同意")
    ai = att.get("生成式AI") or att.get("資訊科技")
    uses_ai = bool(ai) and not str(ai).startswith("否")

    subjects = NL2.join([
        _sub("收案對象與執行地點", _or_todo(site, "收案或執行之科部、病房、院區")),
        _sub("樣本數", NL2.join(x for x in (
            f"預計收案 {subj.get('planned_n', '')} 人／筆。", group_lines,
            _or_todo(att.get("樣本數估算"), "樣本數估算依據（效果量、檢定力、顯著水準）")) if x)),
        _sub("納入條件", _items(p.get("inclusion")) or _todo("納入條件")),
        _sub("排除條件", _items(p.get("exclusion")) or _todo("排除條件")),
    ])
    method_parts = [_text(p.get("methods"))] if p.get("methods") else []
    for key, title, fmt in (("data_source", "資料來源", _text), ("variables", "資料收集項目", _items),
                            ("endpoints", "研究終點", _text)):
        if p.get(key):
            method_parts.append(_sub(title, fmt(p[key])))
    methods = NL2.join(method_parts) or _todo("執行步驟、收集項目、評估指標與時程")
    rights = NL2.join([
        _sub("知情同意", consent),
        _sub("風險與效益", _or_todo(online.get("G28-1"), "受試者可能之風險、降低風險的方法，及預期效益")),
        _sub("隱私保護", _or_todo(online.get("G29-2"), "如何保護受試者隱私")),
    ])
    storage = NL2.join([
        _or_todo(online.get("G29-1") or att.get("資安措施"), "資料保存地點、加密、存取權限"),
        f"研究資料於計畫結束後保存 {ds['retention_years']} 年，期滿銷毀。" if ds.get("retention_years")
        else _todo("保存年限與銷毀方式"),
    ])
    ai_body = _text(ai) + NL2 + _or_todo(att.get("AI合約"), "說明輸入模型之資料範圍、去識別化方式，以及提供者是否保留或用於訓練")

    chapters = [
        ("研究背景與文獻回顧", _or_todo(p.get("background"), "疾病或問題現況、現有證據與不足、本研究的必要性（附文獻）")),
        ("研究目的", _items(p.get("objectives")) or _todo("主要目的與次要目的")),
        ("研究設計", design),
        ("研究對象", subjects),
        ("研究方法與執行步驟", methods),
        ("統計分析", _or_todo(p.get("statistics"), "主要與次要分析方法、缺失值處理、顯著水準、使用軟體")),
        ("研究對象權益之保障", rights),
        ("資料保存與安全", storage),
        ("人工智慧之使用", ai_body) if uses_ai else None,
        ("研究期程", f"預計執行期間：{dates.get('study_start', '')} 至 {dates.get('study_end', '')}。"
                    + NL2 + _todo("各階段時程（資料擷取、分析、撰寫）")),
        ("預期成果及效益", _or_todo(p.get("預期成果") or p.get("expected"), "預期結果、對臨床或學術的貢獻、成果發表方式")),
        ("參考文獻", _todo("依引用順序列出；含 DOI 或 PMID 以便 `rech refs` 核對")),
    ]
    pi = config.get("pi", {})
    lines = ["# 研究計畫書",
             f"**計畫名稱**：{s.get('title_zh', '')}",
             f"**英文名稱**：{s.get('title_en', '')}",
             f"**計畫主持人**：{pi.get('name', '')}（{pi.get('dept', '')}）"]
    for n, (title, body) in enumerate((c for c in chapters if c), 1):
        lines.append(f"## {_zh_number(n)}、{title}{NL2}{body}")
    note = ("<!-- 由 rech protocol --skeleton 依現有資料擬稿；【待寫】處請補上，其餘段落請逐段確認或改寫。\n"
            "     config.toml：protocol = \"計畫書.md\"；版本：[version] 計畫書 = \"1.0\" -->")
    return note + NL2 + NL2.join(lines) + "\n"


ENGLISH_TEMPLATE = """# Abstract

**Title**: {title}

## Background

【待寫】

## Objectives

【待寫】

## Methods

【待寫】

## Expected Results

【待寫】

## Keywords

【待寫】
"""


def _source(config, key, default):
    path = config.get(key)
    if not isinstance(path, str) or not path:
        return None
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{key} = {path!r}: file not found (rech protocol --skeleton writes {default})")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def generate_protocol(config, output_dir):
    from rec_helper.versions import label, version_of
    md = _source(config, "protocol", "計畫書.md") or skeleton(config)   # no source yet: the draft, 【待寫】 highlighted
    number, _ = version_of(config, "計畫書")
    return render(md, os.path.join(output_dir, f"計畫書_v{number}.docx"), header=label(config, "計畫書"))


def generate_english_abstract(config, output_dir):
    from rec_helper.versions import label, version_of
    md = _source(config, "english_abstract", "英文摘要.md") or ENGLISH_TEMPLATE.format(title=config["study"]["title_en"])
    number, _ = version_of(config, "英文摘要")
    return render(md, os.path.join(output_dir, f"英文摘要_v{number}.docx"),
                  header=label(config, "英文摘要", english=True), size=11)


def main(config_path="config.toml", path="計畫書.md"):
    from rec_helper.config import ConfigError, load_config
    from rec_helper.generators.markdown_doc import todo_count
    from rec_helper.institution import activate
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    activate(config)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            print(f"✗ {path} already exists ({todo_count(fh.read())} 處【待寫】) — edit it, or delete it to redraft")
        return 1
    md = skeleton(config)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"■ {path} written — {todo_count(md)} 處【待寫】; add `protocol = \"{path}\"` to config.toml, then `rech generate`")
    return 0
