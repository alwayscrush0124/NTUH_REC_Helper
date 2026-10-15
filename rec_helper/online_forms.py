"""Copy-paste sheets for IRB forms that are filled in a web system, not a DOCX.

Some committees (e.g. NTUH) take the application itself as web pages and only
the attachments as files. A pack declares those pages in an `online_module`
(profile.toml) exposing ONLINE_FORMS:

    ONLINE_FORMS = {"new": [Form("新案申請書", where="…", sections=[("A. …", [fields…])])]}

Each field is answered, first match wins, from:

  1. config["online"][<field id>]   — `online = "@線上填寫.md"`, one `## <id> …` per answer
  2. the field's `value`             — format string / callable over config.toml
  3. nothing                         — flagged ✎ 待填 in the sheet

Output, per form: output/online/<NN>_<name>.md and .html (one 複製 button per
answer). `rech online --skeleton` writes 線上填寫.md listing every 待填 field.

Usage: rech online [config.toml] [--output DIR] [--phase PHASE] [--skeleton]
"""
import glob
import html
import importlib
import os
import re
import sys
from dataclasses import dataclass, field

from rec_helper.config import SECTION_KEYS, ConfigError, load_config
from rec_helper.form_selector import PHASE_NAMES
from rec_helper.institution import activate
from rec_helper.template_fill import resolve

ONLINE_DIR = "online"
SKELETON = "線上填寫.md"
KINDS = ("text", "textarea", "choice", "multi")
MARKS = {"md": "●", "auto": "◆", "todo": "✎", "skip": "－"}
MARK_HELP = f"{MARKS['md']} 來自 {SKELETON}　{MARKS['auto']} 依 config 推定（請確認）　{MARKS['todo']} 待填"


@dataclass
class Field:
    id: str                      # question number as printed (A4, G29-1) or the label itself
    label: str
    value: object = None         # format string / callable(config) / literal; list for multi
    kind: str = "text"           # text | textarea | choice (radio/select) | multi (checkboxes)
    options: tuple = ()
    when: object = None          # callable(config) → show this field at all
    note: str = ""
    optional: bool = False       # blank is a valid answer (not counted as 待填)


@dataclass
class Form:
    name: str
    where: str = ""              # how to reach the page in the web system
    sections: list = field(default_factory=list)   # [(title, [Field, …])]
    when: object = None          # callable(config) → this phase needs the form
    note: str = ""


def T(id, label, value=None, **kw):
    return Field(id, label, value, "text", **kw)


def A(id, label, value=None, **kw):
    return Field(id, label, value, "textarea", **kw)


def C(id, label, options, value=None, **kw):
    return Field(id, label, value, "choice", tuple(options), **kw)


def M(id, label, options, value=None, **kw):
    return Field(id, label, value, "multi", tuple(options), **kw)


# ── answers ─────────────────────────────────────────────────────────────────

def _test(pred, config):
    if pred is None:
        return True
    try:
        return bool(pred(config))
    except (KeyError, TypeError, AttributeError, IndexError):
        return False


def _text(value):
    if isinstance(value, list):
        return "\n".join(f"{i}. {v}" for i, v in enumerate(value, 1)) if len(value) > 1 else "".join(value)
    return "" if value is None else str(value).strip()


def _match(answer, options):
    """Option the answer names: exact, then prefix ('否' → '否，請說明：')."""
    answer = answer.strip()
    for opt in options:
        if answer == opt:
            return opt
    hits = [o for o in options if o.startswith(answer) or answer.startswith(o)]
    return hits[0] if len(hits) == 1 else None


_UNKEYED = {v: k for k, v in SECTION_KEYS.items()}   # 'objectives' → '研究目的' (parse_markdown maps it)


def _override_key(key):
    """'G29-1 請說明如何維護資料機密性' → 'G29-1'; '研究領域' → '研究領域'."""
    key = _UNKEYED.get(key, key)
    return key.split()[0].rstrip(".：:") if key.strip() else key


def overrides(config):
    raw = config.get("online") or {}
    if not isinstance(raw, dict):
        raise ConfigError("`online` must reference a Markdown file with `## <field id>` sections")
    return {_override_key(k): v for k, v in raw.items()}


def answer(fld, config, given):
    """(answer, source, warning). answer is str, or a list of options for multi."""
    if fld.id in given and given[fld.id] not in ("", []):
        value, source = given[fld.id], "md"
    else:
        value = fld.value(config) if callable(fld.value) else fld.value
        if isinstance(value, str) and "{" in value:
            value = resolve(value, config)
        source = "auto"
    if fld.kind == "multi":
        items = value if isinstance(value, list) else [v for v in re.split(r"[、,\n]", _text(value)) if v.strip()]
        picked, bad = [], []
        for item in items:
            opt = _match(str(item), fld.options)
            (picked.append(opt) if opt else bad.append(str(item)))
        warn = f"{fld.id}: 不是選項之一：{'、'.join(bad)}" if bad else ""
        return (picked, source, warn) if picked else ([], "skip" if fld.optional else "todo", warn)
    text = _text(value)
    if not text:
        return "", "skip" if fld.optional else "todo", ""
    if fld.kind == "choice":
        opt = _match(text, fld.options)
        if opt is None:
            return text, source, f"{fld.id}: 「{text}」不是選項之一（{' / '.join(fld.options)}）"
        return opt, source, ""
    return text, source, ""


