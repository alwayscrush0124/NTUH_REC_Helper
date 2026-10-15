"""NTUH REC web system — pages after approval (變更、持續審查、結案、SAE、偏差、其他事項).

Field ids and options follow the committee's 「申請書(含填寫說明)」 PDFs on the 表單下載
pages (e-REC versions as of 2026-10): 變更案申請書 2026.3.6, 持續審查申請書 AF-010-06.0,
結案/終止/撤案申請書 AF-024-05.1, 嚴重不良事件及非預期問題通報表 2026, 試驗偏差 2021,
其他事項 2021. Case data (計畫名稱, 主持人, 許可效期 …) is carried over by the system.

Ids are the printed numbers with a phase prefix (變更6, 持續7-1, 結案5-1, SAE12, 偏差5-2,
其他1) so one 線上填寫.md can hold answers for several submissions.
"""
from rec_helper.institutions.ntuh.online import (
    YES_NO,
    _says,
    drug,
    interventional,
    retro,
    waiver,
)
from rec_helper.online_forms import A, C, Form, M, T

WHERE = "執行中案件 → 點選案件 → 申請{}"


def _amend(c):
    return c.get("amendment") or {}


def _closure(c):
    return c.get("closure") or {}


def _cr(c):
    return c.get("continuing_review") or {}


def _multisite(c):
    return c["study"]["multicenter"]


# ── shared blocks: 收案人數、退出、隱私聲明 ─────────────────────────────────────

SITE_COLUMNS = ("本試驗/研究中心", "本院醫療體系內其他中心", "本國未設置IRB之中心", "本國其他試驗中心")
WITHDRAW = ("不良反應", "死亡", "治療反應不佳", "未回診", "不符合納入條件", "未依計畫書執行",
            "拒絕治療／撤回同意", "早期改善", "行政或其他因素")


def _enrolled(prefix, n, actual):
    """本期間納入收案數 by site column (the system fills 預計 and the totals)."""
    out = []
    for i, col in enumerate(SITE_COLUMNS, 1):
        value = actual if i == 1 else (None if i in (2, 4) else "0")
        out.append(T(f"{prefix}{n}-{i}", f"本期間納入收案數（人/筆）－{col}", value,
                     when=None if i in (1, 3) else _multisite,
                     note="前瞻性／回溯性／回溯性檢體分列時，各表各填一次" if i == 1 else ""))
    return out


def _withdrawals(prefix, n):
    return [T(f"{prefix}{n}-{i}", f"本院中途退出－{why}（本期人數）", lambda c: "0" if retro(c) else None)
            for i, why in enumerate(WITHDRAW, 1)]


def _privacy_declaration(prefix, n, items):
    """主持人聲明隱私保護措施 A–G: (letter, statement, options, default(config))."""
    return [C(f"{prefix}{n}{letter}", f"{letter}. {text}", options, default) for letter, text, options, default in items]


def _outside_partner(c):
    """附件填寫.md `## 院外合作` names an outside collaborator (使用病歷資料進行研究申請表 item 1)."""
    att = c.get("attachments") if isinstance(c.get("attachments"), dict) else {}
    return any(k.split()[0] == "院外合作" and v for k, v in att.items() if k.strip())


def _carried_out(c):
    """Records leave the hospital: web answer F4 是, or 附件填寫.md `## 攜出院外` given."""
    att = c.get("attachments") if isinstance(c.get("attachments"), dict) else {}
    return _says("F4", "是")(c) or any(k.split()[0] == "攜出院外" and v for k, v in att.items() if k.strip())


def _records_inside(c):
    if not retro(c):
        return None
    return "業經院方簽核同意攜出分析或受試者同意書已說明將攜出分析" if _carried_out(c) else "是"


