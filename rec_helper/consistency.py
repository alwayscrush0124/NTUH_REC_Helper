"""Cross-document consistency: the same fact must read the same everywhere.

Administrative review sends a submission back for exactly these slips: the
summary says 18 歲 while the web form says 19, the protocol still lists a
pediatric arm the inclusion criteria dropped, the case count differs between
the summary and G5. This module pulls each fact out of every document
(study_text.corpus) and reports disagreements:

  ✗ 不一致   two documents state different values
  ⚠ 請確認   wording that contradicts a setting (e.g. 兒科 in a study without minors)

Usage: rech consistency [config.toml] [--output DIR]   → output/consistency_report.md
"""
import os
import re
from dataclasses import dataclass

from rec_helper import study_text

ERROR, WARN = "✗ 不一致", "⚠ 請確認"
MINOR_WORDS = r"兒童|兒科|小兒|未成年|孩童|新生兒|嬰兒|青少年|pediatric|paediatric|children|infant"
AI_WORDS = r"大型語言模型|\bLLMs?\b|生成式|\bGPT|Gemini|\bClaude\b|人工智慧|機器學習|深度學習"


@dataclass
class Finding:
    level: str
    topic: str
    message: str


def _int(value):
    m = re.search(r"\d[\d,]*", str(value or ""))
    return int(m.group().replace(",", "")) if m else None


def _year_months(text):
    """'2025年1月至2025年12月' / '2025/01-2025/12' → [(2025, 1), (2025, 12)]."""
    return [(int(y), int(m)) for y, m in re.findall(r"(20\d\d)\s*[年/.-]\s*(\d{1,2})", str(text or ""))]


NEGATION = re.compile(r"(?:不含|不包括|不包含|不涉及|排除|除外|非|無|未納入|不納入|未滿|超出)[^，。；\n]{0,8}$")


def _affirmed(text, match):
    """The match isn't negated by the words just before it (不含兒童, 不涉及 90 歲以上)."""
    return not NEGATION.search(text[max(0, match.start() - 12):match.start()])


def _ages(text):
    """Age bounds stated in prose: (min, max) with None where unstated."""
    lo = hi = None
    for m in re.finditer(r"(\d{1,2})\s*歲?\s*(?:至|到|~|～|－|-|–)\s*(\d{1,3})\s*歲", text):
        if _affirmed(text, m):
            lo, hi = int(m.group(1)), int(m.group(2))
    for m in re.finditer(r"(?:年滿|滿)\s*(\d{1,2})\s*歲|(\d{1,2})\s*歲(?:\(含\)|（含）)?以上(?:之|的)?(?:成人|病人|患者|受試者|個案)", text):
        if _affirmed(text, m):
            lo = int(m.group(1) or m.group(2))
    return lo, hi


def _totals(text):
    """Case totals announced in prose (預計收錄 750 筆, 樣本數 300 人)."""
    pat = r"(?:預計(?:收錄|收案|納入|招募)|總(?:收案|樣本)數?|樣本數|共收錄)[^\d\n]{0,8}(\d[\d,]*)\s*(?:人|筆|例|位|名)"
    return {int(x.replace(",", "")) for x in re.findall(pat, text)}


