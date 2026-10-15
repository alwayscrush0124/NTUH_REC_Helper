"""Pre-review against the committee's reviewer checklist (NTUH: AF-063 臨床研究案件審查重點).

Committee members score each submission on AF-063. Running the same items over
the study before submitting surfaces what they are likely to ask about:

  ■ 符合        the material addresses it (where it is said is shown)
  □ 待補        required for this study and not found
  ？ 人工確認    can't be judged from text (e.g. the PI's qualification)
  － 不適用      the item doesn't apply to this study type

Text evidence is searched in the protocol first, then the summary, web-form
answers and attachment answers (study_text.corpus). Item wording is condensed
from AF-063 v08.2; the official form is the reference.

Usage: rech precheck [config.toml] [--output DIR]   → output/precheck_report.md
"""
import os
import re
from dataclasses import dataclass

from rec_helper import study_text

OK, TODO, MANUAL, NA = "■", "□", "？", "－"
LABEL = {OK: "符合", TODO: "待補", MANUAL: "人工確認", NA: "不適用"}


@dataclass
class Ctx:
    config: dict
    online: dict
    att: dict
    texts: dict
    forms: list

    @property
    def s(self):
        return self.config["study"]

    @property
    def retro(self):
        return self.s["type"] == "retrospective"

    @property
    def interventional(self):
        return self.s["type"] == "clinical_trial" or self.s.get("design") in ("rct", "single_arm")

    @property
    def prospective(self):
        return self.s["type"] in ("prospective", "clinical_trial")

    def find(self, pattern):
        """First document (protocol first) whose text matches; None when nowhere."""
        for name in ("計畫書", "中文計畫摘要", "附件填寫", "線上申請書"):
            if re.search(pattern, self.texts.get(name, ""), flags=re.I):
                return name
        return None

    def says(self, key, prefix):
        v = self.online.get(key)
        items = v if isinstance(v, list) else [v] if v else []
        return any(str(i).startswith(prefix) for i in items)


def _seen(ctx, where):
    """'見計畫書', or a nudge when a protocol exists but only another document says it."""
    if where != "計畫書" and ctx.texts.get("計畫書"):
        return f"見{where}（計畫書未提及，建議補入）"
    return f"見{where}"


def evidence(pattern, what):
    """Item satisfied when `pattern` appears in some document."""
    def rule(ctx):
        where = ctx.find(pattern)
        return (OK, _seen(ctx, where)) if where else (TODO, f"找不到{what}的說明")
    return rule


def only(pred, rule, reason="本案不適用"):
    def wrapped(ctx):
        return rule(ctx) if pred(ctx) else (NA, reason)
    return wrapped


def manual(note):
    return lambda ctx: (MANUAL, note)


def _team(ctx):
    staff = ctx.att.get("接觸人員")
    if ctx.config.get("co_pi") or staff:
        return OK, "研究團隊已列（cv.toml／附件 9.2.1）"
    return MANUAL, "只有主持人：確認人力與時間足以執行（e-REC 研究團隊頁）"


def _sample_size(ctx):
    where = ctx.find(r"樣本數(?:估算|計算)|檢定力|power|effect size|效果量")
    if where:
        return OK, _seen(ctx, where)
    return TODO, "沒有樣本數估算的依據（研究設計與統計方法之合理性）"


def _dsmp(ctx):
    needs = (ctx.interventional and (ctx.s.get("drug_device") or ctx.config["subjects"].get("vulnerable_population"))) \
        or (ctx.interventional and ctx.s.get("multicenter"))
    if "DSMP" in ctx.forms:
        return OK, "已附資料及安全性監測計畫"
    if needs:
        return TODO, "新藥/新醫材/新技術、易受傷害族群介入性研究或本院主導多機構試驗須提 DSMP（extra_forms = [\"DSMP\"]）"
    return OK, "不屬須建置 DSMP 之條件（9.1）"


