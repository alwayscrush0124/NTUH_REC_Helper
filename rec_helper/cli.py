"""`rech` — the REC Helper command line.

Run it in a study folder (config.toml + cv.toml + 中文計畫摘要.md):

    rech init ntuh-chart-review    # start from the bundled example (+ Claude Code skill)
    rech check                     # resolve @references + validate config.toml
    rech templates                 # once: cache the institution's blank forms
    rech all                       # generate + web-form sheets + PDF + layout gate + dashboard
    rech online                    # copy-paste sheets for web-system forms (e.g. NTUH)
    rech attachments --skeleton    # questions of the row-filled attachments → 附件填寫.md
    rech closure                   # = rech all --phase closure (config.toml untouched)
    rech set-phase closure         # persist the phase in config.toml (keeps comments)
    rech onboard myhosp            # new institution: blanks in templates/myhosp/ → draft pack
    rech doctor                    # check LibreOffice, poppler, fonts, config, blanks

`--phase` defaults to $PHASE, so `PHASE=closure rech all` works too.
"""
import argparse
import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

from rec_helper import institution
from rec_helper.form_selector import PHASE_NAMES

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(PACKAGE_DIR, "examples")
SKILL_DEST = os.path.join(".claude", "skills", "rec")
STUDY_GITIGNORE = """\
# REC Helper: generated files and the institution's blank forms
output/
checklist.md
templates/
"""


def package_version():
    try:
        return version("rec-helper")
    except PackageNotFoundError:
        return "0+unknown"


def skill_source():
    """The bundled Claude Code skill: inside the wheel, or .claude/skills/rec in a source checkout."""
    for path in (os.path.join(PACKAGE_DIR, "skill"),
                 os.path.join(os.path.dirname(PACKAGE_DIR), ".claude", "skills", "rec")):
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            return path
    return None


def examples():
    return sorted(d for d in os.listdir(EXAMPLES_DIR) if os.path.isfile(os.path.join(EXAMPLES_DIR, d, "config.toml")))


# ── commands ────────────────────────────────────────────────────────────────

def cmd_init(args):
    if not args.example:
        print("Bundled examples (rech init <name>):")
        for name in examples():
            print(f"  {name}")
        return 0
    src = os.path.join(EXAMPLES_DIR, args.example)
    if args.example not in examples():
        print(f"✗ no example '{args.example}' (have: {', '.join(examples())})")
        return 2
    files = sorted(os.listdir(src))
    clashes = [f for f in files if os.path.exists(f)]
    if clashes and not args.force:
        print(f"✗ {', '.join(clashes)} already exist here (--force to overwrite)")
        return 1
    for f in files:
        shutil.copyfile(os.path.join(src, f), f)
        print(f"  ■ {f}")
    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w", encoding="utf-8") as fh:
            fh.write(STUDY_GITIGNORE)
        print("  ■ .gitignore")
    if not args.no_skill:
        install_skill(force=False)
    from rec_helper import config
    return config.main(["config.toml"])


def install_skill(force=False, dest=SKILL_DEST):
    src = skill_source()
    if src is None:
        print("⚠ Claude Code skill not bundled with this install — skipped")
        return 1
    if os.path.exists(dest):
        if os.path.samefile(src, dest) or not force:
            print(f"  · keep {dest}/ (exists; `rech skill --force` to update)")
            return 0
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"  ■ {dest}/ (Claude Code skill — open this folder in Claude Code and ask it to fill the forms)")
    return 0


def cmd_skill(args):
    return install_skill(force=args.force)


def cmd_check(args):
    from rec_helper import config
    argv = [args.config] + (["--phase", args.phase] if args.phase else [])
    argv += ["--json"] if args.json else ["--shell"] if args.shell else []
    return config.main(argv)


def cmd_generate(args):
    from rec_helper import generate_all
    return generate_all.main(args.config, args.output, args.phase, args.verbose)


def cmd_online(args):
    from rec_helper import online_forms
    return online_forms.main(args.config, args.output, args.phase, skeleton=getattr(args, "skeleton", False))