PRIVACY_COMMON = [
    ("A", "若收集可識別身分的個資均以代碼或加密保護。", ("是", "否_請說明", "不適用(未收集可識別身分個資)"),
     lambda c: "是" if c["closure"].get("data_safety", {}).get("deidentified") else None),
    ("B", "書面資料保存於院內上鎖之辦公室或研究室，電子資料保存於院內電腦/伺服器並以密碼保護。",
     ("是", "否_請說明"), "是"),
    ("C", "收集之病歷資料均僅在院內使用",
     ("是", "否，請說明", "業經院方簽核同意攜出分析或受試者同意書已說明將攜出分析", "不適用(未收集病歷資料)"),
     _records_inside),
    ("D", "主持人已親自確認所有研究人員(含主持人)完成病歷隱私保護與資訊安全訓練、簽署保密聲明切結書等。",
     ("是", "否_請說明"), "是"),
    ("E", "已簽署合作研究合約或產學合作研究合約，約定智財權益的分配及成果保密義務（研究者自行發起且與院外合作者）。",
     ("是", "否_請說明", "不適用"), lambda c: None if _outside_partner(c) else "不適用"),
]


# ── 變更案申請書 ─────────────────────────────────────────────────────────────

CHANGES = ("1.變更計畫內容（文件）", "2.計畫名稱", "3.計畫主持人", "4.協同主持人", "5.研究人員", "6.展延計畫結束日期",
           "7.研究類型", "8.試驗中心類別", "9.預計收案數", "10.回溯收集之資料/檢體來源或收集期間", "11.受試者招募方式",
           "12.收案地點", "13.計畫責任歸屬、經費來源、藥品/器材提供", "14.知情同意程序",
           "15.新增或變更剩餘檢體保留/未去連結之研究材料(含檢體)輸出國外者", "16.新增或變更納入易受傷害族群",
           "17.修改本計畫執行前需經主管機關核准與否之狀態", "18.本次變更涉及基因項目",
           "19.資料安全性監測計畫/資料安全監測委員會(DSMP/DSMB)", "20.其他變更")
CHANGE_DOCS = ("計畫書", "受試者同意書/說明書", "主持人手冊", "個案報告表", "招募受試者廣告文宣品", "問卷", "資料安全監測計畫")


def _change_items(c):
    if _amend(c).get("change_description"):
        return ["20.其他變更"]
    return None


def _changed(n):
    return _says("變更二", f"{n}.")


