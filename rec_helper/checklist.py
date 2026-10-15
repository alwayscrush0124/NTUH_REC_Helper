"""Plain-text checklist generator using ■/□ convention."""
import os
from datetime import date

from rec_helper.institution import current


def generate_checklist(config, results, phase_zh, output_path="checklist.md"):
    """Generate checklist.md from generation results.

    Args:
        config: Study config dict
        results: list of (form_id, name_zh, path_or_None, status)
        phase_zh: Chinese phase name
        output_path: Where to write checklist
    """
    irb_no = config["study"]["irb_no"]
    title_zh = config["study"]["title_zh"]
    today = date.today().strftime("%Y-%m-%d")

    lines = [
        "# Submission Checklist",
        f"## Study: {irb_no} — {title_zh}",
        f"## Phase: {phase_zh}",
        f"## Generated: {today}",
        "",
        "---",
        "",
        "### Generated Forms",
    ]

    for fid, name_zh, path, status in results:
        if status == "generated" and path:
            basename = os.path.basename(path)
            lines.append(f"■ {fid} {name_zh} → {basename}")
        elif status == "error":
            lines.append(f"□ {fid} {name_zh} → GENERATION ERROR")
        elif status == "missing":
            lines.append(f"□ {fid} {name_zh} → NO GENERATOR (manual fill required)")

    lines.extend([
        "",
        "### PDF Conversion",
        "□ Run `rech pdf` and `rech validate` to generate PDFs and pass the layout gate",
        "",
        "### Manual Steps",
    ])

    # Phase-specific manual steps: the institution's [checklist] in profile.toml
    steps = (current().data.get("checklist") or {}).get(config["phase"], [])
    lines.extend(f"□ {step}" for step in steps)

    sub = current().submission
    lines.extend(["", "### Submission"])
    if sub.get("web"):
        lines.append(f"□ 上傳至線上系統：{sub['web']}")
    if current().submission_email:
        lines.append(f"□ Email electronic copies to {current().submission_email}")
    if sub.get("paper"):
        lines.append(f"□ {sub['paper']}")
    lines.extend(["", "---"])

    # Summary
    generated = sum(1 for _, _, _, s in results if s == "generated")
    total = len(results)
    lines.append(f"**Status: {generated}/{total} forms generated**")

    content = "\n".join(lines) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