def cmd_attachments(args):
    from rec_helper import form_rows
    return form_rows.main(args.config, args.phase, skeleton=args.skeleton, forms=args.form or ())


def cmd_pdf(args):
    from rec_helper import convert
    return convert.main(args.output)


def cmd_templates(args):
    from rec_helper import fetch_templates
    _activate(args.config)
    return fetch_templates.main(force=args.force) or 0


def cmd_onboard(args):
    from rec_helper import onboard
    return onboard.main(args.id, force=args.force)


def cmd_validate(args):
    from rec_helper import validate_layout
    _activate(args.config)
    return validate_layout.main(args.output, render=not args.no_render, strict=args.strict)


def cmd_dashboard(args):
    from rec_helper import dashboard
    return dashboard.main(args.config, args.output, args.phase)


def cmd_consistency(args):
    from rec_helper import consistency
    return consistency.main(args.config, args.output, strict=getattr(args, "strict", False))


def cmd_precheck(args):
    from rec_helper import precheck
    return precheck.main(args.config, args.output)


def cmd_guidelines(args):
    from rec_helper import guidelines
    return guidelines.main(args.config, args.output)


def cmd_refs(args):
    from rec_helper import refs
    return refs.main(args.config, args.output, offline=args.offline)


def cmd_protocol(args):
    from rec_helper.generators import protocol
    return protocol.main(args.config)


def cmd_reply(args):
    from rec_helper import reply
    return reply.main(args.config)


def cmd_stamp(args):
    from rec_helper import versions
    return versions.main(args.files, args.config, args.output, args.version, args.date, args.doc)


def cmd_versions(args):
    from rec_helper import versions
    if args.record:
        return versions.main([], args.config, args.output, record_outputs=True)
    if not os.path.exists(versions.LEDGER):
        print(f"(no {versions.LEDGER} yet — `rech stamp FILE…` or `rech versions --record` starts it)")
        return 0
    with open(versions.LEDGER, encoding="utf-8") as fh:
        print(fh.read())
    return 0


def cmd_all(args):
    args.no_render = args.strict = False
    for step in (cmd_generate, cmd_online, cmd_pdf, cmd_validate, cmd_consistency, cmd_precheck, cmd_guidelines,
                 cmd_dashboard):
        code = step(args)
        if code:
            return code
    return 0


def cmd_set_phase(args):
    from rec_helper.set_phase import set_phase
    try:
        set_phase(args.config, args.phase)
    except (OSError, ValueError) as e:
        print(f"✗ {e}")
        return 1
    print(f"■ phase → {args.phase}")
    return 0


def cmd_institutions(args):
    active = institution.resolve_id()
    print("Institution packs (first match wins: local → installed → bundled):")
    for inst_id, (pack_dir, source) in sorted(institution.available().items()):
        mark = "■" if inst_id == active else " "
        print(f"  {mark} {inst_id:<12} {source:<9} {pack_dir}")
    return 0