AMENDMENT_APP = Form(
    "變更案申請書",
    where=WHERE.format("變更案"),
    note="勾選【須變更】的項目才要填；每項都寫「(1)變更原因 (2)變更後內容」。"
         "修正後內容系統會自動帶出，沒變的不要動。另上傳修正前後對照表。",
    sections=[
        ("一、是否符合簡易審查條件", [
            C("變更一", "是否符合簡易審查條件？", YES_NO),
            M("變更一-1", "符合之簡審條件",
              ("1.研究計畫極微的變更", "2.主管機關指定計畫(CIRB機制)以及NRPB聯合審查機制計畫經主審醫院研究倫理委員會審查通過之變更案",
               "3.依衛生福利部意見修正"),
              when=_says("變更一", "是"),
              note="新增或刪除治療、增加受試者風險的納排變更、用藥途徑、有意義的人數或劑量變更，都不算極微變更"),
        ]),
        ("二、變更項目、原因及內容", [
            M("變更二", "本次變更項目（勾【須變更】）", CHANGES, _change_items),
            M("變更1-文件", "1. 變更之計畫文件", CHANGE_DOCS, when=_changed(1)),
            *[A(f"變更{n}", f"{item}：(1)變更原因 (2)變更後內容", when=_changed(n),
                value=(lambda c: _amend(c).get("change_description")) if n == 20 else None,
                note={3: "原計畫主持人將轉任協同主持人／研究團隊／退出研究團隊，請一併註明",
                      4: "新增請以姓名或帳號選取；刪除請勾選姓名",
                      5: "新增研究人員後，系統會通知其登入做利益申報",
                      6: "寫新的結束日期 (yyyy/mm/dd)",
                      10: "寫明資料/檢體來源與收集期間 XX年XX月XX日至XX年XX月XX日；含是否攜出院外",
                      16: "說明納入理由（無法以其他對象取代或明顯有利於該族群）及額外保護措施",
                      18: "列出擬檢測之基因項目及範圍；涉及 WGS 需附 NGS 說明表與同意書",
                      20: "變更計畫書等文件、或上述以外的變更，都寫在這裡"}.get(n, ""))
              for n, item in enumerate(CHANGES, 1) if n != 1],
            A("變更1", "1. 變更計畫內容：(1)變更原因 (2)變更內容摘要", when=_changed(1)),
        ]),
        ("四、核准前是否持續收案、是否重簽同意書", [
            C("變更四", "本變更案經本會核准前是否會持續收案？", YES_NO,
              lambda c: "否" if retro(c) and waiver(c) else None),
            C("變更四-I", "本變更案核准之後，先前已納入之受試者是否需要重新簽署受試者同意書？",
              ("尚未收案，不適用", "是，需重新簽署", "否，請說明原因："),
              lambda c: None if not waiver(c) else "否，請說明原因：",
              note="免除知情同意的案子選「否」並說明「本案經核准免除知情同意」"),
            T("變更四-I-說明", "不重簽之原因", lambda c: "本案經核准免除知情同意。" if waiver(c) else None,
              optional=True, when=_says("變更四-I", "否")),
            C("變更四-重簽", "需重新簽署之對象", ("納入受試者一律需重簽", "已完成受試者不需重簽，僅研究進行中之受試者需重簽", "其他："),
              when=_says("變更四-I", "是")),
        ]),
        ("五、預期變更後帶來之風險", [
            C("變更五", "預期變更後帶來之風險",
              ("變更後面臨的風險與原計畫相當。", "變更後面臨的風險比原計畫高，但明顯地可增進受試者的福祉。",
               "變更後面臨的風險比原計畫高，雖然沒有明顯地增進受試者的福祉，但對於研究主題可得到有價值的結果。"),
              lambda c: None if _amend(c).get("affects_risk") else "變更後面臨的風險與原計畫相當。"),
        ]),
        ("六、為避免受試者受傷害而先行之偏離或變更", [
            C("變更六", "本案是否屬於為了即時避免受試者遭受傷害，而在核准前先進行的偏離(偏差)或變更？", YES_NO, "否"),
            C("變更六-I", "是否有七日內通報本會？", ("是", "否，請說明："), when=_says("變更六", "是")),
        ]),
        ("七、CRF / IB 更新", [
            C("變更七", "本次變更是否涉及更新個案報告表(CRF)、主持人手冊(IB)、醫療器材手冊或類此文件？", YES_NO,
              lambda c: "否" if retro(c) else None),
            C("變更七-1", "是否改變受試者之既有風險利益或影響其權益？",
              ("否", "是，更新資訊已在受試者同意書中呈現", "是，但經評估不需要更新受試者同意書"),
              when=_says("變更七", "是"), note="選第 2 項請寫同意書版本日期；第 3 項請寫理由"),
        ]),
    ],
)


# ── 持續審查申請書 (AF-010) ──────────────────────────────────────────────────

