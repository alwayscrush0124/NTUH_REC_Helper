"""Copy-paste sheets for web-system forms (NTUH pack)."""
import os
import re
import shutil

from rec_helper import online_forms
from rec_helper.config import load_config
from rec_helper.online_forms import C, Form, M, T, answer, fill

CONFIG = {"study": {"title_zh": "示範研究", "type": "retrospective"}, "subjects": {"planned_n": 120}}


def test_answer_sources_and_option_matching():
    assert answer(T("N", "人數", "{subjects.planned_n}"), CONFIG, {}) == ("120", "auto", "")
    assert answer(T("X", "未知"), CONFIG, {}) == ("", "todo", "")
    assert answer(T("X", "未知", optional=True), CONFIG, {})[1] == "skip"
    # 線上填寫.md wins; a unique prefix picks the option
    yn = C("G7", "競爭性收案", ("是", "否，請說明："), "是")
    assert answer(yn, CONFIG, {"G7": "否"}) == ("否，請說明：", "md", "")
    ans, _, warn = answer(yn, CONFIG, {"G7": "也許"})
    assert ans == "也許" and "不是選項" in warn
    multi = M("G1", "地點", ("醫療院所", "社區"))
    assert answer(multi, CONFIG, {"G1": ["社區", "醫療"]}) == (["社區", "醫療院所"], "md", "")


def test_hidden_fields_are_dropped():
    form = Form("表", sections=[("S", [T("a", "a", "1"), T("b", "b", "2", when=lambda c: False)])])
    filled, _ = fill(form, CONFIG, {})
    assert [f.id for f, *_ in filled[0][1]] == ["a"]


def _ntuh_study(tmp_path, monkeypatch, online_md, review_type=None):
    example = "rec_helper/examples/ntuh-chart-review"
    for f in os.listdir(example):
        shutil.copy(os.path.join(example, f), tmp_path / f)
    cfg = tmp_path / "config.toml"
    text = cfg.read_text(encoding="utf-8")
    if review_type:
        text = re.sub(r'review_type\s*=\s*"\w+"', f'review_type = "{review_type}"', text)
    cfg.write_text(text, encoding="utf-8")
    (tmp_path / "線上填寫.md").write_text(online_md, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REC_INSTITUTION", "ntuh")
    config = load_config("config.toml")
    assert config["study"]["review_type"] == (review_type or "expedited")
    return config


def test_ntuh_retrospective_sheets(tmp_path, monkeypatch):
    config = _ntuh_study(tmp_path, monkeypatch, "## A7 經費\n- 自籌\n\n## 研究領域\n腫瘤學\n")
    results = online_forms.generate(config, "output")
    names = [form.name for form, *_ in results]
    assert names == ["新案申請書", "簡審範圍評核表", "上傳文件", "計畫主持人聲明書", "審查費", "利益申報"]
    assert not any(w for *_, warnings in results for w in warnings)

    sheet = (tmp_path / "output" / "online" / "01_新案申請書.md").read_text(encoding="utf-8")
    assert "◉ 觀察性研究" in sheet                      # derived from study.type
    assert "■ 自籌(自行研究無經費補助)" in sheet         # from 線上填寫.md
    assert "■ H3. 申請免除知情同意" in sheet            # consent waiver route
    assert "2027/01/01" in sheet                      # date normalized
    assert (tmp_path / "output" / "online" / "01_新案申請書.html").exists()

    assert online_forms.write_skeleton(config, str(tmp_path / "skeleton.md")) == 0
    assert "## G2 " in (tmp_path / "skeleton.md").read_text(encoding="utf-8")


def test_ntuh_follow_up_questions_need_the_earlier_answer(tmp_path, monkeypatch):
    config = _ntuh_study(tmp_path, monkeypatch, "## F2-2\n- 使用臺大醫院病歷資料\n\n## H\n- H1\n- H3\n")
    form = next(f for f in online_forms.online_forms(config) if f.name == "新案申請書")
    filled, _ = fill(form, config, online_forms.overrides(config))
    ids = {f.id for _, rows in filled for f, *_ in rows}
    assert {"F2-2", "F2-2-2", "F4"} <= ids and "F2-2-1" not in ids    # 院區 of the picked source only
    assert {"H1-1", "H3-1"} <= ids and "H2-1" not in ids              # blocks of the routes picked
    assert not ids & {"C2", "D1", "E1-1", "I1"}                       # no drug/device/product tabs


def test_ntuh_exempt_uses_the_short_form(tmp_path, monkeypatch):
    from rec_helper.form_selector import select_forms
    config = _ntuh_study(tmp_path, monkeypatch, "## 免審11-2\n- 研究計畫屬最低風險\n", review_type="exempt")
    results = online_forms.generate(config, "output")
    assert [form.name for form, *_ in results] == ["新案免審申請書", "上傳文件", "計畫主持人聲明書", "審查費", "利益申報"]
    assert not any(w for *_, warnings in results for w in warnings)
    sheet = (tmp_path / "output" / "online" / "01_新案免審申請書.md").read_text(encoding="utf-8")
    assert "■ 研究計畫屬最低風險" in sheet
    assert [fid for fid, _ in select_forms(config)] == ["PROPOSAL"]   # no 自評表 / 病歷申請表 / 切結書


def test_pack_without_online_module_has_no_sheets(monkeypatch):
    from rec_helper.institution import current
    config = load_config("config.toml")
    monkeypatch.setitem(current().data, "online_module", None)
    assert online_forms.online_forms(config) == []
