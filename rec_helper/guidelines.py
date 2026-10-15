"""Reporting-guideline coverage of the protocol (SPIRIT, STROBE, STARD, CLAIM, TRIPOD+AI, TRIPOD-LLM).

Reviewers and later journals expect a study planned along the guideline for
its design. This checks, item by item, whether the protocol text mentions what
the guideline asks a study to define. Items are short paraphrases for planning
(not the official wording — consult the guideline itself), each with words that
count as covering it, in Chinese and English.

Guidelines are chosen from the study (trial → SPIRIT; otherwise STROBE; LLM →
TRIPOD-LLM; imaging AI → CLAIM; prediction model → TRIPOD+AI; diagnostic
accuracy → STARD) or set explicitly: `guidelines = ["STROBE", "CLAIM"]`.

Usage: rech guidelines [config.toml] [--output DIR]   → output/guidelines_report.md
"""
import os
import re

from rec_helper import study_text

# name → (full name, [(item, regex)])
GUIDELINES = {
    "SPIRIT": ("SPIRIT（臨床試驗計畫書）", [
        ("試驗登錄（登錄網站與編號）", r"登錄|ClinicalTrials|registr"),
        ("背景與選用對照之理由", r"背景|background"),
        ("具體目的或假說", r"目的|假說|objective|hypothes"),
        ("試驗設計（平行、交叉、優越性/不劣性）", r"平行|交叉|不劣|優越|parallel|crossover|non-?inferior|superior"),
        ("試驗場所與國家", r"執行地點|試驗場所|院區|site|setting"),
        ("受試者納入與排除條件", r"納入條件|排除條件|inclusion|exclusion"),
        ("介入措施（內容、給予方式、遵從性）", r"介入|試驗藥|劑量|intervention|dose"),
        ("主要與次要結果指標（含時間點）", r"主要(?:評估)?(?:指標|終點)|次要|primary|secondary|outcome|endpoint"),
        ("受試者時程表（篩選、介入、追蹤）", r"時程|流程圖|schedule|timeline|追蹤"),
        ("樣本數估算", r"樣本數|檢定力|power|sample size"),
        ("招募策略", r"招募|recruit"),
        ("隨機分派方法與分派隱匿", r"隨機|分派|random|allocation"),
        ("盲性（對誰設盲、如何解盲）", r"盲|blind|mask"),
        ("資料收集與管理方法", r"資料收集|資料管理|data (?:collection|management)"),
        ("統計方法（主要分析、次群組、缺失值）", r"統計|statistic|缺失|missing"),
        ("資料監測（DSMB）與期中分析", r"DSMB|監測|期中分析|interim|monitor"),
        ("不良事件收集與通報", r"不良事件|adverse|SAE"),
        ("倫理審查與知情同意", r"倫理|知情同意|consent|ethic"),
        ("保密與資料存取", r"保密|隱私|confidential|privacy|存取"),
        ("結果發表與傳播", r"發表|publish|dissemin"),
    ]),
    "STROBE": ("STROBE（觀察性研究：世代、病例對照、橫斷）", [
        ("背景與研究理由", r"背景|background|rationale"),
        ("具體目的與事先設定的假說", r"目的|假說|objective|hypothes"),
        ("研究設計", r"世代|病例對照|橫斷|cohort|case-control|cross-sectional"),
        ("場所、地點與招募／資料期間", r"資料期間|收案期間|院區|地點|setting|period"),
        ("研究對象之納入條件與選取方式", r"納入條件|選取|inclusion|eligib"),
        ("變項定義（結果、暴露、預測因子、干擾因子）", r"變項|暴露|干擾|confound|exposure|variable|covariate"),
        ("資料來源與測量方法", r"資料來源|測量|data source|measure"),
        ("偏差及處理方式", r"偏差|偏誤|bias"),
        ("樣本數如何決定", r"樣本數|檢定力|sample size|power"),
        ("定量變項的處理（分組方式）", r"連續變項|類別|分組|categor|continuous"),
        ("統計方法（含干擾控制）", r"統計|回歸|regression|statistic|調整|adjust"),
        ("次群組與交互作用分析", r"次群組|分層|交互作用|subgroup|interaction|stratif"),
        ("缺失資料的處理", r"缺失|缺漏|missing|imputation"),
        ("敏感度分析", r"敏感度分析|sensitivity analys"),
    ]),
    "STARD": ("STARD（診斷準確性研究）", [
        ("待評估之檢測與參考標準（reference standard）", r"參考標準|標準答案|金標準|reference standard|ground truth"),
        ("研究對象選取與收案方式（連續或方便取樣）", r"連續收案|隨機抽|選取|consecutive|convenience|sampl"),
        ("判讀者對其他結果是否盲性", r"盲|blind"),
        ("陽性判定閾值（事先或事後訂定）", r"閾值|cut-?off|threshold"),
        ("準確性指標（敏感度、特異度、AUC）與信賴區間", r"敏感度|特異度|準確率|AUC|sensitivity|specificity|accuracy|信賴區間|confidence interval"),
        ("不確定或缺失結果的處理", r"不確定|缺失|indeterminate|missing"),
        ("樣本數估算", r"樣本數|sample size"),
        ("變異來源分析（次群組）", r"次群組|subgroup|變異"),
    ]),
    "CLAIM": ("CLAIM（醫學影像人工智慧）", [
        ("臨床問題與 AI 的角色", r"臨床(?:問題|任務|情境)|clinical (?:task|question)|use case"),
        ("資料來源、期間與收集方式（回溯/前瞻）", r"資料來源|資料期間|回溯|前瞻|data source|retrospective"),
        ("納入／排除條件", r"納入條件|排除條件|inclusion|exclusion"),
        ("資料前處理與去識別化", r"前處理|去識別|preprocess|de-?identif|anonymi"),
        ("參考標準（ground truth）的定義與標註者資格", r"標準答案|參考標準|標註|ground truth|reference standard|annotat"),
        ("資料切分（訓練/驗證/測試）且避免洩漏", r"訓練|驗證|測試|train|validation|test set|leak"),
        ("模型說明（架構、版本、參數）", r"模型版本|參數|temperature|架構|model (?:version|architecture)|parameter"),
        ("評估指標與統計方法", r"準確率|F1|AUC|指標|metric|統計"),
        ("外部驗證或跨院測試", r"外部驗證|跨院|external (?:validation|test)"),
        ("失敗案例或錯誤分析", r"錯誤分析|失敗|error analys|failure"),
        ("程式碼、模型或資料的可取得性", r"程式碼|開源|GitHub|code availab|可取得"),
    ]),
    "TRIPOD+AI": ("TRIPOD+AI（預測模型，含機器學習）", [
        ("預測的結果與預測時間點", r"預測(?:目標|結果)|outcome|predict"),
        ("預測因子的定義與取得時間", r"預測因子|特徵|predictor|feature"),
        ("資料來源、期間與場域", r"資料來源|資料期間|setting|data source"),
        ("樣本數或事件數之合理性", r"樣本數|事件數|sample size|events per"),
        ("缺失資料處理", r"缺失|missing|imputation"),
        ("模型建構方法與超參數調整", r"超參數|模型建構|hyperparameter|tuning|model develop"),
        ("內部／外部驗證", r"內部驗證|外部驗證|cross-?validation|bootstrap|external validation"),
        ("效能指標（區辨、校準）", r"校準|區辨|AUC|calibration|discrimination"),
        ("公平性與次族群表現", r"公平|次族群|fairness|subgroup"),
        ("模型可取得性與使用說明", r"程式碼|可取得|availab|GitHub"),
    ]),
    "TRIPOD-LLM": ("TRIPOD-LLM（大型語言模型研究）", [
        ("使用的 LLM 名稱、版本與取得日期", r"模型名稱|版本|GPT|Gemini|Claude|Llama|Qwen|Gemma|model version"),
        ("部署方式（本地或雲端 API）與資料傳輸", r"本地部署|地端|雲端|API|on-?premise|local"),
        ("提示詞（prompt）設計與完整內容", r"提示詞|prompt"),
        ("生成參數（temperature 等）與重複次數", r"temperature|top-?p|重複(?:查詢|次數)|random seed|種子"),
        ("任務與輸入資料的說明", r"輸入|任務|input|task"),
        ("參考標準與人工評估方式", r"標準答案|參考標準|人工評估|ground truth|reference standard"),
        ("評估指標", r"準確率|F1|一致性|指標|metric|accuracy"),
        ("輸出不穩定性與一致性評估", r"一致性|穩定|consistency|variab|reproduc"),
        ("資料洩漏與訓練資料汙染的處理", r"洩漏|汙染|污染|contamination|leak"),
        ("隱私與去識別化（輸入模型前）", r"去識別|隱私|de-?identif|privacy"),
        ("安全性風險（幻覺、提示注入）", r"幻覺|提示注入|prompt injection|hallucinat|安全"),
        ("限制與適用範圍", r"限制|limitation|適用範圍"),
    ]),
}


