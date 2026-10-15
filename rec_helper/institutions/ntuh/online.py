"""NTUH REC web system (臺大醫院倫委會申請暨審查管理系統) — pages filled online.

Field ids and option texts follow the web pages as of 2026-10 (新案申請書
v10). Values are derived from config.toml where the study facts allow it;
everything else is answered in 線上填寫.md (`## <id>` sections, see
rec_helper/online_forms.py).

Only questions the system shows for the study type are listed (it hides much
of tab G for chart reviews). Follow-up questions the page reveals after an
earlier answer (C3 → C3-1, H route → its block) are keyed on that answer via
`_says`, so they appear once it is given in 線上填寫.md.

Review types (審查方式, chosen when the case is created):
  一般審查 / 簡易審查 → 新案申請書 v10 (formTypeId=1; 簡審 adds 簡審範圍評核表)
  免審               → 新案免審申請書 v3 (formTypeId=3), a much shorter page
Both add 上傳/檢視案件相關文件 (upload checklist), 計畫主持人聲明書, 審查費.
"""
import re

from rec_helper.online_forms import A, C, Form, M, T, overrides

YES_NO = ("是", "否")
SITES = ("臺大醫院總院", "雲林分院", "金山分院", "北護分院", "新竹臺大分院", "癌醫中心分院", "其他")


# ── answers given in 線上填寫.md ────────────────────────────────────────────

def _says(key, *prefixes, default=None):
    """Predicate: the answer to `key` (線上填寫.md, else `default(config)`) picks an option
    starting with one of `prefixes` — mirrors the page revealing follow-up questions."""
    def pred(c):
        v = overrides(c).get(key)
        if v in (None, "", []):
            v = default(c) if callable(default) else default
        items = v if isinstance(v, list) else [v] if v else []
        return any(str(i).strip().startswith(p) for i in items for p in prefixes)
    return pred


def _all(*preds):
    return lambda c: all(p(c) for p in preds)


# ── study facts → answers ──────────────────────────────────────────────────

def _s(c):
    return c["study"]


def retro(c):
    return _s(c)["type"] == "retrospective"


def prospective(c):
    return _s(c)["type"] in ("prospective", "clinical_trial")


def interventional(c):
    return _s(c)["type"] == "clinical_trial" or _s(c).get("design") in ("rct", "single_arm")


def waiver(c):
    return c["subjects"]["consent_waiver"]


def expedited(c):
    return _s(c)["review_type"] == "expedited"


def exempt(c):
    return _s(c)["review_type"] == "exempt"


def reviewed(c):
    """一般審查 or 簡易審查: the full 新案申請書."""
    return not exempt(c)


def _yn(flag):
    return "是" if flag else "否"


def _date(text):
    """'2026年04月01日' / '2026-04-01' → '2026/04/01'."""
    m = re.match(r"\s*(\d{4})\D+(\d{1,2})\D+(\d{1,2})", str(text or ""))
    return f"{m[1]}/{int(m[2]):02d}/{int(m[3]):02d}" if m else ""


def _prop(key):
    return lambda c: (c.get("proposal") or {}).get(key) if isinstance(c.get("proposal"), dict) else None


def _precis(c):
    p = c.get("proposal") if isinstance(c.get("proposal"), dict) else {}
    parts = [p.get(k) for k in ("background", "design") if p.get(k)]
    return "\n".join(x if isinstance(x, str) else "\n".join(x) for x in parts) or None


def _project_no(c):
    no = _s(c).get("project_no", "")
    return "" if no in ("", "不適用", "N/A") else no


def _confidentiality(c):
    ds = c["closure"]["data_safety"]
    if not ds:
        return None
    out = []
    if ds.get("deidentified"):
        out.append("研究資料於收集時即以研究編號取代姓名、病歷號等可直接識別個人之資訊（去識別化），對照表另行保存。")
    if ds.get("encrypted"):
        out.append("電子資料檔案加密，存放於設有帳號密碼管制之院內電腦，不存放於個人可攜式裝置或雲端。")
    if ds.get("authorized_personnel"):
        out.append(f"僅授權研究人員（{ds['authorized_personnel']}）可存取研究資料。")
    if ds.get("retention_years"):
        out.append(f"研究資料於計畫結束後保存{ds['retention_years']}年，期滿依規定銷毀。")
    return "\n".join(f"{i}. {t}" for i, t in enumerate(out, 1)) or None


def _privacy(c):
    if not c["closure"]["data_safety"]:
        return None
    text = "研究結果僅以群體統計方式呈現，發表時不揭露任何可識別個人之資訊。"
    if retro(c):
        text = "本研究僅回溯分析既有病歷資料，不直接接觸研究對象；" + text
    return text


def _sites(c):
    return "本國多中心" if _s(c)["multicenter"] else "單一中心"


def _study_type(c):
    if interventional(c):
        return "介入性研究"
    if retro(c) or _s(c)["type"] == "genetic":
        return "觀察性研究"
    return None  # prospective: interventional or observational is the PI's call


def specimens(c):
    return retro(c) and bool(c["closure"].get("specimens"))


def same_retro_subjects(c):
    """B4: retrospective data and specimens come from the same subjects."""
    return specimens(c) and _says("B4", "是")(c)


def _n(c):
    return c["subjects"]["planned_n"]


def _n_site(c):
    return _n(c) if not _s(c)["multicenter"] else None


# ── 新案申請書 ──────────────────────────────────────────────────────────────

BASIC = [
    A("計畫中文名稱", "計畫中文名稱", "{study.title_zh}"),
    A("計畫英文名稱", "計畫英文名稱", "{study.title_en}"),
    T("計畫編號", "計畫編號", _project_no, optional=True, note="院內/補助計畫編號；沒有就留空"),
    T("預期開始日期", "預期試驗/研究開始日期", lambda c: _date(c["dates"]["study_start"])),
    T("預期結束日期", "預期試驗/研究結束日期", lambda c: _date(c["dates"]["study_end"])),
    C("簡易審查", "是否符合簡易審查條件？", YES_NO, lambda c: _yn(expedited(c))),
    C("審查機制", "審查機制", ("非NRPB-IRB或非C-IRB", "臨床試驗聯盟聯合倫理審查機制(NRPB-IRB)",
                           "藥品臨床試驗聯合倫理審查機制(C-IRB)"), "非NRPB-IRB或非C-IRB"),
    C("申請醫院", "本次申請醫院為", ("主審醫院", "副審醫院"), "主審醫院"),
    A("研究目的", "試驗/研究計畫目的", _prop("objectives")),
    A("簡要說明", "試驗/研究計畫簡要說明", _precis, note="預設＝摘要的研究背景＋研究設計"),
    T("研究領域", "研究領域", note="系統下拉選單（輸入關鍵字挑選）"),
    T("關鍵字", "關鍵字"),
]

