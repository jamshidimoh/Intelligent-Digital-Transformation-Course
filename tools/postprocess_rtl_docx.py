from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys
import unicodedata

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

PERSIAN_FONT = "Noto Naskh Arabic"
LATIN_FONT = "Noto Sans"
FA_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_RE = re.compile(r"[A-Za-z]")


def set_bool(parent, tag: str, enabled: bool = True) -> None:
    node = parent.find(qn(tag))
    if enabled:
        if node is None:
            parent.append(OxmlElement(tag))
    elif node is not None:
        parent.remove(node)


def set_lang(rpr, val: str) -> None:
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:val"), val)


def set_run_direction(run_el, rtl: bool) -> None:
    rpr = run_el.get_or_add_rPr()
    set_bool(rpr, "w:rtl", rtl)
    set_lang(rpr, "fa-IR" if rtl else "en-US")
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    rfonts.set(qn("w:cs"), PERSIAN_FONT)
    rfonts.set(qn("w:eastAsia"), LATIN_FONT)


def classify(text: str) -> str:
    fa = len(FA_RE.findall(text))
    en = len(LATIN_RE.findall(text))
    if fa and en:
        return "mixed"
    if fa:
        return "fa"
    if en:
        return "en"
    for ch in text:
        if ch.isdigit():
            return "en"
        if unicodedata.category(ch).startswith("L"):
            return "fa"
    return "neutral"


def split_run_if_mixed(run) -> None:
    run_el = run._r
    texts = run_el.findall(".//" + qn("w:t"))
    if len(texts) != 1:
        direction = classify(run.text or "")
        set_run_direction(run_el, direction == "fa")
        return

    text_node = texts[0]
    text = text_node.text or ""
    if not text:
        return

    # Preserve invisible directional marks around Latin technical tokens inside RTL paragraphs.
    chunks = []
    current = ""
    current_kind = None
    for ch in text:
        kind = "fa" if FA_RE.match(ch) else "en" if LATIN_RE.match(ch) or ch.isdigit() else "neutral"
        if kind == "neutral" and current_kind is not None:
            kind = current_kind
        if current_kind is None:
            current_kind = kind
        if kind != current_kind:
            chunks.append((current_kind, current))
            current = ch
            current_kind = kind
        else:
            current += ch
    if current:
        chunks.append((current_kind, current))

    meaningful = [(k, t) for k, t in chunks if t]
    if len(meaningful) <= 1:
        direction = classify(text)
        set_run_direction(run_el, direction == "fa")
        return

    parent = run_el.getparent()
    insertion_index = parent.index(run_el)
    for kind, chunk in meaningful:
        clone = deepcopy(run_el)
        t_nodes = clone.findall(".//" + qn("w:t"))
        for node in t_nodes:
            node.text = ""
        t_nodes[0].text = chunk
        set_run_direction(clone, kind == "fa")
        parent.insert(insertion_index, clone)
        insertion_index += 1
    parent.remove(run_el)


def add_bidi(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    set_bool(p_pr, "w:bidi", True)
    if paragraph.style.name in {"Normal", "Body Text"}:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def configure_paragraph(paragraph) -> None:
    add_bidi(paragraph)
    for run in list(paragraph.runs):
        split_run_if_mixed(run)


def configure_table(table) -> None:
    tbl_pr = table._tbl.tblPr
    # Right-to-left table ordering without rotating cell text.
    set_bool(tbl_pr, "w:bidiVisual", True)
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc_pr = cell._tc.get_or_add_tcPr()
            rotated = tc_pr.find(qn("w:textDirection"))
            if rotated is not None:
                tc_pr.remove(rotated)
            for paragraph in cell.paragraphs:
                configure_paragraph(paragraph)
                paragraph.paragraph_format.space_after = Pt(3)
                if row_index == 0:
                    for run in paragraph.runs:
                        run.bold = True


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: postprocess_rtl_docx.py <docx>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Missing DOCX: {path}", file=sys.stderr)
        return 1

    doc = Document(path)
    for paragraph in doc.paragraphs:
        configure_paragraph(paragraph)
    for table in doc.tables:
        configure_table(table)
    for section in doc.sections:
        for paragraph in section.header.paragraphs + section.footer.paragraphs:
            add_bidi(paragraph)
            for run in list(paragraph.runs):
                direction = classify(run.text or "")
                set_run_direction(run._r, direction == "fa")

    doc.save(path)
    print(f"Post-processed academic RTL/bilingual DOCX: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
