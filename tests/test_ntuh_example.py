"""The bundled NTUH example study, end to end, in every phase the NTUH pack routes.

The NTUH attachments fill the committee's official blanks, which are downloaded
per study (`rech templates`) and never committed: the DOCX part is skipped when
templates/ntuh/ isn't there (CI). The web-form sheets need no blanks.
"""
import os
import shutil

import pytest

from rec_helper import generate_all, online_forms
from rec_helper.config import load_config
from rec_helper.form_selector import select_forms

EXAMPLE = "rec_helper/examples/ntuh-chart-review"
BLANKS = os.path.abspath("templates")


@pytest.fixture
def study(tmp_path, monkeypatch):
    for f in os.listdir(EXAMPLE):
        shutil.copy(os.path.join(EXAMPLE, f), tmp_path / f)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REC_INSTITUTION", "ntuh")
    monkeypatch.setenv("REC_TEMPLATES", BLANKS)
    return tmp_path


PHASES = ("new", "amendment", "continuing", "closure", "suspension", "sae", "deviation", "other", "import")


@pytest.mark.parametrize("phase", PHASES)
def test_online_sheets_every_phase(study, phase):
    config = load_config("config.toml", phase=phase)
    results = online_forms.generate(config, "output")
    assert results or phase == "import"            # 專案進口 is paper-only
    assert not any(w for *_, warnings in results for w in warnings)


def test_new_case_example_answers_every_web_question(study):
    results = online_forms.generate(load_config("config.toml"), "output")
    assert [form.name for form, *_ in results][:2] == ["新案申請書", "簡審範圍評核表"]
    assert {form.name: todo for form, todo, _ in results if todo} == {}


@pytest.mark.skipif(not os.path.isdir(os.path.join(BLANKS, "ntuh")), reason="NTUH blanks not downloaded (rech templates)")
@pytest.mark.parametrize("phase", PHASES)
def test_docx_every_phase(study, phase):
    code = generate_all.main("config.toml", "output", phase=phase, checklist_path=str(study / "checklist.md"))
    assert code == 0
    config = load_config("config.toml", phase=phase)
    assert len(list((study / "output").glob("*.docx"))) == len(select_forms(config))
    if phase == "new":
        from docx import Document
        medrec = Document(study / "output" / "使用病歷資料進行研究申請表.docx")
        text = "\n".join(c.text for t in medrec.tables for r in t.rows for c in r.cells)
        assert "【待填】" not in text and "王小明" in text
