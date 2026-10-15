"""NTUH REC — DOCX attachments (draft).

The NTUH application is filled in the REC web system; see online.py for those
pages. Attachments with official blanks are filled by attachments.py (自評表,
使用病歷資料進行研究申請表, 保密聲明切結書); 計畫中文摘要 has no blank and
uses the shared generators.proposal. 免審 (review_type exempt) only uploads the
protocol with its Chinese summary, so it gets PROPOSAL alone. The other blanks
(同意書, DSMP, 易受傷害族群說明表, 網路研究自評表, 藥品, FDA, NGS) are filled row by
row by rec_helper.form_rows, routed by the web-form answers in 線上填寫.md.
Not mapped: 兒童版受試者同意書 (its .doc converts to unreadable text).

FORM_REGISTRY: form_id → (Chinese name, generator module path, function name)
PHASE_FORMS:   phase → {"base": [...], "conditions": [(predicate(config), [...])]}.
"""

from rec_helper.institutions.ntuh.online import _says, route

ATT = "rec_helper.institutions.ntuh.attachments"

FORM_REGISTRY = {
    "AF001": ("臨床研究計畫申請人自評表", ATT, "generate_af001"),
    "MEDREC": ("使用病歷資料進行研究申請表", ATT, "generate_medrec"),
    "AF164": ("保密聲明切結書（計畫主持人）", ATT, "generate_af164"),
    # No official blank: the shared rebuild generator, fed by 中文計畫摘要.md
    "PROPOSAL": ("計畫中文摘要", "generators.proposal", "generate_proposal_summary"),
    # The study's own Markdown, rendered (rech protocol / rech reply)
    "PROTOCOL": ("研究計畫書", "rec_helper.generators.protocol", "generate_protocol"),
    "ABSTRACT_EN": ("計畫英文摘要", "rec_helper.generators.protocol", "generate_english_abstract"),
    "REPLY": ("審查意見回覆表", "rec_helper.reply", "generate_reply"),
    # Question-per-row blanks filled by rec_helper.form_rows (answers: `## <id>-<n>`)
    "CONSENT": ("臨床試驗研究受試者說明及同意書", ATT, "generate_consent"),
    "INTERVIEW": ("研究受訪者說明及同意書", ATT, "generate_interview"),
    "DSMP": ("資料及安全性監測計畫", ATT, "generate_dsmp"),
    "AF118": ("本院計畫主持人主導之跨國研究計畫說明表", ATT, "generate_af118"),
    "AF126": ("納入易受傷害族群說明表（未成年人）", ATT, "generate_af126"),
    "AF127": ("納入易受傷害族群說明表（孕婦或胎兒）", ATT, "generate_af127"),
    "AF128": ("納入易受傷害族群說明表（生存力不明新生兒）", ATT, "generate_af128"),
    "AF129": ("納入易受傷害族群說明表（無法存活新生兒）", ATT, "generate_af129"),
    "AF130": ("納入易受傷害族群說明表（受拘禁人）", ATT, "generate_af130"),
    "AF135": ("納入易受傷害族群說明表（無法行使同意之成人）", ATT, "generate_af135"),
    "AF143": ("網路研究自評表", ATT, "generate_af143"),
    "FDA": ("受美國FDA管轄案件確認事項表", ATT, "generate_fda"),
    "DRUGINFO": ("藥品資料表", ATT, "generate_druginfo"),
    "DRUGSELF": ("臨床試驗用藥自行管理自評表", ATT, "generate_drugself"),
    "NGSFORM": ("次世代基因定序(NGS)研究發現之告知方式說明表", ATT, "generate_ngsform"),
    "NGSCONSENT": ("NGS研究結果之告知說明暨同意書", ATT, "generate_ngsconsent"),
}
# every other row-filled blank (attachments.ROW_FORMS): registered under its own name
from rec_helper.institutions.ntuh.attachments import ROW_FORMS as _ROW_FORMS  # noqa: E402

for _fid, (_name, _) in _ROW_FORMS.items():
    FORM_REGISTRY.setdefault(_fid, (_name, ATT, f"generate_{_fid.lower()}"))


def _reviewed(c):
    """一般審查 / 簡易審查. 免審 uploads only the protocol (with its Chinese summary)."""
    return c["study"]["review_type"] != "exempt"


def _chart_review_waiver(c):
    """申請病歷資料並申請免告知同意 → 使用病歷資料進行研究申請表 + 保密聲明切結書."""
    return (_reviewed(c) and c["study"]["type"] == "retrospective"
            and c["subjects"]["consent_waiver"])


def _trial(c):
    return c["study"]["type"] == "clinical_trial" or c["study"].get("design") in ("rct", "single_arm")


def _consent(c):
    """Signed consent (H1) or an information sheet (H2)."""
    return route(1)(c) or route(2)(c)


def _vulnerable(group):
    """易受傷害族群說明表 for a G21-1 category; not needed for retrospective waivers."""
    return lambda c: (c["subjects"]["vulnerable_population"] and not _waived_chart_review(c)
                      and _says("G21-1", group)(c))


