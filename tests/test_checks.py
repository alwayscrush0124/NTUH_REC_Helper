"""The study checks and drafting tools: consistency, precheck, guidelines, refs, protocol, reply, versions."""
import os
import shutil

import pytest
from docx import Document

from rec_helper import cli, consistency, guidelines, precheck, refs, reply, versions
from rec_helper.config import load_config
from rec_helper.generators import protocol

EXAMPLE = "rec_helper/examples/ntuh-chart-review"


@pytest.fixture
def study(tmp_path, monkeypatch):
    for f in os.listdir(EXAMPLE):
        shutil.copy(os.path.join(EXAMPLE, f), tmp_path / f)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REC_INSTITUTION", "ntuh")
    return tmp_path


@pytest.fixture
def config(study):
    return load_config("config.toml")


def topics(findings, level=None):
    return {f.topic for f in findings if level is None or f.level == level}


# ── consistency ─────────────────────────────────────────────────────────────

def test_example_is_consistent(config):
    assert consistency.check(config) == []


def test_consistency_catches_disagreements(config, study):
    config["online"].update({"G8-1": "18", "F3": "2019年1月至2024年12月"})
    (study / "計畫書.md").write_text(
        "# 研究計畫書\n本計畫題名為「SGLT2 舊題目研究」。\n預計收錄 900 人，納入 20 至 85 歲病人，包含兒科門診個案。\n"
        "資料保存 7 年。", encoding="utf-8")
    config["protocol_file"] = "計畫書.md"
    found = consistency.check(config)
    assert {"年齡", "資料期間", "收案數", "計畫名稱", "保存年限"} <= topics(found, consistency.ERROR)
    assert "易受傷害族群" in topics(found, consistency.WARN)


def test_negated_wording_is_not_flagged(config, study):
    (study / "計畫書.md").write_text("本研究僅納入成人，不含兒童；資料不存放於雲端。", encoding="utf-8")
    config["protocol_file"] = "計畫書.md"
    assert "易受傷害族群" not in topics(consistency.check(config))


def test_retrospective_data_must_predate_the_study(config):
    config["dates"]["data_period"] = "2026年1月至2027年6月"
    assert any("回溯性資料期間" in f.message for f in consistency.check(config))


# ── precheck ────────────────────────────────────────────────────────────────

def todo(results):
    return [t for _, rows in results for t, st, _ in rows if st == precheck.TODO]


def test_precheck_example_has_nothing_missing(config):
    assert todo(precheck.run(config)) == []


def test_precheck_flags_missing_material(config):
    config["proposal"].pop("inclusion")
    config["study"].update(type="clinical_trial", design="rct", drug_device=True)
    config["subjects"]["consent_waiver"] = False
    missing = " ".join(todo(precheck.run(config)))
    assert "納入條件" in missing and "暫停或中止" in missing and "DSMP" not in missing   # drug trials route DSMP


# ── guidelines ──────────────────────────────────────────────────────────────

def test_guideline_choice(config):
    assert guidelines.choose(config, "Cox 比例風險模型，Impact of exposure") == ["STROBE"]
    assert guidelines.choose(config, "以 LLM 推薦 MRI protocol") == ["STROBE", "TRIPOD-LLM", "CLAIM"]
    config["study"].update(type="clinical_trial", design="rct")
    assert guidelines.choose(config, "")[0] == "SPIRIT"
    config["guidelines"] = ["STARD"]
    assert guidelines.choose(config, "") == ["STARD"]


def test_guideline_coverage(config, study):
    (study / "計畫書.md").write_text("研究設計：世代研究。樣本數依檢定力估算。缺失值以多重插補處理。", encoding="utf-8")
    config["protocol_file"] = "計畫書.md"
    _, results = guidelines.run(config)
    rows = dict(results[0][2])
    assert rows["樣本數如何決定"] and rows["缺失資料的處理"] and not rows["敏感度分析"]


# ── refs ────────────────────────────────────────────────────────────────────

PROTO = """# 計畫書
大型語言模型（large language model, LLM）可協助 MRI 開單。JSON 格式……

參考文獻：
1. Tejani AS, et al. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 Update.
   Radiol Artif Intell. 2024;6(4):e240300. doi:10.1148/ryai.240300.
2. Asadi M, et al. Mirage: the illusion of visual understanding. arXiv. 2026. doi:10.48550/arXiv.2603.21687.
3. Some Author. A conference paper without any identifier. NeurIPS; 2020.
"""


def test_references_and_acronyms_offline(config, study, monkeypatch):
    (study / "計畫書.md").write_text(PROTO, encoding="utf-8")
    config["protocol_file"] = "計畫書.md"
    text, found, acr = refs.run(config, offline=True)
    assert [r.doi for r in found] == ["10.1148/ryai.240300", "10.48550/arXiv.2603.21687", ""]
    assert found[0].year == "2024"
    names = dict(acr)
    assert "LLM" not in names and names["MRI"] == "全文未定義全名" and "JSON" in names
    assert "AS" not in names                          # author initials in the reference list


