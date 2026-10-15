"""Reference and acronym check for the protocol (and summary).

References — the list under 參考文獻 / References in the protocol. Each entry's
DOI, PMID or arXiv id is looked up (Crossref, PubMed E-utilities, arXiv API);
entries without an id are matched by a Crossref bibliographic query. Reported:

  ■ 相符        found; year and title agree
  ⚠ 請核對      found, but the year or title differs (typo? preprint vs. journal version?)
  ✗ 查無        the DOI/PMID/arXiv id resolves to nothing
  ？ 人工確認    no id and no Crossref match (conference papers, web pages)
  － 未查        --offline, or no network

Only the reference strings (public citations) are sent to those services.

Acronyms — offline: every acronym in the protocol body should be spelled out at
its first use, e.g. 大型語言模型（large language model, LLM）. Flags acronyms never
defined and those defined only after they were first used.

Usage: rech refs [config.toml] [--offline] [--output DIR]   → output/refs_report.md
"""
import difflib
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

from rec_helper import study_text

UA = {"User-Agent": "rec-helper/0.1 (reference check)"}
REF_HEADING = re.compile(r"^\s*(?:#+\s*)?(?:[一二三四五六七八九十]+、)?\s*(參考文獻|參考資料|References?|Bibliography)\s*[：:]?\s*$",
                         re.I | re.M)
COMMON = {"DNA", "RNA", "HIV", "AIDS", "ID", "IRB", "REC", "NTUH", "PDF", "USA", "WHO", "COVID", "II", "III", "IV", "OK"}


@dataclass
class Ref:
    n: int
    text: str
    doi: str = ""
    pmid: str = ""
    arxiv: str = ""
    year: str = ""
    status: str = "－"
    note: str = ""


def split_references(text):
    """The entries after the last 參考文獻/References heading, one per numbered item or line."""
    heads = list(REF_HEADING.finditer(text))
    if not heads:
        return []
    body = text[heads[-1].end():]
    entries, cur = [], ""
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^(?:\[\d+\]|\d+[.)、]|[-*•])\s*", s):
            if cur:
                entries.append(cur)
            cur = re.sub(r"^(?:\[\d+\]|\d+[.)、]|[-*•])\s*", "", s)
        else:
            cur = f"{cur} {s}".strip() if cur else s
    if cur:
        entries.append(cur)
    return [e for e in entries if len(e) > 15 and "【待寫】" not in e]


def parse(n, text):
    r = Ref(n, text)
    m = re.search(r"10\.\d{4,9}/[^\s,;]+", text)
    r.doi = m.group().rstrip(".") if m else ""
    m = re.search(r"PMID[:\s]*(\d{6,9})", text, re.I)
    r.pmid = m.group(1) if m else ""
    m = re.search(r"arXiv[:.\s]*(\d{4}\.\d{4,5})", text, re.I)
    r.arxiv = m.group(1) if m else ""
    m = re.search(r"\b(19\d\d|20\d\d)\b", text)
    r.year = m.group(1) if m else ""
    return r