CONTINUING_APP = Form(
    "持續審查申請書",
    where=WHERE.format("持續審查"),
    note="預計收案數、第 1 位收案日、總數由系統帶出；只填本期數字。回溯性病歷研究的「收案時間」＝調閱病歷的時間。",
    sections=[
        ("1. 簡易審查", [
            C("持續1", "是否符合簡易審查條件？", YES_NO,
              lambda c: "是" if c["study"]["review_type"] == "expedited" else None,
              note="新案是簡審、之後變更也沒超出簡審範圍，就符合第 1 項"),
            M("持續1-1", "簡易審查範圍評檢表",
              ("1.原新案為簡易審查案件且後續變更未涉及超過新案簡易審查範圍。", "2.該研究已不再收錄新個案，且所收錄之研究對象均已完成所有相關的研究試驗，惟仍須長期追蹤。",
               "3.尚未納入受試者，且沒有新的危險性。", "4.僅限於接續前階段研究之後續資料分析。"),
              lambda c: ["1.原新案為簡易審查案件"] if c["study"]["review_type"] == "expedited" else None,
              when=_says("持續1", "是", default=lambda c: "是" if c["study"]["review_type"] == "expedited" else None)),
        ]),
        ("2–3. 執行狀況與收案期間", [
            C("持續2-1", "本院執行狀況",
              ("1.Not yet recruiting: 尚未開始招募受試者", "2.Recruiting: 目前持續招募受試者",
               "3.Enrolling by invitation : 獲邀請者才能進入研究或試驗", "4.Active, not recruiting: 研究或試驗仍進行中，但不再招募受試者",
               "5.Suspended(暫停): 暫停招募受試者，未來視情況決定是否繼續"),
              lambda c: {"recruiting": "2.Recruiting", "active": "4.Active", "not_yet": "1.Not yet",
                         "suspended": "5.Suspended"}.get(str(_cr(c).get("enrollment_status", "")).lower())),
            A("持續2-1-理由", "前次勾 4.Active, not recruiting、本次改 2.Recruiting 時，說明持續招募之理由", optional=True),
            T("持續3", "最近 1 位個案收案時間 (yyyy/mm/dd)"),
        ]),
        ("4. 本期間收案人數", _enrolled("持續", 4, lambda c: _cr(c).get("enrolled_this_period"))),
        ("5. 本院中途退出（本期）", _withdrawals("持續", 5)),
        ("6. 資料安全監測委員會", [
            C("持續6-1", "本試驗案是否設置資料安全委員會(DSMB)？（系統帶入）", ("否", "是，有設置資料安全委員會"),
              lambda c: "否" if not interventional(c) else None),
            C("持續6-2", "本期間 DSMB 是否開會？", YES_NO, when=_says("持續6-1", "是")),
            T("持續6-2-1", "會議排程(頻率)", when=_says("持續6-1", "是")),
            T("持續6-2-2", "會議日期", when=_says("持續6-2", "是")),
            A("持續6-2-3", "會議紀錄或結果說明（紀錄另上傳）", when=_says("持續6-2", "是")),
        ]),
        ("7. 嚴重不良事件、非預期問題、不良事件", [
            C("持續7-1", "本期間是否發生嚴重不良事件(含院外)及非預期問題或有意義之不良事件(僅本院)？", ("否", "是（續填）"),
              lambda c: "否" if retro(c) else None),
            *[T(f"持續7-{k}", label, when=_says("持續7-1", "是"))
              for k, label in (("2-1", "SAE 及 UP 件數－院內"), ("2-2", "SAE 及 UP 件數－國內其他醫院"), ("2-3", "SAE 及 UP 件數－國外"),
                               ("3-1", "非預期問題通報本會件數"), ("4-1", "本院有意義之不良事件件數"))],
            A("持續7-4-2", "有意義之不良事件說明", optional=True, when=_says("持續7-1", "是")),
        ]),
        ("8. 案件執行情形", [
            C("持續8-1", "本次持續審查提出時是否已逾原核可效期？", ("否", "是（續填）"), "否"),
            A("持續8-1-1", "逾期理由", when=_says("持續8-1", "是")),
            C("持續8-1-2", "逾期期間是否暫緩所有試驗活動？",
              ("是", "否，請說明", "因安全性考量無法立即停止試驗者，業經研究倫理委員會(REC)同意", "其他，理由："),
              when=_says("持續8-1", "是")),
            C("持續8-2", "現行使用之受試者同意書是否為本會核准之最後版本？",
              ("本案經核准免除同意或免除簽署書面同意書", "是", "否，請說明："),
              lambda c: "本案經核准免除同意或免除簽署書面同意書" if waiver(c) else None),
            C("持續8-3", "自評是否符合進度", ("進度超前", "符合進度", "落後進度，＿＿個月")),
        ]),
        ("9. 風險評估", [
            C("持續9-1", "是否有科學新知發現參與試驗的受試者風險會提高？", ("否", "是，請說明"), "否"),
            C("持續9-1-1", "有影響持續參與意願的風險資訊時，主持人是否皆已主動告知受試者？", ("是", "否，請說明"),
              when=_says("持續9-1", "是")),
            C("持續9-1-2", "是否需要修訂同意書？", ("否，請說明", "是"), when=_says("持續9-1", "是")),
            C("持續9-2", "本期間是否曾接受稽核/實地訪查/監測/查核？", ("否", "是"), "否"),
            M("持續9-2-1", "稽核單位（並寫次數）", ("本院稽核小組", "試驗委託者", "衛生福利部", "其他："), when=_says("持續9-2", "是")),
            A("持續9-3", "研究期間遭遇與倫理相關之問題與處理（無則填「無」）", "無"),
        ]),
        ("10. 本院主持人主導之多機構臨床試驗", [
            A("持續10-1", "本期間計畫書變更、不良反應、非預期問題、期中分析等與各機構溝通之執行情形", when=lambda c: _multisite(c) and interventional(c)),
            A("持續10-2", "其他參與機構是否均已獲得其研究倫理委員會之許可？", when=_multisite),
        ]),
        ("11–12. 補充說明與隱私保護聲明", [
            A("持續11", "其他補充說明（無則留空）", optional=True),
            *_privacy_declaration("持續", "12", PRIVACY_COMMON + [
                ("F", "研究主持人及研究有關人員，不得洩露因業務知悉之秘密或與研究對象有關之資訊。", ("是", "否_請說明"), "是"),
            ]),
        ]),
    ],
)


