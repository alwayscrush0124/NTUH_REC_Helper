"""Form routing (form_selector.py) with the NTUH pack."""
import pytest

from rec_helper.config import load_config
from rec_helper.form_selector import FORM_REGISTRY, PHASE_FORMS, get_generator, select_forms

EXAMPLE = "rec_helper/examples/ntuh-chart-review/config.toml"


@pytest.fixture
def retro_config(monkeypatch):
    monkeypatch.setenv("REC_INSTITUTION", "ntuh")
    return load_config(EXAMPLE)


def ids(config):
    return [fid for fid, _ in select_forms(config)]


def test_chart_review_with_waiver(retro_config):
    assert ids(retro_config) == ["PROPOSAL", "AF001", "MEDREC", "AF164"]


def test_exempt_needs_only_the_summary(retro_config):
    retro_config["study"]["review_type"] = "exempt"
    assert ids(retro_config) == ["PROPOSAL"]


def test_signed_consent_trial_routes_consent_and_dsmp(retro_config):
    retro_config["study"].update(type="clinical_trial", design="rct", drug_device=True)
    retro_config["subjects"]["consent_waiver"] = False
    forms = ids(retro_config)
    assert "CONSENT" in forms and "DSMP" in forms
    assert "MEDREC" not in forms


def test_branch_consent_from_pi_department(retro_config):
    retro_config["study"].update(type="prospective", design="cohort")
    retro_config["subjects"]["consent_waiver"] = False
    retro_config["pi"]["dept"] = "新竹臺大分院內科部／主治醫師"
    assert "INTERVIEW" in ids(retro_config)
    retro_config["study"].update(type="clinical_trial", design="rct")
    assert "CONSENT_HCH" in ids(retro_config) and "CONSENT" not in ids(retro_config)


def test_web_answers_route_attachments(retro_config):
    retro_config["online"] = {"G33": "是", "G21-1": ["孕婦"]}
    retro_config["study"].update(type="prospective")
    retro_config["subjects"]["vulnerable_population"] = True
    retro_config["subjects"]["consent_waiver"] = False
    forms = ids(retro_config)
    assert "AF143" in forms and "AF127" in forms


def test_extra_forms(retro_config):
    retro_config["extra_forms"] = ["DELEGATION"]
    assert ids(retro_config)[-1] == "DELEGATION"


def test_unknown_phase_raises(retro_config):
    retro_config["phase"] = "unknown"
    with pytest.raises(ValueError, match="Unknown phase"):
        select_forms(retro_config)


def test_generator_lookup(retro_config):
    assert get_generator("MEDREC") == ("rec_helper.institutions.ntuh.attachments", "generate_medrec")
    assert get_generator("SF999") is None


def test_form_registry_completeness(retro_config):
    for phase, rules in PHASE_FORMS.items():
        for fid in rules["base"] + [f for _, forms in rules["conditions"] for f in forms]:
            assert fid in FORM_REGISTRY, f"{fid} in {phase} not in registry"