def cmd_doctor(args):
    from rec_helper.config import ConfigError, load_config
    from rec_helper.convert import find_soffice

    problems = warnings = 0

    def report(ok, label, detail, required=True):
        nonlocal problems, warnings
        mark = "■" if ok else ("✗" if required else "⚠")
        problems += not ok and required
        warnings += not ok and not required
        print(f"  {mark} {label:<14} {detail}")

    print(f"rec-helper {package_version()} · Python {sys.version.split()[0]} · {sys.platform}")
    soffice = find_soffice()
    report(bool(soffice), "LibreOffice", soffice or "missing — needed for PDF + layout gate "
           "(brew install --cask libreoffice / winget install TheDocumentFoundation.LibreOffice / apt install libreoffice)")
    pdftoppm = shutil.which("pdftoppm")
    report(bool(pdftoppm), "poppler", pdftoppm or "missing — PNG previews only (brew install poppler / apt install poppler-utils)",
           required=False)

    config = None
    if os.path.isfile(args.config):
        try:
            config = load_config(args.config)
            report(True, "config", f"{args.config} OK (phase {config['phase']})")
        except ConfigError as e:
            report(False, "config", str(e).splitlines()[0])
    else:
        report(False, "config", f"no {args.config} here — `rech init <example>` to start", required=False)

    try:
        prof = institution.load(institution.resolve_id(config))
    except FileNotFoundError as e:
        report(False, "institution", str(e))
        return 1
    report(True, "institution", f"{prof.id} ({prof.source}: {prof.dir})")
    cached = os.path.isfile(os.path.join(prof.template_dir, "index.json"))
    report(cached, "blank forms", os.path.relpath(prof.template_dir) if cached else
           f"not cached in {os.path.relpath(prof.template_dir)}/ — run `rech templates`", required=False)

    font = prof.font["name"]
    if shutil.which("fc-match"):
        names = sorted(prof.font_aliases)
        env = None
        if sys.platform.startswith("linux"):
            from rec_helper.convert import soffice_env
            env = soffice_env()
        matched = subprocess.run(["fc-match", "-f", "%{family}", font], capture_output=True, text=True,
                                 env=env).stdout.strip()
        exact = any(n in matched for n in names) or "Kai" in matched
        report(exact, "form font", f"{font} → {matched or '?'}" + ("" if exact else
               " (PDF renders will substitute; install the font or fonts-arphic-ukai on Linux)"), required=False)
    else:
        report(True, "form font", f"{font} (fc-match unavailable; check Word shows {font})")
    if problems:
        print(f"\n{problems} problem(s) to fix before `rech all`.")
    else:
        print("\nAll set." + (f" ({warnings} warning(s) above are optional.)" if warnings else ""))
    return 1 if problems else 0


def _activate(config_path):
    """Pick the institution named in the study's config (for commands that don't load it themselves)."""
    from rec_helper.config import ConfigError, load_config
    if os.path.isfile(config_path):
        try:
            institution.activate(load_config(config_path))
        except ConfigError:
            pass


# ── parser ──────────────────────────────────────────────────────────────────