def fill(form, config, given):
    """[(section, [(field, answer, source)])], warnings — hidden fields dropped."""
    out, warnings = [], []
    for title, fields in form.sections:
        rows = []
        for fld in fields:
            if not _test(fld.when, config):
                continue
            ans, source, warn = answer(fld, config, given)
            if warn:
                warnings.append(warn)
            rows.append((fld, ans, source))
        if rows:
            out.append((title, rows))
    return out, warnings


# ── rendering ───────────────────────────────────────────────────────────────

def _heading(fld):
    """Question numbers as printed on the page (A4, G29-1, H1-2); named fields by label only."""
    return f"{fld.id}. {fld.label}" if re.match(r"[A-Z]\d", fld.id) else fld.label


def render_md(form, filled, config):
    lines = [f"# {form.name}（線上填寫）", ""]
    if form.where:
        lines.append(f"> 位置：{form.where}")
    lines += [f"> 計畫：{config['study']['title_zh']}", f"> 標記：{MARK_HELP}", ""]
    if form.note:
        lines += [form.note, ""]
    for title, rows in filled:
        lines += [f"## {title}", ""]
        for fld, ans, source in rows:
            lines.append(f"### {MARKS[source]} {_heading(fld)}")
            if fld.note:
                lines.append(f"> {fld.note}")
            lines.append("")
            if fld.kind in ("choice", "multi"):
                chosen = ans if fld.kind == "multi" else [ans]
                on, off = ("◉", "○") if fld.kind == "choice" else ("■", "□")
                lines += [f"- {on if o in chosen else off} {o}" for o in fld.options]
                if fld.kind == "choice" and ans and ans not in fld.options:
                    lines.append(f"- ？ {ans}")
            elif ans:
                lines += ["```text", ans, "```"]
            else:
                lines.append("（視情況，不需要就留空）" if source == "skip" else "（待填）")
            lines.append("")
    return "\n".join(lines)


CSS = """
body{font-family:"Microsoft JhengHei","PingFang TC","Noto Sans TC",sans-serif;max-width:860px;margin:2em auto;padding:0 1em;color:#222}
h1{font-size:1.4em}h2{font-size:1.15em;border-bottom:2px solid #ccc;padding-bottom:.2em;margin-top:2em}
.meta{color:#555;font-size:.9em}.card{border:1px solid #ddd;border-radius:6px;padding:.6em .8em;margin:.6em 0}
.card.todo{border-color:#e0a000;background:#fff8e6}.label{font-weight:600}.note{color:#666;font-size:.85em}
.src{font-size:.8em;color:#888;float:right}pre{white-space:pre-wrap;background:#f5f5f5;padding:.5em;margin:.4em 0;border-radius:4px;font-family:inherit}
button{float:right;margin-left:.5em;cursor:pointer}.opt{margin:.15em 0}.opt.on{font-weight:600;color:#0a6}.opt.off{color:#999}
"""
JS = """
function cp(b){const t=b.parentElement.querySelector('pre').innerText;navigator.clipboard.writeText(t).then(()=>{b.textContent='已複製';setTimeout(()=>b.textContent='複製',1200)})}
"""
SOURCE_ZH = {"md": f"{SKELETON}", "auto": "依 config 推定，請確認", "todo": "待填", "skip": "視情況"}


def render_html(form, filled, config):
    e = html.escape
    parts = [f"<!doctype html><meta charset='utf-8'><title>{e(form.name)}</title><style>{CSS}</style>"
             f"<script>{JS}</script><h1>{e(form.name)}（線上填寫）</h1>"]
    meta = [f"位置：{form.where}"] if form.where else []
    meta += [f"計畫：{config['study']['title_zh']}", f"標記：{MARK_HELP}"]
    parts.append("".join(f"<div class=meta>{e(m)}</div>" for m in meta))
    if form.note:
        parts.append(f"<p class=note>{e(form.note)}</p>")
    for title, rows in filled:
        parts.append(f"<h2>{e(title)}</h2>")
        for fld, ans, source in rows:
            body = ""
            if fld.kind in ("choice", "multi"):
                chosen = ans if fld.kind == "multi" else [ans]
                on, off = ("◉", "○") if fld.kind == "choice" else ("■", "□")
                body = "".join(f"<div class='opt {'on' if o in chosen else 'off'}'>{on if o in chosen else off} {e(o)}</div>"
                               for o in fld.options)
                if fld.kind == "choice" and ans and ans not in fld.options:
                    body += f"<div class='opt on'>？ {e(ans)}</div>"
            elif ans:
                body = f"<button onclick='cp(this)'>複製</button><pre>{e(ans)}</pre>"
            else:
                body = f"<div class=note>（{'視情況，不需要就留空' if source == 'skip' else '待填'}）</div>"
            note = f"<div class=note>{e(fld.note)}</div>" if fld.note else ""
            parts.append(f"<div class='card {source}'><span class=src>{MARKS[source]} {e(SOURCE_ZH[source])}</span>"
                         f"<div class=label>{e(_heading(fld))}</div>{note}{body}</div>")
    return "\n".join(parts)