def choose(config, text):
    """Guidelines for this study: config `guidelines`, else from design and content."""
    chosen = config.get("guidelines")
    if isinstance(chosen, list) and chosen:
        return [g for g in chosen if g in GUIDELINES]
    s = config["study"]
    trial = s["type"] == "clinical_trial" or s.get("design") in ("rct", "single_arm")
    out = ["SPIRIT" if trial else "STROBE"]
    if re.search(r"大型語言模型|LLM|GPT|生成式", text, re.I):
        out.append("TRIPOD-LLM")
    imaging = re.search(r"\b(?:MRI|CT|PET)\b|X光|影像|超音波", text) or re.search(r"radiolog|imaging", text, re.I)
    ai = re.search(r"\bAI\b|人工智慧|深度學習|機器學習|神經網路|LLM|大型語言模型", text)
    if imaging and ai:
        out.append("CLAIM")
    if re.search(r"預測模型|prediction model|風險預測", text, re.I):
        out.append("TRIPOD+AI")
    if re.search(r"敏感度|特異度|sensitivity|specificity|診斷準確", text, re.I):
        out.append("STARD")
    return out


def run(config):
    text = study_text.protocol_text(config)
    source = "計畫書"
    if not text:
        text, source = study_text.proposal_text(config), "中文計畫摘要（無計畫書）"
    results = []
    for name in choose(config, text + study_text.proposal_text(config)):
        title, items = GUIDELINES[name]
        rows = [(item, bool(re.search(rx, text, re.I))) for item, rx in items]
        results.append((name, title, rows))
    return source, results


def report(config, source, results):
    lines = ["# 研究報告指引檢核", "", f"> 計畫：{config['study']['title_zh']}", f"> 比對來源：{source}",
             "> 依關鍵字判斷是否提及；■ 不代表寫得充分，□ 是建議補充的項目。指引條目為規劃用摘要，請以官方清單為準。", ""]
    for _name, title, rows in results:
        covered = sum(ok for _, ok in rows)
        lines += [f"## {title}：{covered}/{len(rows)}", ""]
        lines += [f"- {'■' if ok else '□'} {item}" for item, ok in rows]
        lines.append("")
    return "\n".join(lines)


def main(config_path="config.toml", output_dir="output"):
    from rec_helper.config import ConfigError, load_config
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    source, results = run(config)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "guidelines_report.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report(config, source, results))
    summary = "、".join(f"{name} {sum(ok for _, ok in rows)}/{len(rows)}" for name, _, rows in results)
    print(f"Guidelines ({source}): {summary} → {path}")
    for name, _, rows in results:
        for item, ok in rows:
            if not ok:
                print(f"  □ {name}：{item}")
    return 0