# ── 結案、終止、撤案申請書 (AF-024) ──────────────────────────────────────────

STATUS = ("Completed(結案)：研究或試驗已結束，所有受試者皆已完成研究或試驗相關程序",
          "Terminated(終止)：研究或試驗因故無法繼續進行，且未來不再執行",
          "Withdrawn(撤案)：研究或試驗尚未納入受試者，即因故不再執行")


def _not_withdrawn(c):
    return not _says("結案1", "Withdrawn")(c)


CLOSURE_APP = Form(
    "結案、終止、撤案申請書",
    where=WHERE.format("結案/終止/撤案"),
    note="撤案只要填第 1 題。另上傳 SAE 摘要報告清單（若有）、已發表文獻（若有）。",
    sections=[
        ("1. 本院執行狀況", [
            C("結案1", "本院執行狀況", STATUS, STATUS[0]),
            A("結案1-原因", "終止/撤案原因", when=_says("結案1", "Terminated", "Withdrawn")),
            A("結案1-後續", "終止計畫之後續處理（受試者權益保護、後續醫療照護、轉介、如何通知受試者）",
              when=_says("結案1", "Terminated")),
        ]),
        ("2–4. 收案期間、人數、退出", [
            T("結案2", "最近 1 位個案收案時間 (yyyy/mm/dd)", when=_not_withdrawn,
              note="回溯性病歷研究＝最後一位個案調閱病歷的時間"),
            *[f for f in _enrolled("結案", 3, lambda c: _closure(c).get("actual_n"))],
            *_withdrawals("結案", 4),
        ]),
        ("5–6. SAE、稽核、倫理問題", [
            C("結案5-1", "本計畫自通過後至結案期間是否有發生嚴重不良事件及非預期問題？", ("否", "是（續填）"),
              lambda c: "否" if not _closure(c).get("sae_count") else "是（續填）"),
            T("結案5-2-1", "SAE 及 UP 件數－院內", lambda c: _closure(c).get("sae_count") or None,
              when=_says("結案5-1", "是", default=lambda c: "是" if _closure(c).get("sae_count") else "否")),
            T("結案5-2-2", "SAE 及 UP 件數－國內其他醫院", when=_says("結案5-1", "是")),
            T("結案5-2-3", "SAE 及 UP 件數－國外", when=_says("結案5-1", "是")),
            C("結案6-1", "計畫執行期間是否曾接受稽核/實地訪查/監測/查核？", ("否", "是"), "否"),
            M("結案6-1-1", "稽核單位（並寫次數）", ("本院稽核小組", "試驗委託者", "衛生福利部", "其他："), when=_says("結案6-1", "是")),
            A("結案6-2", "研究期間遭遇與倫理相關之問題與處理（無則填「無」）", "無"),
        ]),
        ("7. 試驗結果", [
            C("結案7-1", "受試者/研究對象是否遭遇任何非預期之結果（生理、心理或社會）？", YES_NO[::-1],
              lambda c: "否" if retro(c) else None),
            C("結案7-2", "是否有重要結果足以影響受試者族群的利害而需要向受試者公開揭露？", ("否", "是"), "否"),
            C("結案7-3", "是否已發表？", ("否", "是，期刊名稱："), note="已發表請上傳文獻電子檔"),
            T("結案7-3-期刊", "期刊名稱", when=_says("結案7-3", "是")),
        ]),
        ("8–9. 補充說明、藥品與經費", [
            A("結案8-1", "其他補充說明（無則留空）", optional=True),
            C("結案9-1", "是否已完成本院臨床試驗用藥管理中心結案相關程序（藥品回收、藥品管理費）？",
              ("是(請檢附藥劑部證明文件或有藥劑部核章)", "否：理由", "不適用(為醫療常規用藥或已簽准自行管理)"),
              lambda c: None if drug(c) else "不適用(為醫療常規用藥或已簽准自行管理)"),
            C("結案9-2", "廠商是否已依臨床試驗合約完成本院臨床試驗各項經費之繳納？", ("是", "否：請說明"),
              when=_says("A1", "試驗委託者", "受託")),
        ]),
        ("10. 隱私保護聲明", _privacy_declaration("結案", "10", PRIVACY_COMMON + [
            ("F", "將依本計畫所述保存期限妥善保存資料，期限到後將予以銷毀，硬碟格式化處理。", ("是", "否_請說明"), "是"),
            ("G", "研究主持人及研究有關人員，不得洩露因業務知悉之秘密或與研究對象有關之資訊。", ("是", "否_請說明"), "是"),
        ])),
    ],
)