def check(config):
    findings = []
    texts = study_text.corpus(config)
    online = study_text.online_answers(config)
    att = study_text.attachment_answers(config)
    s, subj, dates = config["study"], config["subjects"], config.get("dates", {})
    add = lambda level, topic, msg: findings.append(Finding(level, topic, msg))  # noqa: E731

    # ── 收案數 ──
    n = subj.get("planned_n")
    groups = [g.get("n") for g in subj.get("groups") or [] if isinstance(g, dict) and g.get("n")]
    if groups and n and sum(groups) != n and len(groups) > 1:
        add(WARN, "收案數", f"分組人數合計 {sum(groups)}（{'+'.join(map(str, groups))}）≠ planned_n {n}；若分組有重疊（如配對後）可忽略")
    for prefix in ("G3", "G4", "G5", "G6"):
        parts = [_int(online.get(f"{prefix}-{i}")) for i in range(1, 5)]
        if any(p for p in parts) and all(p is not None for p in parts) and n and sum(parts) != n:
            add(ERROR, "收案數", f"線上申請書 {prefix}-1～4 合計 {sum(parts)} ≠ config 預計收案數 {n}")
    allowed = {n, *groups} | {_int(online.get(f"G{g}-{i}")) for g in (3, 4, 5, 6) for i in range(1, 6)}
    for name, text in texts.items():
        for total in sorted(_totals(text) - allowed):
            add(ERROR, "收案數", f"{name}寫預計收案 {total}，但 config 為 {n}")

    # ── 年齡 ──
    g_lo, g_hi = _int(online.get("G8-1")), _int(online.get("G8-2"))
    for name, text in texts.items():
        if name == "線上申請書":
            continue
        lo, hi = _ages(text)
        if lo is not None and g_lo is not None and lo != g_lo:
            add(ERROR, "年齡", f"{name}最小年齡 {lo} 歲，線上申請書 G8-1 為 {g_lo} 歲")
        if hi is not None and g_hi not in (None, 999) and hi != g_hi:
            add(ERROR, "年齡", f"{name}最大年齡 {hi} 歲，線上申請書 G8-2 為 {g_hi} 歲")
    minors_allowed = subj.get("vulnerable_population") or (g_lo is not None and g_lo < 18)
    if not minors_allowed:
        for name, text in texts.items():
            hits = sorted({m.group() for m in re.finditer(MINOR_WORDS, text, flags=re.I) if _affirmed(text, m)})
            if hits:
                add(WARN, "易受傷害族群", f"{name}出現「{'、'.join(hits)}」，但本案未納入未成年人（vulnerable_population = false）")

    # ── 日期 ──
    start, end = _year_months(dates.get("study_start")), _year_months(dates.get("study_end"))
    if start and end and start[0] >= end[0]:
        add(ERROR, "日期", f"研究開始 {dates['study_start']} 不早於結束 {dates['study_end']}")
    period = _year_months(dates.get("data_period"))
    f3 = _year_months(online.get("F3"))
    if period and f3 and period != f3:
        add(ERROR, "資料期間", f"線上申請書 F3「{online['F3']}」≠ config data_period「{dates['data_period']}」")
    if s.get("type") == "retrospective" and period and start and period[-1] >= start[0]:
        add(ERROR, "資料期間", f"回溯性資料期間結束於 {period[-1][0]}/{period[-1][1]}，晚於研究開始 {dates['study_start']}"
                              "：回溯性研究只能使用申請前已存在的資料")
    for name, text in texts.items():
        for y, m, y2, m2 in re.findall(r"(20\d\d)\s*年\s*(\d{1,2})\s*月\s*(?:至|到|~|～|－|-)\s*(20\d\d)\s*年\s*(\d{1,2})\s*月", text):
            stated = [(int(y), int(m)), (int(y2), int(m2))]
            if period and stated != [period[0], period[-1]] and "資料" in text:
                if stated[0][0] <= period[-1][0] and stated[-1][0] >= period[0][0]:
                    add(WARN, "資料期間", f"{name}寫 {y}年{m}月至{y2}年{m2}月，config data_period 為「{dates['data_period']}」")

    # ── 單／多中心 ──
    a4 = str(online.get("A4", ""))
    if s.get("multicenter") and a4.startswith("單一"):
        add(ERROR, "多中心", "config multicenter = true，線上申請書 A4 卻是單一中心")
    if not s.get("multicenter") and any("多中心" in t for t in texts.values()):
        add(WARN, "多中心", "文件提到「多中心」，但 config multicenter = false")

    # ── 研究類型、同意 ──
    if s.get("type") == "retrospective":
        for name, text in texts.items():
            if re.search(r"(?<!非)前瞻", text) and name != "線上申請書":
                add(WARN, "研究類型", f"{name}提到「前瞻」，但 config 為回溯性研究")
    if subj.get("consent_waiver"):
        for name, text in texts.items():
            if re.search(r"簽署(?:受試者)?(?:說明及)?同意書", text) and not re.search(r"免除", text) and name != "附件填寫":
                add(WARN, "知情同意", f"{name}提到簽署同意書，但本案申請免除知情同意")

    # ── 保存年限 ──
    years = (config.get("closure", {}).get("data_safety") or {}).get("retention_years")
    if years:
        for name, text in texts.items():
            for y in {int(v) for v in re.findall(r"保存\s*(\d{1,2})\s*年", text)} - {int(years)}:
                add(ERROR, "保存年限", f"{name}寫保存 {y} 年，config retention_years = {years}")

    # ── 資料是否出院、AI 使用 ──
    # what the study says (answer values, not the 附件填寫 key names like 生成式AI)
    content = "\n".join([texts["計畫書"], texts["中文計畫摘要"], texts["線上申請書"],
                         "\n".join(str(v) for v in att.values())])
    gen_ai = str(att.get("生成式AI", ""))
    cloud = any(_affirmed(content, m) for m in re.finditer(r"雲端|\bcloud\b|\bAPI\b", content, flags=re.I))
    uses_ai = (gen_ai and not gen_ai.startswith("否")) or any(
        _affirmed(content, m) for m in re.finditer(AI_WORDS, content, flags=re.I))
    if str(online.get("F4", "")).startswith("否") and cloud and uses_ai:
        add(WARN, "資料攜出", "F4 勾「資料僅在院內使用」，但文件提到雲端／API 服務：請確認送往雲端的是否僅限去識別化資料，並在病歷申請表第 10 大題說明")
    if gen_ai.startswith("否") and re.search(AI_WORDS, texts["計畫書"] + texts["中文計畫摘要"], flags=re.I):
        add(ERROR, "生成式 AI", "計畫書／摘要使用 AI 模型，但病歷申請表第 10.1 題答「否」")

    # ── 計畫名稱 ──
    proto = texts["計畫書"]
    norm = lambda t: re.sub(r"[\s:：]", "", t)  # noqa: E731
    if proto and s.get("title_zh") and norm(s["title_zh"]) not in norm(proto):
        quoted = re.search(r"(?:題名|計畫名稱|研究題目|計畫題目)[^「\n]{0,6}「([^」]{8,160})」", proto)
        if quoted:
            add(ERROR, "計畫名稱", f"計畫書寫「{re.sub(chr(10), '', quoted.group(1))}」，config 為「{s['title_zh']}」")
        else:
            add(WARN, "計畫名稱", "計畫書裡找不到與 config 完全相同的中文計畫名稱（舊題目？）")
    return findings


def report(config, findings):
    lines = ["# 跨文件一致性檢查", "", f"> 計畫：{config['study']['title_zh']}",
             f"> 比對來源：中文計畫摘要、線上申請書（含推定答案）、附件填寫{'、計畫書' if study_text.protocol_path(config) else '（無計畫書：在 config.toml 設 protocol 或 protocol_file）'}", ""]
    if not findings:
        lines.append("■ 沒有發現不一致。")
    for level in (ERROR, WARN):
        rows = [f for f in findings if f.level == level]
        if rows:
            lines += [f"## {level}（{len(rows)}）", ""] + [f"- **{f.topic}**：{f.message}" for f in rows] + [""]
    return "\n".join(lines) + "\n"


def main(config_path="config.toml", output_dir="output", strict=False):
    from rec_helper.config import ConfigError, load_config
    from rec_helper.institution import activate
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    activate(config)
    findings = check(config)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "consistency_report.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report(config, findings))
    errors = sum(f.level == ERROR for f in findings)
    print(f"Consistency: {errors} 不一致, {len(findings) - errors} 請確認 → {path}")
    for f in findings:
        print(f"  {f.level[0]} {f.topic}：{f.message}")
    return 1 if strict and errors else 0