def build_parser():
    env_phase = os.environ.get("PHASE") or None
    ap = argparse.ArgumentParser(prog="rech", description="REC Helper: study facts → official IRB forms → PDF.",
                                 epilog="Phase shortcut: `rech <phase>` = `rech all --phase <phase>` "
                                        f"({', '.join(PHASE_NAMES)}).")
    ap.add_argument("-V", "--version", action="version", version=f"rec-helper {package_version()}")
    ap.add_argument("-C", "--dir", metavar="DIR", help="run in this study folder instead of the current one")
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    def command(name, func, help, *, config=False, output=False, phase=False):
        p = sub.add_parser(name, help=help, description=help)
        p.set_defaults(func=func)
        if config:
            p.add_argument("config", nargs="?", default="config.toml", help="study config (default: config.toml)")
        if output:
            p.add_argument("-o", "--output", default="output", help="output folder (default: output)")
        if phase:
            p.add_argument("--phase", choices=list(PHASE_NAMES), default=env_phase,
                           help="override `phase` for this run without editing config.toml (default: $PHASE)")
        return p

    p = command("init", cmd_init, "start a study here from a bundled example (no name: list them)")
    p.add_argument("example", nargs="?")
    p.add_argument("--force", action="store_true", help="overwrite existing files")
    p.add_argument("--no-skill", action="store_true", help="don't install the Claude Code skill")

    p = command("check", cmd_check, "resolve @references in config.toml and validate it", config=True, phase=True)
    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="print the resolved config")
    fmt.add_argument("--shell", action="store_true", help="print shell variables")

    p = command("generate", cmd_generate, "generate the phase's DOCX forms", config=True, output=True, phase=True)
    p.add_argument("-v", "--verbose", action="store_true", help="print tracebacks for failed forms")

    p = command("online", cmd_online, "copy-paste sheets for forms filled in the IRB's web system",
                config=True, output=True, phase=True)
    p.add_argument("--skeleton", action="store_true", help="write 線上填寫.md listing every field still to answer")

    p = command("attachments", cmd_attachments,
                "list the questions of the study's question-per-row attachments (同意書, DSMP, …)",
                config=True, phase=True)
    p.add_argument("--skeleton", action="store_true", help="append the unanswered questions to 附件填寫.md")
    p.add_argument("--form", action="append", metavar="ID", help="also include this form (repeatable)")

    p = command("consistency", cmd_consistency, "cross-document consistency: case counts, ages, dates, wording",
                config=True, output=True)
    p.add_argument("--strict", action="store_true", help="exit 1 when anything disagrees")
    command("precheck", cmd_precheck, "pre-review against the committee's reviewer checklist (NTUH AF-063)",
            config=True, output=True)
    command("guidelines", cmd_guidelines, "reporting-guideline coverage of the protocol (STROBE, CLAIM, TRIPOD-LLM, …)",
            config=True, output=True)
    p = command("refs", cmd_refs, "verify the protocol's references (Crossref/PubMed/arXiv) and acronyms",
                config=True, output=True)
    p.add_argument("--offline", action="store_true", help="acronyms only; don't query reference databases")
    p = command("protocol", cmd_protocol, "draft 計畫書.md from the study (then protocol = \"計畫書.md\")", config=True)
    p.add_argument("--skeleton", action="store_true", help="(default) write the draft; never overwrites")
    p = command("reply", cmd_reply, "審查意見.md: template for answering review comments, or its status", config=True)
    p.add_argument("--skeleton", action="store_true", help="(default when the file is missing) write the template")
    p = command("stamp", cmd_stamp, "stamp 版本/版本日期 on PDF/DOCX copies in output/stamped/ (+ 版本紀錄.md)",
                output=True)
    p.add_argument("files", nargs="+", help="PDF or DOCX files (originals are not modified)")
    p.add_argument("--config", default="config.toml", help="study config (default: config.toml)")
    p.add_argument("--version", help="version number (default: [version] in config.toml)")
    p.add_argument("--date", help="version date, e.g. 2026/10/14 (default: [version] date or today)")
    p.add_argument("--doc", help="document name for a per-document version in [version], e.g. 計畫書")
    p = command("versions", cmd_versions, "show 版本紀錄.md; --record adds the PDFs in output/", config=True, output=True)
    p.add_argument("--record", action="store_true", help="record output/*.pdf with their SHA-256")

    command("pdf", cmd_pdf, "convert output DOCX → PDF + PNG previews (LibreOffice)", output=True)

    p = command("templates", cmd_templates, "cache the institution's official blank forms", config=True)
    p.add_argument("--force", action="store_true", help="re-download cached blanks")

    p = command("onboard", cmd_onboard, "draft institutions/<id>/ from the blank forms in templates/<id>/")
    p.add_argument("id")
    p.add_argument("--force", action="store_true", help="overwrite an existing draft")

    p = command("validate", cmd_validate, "layout/font gate against the blank forms", config=True, output=True)
    p.add_argument("--no-render", action="store_true", help="skip the LibreOffice render checks")
    p.add_argument("--strict", action="store_true", help="fail on warnings too")

    p = command("all", cmd_all, "generate + online + pdf + validate + consistency + precheck + guidelines + dashboard",
                config=True, output=True, phase=True)
    p.add_argument("-v", "--verbose", action="store_true", help="print tracebacks for failed forms")

    command("dashboard", cmd_dashboard, "show submission status", config=True, output=True, phase=True)

    p = command("set-phase", cmd_set_phase, "persist `phase` in config.toml (keeps comments)")
    p.add_argument("phase", choices=list(PHASE_NAMES))
    p.add_argument("config", nargs="?", default="config.toml")

    command("institutions", cmd_institutions, "list institution packs and which one is active")

    p = command("skill", cmd_skill, f"install the Claude Code skill into {SKILL_DEST}/")
    p.add_argument("--force", action="store_true", help="replace an existing copy")

    command("doctor", cmd_doctor, "check LibreOffice, poppler, font, config and blank forms", config=True)
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # `rech closure …` → `rech all --phase closure …` (after any global -C DIR)
    i = 2 if argv[:1] in (["-C"], ["--dir"]) else 0
    if len(argv) > i and argv[i] in PHASE_NAMES:
        argv[i:i + 1] = ["all", "--phase", argv[i]]
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.dir:
        os.chdir(args.dir)
    if not args.command:
        ap.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