# ── 嚴重不良事件及非預期問題通報表 ──────────────────────────────────────────

def _sae(c):
    return not _says("SAE1", "非預期問題")(c)


SAE_APP = Form(
    "嚴重不良事件及非預期問題通報表",
    where=WHERE.format("嚴重不良事件"),
    note="依規定時效通報（藥品 SUSAR 致死或危及生命：獲知 7 日內）。只勾 UP 時僅填 2、3、4、5、10。",
    sections=[("通報內容", [
        C("SAE1", "通報類別", ("院內嚴重不良事件(SAE)", "非預期問題(UP)"), note="同時屬 SAE 及 UP，勾 SAE"),
        C("SAE2", "是否通報全國藥物不良反應通報中心(ADR)/TFDA？", ("是，通報日期：", "否")),
        T("SAE3", "通報者獲知日期 (yyyy/mm/dd)"),
        T("SAE4", "發生日期 (yyyy/mm/dd)"),
        T("SAE5", "研究團隊通知試驗委託者日期 (yyyy/mm/dd)", optional=True),
        T("SAE6-1", "受試者識別代號", when=_sae),
        C("SAE6-2", "性別", ("男", "女"), when=_sae),
        T("SAE6-3", "出生年月", when=_sae),
        T("SAE6-4", "納入試驗日期", when=_sae),
        C("SAE7", "報告類別", ("初始報告", "追蹤報告"), when=_sae, note="追蹤報告請寫第幾次及初始報告系統申請編號"),
        T("SAE8", "可疑藥品/醫材", when=_sae),
        T("SAE9", "事件或問題名稱", when=_sae),
        A("SAE10", "事件或問題簡述"),
        C("SAE11", "事件或問題是否為預期", ("預期", "非預期"), when=_sae,
          note="預期請註明列於計畫書/主持人手冊/仿單、同意書或其他"),
        C("SAE12", "事件或問題之因果關係", ("不相關 Unrelated", "不太可能相關 Unlikely", "可能相關 Possible",
                                    "很可能相關 Probably/likely", "確定相關 Certain/Definite", "其他，請說明："), when=_sae),
        C("SAE13", "是否涉及對受試者或其他人造成比已知更大的傷害風險？", YES_NO, when=_sae,
          note="非預期＋可能相關以上＋是 → 屬非預期問題(UP)"),
        M("SAE14", "不良事件後果", ("死亡death", "危及生命life threatening", "導致病人住院或延長病人住院時間",
                               "造成永久性殘疾disability", "先天性畸形congenital anomaly", "需作處置以防永久性傷害", "其他，請說明："),
          when=_sae),
        M("SAE15", "事件或問題之處置", ("依計畫繼續執行", "改變劑量", "受試者退出試驗", "其他，請說明："), when=_sae),
        M("SAE16", "事件或問題現況", ("1.住院中", "2.已轉院", "3.已出院", "4.至＿＿＿門診追蹤", "5.症狀已解除",
                                  "6.事件持續中", "7.其他，請說明："), when=_sae),
        M("SAE17", "研究計畫之影響及處置", ("1.不影響、不需採取行動", "2.修改計畫書", "3.修改受試者同意書",
                                     "4.需增加安全性監測", "5.終止或暫停計畫執行"), when=_sae,
          note="選 1 以外的項目，請另提供文件"),
    ])],
)