def _vulnerable(ctx):
    if not ctx.config["subjects"].get("vulnerable_population"):
        return NA, "未納入易受傷害族群"
    if ctx.retro and ctx.config["subjects"].get("consent_waiver"):
        return OK, "回溯性研究免除同意，免附說明表"
    forms = [f for f in ctx.forms if f in ("AF126", "AF127", "AF128", "AF129", "AF130", "AF135")]
    return (OK, f"已附 {'、'.join(forms)}") if forms else (TODO, "G21-1 勾選族群後會附上對應的納入易受傷害族群說明表")


def _consent(ctx):
    subj = ctx.config["subjects"]
    if subj.get("consent_waiver"):
        reason = ctx.online.get("H3-1")
        basis = ctx.online.get("H3-2")
        if not reason or not basis:
            return TODO, "免除知情同意須寫理由（H3-1）並勾選法定情形（H3-2）"
        if ctx.retro and "MEDREC" not in ctx.forms:
            return TODO, "回溯性病歷研究免除同意須附使用病歷資料進行研究申請表"
        return OK, "H3-1 理由與 H3-2 法定情形已填；病歷申請表已附" if ctx.retro else "H3-1、H3-2 已填"
    consent = [f for f in ctx.forms if f.startswith(("CONSENT", "INTERVIEW"))]
    return (OK, f"已附 {'、'.join(consent)}") if consent else (TODO, "需附受試者同意書或說明書")


def _privacy_people(ctx):
    if ctx.att.get("接觸人員") or ctx.find(r"接觸.{0,6}(?:資料|病歷).{0,6}人員|存取權限|授權.{0,4}人員"):
        return OK, "已列可接觸資料之人員"
    return TODO, "列出可能接觸個人資料（病歷、檢體）的人員"


def _privacy_measures(ctx):
    if ctx.online.get("G29-1") and ctx.online.get("G29-2"):
        return OK, "G29-1 機密性、G29-2 隱私已填"
    return TODO, "G29-1／G29-2 未填"


def _multinational(ctx):
    if not ctx.says("A4", "國際"):
        return NA, "非國際多中心"
    return (OK, "已附跨國研究計畫說明表") if "AF118" in ctx.forms else (TODO, "需附本院主持人主導之跨國研究計畫說明表")


def _recruit(ctx):
    if ctx.retro:
        return NA, "回溯性研究不招募受試者"
    return (OK, "G26 招募方式已填") if ctx.online.get("G26") else (TODO, "G26 招募方式未填")


def _criteria(key, what):
    def rule(ctx):
        p = ctx.config.get("proposal") or {}
        return (OK, "中文計畫摘要已列") if isinstance(p, dict) and p.get(key) else (TODO, f"中文計畫摘要缺{what}")
    return rule