SECTION_A = [
    C("A1", "研究計畫責任歸屬", ("本院/計畫主持人", "試驗委託者", "受託研究機構(CRO)"), "本院/計畫主持人"),
    T("A1-1", "試驗委託者公司/機構", when=_says("A1", "試驗委託者")),
    T("A1-2", "受託研究機構公司/機構", when=_says("A1", "受託研究機構")),
    T("A1-3", "委託公司/機構", when=_says("A1", "受託研究機構")),
    C("A2", "是否有受託研究機構(CRO)？", YES_NO, "否"),
    T("A2-1", "CRO公司名稱", when=_says("A2", "是")),
    T("A2-2", "請說明", optional=True, when=_says("A2", "是")),
    C("A3", "本計畫執行前依法是否須經主管機關核准？", YES_NO, lambda c: _yn(_s(c)["drug_device"])),
    M("A3-1", "請問主管機關為何？", ("衛生福利部(係指依醫療法執行前須經衛生福利部審查方可執行)", "歐盟檢驗藥品局(EMA)",
                             "美國食品藥物管理局(FDA)", "美國衛生福利部(DHHS)", "其他"),
      when=lambda c: _s(c)["drug_device"]),
    C("A4", "單中心或多中心", ("單一中心", "本國多中心", "國際多中心"), _sites,
      note="各台大分院之間也算多中心"),
    A("A4-1", "試驗中心資料（國家／城市／試驗中心／計畫主持人，每中心一行，系統內按「新增」逐筆輸入）",
      when=lambda c: _s(c)["multicenter"]),
    M("A5", "主持人是否擔任領導臨床試驗/研究職務", ("擔任國際總主持人(請附證明文件)", "擔任本國總主持人",
                                      "擔任Steering Committee Member (請附證明文件)",
                                      "擔任Publication Committee Member (請附證明文件)", "其他", "否"),
      ["否"], when=lambda c: _s(c)["multicenter"]),
    C("A6", "本計畫是否登錄網站？", YES_NO, lambda c: None if _s(c)["type"] == "clinical_trial" else "否"),
    M("A6-1", "請問登錄網站的名稱？", ("ClinicalTrials.gov", "EU register", "其他"),
      when=lambda c: _s(c)["type"] == "clinical_trial"),
    T("A6-2", "其Identifier", when=lambda c: _s(c)["type"] == "clinical_trial"),
    M("A7", "經費贊助來源（可複選）", ("廠商", "學術研究單位", "自籌(自行研究無經費補助)", "其他")),
    T("A7-說明", "自籌／其他之說明或單位", optional=True, note="勾「自籌」或「其他」時填"),
    C("A7-1", "廠商為全部贊助或部分贊助？", ("全部贊助", "部分贊助"), when=_says("A7", "廠商")),
    T("A7-1-1", "廠商名稱", when=_says("A7", "廠商")),
    M("A7-2", "請問學術研究單位為何？（勾「學術研究單位」時）",
      ("本院院內計畫", "國科會", "衛生福利部", "國家衛生研究院", "中央研究院", "榮台聯大", "大學或科部",
       "國防研究", "基金會", "學會", "美國聯邦政府", "其他"), optional=True),
]

SECTION_B = [
    C("B1", "研究類型", ("介入性研究", "觀察性研究", "研究同時包含介入性、觀察性研究"), _study_type),
    C("B1-1", "是否為醫療器材之觀察性研究？", YES_NO, lambda c: _yn(_s(c)["drug_device"]),
      when=lambda c: not interventional(c)),
    C("B2", "此介入性研究之計畫類別", ("藥品", "醫療器材", "醫療技術", "新醫療器材併用新醫療技術",
                              "食品/健康食品/飲食補充品", "行為科學", "其他"), when=interventional),
    C("B2-1", "是否屬再生醫療製劑？", YES_NO, "否", when=interventional),
    C("B2-1-1", "請勾選類別（勾「是」者另至 REDCap 填表）", ("基因治療製劑", "細胞治療製劑", "組織工程製劑", "複合製劑"),
      when=_all(interventional, _says("B2-1", "是")), note="頁面上每個選項後附定義"),
    C("B2-2", "本研究是否為附加或延伸試驗/研究？", ("附加試驗/研究", "延伸試驗/研究", "否"), "否", when=interventional),
    T("B2-2-1", "原計畫之本會案件編號", when=_all(interventional, _says("B2-2", "附加", "延伸"))),
    T("B2-2-2", "原計畫之計畫編號", when=_all(interventional, _says("B2-2", "附加", "延伸"))),
    C("B2-3", "是否為新醫療技術？", YES_NO, "否", when=interventional),
    C("B2-4", "是否屬細胞治療？", YES_NO, "否", when=interventional),
    M("B3", "資料收集期", ("前瞻性", "回溯性"),
      lambda c: ["回溯性"] if retro(c) else ["前瞻性"] if prospective(c) else None),
    M("B3-1", "收集檢體或資料", ("回溯性檢體", "回溯性資料"),
      lambda c: ["回溯性資料"] + (["回溯性檢體"] if c["closure"].get("specimens") else []), when=retro),
    C("B4", "回溯性資料與回溯性檢體是否為同一受試者/研究對象？", YES_NO,
      when=lambda c: retro(c) and c["closure"].get("specimens")),
]

def _n_other(c):
    return 0 if not _s(c)["multicenter"] else None


def _n_counts(prefix, what, when):
    """G4/G5/G6 預計收案數: this site, other NTUH-system sites, clinics, other domestic sites."""
    return [
        T(f"{prefix}-1", f"預計收案數({what})－本試驗/研究中心（人/筆）", _n_site, when=when),
        T(f"{prefix}-2", f"預計收案數({what})－本院醫療體系內其他中心（人/筆）", _n_other, when=when,
          note="新竹、雲林等台大分院算「本院醫療體系內其他中心」"),
        T(f"{prefix}-3", f"預計收案數({what})－本國未設置IRB之中心（人/筆）", "0", when=when),
        T(f"{prefix}-4", f"預計收案數({what})－本國其他試驗/研究中心（人/筆）", _n_other, when=when),
        T(f"{prefix}-5", f"預計收案數({what})－全球總計（人/筆）", optional=True, when=when,
          note="國際多中心才需要；系統可能自動加總"),
    ]


# ── C. 藥品 / D. 醫療器材 / E. 介入性研究-研究設計 / I. 產品研究資料表 ───────────
# Shown for interventional studies by the B2 category (seen blank 2026-10-15).

def _b2(*cats):
    return _all(interventional, _says("B2", *cats))


drug = _b2("藥品")
device = _b2("醫療器材", "新醫療器材")
food = _b2("食品")

SECTION_C = [
    A("C1", "試驗藥品資料（含併用藥物）：每藥一行「實驗或對照組別／主要或併用／學名／商品名／劑型／含量」",
      when=drug, note="系統內按「新增」逐筆輸入"),
    C("C2", "藥品臨床試驗類別", ("申請查驗登記", "學術研究"), when=drug),
    C("C3", "藥品是否均有衛生福利部許可證？", YES_NO, when=drug),
    C("C3-1", "本研究「使用途徑」、「使用劑量」或「使用劑型」是否為原藥品許可證核准之範圍？", YES_NO,
      when=_all(drug, _says("C3", "是"))),
    M("C3-2", "請說明超過許可證範圍之類別", ("使用途徑", "使用劑量", "使用劑型"),
      when=_all(drug, _says("C3-1", "否"))),
    C("C3-3", "本研究藥品使用之範圍是否為原藥品許可證核准之適應症範圍？", ("是", "否，請說明本研究使用之範圍為："),
      when=_all(drug, _says("C3", "是"))),
    T("C3-3-說明", "本研究使用之範圍（C3-3 勾「否」時）", optional=True, when=_all(drug, _says("C3", "是"))),
    C("C4", "本案是否為藥物生體可用率（BA）/生體相等性(BE)臨床試驗？", YES_NO, "否", when=drug),
    C("C5", "藥品試驗階段（下拉選單）",
      ("N/A：無試驗階段", "Phase 0 ：第一期之前小規模、小劑量之藥效、藥動試驗", "Phase I ：了解藥物毒性為目的之安全性試驗",
       "Phase I/II ：包含Phase 1及Phase 2目的試驗", "Phase II ：了解療效、副作用及安全性之初步試驗",
       "Phase II/III ：包含Phase 2及Phase3目的試驗", "Phase III： 完整療效評估試驗",
       "Phase IV： 上市後長期治療的安全性和有效性試驗"), when=drug),
    C("C6", "藥品是否由本院藥劑部門管理", ("是", "否，請上傳自行管理簽文及臨床試驗用藥自行管理自評表"), "是", when=drug),
    C("C6-1", "藥品是否為本院進用藥物？", YES_NO, when=drug),
    M("C7", "藥品提供者（可複選）", ("廠商", "自籌經費購買", "學術單位經費購買", "本院進用藥物", "其他，請說明："), when=drug),
    T("C7-1", "廠商名稱", when=_all(drug, _says("C7", "廠商"))),
]