def _get(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _similar(title, text):
    """How much of the found title appears in the reference string (0–1)."""
    a = re.sub(r"\W+", " ", title.lower()).strip()
    b = re.sub(r"\W+", " ", text.lower())
    if not a:
        return 0.0
    if a in b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size / len(a)


def _lookup(r):
    """(title, year) of the cited work, or None."""
    if r.arxiv or r.doi.lower().startswith("10.48550/arxiv."):
        arxiv_id = r.arxiv or r.doi.split("arxiv.", 1)[1]
        try:                                   # arXiv DOIs are registered with DataCite (fast)
            attrs = json.loads(_get(f"https://api.datacite.org/dois/10.48550/arXiv.{arxiv_id}"))["data"]["attributes"]
            return (attrs.get("titles") or [{}])[0].get("title", ""), str(attrs.get("publicationYear", ""))
        except Exception:
            pass
        xml = _get(f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}", timeout=30)
        entry = xml.split("<entry>", 1)[1] if "<entry>" in xml else ""
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        year = re.search(r"<published>(\d{4})", entry)
        return (" ".join(title.group(1).split()), year.group(1) if year else "") if title else None
    if r.doi:
        data = json.loads(_get(f"https://api.crossref.org/works/{urllib.parse.quote(r.doi)}"))["message"]
        year = str((data.get("issued", {}).get("date-parts") or [[""]])[0][0])
        return (data.get("title") or [""])[0], year
    if r.pmid:
        data = json.loads(_get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=" + r.pmid))
        doc = data.get("result", {}).get(r.pmid)
        return (doc.get("title", ""), (doc.get("pubdate") or "")[:4]) if doc else None
    q = urllib.parse.quote(r.text[:300])
    items = json.loads(_get(f"https://api.crossref.org/works?rows=1&query.bibliographic={q}"))["message"]["items"]
    if not items:
        return None
    it = items[0]
    year = str((it.get("issued", {}).get("date-parts") or [[""]])[0][0])
    title = (it.get("title") or [""])[0]
    if _similar(title, r.text) < 0.6:
        return None
    r.note = f"建議補 DOI：{it.get('DOI')}"
    return title, year


def verify(r):
    try:
        found = _lookup(r)
    except Exception as e:     # network down, rate-limited, malformed reply
        r.status, r.note = "－", f"未查（{type(e).__name__}）"
        return r
    if not found:
        if r.doi or r.pmid or r.arxiv:
            r.status, r.note = "✗", "此 DOI/PMID/arXiv 查無資料：請核對編號"
        else:
            r.status, r.note = "？", "Crossref 查無；會議論文、網頁與灰色文獻常不在 Crossref，請人工確認"
        return r
    title, year = found
    problems = []
    if r.year and year and r.year != year:
        problems.append(f"年份 {r.year} ≠ 資料庫 {year}")
    if title and _similar(title, r.text) < 0.6:
        problems.append(f"題名與資料庫不符：「{title[:90]}」")
    r.status = "⚠" if problems else "■"
    r.note = "；".join(problems + ([r.note] if r.note else [])) or f"{title[:90]}（{year}）"
    return r


def acronyms(text):
    """[(acronym, problem)] for acronyms used before (or without) their definition."""
    body = REF_HEADING.split(text)[0] if REF_HEADING.search(text) else text
    out = []
    seen = set()
    # ALL-CAPS words of 2+ letters (LLM, MRI, F1 excluded), plural "LLMs" counts as LLM
    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]*[A-Z][A-Z0-9]*)s?(?![A-Za-z0-9])", body):
        acr = m.group(1)
        if acr in seen or acr in COMMON or len(acr) > 10:
            continue
        seen.add(acr)
        defs = [d.start() for d in re.finditer(
            rf"[（(][^（）()]{{3,}}[,，、\s]\s*{re.escape(acr)}\s*[）)]|{re.escape(acr)}\s*[（(][^（）()]{{3,}}[）)]|"
            rf"[A-Za-z][A-Za-z -]{{3,}}\s*[（(]\s*{re.escape(acr)}\s*[）)]|[一-鿿]{{2,}}\s*[（(]\s*{re.escape(acr)}\s*[）)]", body)]
        if not defs:
            out.append((acr, "全文未定義全名"))
        elif defs[0] > m.start() + len(acr) + 2:
            out.append((acr, "定義出現在首次使用之後"))
    return out


def run(config, offline=False):
    text = study_text.protocol_text(config)
    refs = [parse(i, t) for i, t in enumerate(split_references(text), 1)]
    if not offline:
        refs = [verify(r) for r in refs]
    acr = acronyms(text + "\n" + study_text.proposal_text(config))
    return text, refs, acr


def report(config, text, refs, acr, offline):
    lines = ["# 參考文獻與縮寫檢查", "", f"> 計畫：{config['study']['title_zh']}",
             f"> 來源：{study_text.protocol_path(config) or '（無計畫書：config.toml 設 protocol 或 protocol_file）'}"
             + ("（離線：未查詢資料庫）" if offline else ""), ""]
    lines += [f"## 參考文獻（{len(refs)} 筆）", ""]
    if not refs:
        lines.append("找不到「參考文獻／References」段落或其中沒有條目。")
    for r in refs:
        ids = " ".join(x for x in (f"DOI {r.doi}" if r.doi else "", f"PMID {r.pmid}" if r.pmid else "",
                                    f"arXiv {r.arxiv}" if r.arxiv else "") if x)
        lines.append(f"{r.n}. {r.status} {r.text[:120]}{'…' if len(r.text) > 120 else ''}")
        lines.append(f"   - {ids or '無 DOI/PMID'}；{r.note or '—'}")
    lines += ["", f"## 縮寫（{len(acr)} 個待處理）", ""]
    lines += [f"- {a}：{p}" for a, p in acr] or ["■ 所有縮寫都在首次使用時定義。"]
    return "\n".join(lines) + "\n"


def main(config_path="config.toml", output_dir="output", offline=False):
    from rec_helper.config import ConfigError, load_config
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"✗ {e}")
        return 2
    text, refs, acr = run(config, offline)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "refs_report.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report(config, text, refs, acr, offline))
    bad = [r for r in refs if r.status in ("✗", "⚠", "？")]
    print(f"References: {len(refs)} 筆，{len(bad)} 筆待核對；縮寫 {len(acr)} 個待處理 → {path}")
    for r in bad:
        print(f"  {r.status} [{r.n}] {r.note}")
    return 0