# ── 試驗偏差通報申請書 ──────────────────────────────────────────────────────

DEVIATION_APP = Form(
    "試驗偏差通報申請書",
    where=WHERE.format("試驗偏差"),
    note="不同型態的事件要分開通報；同型態多位受試者時，1～3 填最早一筆。獲知日起 15 個工作日內通報。",
    sections=[("通報內容", [
        T("偏差1", "發生日期 (yyyy/mm/dd)"),
        T("偏差2", "研究團隊獲知日期 (yyyy/mm/dd)"),
        T("偏差3", "研究團隊通知試驗委託者日期（無委託者免填）", optional=True),
        A("偏差4", "受試者識別代號（多位請全部列出，並寫各自發生日期與事件內容）"),
        A("偏差5-1", "事件緣由"),
        C("偏差5-2", "本偏差是否重大影響臨床試驗執行或增加受試者風險？", ("是", "否，請說明：")),
        M("偏差5-2-1", "影響（請說明）", ("重大影響臨床試驗執行", "增加受試者風險"), when=_says("偏差5-2", "是")),
        C("偏差5-2-2", "主持人於獲知後是否立即通報？", ("是", "否，請說明："), when=_says("偏差5-2", "是")),
        C("偏差5-2-3", "是否屬主持人自評其他可能影響受試者權益或研究正確性之偏差/違規？", ("否", "是，請說明：")),
        C("偏差5-2-4", "是否符合計畫書規範之通報時效？", ("是", "否，請說明：", "計畫書並未規範")),
        C("偏差5-2-5", "是否符合獲知日起15個工作日內通報？", ("是", "否，請說明延遲通報之理由："),
          when=_says("偏差5-2-4", "計畫書並未規範")),
        A("偏差5-3", "相關處理方式"),
        A("偏差5-4", "改善方案（如何預防再發；延遲通報也要提改善方案）"),
        A("偏差5-5", "如何進行檢討與追蹤"),
        C("偏差5-6", "本次事件是否在本試驗/研究曾經發生過？", ("否", "是")),
        A("偏差5-7", "上次事件後使用之預防措施為何，及為何失效？", when=_says("偏差5-6", "是")),
    ])],
)


# ── 其他事項通報申請書 ──────────────────────────────────────────────────────

OTHER_APP = Form(
    "其他事項通報申請書",
    where=WHERE.format("其他事項"),
    sections=[("通報內容", [
        M("其他1", "通報項目（可複選）",
          ("DSMB 決議通知", "通報試驗相關通知信函", "試驗開始執行前必備文件（屬須通報衛生福利部案件）", "成果報告",
           "計畫主持人長期請假由協同主持人代理", "持續審查效期逾期，但在安全性考量下無法立即停止試驗",
           "定期安全性報告（屬報告結論改變計畫之風險效益且需變更計畫書或受試者同意書）", "計畫暫停執行", "其他")),
        A("其他2", "事件描述（送審文件請註明名稱及版本日期）",
          note="信函：寫信件日期與內容，並說明是否改變計畫書；主持人請假：起訖期間與代理內容；"
               "安全性報告：藥名、資料區間、是否影響風險效益；暫停：原因與期間"),
    ])],
)


PHASE_ONLINE_FORMS = {
    "amendment": [AMENDMENT_APP],
    "continuing": [CONTINUING_APP],
    "closure": [CLOSURE_APP],
    "suspension": [CLOSURE_APP],
    "sae": [SAE_APP],
    "deviation": [DEVIATION_APP],
    "other": [OTHER_APP],
}