SECTION_D = [
    C("D1", "醫療器材臨床試驗類別", ("申請查驗登記", "學術研究"), when=device),
    C("D2", "醫療器材風險評估", ("有顯著危險(Significant Risk，SR)", "無顯著危險(Non-Significant Risk，NSR)"), when=device,
      note="SR：植入物、維持生命，或用於診斷治療且可能嚴重傷害受試者健康安全者"),
    C("D3", "是否屬醫療器材管理法第三十七條第一項但書公告之「無顯著風險之醫療器材臨床試驗態樣」？",
      ("是（免予申請中央主管機關之核准）", "否"), when=device),
    M("D3-1", "請勾選符合之無顯著風險醫療器材臨床試驗態樣",
      ("(1)試驗用醫療器材已依醫療器材管理法規定取得許可證或登錄，且其臨床試驗之預期用途、使用方式及技術特點均未超出核准範圍；"
       "其登錄者，未超出鑑別範圍。",
       "(2)試驗用醫療器材，逕以合法取得之受試者檢體或資料作為診斷試驗之客體，且其試驗階段所得之結果不作為臨床診斷依據。",
       "(3)未具游離輻射之試驗用醫療器材，其使用係置於受試者之體表或無須與受試者體表接觸，進行資料收集試驗，"
       "或就其所收集之資料為診斷試驗，且其試驗階段所得之結果不作為臨床診斷依據。"),
      when=_all(device, _says("D3", "是"))),
    C("D4", "醫療器材是否有衛生福利部許可證？", ("無衛生福利部許可證", "有衛生福利部許可證"), when=device),
    C("D4-1", "國外是否已有許可證？", ("否", "是(請檢附國外仿單)"), when=_all(device, _says("D4", "無"))),
    C("D4-2", "使用範圍是否超過許可證之適應症", ("是，超過許可證之適應症，請說明使用範圍", "在許可證範圍內"),
      when=_all(device, _says("D4", "有"))),
    T("D4-2-說明", "超過許可證之使用範圍（D4-2 勾「是」時）", optional=True, when=_all(device, _says("D4", "有"))),
    M("D5", "醫療器材的種類", ("診斷", "治療", "減輕、直接預防人類疾病", "調節生育", "足以影響人類身體結構及機能"), when=device),
    M("D6", "醫療器材提供者（可複選）", ("廠商", "自籌經費購買", "學術單位經費購買", "本院進用醫療器材", "其他，請說明"),
      when=device),
    T("D6-1", "廠商名稱", when=_all(device, _says("D6", "廠商"))),
    C("D7", "是否屬電氣類之新醫療器材者？", ("是，請檢附電氣配置圖、醫療儀器電性安全測試報告以及裝置之使用手冊", "否"),
      when=device),
    C("D8", "是否屬可發生游離輻射設備或使用放射性物質者？", ("是，請檢附符合原子能法有關規定之證明文件影本", "否"),
      when=device),
]

SECTION_E = [
    C("E1-1", "研究設計－研究目的", ("治療", "預防", "診斷", "支持療法", "篩檢", "衛生政策", "基礎醫學", "其它"),
      when=interventional),
    C("E1-2", "隨機分配", ("單一組別", "隨機分配", "非隨機分配"),
      lambda c: {"rct": "隨機分配", "single_arm": "單一組別"}.get(_s(c).get("design")), when=interventional),
    C("E1-3", "盲性試驗", ("開放", "單盲", "雙盲", "三盲"), when=interventional),
    C("E1-4", "組數", ("單組", "雙組平行", "雙組交叉", "三組以上"),
      lambda c: "單組" if _s(c).get("design") == "single_arm" else None, when=interventional),
    C("E1-5", "有無使用歷史對照？", ("有", "無"), when=interventional),
    M("E1-6", "對照使用（可複選）", ("安慰劑", "主動(Active)", "劑量比較", "無"), when=interventional),
    C("E1-7", "主要評估終點 (Primary endpoint)", ("安全", "療效", "安全/療效", "生物等效性", "生物有效性", "藥物動力學",
                                             "藥效學", "藥物動力學/藥效學", "不適用"), when=interventional),
    C("E2", "是否有期中分析(Interim analysis)？", YES_NO, when=interventional),
    C("E3", "是否有主持人手冊(IB)、醫療器材手冊或類此說明試驗藥品或醫療器材臨床及非臨床數據之文件？", YES_NO,
      when=interventional),
    C("E4", "研究計畫是否有資料安全性監測計畫/資料安全監測委員會(DSMP/DSMB)", YES_NO, when=interventional),
    M("E4-1", "請問為DSMP、DSMB或兩者皆是？", ("資料安全性監測計畫(DSMP)", "資料安全監測委員會(DSMB)"),
      when=_all(interventional, _says("E4", "是"))),
]

SECTION_I = [
    T("I1", "產品名稱(中文)", when=food),
    T("I2", "產品名稱(英文)", when=food),
    C("I3", "產品申請類型", ("食品", "健康食品"), when=food),
    C("I3-1", "製造廠商資訊", ("國內", "國外"), when=food),
    T("I3-1-1", "製造廠名稱、地址", when=_all(food, _says("I3-1", "國內"))),
    T("I3-1-2", "原產地國名、製造廠名稱、地址", when=_all(food, _says("I3-1", "國外"))),
    A("I3-2", "該食品販賣者（由國外輸入國內販賣者須填寫）", when=_all(food, _says("I3-1", "國外"))),
    C("I3-3", "是否已有食品GMP？", ("是，食品GMP號碼：", "否"), when=food,
      note="否：國外輸入者請附食品藥物管理署許可資料"),
    C("I3-4", "是否已有健康食品標章？", YES_NO, when=food),
    T("I3-4-1", "認證字號（衛署健食規字號／衛署健食字號）", when=_all(food, _says("I3-4", "是"))),
    A("I4", "內容物名稱及其重量、容量或數量（兩種以上混合物應分別標明）", when=food),
    A("I5", "建議攝取量及注意事項（若有每日攝取安全容許量，亦須說明）", when=food),
    M("I6", "核准之功效（健康食品須填寫）",
      ("免疫調節作用", "調節血脂作用", "調整腸胃功能", "護肝（化學性）", "改善骨質疏鬆", "牙齒保健", "延緩衰老功能",
       "調節血糖", "抗疲勞功能", "輔助調節血壓功能", "促進鐵吸收功能", "輔助調節過敏體質", "不易形成體脂肪", "其他"),
      optional=True, when=food),
    M("I7", "產品提供者（可複選）", ("廠商", "自籌經費購買", "學術單位經費購買", "本院進用產品", "其他，請說明："), when=food),
    T("I7-1", "廠商名稱", when=_all(food, _says("I7", "廠商"))),
    A("I8", "儲存方式及條件", when=food),
]


