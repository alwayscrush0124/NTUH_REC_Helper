"""`rech` CLI and installed-package behaviour: everything runs from a study folder, not the repo."""
import os
import sys

import pytest

from rec_helper import cli, institution
from tests.test_institution import make_blank

EXAMPLE = "ntuh-chart-review"
BLANKS = os.path.abspath("templates")
needs_blanks = pytest.mark.skipif(not os.path.isdir(os.path.join(BLANKS, "ntuh")),
                                  reason="NTUH blanks not downloaded (rech templates)")


@pytest.fixture
def study(tmp_path, monkeypatch):
    """An empty study folder as the working directory, with no institution forced."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(institution.ENV_VAR, raising=False)
    monkeypatch.delenv(institution.TEMPLATES_ENV, raising=False)
    monkeypatch.delenv("PHASE", raising=False)
    yield tmp_path
    os.environ.pop(institution.ENV_VAR, None)      # activate() pins the institution for the process


def test_init_lists_and_copies_examples(study, capsys):
    assert cli.main(["init"]) == 0
    assert EXAMPLE in capsys.readouterr().out

    assert cli.main(["init", EXAMPLE, "--no-skill"]) == 0
    for f in ("config.toml", "cv.toml", "中文計畫摘要.md", "線上填寫.md", "附件填寫.md"):
        assert (study / f).is_file(), f
    assert "templates/" in (study / ".gitignore").read_text()
    # never clobbers a study in progress
    assert cli.main(["init", EXAMPLE, "--no-skill"]) == 1
    assert cli.main(["init", "no-such-example"]) == 2


def test_init_installs_skill(study):
    assert cli.main(["init", EXAMPLE]) == 0
    assert (study / ".claude" / "skills" / "rec" / "SKILL.md").is_file()


def test_online_and_phase_shortcut(study):
    cli.main(["init", EXAMPLE, "--no-skill"])
    assert cli.main(["online"]) == 0
    assert any(f.startswith("01_新案申請書") for f in os.listdir(study / "output" / "online"))

    # `rech closure` runs the closure phase without editing config.toml
    before = (study / "config.toml").read_text(encoding="utf-8")
    args = cli.build_parser().parse_args(["all", "--phase", "closure"])
    assert args.phase == "closure"
    assert cli.main(["online", "--phase", "closure"]) == 0
    assert (study / "config.toml").read_text(encoding="utf-8") == before
    assert any("結案" in f for f in os.listdir(study / "output" / "online"))


@needs_blanks
def test_generate_with_shared_blanks(study, monkeypatch):
    monkeypatch.setenv(institution.TEMPLATES_ENV, BLANKS)
    cli.main(["init", EXAMPLE, "--no-skill"])
    assert cli.main(["generate"]) == 0
    assert any(f.endswith(".docx") for f in os.listdir(study / "output"))
    assert (study / "checklist.md").is_file()


def test_phase_shortcut_rewrites_argv(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_all", lambda args: seen.update(vars(args)) or 0)
    assert cli.main(["closure", "-o", "out"]) == 0
    assert seen["phase"] == "closure" and seen["output"] == "out"


def test_dir_option_and_set_phase(study, tmp_path_factory):
    other = tmp_path_factory.mktemp("other")
    assert cli.main(["-C", str(other), "init", EXAMPLE, "--no-skill"]) == 0
    assert cli.main(["set-phase", "closure"]) == 0  # cwd is now `other`
    assert 'phase = "closure"' in (other / "config.toml").read_text(encoding="utf-8")


def test_dashboard_and_check(study, capsys):
    cli.main(["init", EXAMPLE, "--no-skill"])
    capsys.readouterr()
    assert cli.main(["dashboard"]) == 0
    assert "NTUH Submission Dashboard" in capsys.readouterr().out
    assert cli.main(["check", "--shell"]) == 0
    assert "PHASE=new" in capsys.readouterr().out


def test_attachments_lists_questions(study, capsys):
    cli.main(["init", EXAMPLE, "--no-skill"])
    capsys.readouterr()
    assert cli.main(["attachments"]) == 0
    assert "沒有逐題填寫的附件" in capsys.readouterr().out


def test_bundled_pack_is_found_outside_the_repo(study, capsys):
    prof = institution.load("ntuh")
    assert prof.source in ("installed", "bundled")
    assert os.path.isfile(os.path.join(prof.dir, "profile.toml"))
    # blanks are looked up in the study folder, not inside the package
    assert prof.template_dir == os.path.join(str(study), "templates", "ntuh")
    assert cli.main(["institutions"]) == 0
    assert "ntuh" in capsys.readouterr().out


def test_shared_template_cache(study, monkeypatch, tmp_path_factory):
    shared = tmp_path_factory.mktemp("blanks")
    monkeypatch.setenv(institution.TEMPLATES_ENV, str(shared))
    assert institution.load("ntuh").template_dir == os.path.join(str(shared), "ntuh")


def test_local_pack_from_onboard_generates(study, monkeypatch):
    """onboard → institutions/<id>/ in the study folder → selectable and importable."""
    tpl = study / "templates" / "demo"
    tpl.mkdir(parents=True)
    make_blank(tpl / "IRB-F1 新案申請書.docx")
    assert cli.main(["onboard", "demo"]) == 0
    assert institution.available()["demo"][1] == "local"

    cli.main(["init", EXAMPLE, "--no-skill"])
    cfg = (study / "config.toml").read_text(encoding="utf-8")
    (study / "config.toml").write_text(cfg.replace('institution = "ntuh"', 'institution = "demo"'),
                                       encoding="utf-8")
    monkeypatch.setattr(sys, "path", list(sys.path))
    for mod in [m for m in sys.modules if m == "institutions" or m.startswith("institutions.")]:
        monkeypatch.delitem(sys.modules, mod)
    assert cli.main(["generate"]) == 0
    assert (study / "output").is_dir() and os.listdir(study / "output")


def test_local_pack_overrides_bundled(study):
    local = study / "institutions" / "ntuh"
    local.mkdir(parents=True)
    (local / "profile.toml").write_text(
        'id = "ntuh"\nname = "本地測試"\nforms_module = "institutions.ntuh.forms"\n'
        '[page]\nwidth = 1\nheight = 1\n[font]\nname = "標楷體"\n', encoding="utf-8")
    prof = institution.load("ntuh")
    assert prof.source == "local" and prof.name == "本地測試"


def test_doctor_runs(study, capsys):
    cli.main(["init", EXAMPLE, "--no-skill"])
    capsys.readouterr()
    cli.main(["doctor"])
    out = capsys.readouterr().out
    assert "LibreOffice" in out and "institution" in out and "config.toml OK" in out