ITEMS = [
    ("一、計畫設計與執行", [
        ("1. 於本院執行之適當性；已列研究人員，人力與時間足以保護受試者", _team),
        ("2. 計畫主持人資格及經驗", manual("e-REC 研究團隊 CV 與訓練時數；確認主持人資格符合本會受理資格")),
        ("3. 研究設計與目的之關聯、統計方法與樣本數之合理性", _sample_size),
        ("3.1 研究程序符合完善設計", evidence(r"研究設計|研究方法|study design", "研究設計")),
        ("3.2 研究設計足以產生預期知識", evidence(r"預期(?:成果|效益|結果)|主要(?:評估)?(?:指標|終點)|primary (?:outcome|endpoint)", "預期成果／主要評估指標")),
        ("4. 預期風險與效益之合理性，風險已極小化", evidence(r"風險|risk", "風險與效益")),
        ("5. 選擇對照組之合理性", lambda c: (NA, "G28-2 無對照組") if c.says("G28-2", "否") else evidence(r"對照組|control", "對照組")(c)),
        ("6. 受試者提前退出研究之條件", only(lambda c: c.prospective, evidence(r"退出|withdraw", "退出條件"), "回溯性研究無受試者退出")),
        ("7. 暫停或中止全部研究之條件", only(lambda c: c.interventional, evidence(r"(?:暫停|中止|終止).{0,6}(?:研究|試驗)|stopping rule", "暫停或中止條件"), "非介入性研究")),
        ("8. 監測與稽核之規定", only(lambda c: c.interventional, evidence(r"監測|稽核|monitor", "監測與稽核"), "非介入性研究")),
        ("9. 資料及安全監測計畫(DSMP)", _dsmp),
        ("10. 研究結果之報告或發表方式", evidence(r"發表|期刊|研討會|publish", "成果發表方式")),
        ("11. 儘量使用受試者原本將接受之常規程序", only(lambda c: c.prospective, evidence(r"常規|routine", "常規程序"), "回溯性研究使用既有資料")),
    ]),
    ("三、本院主持人主導之跨國研究", [("跨國研究之合理性、監測、同意程序", _multinational)]),
    ("四、本院主持人主導之多機構臨床試驗", [
        ("1. 計畫書記載各主持人責任分配及協調方式",
         only(lambda c: c.s.get("multicenter") and c.interventional, evidence(r"責任分(?:配|工)|協調", "各中心責任分配與協調"), "非本院主導之多機構臨床試驗")),
    ]),
    ("五、受試者之照護", [
        ("研究期間及研究後之醫療照護、自願退出之步驟", only(lambda c: c.prospective, evidence(r"醫療照護|照護|退出", "受試者照護"), "回溯性研究不接觸受試者")),
        ("受試者之補助、補償；受傷之補償、保險", only(lambda c: c.interventional, evidence(r"補償|保險|compensation|insurance", "補償與保險"), "非介入性研究")),
    ]),
    ("六、隱私及資料機密性", [
        ("1. 記載可能接觸受試者個人資料之人", _privacy_people),
        ("2. 確保隱私與個人資訊安全之措施", _privacy_measures),
    ]),
    ("八、易受傷害族群", [("納入之必要性、額外保護措施及對應說明表", _vulnerable)]),
    ("九、潛在受試者之招募", [
        ("2–3. 最初接觸、招募與傳達資訊之方式", _recruit),
        ("4. 受試者納入條件", _criteria("inclusion", "納入條件")),
        ("5. 受試者排除條件", _criteria("exclusion", "排除條件")),
    ]),
    ("十、受試者同意", [("同意程序與文件，或免除同意之理由與法定情形", _consent)]),
]


def run(config):
    from rec_helper.form_selector import select_forms
    ctx = Ctx(config, study_text.online_answers(config), study_text.attachment_answers(config),
              study_text.corpus(config), [fid for fid, _ in select_forms(config | {"phase": "new"})])
    return [(section, [(text, *rule(ctx)) for text, rule in items]) for section, items in ITEMS]


def report(config, results):
    counts = {k: sum(st == k for _, rows in results for _, st, _ in rows) for k in LABEL}
    lines = ["# 送件前模擬預審（依 AF-063 臨床研究案件審查重點）", "",
             f"> 計畫：{config['study']['title_zh']}",
             "> " + "　".join(f"{k} {LABEL[k]} {counts[k]}" for k in LABEL),
             "> 這是依文字自動比對的預審，不代表委員會判斷；請以 □ 待補、？ 人工確認為優先。", ""]
    for section, rows in results:
        lines += [f"## {section}", ""]
        lines += [f"- {st} {text}　—　{note}" for text, st, note in rows]
        lines.append("")
    return "\n".join(lines)


def main(config_path="config.toml", output_dir="output"):
    from rec_helper.config import ConfigError, load_config
    from rec_helper.institution import activate
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    activate(config)
    results = run(config)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "precheck_report.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report(config, results))
    todo = [(t, n) for _, rows in results for t, st, n in rows if st == TODO]
    print(f"Pre-review (AF-063): {len(todo)} 待補 → {path}")
    for text, note in todo:
        print(f"  □ {text}：{note}")
    return 0