# Data-only chart reviews: the web form hides G1, G3, G7, G10-G13, G16-G18, G20,
# G22-G23, G25-G27, G29-3 and G30 (seen 2026-10), so those are prospective-only here.
DESIGNS = {"cohort": "世代研究", "case_control": "病例對照研究", "cross_sectional": "橫斷研究"}

SECTION_F = [
    C("F1", "採用何種研究設計進行個案收集？", ("橫斷研究", "世代研究", "病例對照研究", "病例研究", "社會學或行為科學調查研究",
                                  "家族研究", "次級資料分析"), lambda c: DESIGNS.get(_s(c).get("design")),
      when=lambda c: not interventional(c)),
    M("F2", "若使用既有資料進行研究，資料來源為何？",
      ("政府機關提供之健康資料庫", "人體生物資料庫", "病歷資料庫", "其它"),
      lambda c: ["病歷資料庫"] if retro(c) else None, when=retro),
    T("F2-其它", "資料來源－其它，請說明", optional=True, when=retro),
    T("F2-1", "請列出人體生物資料庫", when=_all(retro, _says("F2", "人體生物資料庫"))),
    M("F2-2", "病歷資料之來源？（可複選）",
      ("臺大醫療體系醫療整合資料中心", "使用臺大醫院病歷資料", "回溯性使用已收集之資料", "院外病歷資料", "其他："),
      when=_all(retro, _says("F2", "病歷資料庫", default=lambda c: ["病歷資料庫"])),
      note="勾「臺大醫療體系醫療整合資料中心」要另上傳資料需求單"),
    M("F2-2-1", "請選擇臺大醫療體系整合資料中心資料院區", SITES[:-1],
      when=_all(retro, _says("F2-2", "臺大醫療體系"))),
    M("F2-2-2", "請選擇臺大醫院病歷資料院區", SITES[:-1],
      when=_all(retro, _says("F2-2", "使用臺大醫院病歷"))),
    T("F3", "回溯收集之資料期間（例如：xxxx年xx月至xxxx年xx月病歷資料）", "{dates.data_period}", when=retro),
    C("F4", "病歷資料是否有必要理由必須攜出院外，否則計畫無法執行？", ("是(含部分攜出)", "否，資料僅會在院內使用"),
      when=retro, note="勾「是」：審查通過後還要主持人簽核院方同意才能攜出，且攜出資料須無法辨識個人"),
    A("F4-1", "請說明其必要理由及方式", when=_all(retro, _says("F4", "是"))),
    M("F5", "若申請檢體進行研究，檢體來源為何？",
      ("政府機關提供之健康資料庫", "使用臺大醫院病理部既有檢體", "現存之既有檢體，REC案號：", "人體生物資料庫",
       "合法商業購買（包含：細胞株）", "其它"), when=lambda c: retro(c) and c["closure"].get("specimens")),
    T("F5-1", "請列出人體資料庫", when=_all(retro, _says("F5", "人體生物資料庫"))),
    M("F5-2", "請選擇院區（病理部既有檢體）", SITES[:-1], when=_all(retro, _says("F5", "使用臺大醫院病理部"))),
    T("F6", "回溯收集之檢體期間（例如：xxxx年xx月至xxxx年xx月的台大醫院總院病理部既有檢體）",
      when=lambda c: retro(c) and c["closure"].get("specimens")),
]