# ── driver ──────────────────────────────────────────────────────────────────

def online_forms(config):
    """Forms of the active institution's web system needed in this phase ([] if none)."""
    inst = activate(config)
    module = inst.data.get("online_module")
    if not module:
        return []
    forms = importlib.import_module(module).ONLINE_FORMS.get(config["phase"], [])
    return [f for f in forms if _test(f.when, config)]


def _safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name)


def generate(config, output_dir="output"):
    """Write the copy-paste sheets. Returns [(form, todo_fields, warnings)]."""
    out_dir = os.path.join(output_dir, ONLINE_DIR)
    for f in glob.glob(os.path.join(out_dir, "*")):
        os.remove(f)
    forms = online_forms(config)
    if not forms:
        return []
    os.makedirs(out_dir, exist_ok=True)
    given = overrides(config)
    # one 線上填寫.md serves every submission: only ids no phase uses are typos
    every = importlib.import_module(activate(config).data["online_module"]).ONLINE_FORMS.values()
    known = {fld.id for forms_ in every for form in forms_ for _, fields in form.sections for fld in fields}
    unknown = sorted(set(given) - known)
    results = []
    for i, form in enumerate(forms, 1):
        filled, warnings = fill(form, config, given)
        base = os.path.join(out_dir, f"{i:02d}_{_safe(form.name)}")
        with open(base + ".md", "w", encoding="utf-8") as fh:
            fh.write(render_md(form, filled, config))
        with open(base + ".html", "w", encoding="utf-8") as fh:
            fh.write(render_html(form, filled, config))
        todo = [fld for _, rows in filled for fld, _, src in rows if src == "todo"]
        results.append((form, todo, warnings))
    if unknown:
        results.append((Form(SKELETON), [], [f"{SKELETON} 裡沒有對應欄位的標題：{'、'.join(unknown)}"]))
    return results


def write_skeleton(config, path=SKELETON):
    """線上填寫.md listing every field still 待填 (plus all long-text fields)."""
    if os.path.exists(path):
        print(f"✗ {path} already exists — edit it, or delete it to regenerate")
        return 1
    given = overrides(config)
    lines = ["# 線上填寫", "", "<!--",
             "Answers for the web forms that config.toml can't derive. In config.toml (top level):",
             f'    online = "@{path}"',
             "One `## <題號> <標題>` per answer; only the first word of the heading (題號) matters.",
             "Choice questions: write the option text (a unique prefix is enough). Multi-choice: a `-` list.",
             "Delete sections you don't need; an empty section is ignored.", "-->", ""]
    for form in online_forms(config):
        filled, _ = fill(form, config, given)
        rows = [(fld, src) for _, r in filled for fld, _, src in r if src in ("todo", "skip") or fld.kind == "textarea"]
        if not rows:
            continue
        lines += [f"<!-- ════ {form.name} ════ -->", ""]
        for fld, src in rows:
            lines.append(f"## {fld.id} {fld.label if fld.id != fld.label else ''}".rstrip())
            hint = f"選項：{' / '.join(fld.options)}" if fld.options else ""
            if src == "skip":
                hint = (hint + "　" if hint else "") + "視情況，不需要就刪掉這段"
            elif src != "todo":
                hint = (hint + "　" if hint else "") + "已由 config 推定，要改寫再填"
            if hint:
                lines.append(f"<!-- {hint} -->")
            lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"■ {path} written — fill it, add `online = \"@{path}\"` to config.toml, then `rech online`")
    return 0


def main(config_path="config.toml", output_dir="output", phase=None, skeleton=False):
    try:
        config = load_config(config_path, phase)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    if skeleton:
        return write_skeleton(config)
    try:
        results = generate(config, output_dir)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    if not results:
        print(f"  (no web-system forms for {PHASE_NAMES.get(config['phase'], config['phase'])} at this institution)")
        return 0
    print(f"Web-system copy-paste sheets → {os.path.join(output_dir, ONLINE_DIR)}/")
    for form, todo, warnings in results:
        if form.name != SKELETON:
            tail = f"  ✎ 待填 {len(todo)}：{'、'.join(f.id for f in todo[:12])}{' …' if len(todo) > 12 else ''}" if todo else ""
            print(f"  ■ {form.name}{tail}")
        for w in warnings:
            print(f"    ⚠ {w}")
    if any(todo for _, todo, _ in results) and "online" not in config:
        print(f"  → `rech online --skeleton` writes {SKELETON} with every 待填 field")
    return 0


if __name__ == "__main__":
    from rec_helper.cli import main as cli
    sys.exit(cli(["online", *sys.argv[1:]]))
