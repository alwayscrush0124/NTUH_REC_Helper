"""審查意見回覆: the committee's comments, answered point by point.

After review the committee returns numbered comments; the PI answers each and
revises the documents. The source is `reply = "審查意見.md"` in config.toml:

    ## 1
    意見：請補充樣本數估算之依據。
    回覆：已於計畫書第五章補充……
    修正：計畫書｜6｜五、研究對象｜（無）｜新增樣本數估算一段｜依委員意見補充

`意見` / `回覆` may span several lines; each `修正` line is one row of the
修正前後對照表 (文件｜頁碼｜章節｜修正前｜修正後｜原因) and, in an amendment, fills
that table automatically when 附件填寫.md doesn't. `rech reply --skeleton`
writes the template; `rech generate` renders 審查意見回覆表.docx.
"""
import os
import re
from dataclasses import dataclass, field

REPLY_MD = "審查意見.md"
LABELS = ("意見", "回覆", "修正")


@dataclass
class Item:
    no: str
    comment: str = ""
    reply: str = ""
    changes: list = field(default_factory=list)


def parse(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    items = []
    for head, body in re.findall(r"^##[ \t]+(.+?)[ \t]*\n(.*?)(?=^##[ \t]|\Z)", text, flags=re.M | re.S):
        item, current = Item(head.strip()), None
        for line in body.splitlines():
            m = re.match(rf"^\s*(?:[-*]\s*)?({'|'.join(LABELS)})\s*[：:]\s*(.*)$", line)
            if m:
                current = m.group(1)
                if current == "修正":
                    if m.group(2).strip():
                        item.changes.append(m.group(2).strip())
                    continue
                setattr(item, "comment" if current == "意見" else "reply", m.group(2).strip())
            elif current in ("意見", "回覆") and line.strip():
                attr = "comment" if current == "意見" else "reply"
                setattr(item, attr, (getattr(item, attr) + "\n" + line.strip()).strip())
            elif current == "修正" and line.strip():
                item.changes.append(line.strip().lstrip("-* "))
        if item.comment or item.reply or item.changes:
            items.append(item)
    return items


def load(config):
    path = config.get("reply")
    if not isinstance(path, str) or not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return parse(fh.read())


def amendment_rows(config):
    """修正 lines of every comment, for the 修正前後對照表."""
    return [row for item in load(config) for row in item.changes]


def generate_reply(config, output_dir):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    from rec_helper.docx_utils import add_ct, add_p, apply_tb, init_doc
    from rec_helper.institution import current
    from rec_helper.versions import add_header, label

    items = load(config)
    doc = init_doc(11)
    add_header(doc, label(config, "審查意見回覆"))
    add_p(doc, "審查意見回覆表", True, 15, WD_ALIGN_PARAGRAPH.CENTER, Pt(6))
    irb = config["study"].get("irb_no") or "（待核發）"
    add_p(doc, f"{current().irb_no_label}：{irb}", size=11, sa=Pt(2))
    add_p(doc, f"計畫名稱：{config['study']['title_zh']}", size=11, sa=Pt(8))
    table = doc.add_table(rows=1, cols=4)
    for cell, title in zip(table.rows[0].cells, ("序號", "審查意見", "回覆說明", "修正處"), strict=True):
        add_ct(cell, title, bold=True, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    for item in items:
        row = table.add_row().cells
        where = "\n".join("｜".join(re.split(r"\s*[｜|]\s*", c)[:3]) for c in item.changes) or "—"
        for cell, text in zip(row, (item.no, item.comment, item.reply or "【待回覆】", where), strict=True):
            add_ct(cell, text)
    apply_tb(table)
    widths = (Pt(32), Pt(170), Pt(200), Pt(90))
    for r in table.rows:
        for cell, w in zip(r.cells, widths, strict=True):
            cell.width = w
    path = os.path.join(output_dir, "審查意見回覆表.docx")
    doc.save(path)
    return path


SKELETON = """# 審查意見回覆

<!--
config.toml：reply = "審查意見.md"。每則意見一段 `## <序號>`：
  意見：照抄審查意見（可多行）
  回覆：你的回覆（可多行）
  修正：文件｜頁碼｜章節｜修正前｜修正後｜原因   （每處修改一行，可多行；沒有修改就刪掉）
修正行會同時帶入變更案的修正前後對照表。`rech generate` 產生 審查意見回覆表.docx。
-->

## 1
意見：
回覆：
修正：計畫書｜｜｜｜｜

## 2
意見：
回覆：
"""


def main(config_path="config.toml", path=REPLY_MD):
    if os.path.exists(path):
        from rec_helper.config import ConfigError, load_config
        try:
            config = load_config(config_path)
        except ConfigError as e:
            print(f"✗ {e}")
            return 2
        items = load(config | {"reply": path})
        open_ = [i.no for i in items if not i.reply]
        print(f"■ {path}: {len(items)} 則意見，{len(open_)} 則未回覆" + (f"（{'、'.join(open_)}）" if open_ else ""))
        return 0
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SKELETON)
    print(f"■ {path} written — 貼上審查意見並逐則回覆，config.toml 加 reply = \"{path}\"，再 `rech generate`")
    return 0