SECTION_G = [
    M("G1", "收案地點（可複選）", ("醫療院所", "社區", "學校", "以網路方式收案", "其他"), ["醫療院所"], when=prospective),
    M("G1-1", "醫療院所地點", SITES,
      when=prospective),
    A("G2", "計畫執行地點（科部、病房、門診或院外地點）"),
    # G3/G10/G11 (回溯性, data and specimens counted together) appear instead of G4/G5 +
    # G12-G15 when B4 says the data and specimens come from the same subjects (checked live 2026-10-15).
    *_n_counts("G3", "回溯性", same_retro_subjects),
    *_n_counts("G4", "回溯性檢體", lambda c: specimens(c) and not same_retro_subjects(c)),
    *_n_counts("G5", "回溯性資料", lambda c: retro(c) and not same_retro_subjects(c)),
    *_n_counts("G6", "前瞻性", prospective),
    C("G7", "本研究是否為競爭性收案", YES_NO, "否", when=prospective),
    T("G8-1", "受試者/研究對象最小年齡（歲）"),
    T("G8-2", "受試者/研究對象最大年齡（歲；無上限填999）", "999"),
    M("G9", "受試者/研究對象型態（可複選）", ("健康人", "罹患疾病之病患"), ["罹患疾病之病患"]),
    T("G9-疾病", "疾病名稱", optional=True, note="勾「罹患疾病之病患」時填"),
    A("G10", "受試者/研究對象納入條件(回溯性)", _prop("inclusion"), when=same_retro_subjects),
    A("G11", "受試者/研究對象排除條件(回溯性)", _prop("exclusion"), when=same_retro_subjects),
    A("G12", "受試者/研究對象納入條件(回溯性檢體)", when=lambda c: specimens(c) and not same_retro_subjects(c)),
    A("G13", "受試者/研究對象排除條件(回溯性檢體)", when=lambda c: specimens(c) and not same_retro_subjects(c)),
    A("G14", "受試者/研究對象納入條件(回溯性資料)", _prop("inclusion"),
      when=lambda c: retro(c) and not same_retro_subjects(c)),
    A("G15", "受試者/研究對象排除條件(回溯性資料)", _prop("exclusion"),
      when=lambda c: retro(c) and not same_retro_subjects(c)),
    A("G16", "受試者/研究對象納入條件(前瞻性)", _prop("inclusion"), when=prospective),
    A("G17", "受試者/研究對象排除條件(前瞻性)", _prop("exclusion"), when=prospective),
    T("G18", "受試者/研究對象預期試驗時間（例如：小時、天、週、年）", when=prospective),
    C("G19", "是否有依性別選擇受試者/研究對象？", YES_NO, "否"),
    C("G20", "此試驗是否有影響胎兒之可能？", YES_NO, when=prospective),
    C("G20-1", "此試驗是否執行懷孕檢測及避孕措施？", ("是", "否，請說明："), when=_all(prospective, _says("G20", "是"))),
    T("G20-1-說明", "未執行懷孕檢測及避孕措施之說明（G20-1 勾「否」時）", optional=True, when=_all(prospective, _says("G20", "是"))),
    C("G21", "受試者/研究對象是否主要包含易受傷害族群？", ("否", "是"),
      lambda c: _yn(c["subjects"]["vulnerable_population"])),
    M("G21-1", "請問易受傷害族群類別？", ("生存力不明的新生兒", "無法存活的新生兒", "兒童/未成年人", "孕婦", "軍人",
                                "原住民", "受拘禁人", "有從屬關係之學生/部屬", "無意識能力而無法行使同意之成年人",
                                "精神障礙者", "重症末期病患", "經濟弱勢或教育弱勢者", "其他"),
      when=lambda c: c["subjects"]["vulnerable_population"]),
    T("G21-1-1", "未成年人之收案年齡範圍（歲～歲）",
      when=lambda c: c["subjects"]["vulnerable_population"] and _says("G21-1", "兒童")(c)),
    T("G21-1-2", "其他易受傷害族群，請說明",
      when=lambda c: c["subjects"]["vulnerable_population"] and _says("G21-1", "其他")(c)),
    A("G21-2", "依人體研究法，說明為何無法以其他研究對象取代，或此研究明顯有利於研究對象",
      when=lambda c: c["subjects"]["vulnerable_population"]),
    A("G21-3", "請說明提供額外保護之措施", when=lambda c: c["subjects"]["vulnerable_population"]),
    C("G22", "本試驗/研究過程中受試者/研究對象是否將接受輻射暴露？", YES_NO, when=prospective),
    C("G22-1", "本計畫受試者是否因研究而接受或增加輻射暴露？", YES_NO, when=_all(prospective, _says("G22", "是"))),
    C("G22-1-1", "受試者從非常規性診斷或治療接受之有效輻射總劑量（ASRT 公式計算，結果另上傳）",
      ("a.計畫對所有受試者之暴露有效輻射劑量≦100 mrem(不涉及兒童、孕婦或健康受試者)",
       "b. 計畫對所有受試者之暴露有效輻射劑量>100 mrem，但≦ 3000 mrem (3 rem) …",
       "c.計畫涉及以下：未成年人、孕婦、健康受試者且暴露有效輻射劑量>100 mrem、計畫對所有受試者之暴露有效輻射劑量>3 …"),
      when=_all(prospective, _says("G22-1", "是")), note="b、c 選項頁面文字較長，請對照頁面"),
    A("G22-2", "輻射情況（X光或核子放射線），簡述使用輻射種類、方法和總次數", when=_all(prospective, _says("G22", "是"))),
    C("G23", "是否利用輻射化學物質在人體進行試驗？", ("否", "是，請說明何種物質："), "否", when=prospective),
    C("G24", "計畫是否涉及基因重組、特殊病毒療法或操作具有生物危險性之微生物？", YES_NO, "否"),
    C("G25", "本計畫是否抽血？", YES_NO, when=prospective),
    T("G25-1", "每次抽血量", when=_all(prospective, _says("G25", "是"))),
    T("G25-2", "抽血總次數", when=_all(prospective, _says("G25", "是"))),
    T("G25-3", "總共抽血量", when=_all(prospective, _says("G25", "是"))),
    C("G25-4", "執行抽血人員是否為受過抽血訓練、具有效執業執照之醫事專業人員？", YES_NO, when=_all(prospective, _says("G25", "是"))),
    T("G25-4-1", "執行者之證照類別", when=_all(prospective, _says("G25-4", "是"))),
    T("G25-4-2", "請說明理由", when=_all(prospective, _says("G25-4", "否"))),
    M("G26", "招募受試者/研究對象方式（可複選）", ("計畫主持人（含協同主持人）口頭介紹", "其他醫師、護理師（非共/協同主持人）口頭介紹",
                                    "海報廣告", "社群/網路廣告", "其他"), when=prospective),
    T("G26-1", "海報廣告張貼地點", when=_all(prospective, _says("G26", "海報"))),
    T("G26-2", "社群/網站名稱", when=_all(prospective, _says("G26", "社群"))),
    A("G26-3", "若非公開招募或非於醫療過程中邀請，說明如何接觸受試者", optional=True, when=prospective),
    C("G27", "是否提供受試者/研究對象金錢或禮物等補助？", YES_NO, when=prospective),
    T("G27-1", "何時提供？", when=_all(prospective, _says("G27", "是"))),
    T("G27-2", "提供內容及其等值金額？", when=_all(prospective, _says("G27", "是"))),
    C("G28-1", "受試者/研究對象之風險及權益－實驗組",
      ("參加本計畫將面臨的風險與未參加計畫時相當。", "參加本計畫將面臨的風險比未參加計畫時高，但明顯地可增進受試者的福祉。",
       "參加本計畫將面臨的風險比未參加計畫時高，雖然沒有明顯地增進受試者的福祉，但對於研究主題可得到有價值的結果。"),
      lambda c: "參加本計畫將面臨的風險與未參加計畫時相當。" if retro(c) else None),
    C("G28-2", "是否有對照組", YES_NO, lambda c: None if interventional(c) else "否"),
    C("G28-2-1", "受試者/研究對象之風險及權益－對照組",
      ("參加本計畫時，其權益與未參加計畫時相當。", "參加本計畫時，其權益比未參加計畫時受損，但不會明顯增加其風險。",
       "參加本計畫時，其權益比未參加計畫時明顯受損，但對於研究主題可得到有價值的結果。"), when=_says("G28-2", "是")),
    A("G29-1", "請說明如何維護資料機密性", _confidentiality),
    A("G29-2", "請說明如何保護受試者隱私", _privacy),
    C("G29-3", "本計畫是否符合美國DHHS的要求（取得美國「保密證書」）？", YES_NO, "否", when=prospective),
    M("G30", "受試者/研究對象決定是否參與時，如何減少其受到脅迫或干預？（可複選）",
      ("明確告訴受試者可拒絕參與研究，或可隨時撤回同意而不影響其權益或醫病關係。",
       "讓完全與受試者無倚賴或從屬關係之研究人員取得其知情同意。", "其他"), when=prospective),
    C("G31", "本案是否保留剩餘檢體？", ("不適用(本案不涉及檢體)", "否", "是"),
      lambda c: "否" if c["closure"].get("specimens") else "不適用(本案不涉及檢體)"),
    C("G32", "本案是否將未去連結之研究材料(含檢體)輸出國外？", ("是（勾選此項須上傳檢體擔保書）", "否"), "否"),
    C("G33", "本案是否屬本院規範之網路研究？", YES_NO, "否"),
]

H_ROUTES = ("H1. 以受試者同意書進行知情同意", "H2. 申請免除簽署書面知情同意書", "H3. 申請免除知情同意(不屬DHHS或FDA管轄之研究)",
            "H4. 屬FDA/DHHS管轄之計畫申請免除知情同意", "H5. 申請緊急醫療研究免除事前知情同意",
            "H6. 申請未成年人之研究申請免除其父母同意")

def route(n):
    """H: the consent route(s) picked — H3 for a waiver, else H1, unless 線上填寫.md says otherwise."""
    return _says("H", f"H{n}", default=lambda c: ["H3"] if waiver(c) else ["H1"])


EMERGENCY = ("受試者處於危急生命狀況", "參與研究對於受試者可能有益處", "現階段既有之治療方法其效果尚未確立或未達滿意",
             "受試者的健康狀況太差致使無法行使同意，或是與研究相關之介入性處置必須趕在取得受試者之法定代理人及有同意權人同意之前就要進行",
             "支持此研究性治療之動物及臨床前期研究已經執行", "已建置資料及安全監測委員會，以進行研究的監督事宜",
             "當受試者或其法定代理人、有同意權人可行使知情同意時，將儘快告知該研究內容並取得其同意是否繼續參加研究")