def _waived_chart_review(c):
    return c["study"]["type"] == "retrospective" and c["subjects"]["consent_waiver"]


def _any(*preds):
    return lambda c: any(p(c) for p in preds)


def site(c):
    """Branch with its own consent templates: `site = "HCH"` in config.toml, else the PI's department."""
    if c.get("site"):
        return str(c["site"]).upper()
    dept = str(c.get("pi", {}).get("dept", ""))
    return "HCH" if "新竹" in dept else "BMH" if "生醫" in dept else ""


def _variant(form_id):
    """CONSENT → CONSENT_HCH for 新竹臺大分院 (and _BMH for 生醫醫院)."""
    def pick(c):
        return f"{form_id}_{site(c)}" if site(c) else form_id
    return pick


def _route_variant(pred, form_id):
    """(predicate, [form]) pairs for each branch variant of a form."""
    return [(lambda c, v=v: pred(c) and _variant(form_id)(c) == v, [v])
            for v in (form_id, f"{form_id}_HCH", f"{form_id}_BMH")]


def _food(c):
    return _says("B2", "食品")(c)


PHASE_FORMS = {
    "new": {
        "base": ["PROPOSAL"],
        "conditions": [
            (_reviewed, ["AF001"]),
            (_chart_review_waiver, ["MEDREC", "AF164"]),
            *_route_variant(lambda c: _consent(c) and _trial(c), "CONSENT"),
            (lambda c: _consent(c) and not _trial(c), ["INTERVIEW"]),
            (_any(_says("E4", "是"), lambda c: _trial(c) and c["study"]["drug_device"]), ["DSMP"]),
            (_says("A4", "國際多中心"), ["AF118"]),
            (_vulnerable("兒童"), ["AF126"]), (_vulnerable("孕婦"), ["AF127"]),
            (_vulnerable("生存力不明"), ["AF128"]), (_vulnerable("無法存活"), ["AF129"]),
            (_vulnerable("受拘禁人"), ["AF130"]), (_vulnerable("無意識能力"), ["AF135"]),
            (_any(_says("G33", "是"), _says("免審10", "是")), ["AF143"]),
            (_any(_says("A3-1", "美國食品藥物管理局"), _says("免審3-1", "美國食品藥物管理局")), ["FDA"]),
            (_says("B2", "藥品"), ["DRUGINFO"]),
            (_says("C6", "否"), ["DRUGSELF"]),
            (lambda c: c["study"]["genetic"], ["NGSFORM"]),
            *_route_variant(lambda c: c["study"]["genetic"] and _consent(c), "NGSCONSENT"),
            (_says("F5", "現存之既有檢體"), ["LEFTOVER"]),
            (_says("G31", "是"), ["AF046"]),
            (_food, ["AF165"]),
            (_says("免審3", "是"), ["AF146"]),
        ],
    },
    # ── after approval ──
    "amendment": {"base": ["AMENDTABLE"], "conditions": [
        (_says("變更二", "1."), ["PROPOSAL"]),
    ]},
    "continuing": {"base": [], "conditions": [
        (_says("持續7-1", "是"), ["SAELIST_CR"]),
        (lambda c: c["study"]["multicenter"] and _trial(c), ["AF157"]),
        (_says("B2", "醫療器材", "新醫療器材"), ["DEVICE_INTERIM"]),
        (_says("B2", "醫療技術", "新醫療器材併用"), ["TECH_REPORT"]),
    ]},
    "closure": {"base": [], "conditions": [
        (_any(_says("結案5-1", "是"), lambda c: bool(c["closure"].get("sae_count"))), ["SAELIST_CL"]),
        (_says("B2", "醫療技術", "新醫療器材併用"), ["TECH_RESULT"]),
    ]},
    "suspension": {"base": [], "conditions": [
        (_any(_says("結案5-1", "是"), lambda c: bool(c["closure"].get("sae_count"))), ["SAELIST_CL"]),
    ]},
    "sae": {"base": [], "conditions": [(_says("SAE14", "死亡"), ["DEATHFOLLOW"])]},
    "deviation": {"base": [], "conditions": [(_says("偏差5-2", "是"), ["AF161"])]},
    "other": {"base": [], "conditions": [(_says("其他1", "試驗開始執行前必備文件"), ["PRESTART"])]},
    # 專案進口／恩慈療法 (paper forms; no web application)
    "import": {"base": ["COMPASS_APP", "COMPASS_SELF", "COMPASS_PLAN", "COMPASS_CONSENT"], "conditions": []},
}


def _has(key):
    return lambda c: isinstance(c.get(key), str) and bool(c.get(key))


# The protocol and English abstract go with the new case and with amendments that change
# documents; a review reply goes with whatever submission answers the comments.
for _phase, _rules in PHASE_FORMS.items():
    if _phase in ("new", "amendment"):
        _rules["conditions"] += [(_has("protocol"), ["PROTOCOL"]), (_has("english_abstract"), ["ABSTRACT_EN"])]
    _rules["conditions"].append((_has("reply"), ["REPLY"]))