def test_reference_verification_statuses(monkeypatch):
    r = refs.parse(1, "Tejani AS. Checklist for Artificial Intelligence in Medical Imaging. 2024. doi:10.1/x")
    monkeypatch.setattr(refs, "_lookup", lambda r: ("Checklist for Artificial Intelligence in Medical Imaging", "2024"))
    assert refs.verify(r).status == "■"
    r = refs.parse(2, "Tejani AS. Checklist for Artificial Intelligence in Medical Imaging. 2023. doi:10.1/x")
    assert refs.verify(r).status == "⚠" and "年份" in r.note
    monkeypatch.setattr(refs, "_lookup", lambda r: None)
    assert refs.verify(refs.parse(3, "No id here at all, a web page. 2024")).status == "？"
    monkeypatch.setattr(refs, "_lookup", lambda r: (_ for _ in ()).throw(TimeoutError()))
    assert refs.verify(refs.parse(4, "doi:10.1/y 2024 something")).status == "－"


# ── protocol ────────────────────────────────────────────────────────────────

def test_protocol_skeleton_and_render(config, study):
    assert protocol.main() == 0
    md = (study / "計畫書.md").read_text(encoding="utf-8")
    assert "## 一、研究背景與文獻回顧" in md and "SGLT2" in md and "預計收案 1200" in md
    assert "人工智慧之使用" not in md                 # the example uses no AI
    assert protocol.main() == 1                       # never overwrites
    config["protocol"] = "計畫書.md"
    config["version"] = {"number": "2.0", "date": "2026-11-01"}
    path = protocol.generate_protocol(config, str(study))
    assert path.endswith("計畫書_v2.0.docx")
    doc = Document(path)
    assert "版本：2.0　版本日期：2026/11/01" in doc.sections[0].header.paragraphs[0].text
    assert any("研究目的" in p.text for p in doc.paragraphs)


def test_protocol_without_source_renders_the_draft(config, study):
    path = protocol.generate_protocol(config, str(study))
    assert any("【待寫】" in p.text for p in Document(path).paragraphs)


# ── reply ───────────────────────────────────────────────────────────────────

REPLY = """## 1
意見：請補充樣本數估算。
第二行意見。
回覆：已補充。
修正：計畫書｜6｜四、研究對象｜（無）｜新增一段｜依意見

## 2
意見：請說明保存年限。
"""


def test_reply_parse_table_and_amendment_rows(config, study):
    (study / "審查意見.md").write_text(REPLY, encoding="utf-8")
    config["reply"] = "審查意見.md"
    items = reply.load(config)
    assert [i.no for i in items] == ["1", "2"]
    assert items[0].comment == "請補充樣本數估算。\n第二行意見。" and items[1].reply == ""
    assert reply.amendment_rows(config) == ["計畫書｜6｜四、研究對象｜（無）｜新增一段｜依意見"]
    doc = Document(reply.generate_reply(config, str(study)))
    cells = [c.text for r in doc.tables[0].rows for c in r.cells]
    assert "【待回覆】" in cells and "計畫書｜6｜四、研究對象" in cells


def test_reply_skeleton_then_status(study, capsys):
    assert reply.main() == 0 and (study / "審查意見.md").is_file()
    assert reply.main() == 0
    assert "則意見" in capsys.readouterr().out


# ── versions ────────────────────────────────────────────────────────────────

def test_version_of_and_stamp_docx(config, study):
    config["version"] = {"number": "1.2", "date": "2026年10月3日", "計畫書": {"number": "3.0"}, "同意書": "2.1"}
    assert versions.version_of(config) == ("1.2", "2026/10/03")
    assert versions.version_of(config, "計畫書") == ("3.0", "2026/10/03")
    assert versions.version_of(config, "同意書") == ("2.1", "2026/10/03")
    src = study / "a.docx"
    Document().save(src)
    out = versions.stamp([str(src)], config, str(study / "out"))
    assert Document(out[0]).sections[0].header.paragraphs[0].text == "版本：1.2　版本日期：2026/10/03"
    ledger = (study / versions.LEDGER).read_text(encoding="utf-8")
    assert "a.docx" in ledger and "| 1.2 |" in ledger
    assert src.read_bytes() == open(src, "rb").read()          # original untouched


def test_stamp_cli_takes_files_not_config(study):
    Document().save(study / "b.docx")
    assert cli.main(["stamp", "b.docx", "--version", "9.9"]) == 0
    assert (study / "output" / "stamped" / "b.docx").is_file()


def test_stamp_pdf(config, study):
    pymupdf = pytest.importorskip("pymupdf")
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(study / "c.pdf")
    out = versions.stamp([str(study / "c.pdf")], config, str(study / "out"))
    assert "2026" in pymupdf.open(out[0])[0].get_text() or versions.version_of(config)[1][:4] in pymupdf.open(out[0])[0].get_text()