SECTION_H = [
    M("H", "知情同意程序（至少選一）", H_ROUTES,
      lambda c: ["H3. 申請免除知情同意"] if waiver(c) else ["H1. 以受試者同意書進行知情同意"]),
    # H1 — signed consent
    M("H1-1", "以書面同意書解釋試驗/研究內容之人員", ("計畫主持人(含協同主持人)", "研究人員："),
      ["計畫主持人(含協同主持人)"], when=route(1)),
    C("H1-2", "取得同意的時間？", ("篩選前", "篩選後，請說明篩選程序："), "篩選前", when=route(1)),
    T("H1-3", "在什麼地點解釋試驗/研究內容？", when=route(1)),
    T("H1-4", "每件約花費多久時間？", when=route(1)),
    M("H1-5", "除知情同意程序外，如何確保受試者了解試驗/研究內容？",
      ("主持人手冊", "與受試者/研究對象及其家人共同討論", "與受試者/研究對象及協助說明者共同討論", "另安排時間作追蹤", "其他"),
      when=route(1)),
    C("H1-6", "是否會收納非說本國語言之受試者/研究對象？", YES_NO, "否", when=route(1)),
    T("H1-6-1", "何種語言？", when=_all(route(1), _says("H1-6", "是"))),
    T("H1-6-2", "採取什麼方式以確保受試者/研究對象了解知情同意程序", when=_all(route(1), _says("H1-6", "是"))),
    # H2 — waiver of the signed form (an information sheet is still uploaded)
    A("H2-1", "申請免除簽署書面同意書之理由（若有不同同意方式，說明本方式之適用對象或計畫範圍）", when=route(2)),
    M("H2-2", "免除簽署書面知情同意書，以何種方式取代？", ("電話", "口頭", "網頁可供點選同意", "其它方式："), when=route(2)),
    C("H2-3", "研究對受試者之風險屬於最小風險（傷害或不適的可能性及嚴重度不大於日常生活、例行身體檢查或心理測驗所遭遇），"
      "相同程序若於非研究情況下進行亦不需書面同意", YES_NO, when=route(2), note="2-3 或 2-4 擇一勾選符合之項目"),
    C("H2-4", "連結受/收案對象與本研究的唯一紀錄是受試者同意書，而資料洩漏是造成傷害的主要風險，且該研究非FDA所管轄？",
      YES_NO, when=route(2)),
    C("H2-4-1", "同意參與研究之受試者/收案對象都將被詢問簽署同意書之意願，若是，則需讓其簽署", YES_NO,
      when=_all(route(2), _says("H2-4", "是"))),
    # H3 — waiver (not under DHHS/FDA)
    A("H3-1", "請說明申請免除知情同意之理由（及適用對象或計畫範圍）",
      lambda c: ("本研究為回溯性病歷資料分析，研究對象人數眾多且部分已失聯或死亡，逐一取得同意實務上不可行；"
                 "研究資料經去識別化處理，對研究對象之風險不超過最低風險，免除知情同意不影響其權益。")
      if retro(c) else None, when=route(3)),
    M("H3-2", "申請免除知情同意（符合下列情形之一）",
      ("3-2-1. 公務機關執行法定職務，自行或委託專業機構進行之公共政策成效評估研究",
       "3-2-2. 自合法之生物資料庫取得之去連結或無法辨識特定個人之資料、檔案、文件、資訊或檢體進行研究",
       "3-2-3. 研究屬最低風險，對研究對象之可能風險不超過未參與研究者，且免除事先取得其同意亦不影響其權益。",
       "3-2-4. 研究屬最低風險，對研究對象之可能風險不超過未參與研究者，不免除事先取得其同意則無法進行，且不影響其權益。"),
      lambda c: ["3-2-4"] if retro(c) else None, when=route(3),
      note="回溯性病歷研究常勾 3-2-4；請依實際情形確認"),
    # H4 — FDA/DHHS waiver: every item must hold
    M("H4-1", "屬FDA/DHHS管轄之計畫申請免除知情同意（必須符合所有項目）",
      ("研究對受試者之風險屬於為最小風險", "免除（或改變）知情同意對受試者的權利和福祉無不良影響",
       "若不免除（或改變）知情同意，研究便無法執行試驗/研究", "若適當，受試者在參與研究後，將會提供額外相關資訊"),
      lambda c: ["研究對受試者", "免除（或改變）知情同意對", "若不免除", "若適當"] if waiver(c) else None,
      when=route(4), note="4 項都要符合才能申請"),
    # H5 — emergency research: each item 是, or 否 with a reason
    *[C(f"H5-{i}", q, ("是", "否，請說明："), when=route(5)) for i, q in enumerate(EMERGENCY, 1)],
    # H6 — waiver of parental permission (not under FDA)
    M("H6-1", "未成年人之研究申請免除其父母同意",
      ("針對研究目的或所研究之族群，取得父母或監護人同意對於保障受試者並非合理的要求（如：受試者為受忽略或虐待的兒童）",
       "已備適當機制以保障參與研究之兒童"), when=route(6)),
]

NEW_CASE_APP = Form(
    "新案申請書",
    where="案件資訊頁面 → 申請案相關資料 → 新案申請書（分頁：基本資料、A～I）",
    when=reviewed,
    note="一般審查與簡易審查用同一份申請書。計畫主持人、團隊、聯絡人資料由系統帶入，不必填。"
         "只列出系統會顯示的題目；C、D、I 分頁依 B2 計畫類別出現，前面題目回答後才會出現的追問題，"
         "要在 線上填寫.md 先寫好前一題的答案才會列出。",
    sections=[("基本資料", BASIC), ("A. 研究基本資料", SECTION_A), ("B. 研究類型", SECTION_B),
              ("C. 藥品", SECTION_C), ("D. 醫療器材", SECTION_D), ("E. 介入性研究-研究設計", SECTION_E),
              ("F. 觀察性研究-研究設計", SECTION_F),
              ("G. 受試者資料", SECTION_G), ("H. 知情同意程序", SECTION_H), ("I. 產品研究資料表", SECTION_I)],
)


# ── 簡審範圍評核表 ──────────────────────────────────────────────────────────

SIMP_D = ("使用臨床常規治療或診斷之病歷，含個案報告之研究。前開資料不含人類後天性免疫不全病毒（HIV）陽性患者之病歷",
          "以研究為目的蒐集之錄音、錄影或影像資料。前開資料不含可辨識及可能影響研究對象工作、保險、財務及社會關係之資料。",
          "研究個人或群體特質或行為，但不含造成個人或族群歧視之潛在可能者。",
          "自合法生物資料庫取得之去連結或無法辨識特定個人之資料、檔案、文件、資訊或檢體進行研究。但不包括涉及族群或群體利益者。",
          "新案計畫業經本會審查通過，後續新增本會審查(或代審)之機構為試驗/研究中心之計畫")

def _no_if_retro(c):
    """A chart review touches no one: risk questions about the subjects' experience are 否."""
    return "否" if retro(c) else None


RISK_QS = [
    ("1", "研究對象是否為藥物濫用者?", _no_if_retro),
    ("2", "研究對象是否與研究者有從屬關係，例如：老師/學生或長官/下屬等?", _no_if_retro),
    ("3", "研究是否涉及精神評估或治療?", _no_if_retro),
    ("4", "研究是否涉及給予受試者身體上的刺激、誘發疼痛或侵入性處置?", _no_if_retro),
    ("5", "研究是否採用隨機分組設計?", lambda c: _yn(_s(c).get("design") == "rct")),
    ("6", "研究是否涉及生殖醫學，例如：不孕症、妊娠終止等?", _no_if_retro),
    ("7", "研究是否有可能危害研究者，例如：暴露於不安全的環境等?", _no_if_retro),
    ("8", "研究對象是否包括無法自主行使同意之成人？", _no_if_retro),
    ("9", "研究是否涉及進行全基因體檢測？", lambda c: _yn(_s(c)["genetic"])),
]


