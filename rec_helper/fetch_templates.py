"""Cache the institution's official blank forms for layout validation.

Driven by the `templates:` block of the active institution profile:

- `index_url` set   → scrape those pages, download every linked form whose
                      label matches `form_id_pattern` / `named_forms`
                      (Google Drive or direct links) into templates/<id>/
- no `index_url`    → index blanks you dropped into templates/<id>/ by hand,
                      mapped in `templates.files` (written by onboard.py) or
                      named after their form id

Legacy .doc files are converted to .docx (LibreOffice) so validate_layout.py
can read them. The result is templates/<id>/index.json.

Usage: rech templates [--force]
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

from rec_helper.institution import current

INDEX_FILE = "index.json"
FORM_EXTS = (".docx", ".doc", ".pdf")
EXT_RANK = {".docx": 0, ".doc": 1, ".odt": 2, ".pdf": 3}   # several formats per form: take the editable one

LINK_RE = re.compile(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.S)
DRIVE_ID_RE = re.compile(r"(?:id=|/d/)([A-Za-z0-9_-]{20,})")


def normalize_form_id(text):
    """'AF-127-02_2納入易受傷害族群說明表…' → 'AF127'; '中文計畫摘要' → 'PROPOSAL'; else None."""
    return current().form_id(text)


def index_pages():
    tpl = current().templates
    urls = tpl.get("index_urls") or ([tpl["index_url"]] if tpl.get("index_url") else [])
    lo, hi = tpl.get("index_range", [None, None])
    if lo is not None:
        return [u.format(n=n) for u in urls for n in range(lo, hi + 1)]
    return urls


def download_url(href, page_url):
    """Resolve a form link to a direct-download URL (Google Drive aware)."""
    href = html.unescape(href)
    if "google.com" in href:
        m = DRIVE_ID_RE.search(href)
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}" if m else None
    if current().templates.get("link_host") == "google_drive":
        return None
    return urllib.parse.urljoin(page_url, href)


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "rec-helper"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def scrape_links():
    """Return {form_id: {"title", "url", "page"}} from the profile's index pages."""
    found = {}
    for page in index_pages():
        try:
            body = fetch(page).decode("utf-8", "replace")
        except Exception as e:
            print(f"  ⚠ {page}: {e}")
            continue
        for href, label in LINK_RE.findall(body):
            title = " ".join(re.sub(r"<[^>]+>", "", html.unescape(label)).split())
            # labels are often just "(WORD)" / "PDF": the file name carries the form name
            stem, ext = os.path.splitext(urllib.parse.unquote(html.unescape(href).split("?")[0].rsplit("/", 1)[-1]))
            fid = normalize_form_id(title) or (normalize_form_id(stem) if ext.lower() in FORM_EXTS + (".odt",) else None)
            url = download_url(href, page)
            if not (fid and url):
                continue
            rank = EXT_RANK.get(ext.lower(), len(EXT_RANK))
            found.setdefault(fid, []).append((rank, len(found.get(fid, [])), stem if ext else title, url, page))
    out = {}
    for fid, cands in found.items():       # best format first; the rest are fallbacks for dead links
        # editable format first, then the newest revision (AF-126-03_1 before 03_0), then page order
        cands.sort(key=lambda c: (c[0], [-ord(ch) for ch in c[2]], c[1]))
        _, _, title, url, page = cands[0]
        out[fid] = {"title": title, "url": url, "page": page, "alternates": [c[3] for c in cands[1:]]}
    return out


def local_forms(template_dir):
    """Blanks placed by hand: {form_id: {"title", "file"}}."""
    mapped = current().templates.get("files", {})
    if mapped:
        return {fid: {"title": os.path.splitext(f)[0], "file": f} for fid, f in mapped.items()}
    found = {}
    for f in sorted(os.listdir(template_dir)):
        stem, ext = os.path.splitext(f)
        fid = normalize_form_id(stem) if ext.lower() in FORM_EXTS else None
        if fid and fid not in found:
            found[fid] = {"title": stem, "file": f}
    return found


def sniff_ext(data):
    if data[:4] == b"PK\x03\x04":
        return ".docx"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return ".doc"
    if data[:4] == b"%PDF":
        return ".pdf"
    return None


def to_docx(doc_path):
    """Convert legacy .doc → .docx next to it. Returns new path or None."""
    from rec_helper.convert import find_soffice, soffice_cmd
    soffice = find_soffice()
    if not soffice:
        return None
    out_dir = os.path.dirname(doc_path)
    try:
        subprocess.run(soffice_cmd(soffice, "--convert-to", "docx", "--outdir", out_dir, doc_path),
                       capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None
    docx = os.path.splitext(doc_path)[0] + ".docx"
    return docx if os.path.exists(docx) else None


def main(force=False):
    inst = current()
    template_dir = inst.template_dir
    os.makedirs(template_dir, exist_ok=True)
    if index_pages():
        print(f"Scraping {inst.name} form index ({len(index_pages())} pages)...")
        links = scrape_links()
    else:
        print(f"No templates.index_url for '{inst.id}' — indexing blanks in "
              f"{os.path.relpath(template_dir)}/ (name each file with its form id)")
        links = local_forms(template_dir)
    print(f"Found {len(links)} official forms\n")

    index = {}
    for fid, info in sorted(links.items()):
        mapped = inst.templates.get("files", {}).get(fid)
        existing = [f for f in os.listdir(template_dir)
                    if f.startswith(fid + ".") or (mapped and os.path.splitext(f)[0] == os.path.splitext(mapped)[0])]
        if "file" in info:
            raw = info["file"]
            print(f"  ■ {fid} {info['title']} (local)")
        elif existing and not force:
            raw = next((f for f in existing if not f.endswith(".docx")), existing[0])
            print(f"  ■ {fid} cached")
        else:
            data = None
            for url in [info["url"], *info.get("alternates", [])]:
                try:
                    data = fetch(url)
                    info["url"] = url
                    break
                except Exception as e:
                    err = e
            if data is None:
                print(f"  ✗ {fid} download failed: {err}")
                continue
            ext = sniff_ext(data)
            if ext == ".docx" and urllib.parse.unquote(info["url"]).lower().endswith(".odt"):
                ext = ".odt"                       # also a zip: LibreOffice converts it below
            if ext is None:
                print(f"  ✗ {fid} not a Word/PDF file (Drive returned HTML?)")
                continue
            # keep the name the profile maps the form to (templates.files), else <id><ext>
            mapped = inst.templates.get("files", {}).get(fid)
            raw = (os.path.splitext(mapped)[0] + ext) if mapped else fid + ext
            with open(os.path.join(template_dir, raw), "wb") as f:
                f.write(data)
            print(f"  ■ {fid} {info['title']} ({ext})")

        raw_path = os.path.join(template_dir, raw)
        docx = raw_path if raw.endswith(".docx") else os.path.splitext(raw_path)[0] + ".docx"
        if raw.endswith((".doc", ".odt")) and (force or not os.path.exists(docx)):
            docx = to_docx(raw_path)
            if docx is None:
                print(f"    ⚠ {fid}: .doc→.docx conversion failed (LibreOffice missing?)")
        info.pop("alternates", None)
        index[fid] = {**info, "source": raw,
                      "docx": os.path.basename(docx) if docx and os.path.exists(docx) else None}

    with open(os.path.join(template_dir, INDEX_FILE), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n■ {len(index)} templates indexed → {os.path.relpath(template_dir)}/{INDEX_FILE}")


if __name__ == "__main__":
    from rec_helper.cli import main as cli
    sys.exit(cli(["templates", *sys.argv[1:]]))