SIMP_REVIEW = Form(
    "簡審範圍評核表",
    where="案件資訊頁面 → 申請案相關資料 → 簡審範圍評核表",
    when=expedited,
    sections=[
        ("簡易審查條件（計畫所使用到之方式均須符合）", [
            M("簡審A", "A. 採集血液檢體", ("自體重50公斤以上之成年人，採集手指、腳跟、耳朵或靜脈血液…",), optional=True),
            M("簡審C", "C. 使用非侵入性方法收集資料",
              ("使用於研究對象體表或一段距離之感應器", "測量體重或感覺測試", "核磁共振造影",
               "心電圖、腦波圖、體溫、自然背景輻射偵測、視網膜電圖、超音波…", "適度運動、肌力測試、身體組織成分評估與柔軟度測試",
               "其他符合本條規定之非侵入性方法"), optional=True, note="B 類（非侵入性採集檢體）用到才勾，這裡略列"),
            M("簡審D", "D. 其他", SIMP_D, lambda c: [SIMP_D[0]] if retro(c) else None),
            A("簡審E", "E. 不符合 A～D，但認為仍符合簡審之理由", optional=True),
        ]),
        ("危險評估（全部「否」才符合簡審）", [
            C(f"簡審{n}", q, YES_NO, value) for n, q, value in RISK_QS
        ] + [
            A("簡審理由", "上述有任一「是」時，說明符合簡審之理由", optional=True),
            C("簡審10", "受試者會因參與研究可能遭受刑事追訴、民事責任，或對財務、就業、保險、名譽、被標籤化等有負面影響？",
              ("不會", "會"), lambda c: "不會" if retro(c) else None),
        ]),
    ],
)


# ── 審查費 ─────────────────────────────────────────────────────────────────

REVIEW_FEE = Form(
    "審查費",
    where="案件資訊頁面 → 申請案相關資料 → 審查費",
    sections=[("審查費繳費方式", [
        C("繳費方式", "審查費繳費方式",
          ("請提供電子繳費單，將臨櫃繳款", "匯款或ATM轉帳方式繳費", "其他"),
          note="匯款：雲林、北護分院同仁或大學校區老師可用；請等行政審查受理通知信後再繳"),
        T("繳費備註", "其他注意事項（例如收據抬頭；未註明則以主持人姓名開立）", optional=True),
    ])],
)


# ── 利益申報（每位研究人員各填一份）────────────────────────────────────────

COI = Form(
    "利益申報",
    where="案件資訊頁面 → 研究團隊 → 利益申報「待填寫」（主持人、協同主持人、研究人員每人各一份）",
    note="以下是主持人本人的答案。有任何顯著財務利益/非財務關係時，改勾 B 並填「評估暨處置計畫說明表」。",
    sections=[("1. 顯著財務利益暨非財務關係申報表", [
        C("利益-智財", "是否知悉所屬機構或主管，持有本研究運用之任何智慧財產之產權或權利金利益？",
          ("否", "是。請說明產品以及預估金額："), "否"),
        M("利益-申報", "A欄及B欄擇一", ("A.聲明無任何需申報之顯著財務利益/非財務關係", "B.任何顯著財務利益/非財務關係聲明"),
          ["A.聲明無任何需申報之顯著財務利益/非財務關係"]),
        M("利益-主持人聲明", "計畫主持人之聲明",
          ("本人茲聲明：必須申報顯著財務利益/非財務關係之所有研究相關人員，已詳列並提出本表。",),
          ["本人茲聲明：必須申報顯著財務利益/非財務關係之所有研究相關人員，已詳列並提出本表。"]),
    ])],
)


# ── 新案免審申請書（審查方式＝免審，formTypeId=3）─────────────────────────────

def _x(n):
    """免審申請書 field ids: '免審5-1' (the page numbers its questions 1–11 without a letter)."""
    return f"免審{n}"


EXEMPT_REASONS = (
    "於公開場合進行之非記名、非互動且非介入性之研究，且無從自蒐集之資訊辨識特定之個人。",
    "使用已合法公開週知之資訊，且資訊之使用符合其公開週知之目的。",
    "公務機關執行法定職務，自行或委託專業機構進行之公共政策成效評估研究。",
    "於一般教學環境中進行之教育評量或測試、教學技巧或成效評估之研究。",
    "研究計畫屬最低風險，且其研究對象所遭受之風險不高於未參加該研究者，經本會評估得免審查。",
)

EXEMPT_APP = Form(
    "新案免審申請書",
    where="案件資訊頁面 → 申請案相關資料 → 新案免審申請書（分頁：基本資料、免審申請書）",
    when=exempt,
    note="審查方式在建案時選定；免審不適用於易受傷害族群（11-1 答「是」請改送簡審或一般審查）。"
         "免審沒有自評表、病歷申請表、切結書，計畫書須含中文摘要。",
    sections=[
        ("基本資料", [
            A("計畫中文名稱", "計畫中文名稱", "{study.title_zh}"),
            A("計畫英文名稱", "計畫英文名稱", "{study.title_en}"),
            A("研究目的", "試驗/研究計畫目的", _prop("objectives")),
        ]),
        ("免審申請書", [
            M(_x(1), "1. 計畫經費贊助來源（可複選）",
              ("廠商", "政府、學術研究單位", "自籌(自行研究無經費補助)", "其他 (如美國聯邦政府)，請註明單位")),
            C(_x("1-1"), "1-1. 廠商為全部贊助或部分贊助？", ("全部贊助", "部分贊助"), when=_says(_x(1), "廠商")),
            M(_x("1-2"), "1-2. 學術研究單位為何？",
              ("本院院內計畫", "國科會", "衛生福利部", "國家衛生研究院", "中央研究院", "榮台聯大", "大學或科部", "國防研究",
               "其他，請註明單位"), when=_says(_x(1), "政府")),
            C(_x(2), "2. 研究計畫責任歸屬", ("本院/計畫主持人", "試驗委託者", "受託研究機構(CRO)"), "本院/計畫主持人"),
            T(_x("2-1"), "2-1. 委託公司/機構", when=_says(_x(2), "試驗委託者", "受託")),
            C(_x("2-2"), "2-2. 是否有受託研究機構(CRO)協助？", YES_NO, when=_says(_x(2), "試驗委託者", "受託")),
            T(_x("2-3"), "2-3. CRO公司名稱", when=_says(_x("2-2"), "是")),
            C(_x(3), "3. 計畫是否受美國食品藥物管理局(FDA)或美國衛生福利部(DHHS)管轄", YES_NO, "否",
              note="是：另上傳「受 DHHS 或 FDA 管轄計畫申請免審之理由勾選表」"),
            M(_x("3-1"), "3-1. 請續勾選", ("美國食品藥物管理局(FDA)", "美國衛生福利部(DHHS)"), when=_says(_x(3), "是")),
            M(_x(4), "4. 計畫執行地點", SITES[:-1] + ("其他：",)),
            A(_x("5-1"), "5-1. 受試者/收案對象納入條件", _prop("inclusion")),
            A(_x("5-2"), "5-2. 受試者/收案對象排除條件", _prop("exclusion")),
            A(_x(6), "6. 請簡述招募受試者/收案對象方式",
              lambda c: "本研究使用既有資料，不招募受試者，不接觸研究對象。" if retro(c) else None),
            C(_x(7), "7. 計畫與受試者是否有互動過程？", YES_NO, lambda c: "否" if retro(c) else None),
            A(_x("7-1"), "7-1. 取得受試者同意之程序（時機、地點、方式、由誰解釋並取得同意）", when=_says(_x(7), "是")),
            A(_x("7-2"), "7-2. 將告知受試者之資訊（研究性質、參與程序、自願參與、研究人員姓名及聯絡資訊）",
              when=_says(_x(7), "是")),
            A(_x(8), "8. 請簡述研究工具（如：問卷、資料庫）"),
            A(_x("9-1"), "9-1. 請說明如何維護資料機密性", _confidentiality),
            A(_x("9-2"), "9-2. 請說明如何保護受試者隱私", _privacy),
            C(_x(10), "10. 本案是否屬本院規範之網路研究？", ("否", "是(請填台大醫院網路研究自評表)"), "否"),
            C(_x("11-1"), "11-1. 研究對象是否為未成年人、收容人、原住民、孕婦、身心障礙、精神病患、受不當脅迫或無法自由意願決定者？",
              ("否", "是(勾選此項並不符合免審範圍，請改送簡易審查或一般審查)"),
              lambda c: _yn(c["subjects"]["vulnerable_population"])),
            M(_x("11-1-1"), "11-1-1. 勾選研究對象",
              ("未成年人", "收容人", "原住民", "孕婦", "身心障礙", "精神病患", "無法自主行使同意之成人", "受拘禁人"),
              when=_says(_x("11-1"), "是")),
            M(_x("11-2"), "11-2. 自評符合之免審項目（是否符合由倫委會判定）", EXEMPT_REASONS,
              note="頁面題號誤印為 10-2；第 4、5 項後面有 45CFR46 的例示說明"),
            A(_x("11-2-1"), "11-2-1. 請說明符合理由"),
        ]),
    ],
)


# ── 計畫主持人聲明書 ────────────────────────────────────────────────────────

PI_DECLARATION = Form(
    "計畫主持人聲明書",
    where="案件資訊頁面 → 申請案相關資料 → 計畫主持人聲明書",
    note="沒有要填的欄位：閱讀後按「簽核」即可（v20230714）。系統依 B. 研究類型帶出對應版本，"
         "所以要先存好新案申請書的 B 分頁才看得到內容。",
    sections=[("簽核", [
        M("聲明書", "計畫主持人聲明書", ("已閱讀並簽核",), ["已閱讀並簽核"]),
    ])],
)


# ── 上傳/檢視案件相關文件 ────────────────────────────────────────────────────
# (item as listed on the upload page, needed(config) or None = only if the study has one)

UPLOADS_REVIEWED = [
    ("1. 臨床研究計畫申請人自評表（必備）", lambda c: True),
    ("2. 計畫書（必備，註明版本日期）", lambda c: True),
    ("3. 計畫中文摘要（必備，註明版本日期）", lambda c: True),
    ("4. 計畫英文摘要", None),
    ("5. 受試者同意書/受試者說明書（註明版本日期）", lambda c: route(1)(c) or route(2)(c)),
    ("6. 研究執行之問卷、病患日誌卡、訪談大綱", None),
    ("7. 招募受試者廣告文宣品", lambda c: _says("G26", "海報", "社群")(c)),
    ("8. 個案報告表", None),
    ("9. 主持人手冊", lambda c: _says("E3", "是")(c)),
    ("10. 資料及安全性監測計畫", lambda c: _says("E4", "是")(c)),
    ("15. 臨床試驗藥品資料表", drug),
    ("17. 藥品自行管理簽文及臨床試驗用藥自行管理自評表", _all(drug, _says("C6", "否"))),
    ("20. 藥品/醫療器材許可證", lambda c: _says("C3", "是")(c) or _says("D4", "有")(c)),
    ("26. 試驗醫療器材簡介", device),
    ("30. 納入易受傷害族群說明表", lambda c: c["subjects"]["vulnerable_population"] and not (retro(c) and waiver(c))),
    ("31. 擔保書", lambda c: _says("G32", "是")(c)),
    ("32. 台大醫院網路研究自評表", lambda c: _says("G33", "是")(c)),
    ("34. 輻射量計算公式計算結果", lambda c: _says("G22-1", "是")(c)),
    ("35. 生物安全會通過證明", lambda c: _says("G24", "是")(c)),
    ("37. 臺大醫療體系醫療整合資料中心資料需求單", lambda c: _says("F2-2", "臺大醫療體系")(c)),
    ("39. 使用病歷資料進行研究申請表", lambda c: retro(c) and waiver(c)),
    ("40. 保密聲明切結書（主持人及每位研究人員各一份）", lambda c: retro(c) and waiver(c)),
    ("43. 其他：新案申請書（行政審查後由系統列印，主持人及科/部主任簽章後掃描）", lambda c: True),
    ("44. 審查費繳費單及繳費收據掃描檔", lambda c: True),
]

UPLOADS_EXEMPT = [
    ("1. 計畫書（含中文摘要，註明版本日期）", lambda c: True),
    ("2. 受試者同意書/受試者說明書", lambda c: _says(_x(7), "是")(c)),
    ("3. 研究執行之問卷、訪談大綱", None),
    ("4. 招募受試者廣告文宣品", None),
    ("5. 公務機關公共政策成效評估研究之公文", lambda c: _says(_x("11-2"), "公務機關")(c)),
    ("6. 受 DHHS 或 FDA 管轄計畫申請免審之理由勾選表", lambda c: _says(_x(3), "是")(c)),
    ("7. 台大醫院網路研究自評表", lambda c: _says(_x(10), "是")(c)),
    ("8. 參考資料", None),
    ("10. 審查費繳費相關掃描檔", lambda c: True),
]


def _uploads(items, key):
    names = tuple(n for n, _ in items)
    return M(key, "本案要上傳的文件（■ 依目前答案判斷需要；□ 有才上傳）", names,
             lambda c: [n for n, need in items if need and _test_safe(need, c)],
             note="頁面完整清單另有藥品、醫材、技術等項目；檔名不可含 ( ) -- \" ' < > | 等字元")


def _test_safe(pred, c):
    try:
        return bool(pred(c))
    except (KeyError, TypeError, AttributeError):
        return False


UPLOADS = Form(
    "上傳文件",
    where="案件資訊頁面 → 申請案相關資料 → 上傳/檢視案件相關文件",
    when=reviewed,
    note="計畫書、摘要、同意書、問卷、文宣品等都要註明版本日期。",
    sections=[("一般審查／簡易審查", [_uploads(UPLOADS_REVIEWED, "上傳文件")])],
)

UPLOADS_EX = Form(
    "上傳文件",
    where="案件資訊頁面 → 申請案相關資料 → 上傳/檢視案件相關文件",
    when=exempt,
    note="免審只要計畫書（含中文摘要）與實際用到的文件。",
    sections=[("免審", [_uploads(UPLOADS_EXEMPT, "上傳文件")])],
)


ONLINE_FORMS = {
    "new": [NEW_CASE_APP, EXEMPT_APP, SIMP_REVIEW, UPLOADS, UPLOADS_EX, PI_DECLARATION, REVIEW_FEE, COI],
}

# Submissions after approval (變更、持續審查、結案、SAE、偏差、其他事項)
from rec_helper.institutions.ntuh.online_phases import PHASE_ONLINE_FORMS  # noqa: E402

ONLINE_FORMS.update(PHASE_ONLINE_FORMS)
