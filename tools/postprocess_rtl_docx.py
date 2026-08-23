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
NUMBER_RE = re.compile(r"\d")

LRI = "\u2066"
PDI = "\u2069"
RLM = "\u200F"


def set_bool(parent, tag: str, enabled: bool = True) -> None:
    node = parent.find(qn(tag))
    if enabled and node is None:
        parent.append(OxmlElement(tag))
    elif not enabled and node is not None:
        parent.remove(node)


def set_lang(rpr, val: str) -> None:
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:val"), val)


def set_run_font(rpr, rtl: bool) -> None:
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    rfonts.set(qn("w:cs"), PERSIAN_FONT if rtl else LATIN_FONT)
    rfonts.set(qn("w:eastAsia"), LATIN_FONT)


def set_run_direction(run_el, rtl: bool) -> None:
    rpr = run_el.get_or_add_rPr()
    set_bool(rpr, "w:rtl", rtl)
    set_lang(rpr, "fa-IR" if rtl else "en-US")
    set_run_font(rpr, rtl)


def get_text(run_el) -> str:
    return "".join((node.text or "") for node in run_el.findall(".//" + qn("w:t")))


def dominant_direction(text: str) -> str:
    fa = len(FA_RE.findall(text))
    en = len(LATIN_RE.findall(text))
    if fa >= en and fa > 0:
        return "fa"
    if en > 0:
        return "en"
    return "neutral"


def classify_char(ch: str) -> str:
    if FA_RE.match(ch):
        return "fa"
    if LATIN_RE.match(ch) or NUMBER_RE.match(ch):
        return "en"
    if unicodedata.category(ch).startswith("L"):
        return "fa"
    return "neutral"


def tokenize_mixed(text: str) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    current_kind: str | None = None

    for ch in text:
        kind = classify_char(ch)
        if kind == "neutral":
            if current_kind is None:
                current_kind = "neutral"
            current.append(ch)
            continue

        if current_kind is None:
            current_kind = kind
        elif kind != current_kind:
            chunks.append((current_kind, "".join(current)))
            current = []
            current_kind = kind
        current.append(ch)

    if current:
        chunks.append((current_kind or "neutral", "".join(current)))

    # Merge punctuation/whitespace chunks into their most natural neighbour.
    merged: list[tuple[str, str]] = []
    for kind, text_chunk in chunks:
        if kind == "neutral" and merged:
            pk, pt = merged[-1]
            merged[-1] = (pk, pt + text_chunk)
        else:
            merged.append((kind, text_chunk))
    return [(k, t) for k, t in merged if t]


def make_run_clone(run_el, text: str, rtl: bool, isolate_ltr: bool = False):
    clone = deepcopy(run_el)
    t_nodes = clone.findall(".//" + qn("w:t"))
    if not t_nodes:
        return clone
    for node in t_nodes:
        node.text = ""
    value = text
    if isolate_ltr and value.strip():
        value = LRI + value + PDI
    t_nodes[0].text = value
    set_run_direction(clone, rtl)
    return clone


def replace_run_with_bidi_safe_chunks(run) -> None:
    run_el = run._r
    text = get_text(run_el)
    if not text:
        return

    p = run_el.getparent()
    if p is None:
        return

    kind = dominant_direction(text)
    if kind == "neutral":
        set_run_direction(run_el, False)
        return

    chunks = tokenize_mixed(text)
    if len(chunks) <= 1:
        set_run_direction(run_el, kind == "fa")
        return

    # Only split when actual directional content changes. This avoids the old
    # behaviour where punctuation and whitespace destabilized token order.
    meaningful = [(k, t) for k, t in chunks if any(c.isalnum() for c in t)]
    if len(meaningful) <= 1:
        set_run_direction(run_el, kind == "fa")
        return

    idx = p.index(run_el)
    for chunk_kind, chunk_text in chunks:
        if not chunk_text:
            continue
        rtl = chunk_kind == "fa"
        clone = make_run_clone(run_el, chunk_text, rtl, isolate_ltr=(not rtl))
        p.insert(idx, clone)
        idx += 1
    p.remove(run_el)


def set_paragraph_bidi(paragraph, enabled: bool) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    set_bool(ppr, "w:bidi", enabled)


def clear_paragraph_rtl(paragraph) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    set_bool(ppr, "w:bidi", False)


def paragraph_is_code_like(paragraph) -> bool:
    style_name = paragraph.style.name.lower() if paragraph.style else ""
    text = paragraph.text or ""
    return "code" in style_name or text.strip().startswith(("```", "$ ", "> "))


def configure_paragraph(paragraph) -> None:
    text = paragraph.text or ""
    direction = dominant_direction(text)

    if paragraph_is_code_like(paragraph):
        clear_paragraph_rtl(paragraph)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in list(paragraph.runs):
            set_run_direction(run._r, False)
        return

    is_rtl = direction == "fa"
    set_paragraph_bidi(paragraph, is_rtl)
    if is_rtl:
        if paragraph.style.name in {"Normal", "Body Text"}:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif paragraph.style.name.startswith("Heading"):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for run in list(paragraph.runs):
        replace_run_with_bidi_safe_chunks(run)


def remove_cell_text_direction(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.find(qn("w:textDirection"))
    if node is not None:
        tc_pr.remove(node)


def set_cell_borders_neutral(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.find(qn("w:tcMar"))
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", 90), ("left", 110), ("bottom", 90), ("right", 110)):
        node = tc_mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def configure_table(table) -> None:
    tbl_pr = table._tbl.tblPr
    set_bool(tbl_pr, "w:bidiVisual", True)

    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            remove_cell_text_direction(cell)
            set_cell_borders_neutral(cell)
            for paragraph in cell.paragraphs:
                set_paragraph_bidi(paragraph, True)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.08
                for run in list(paragraph.runs):
                    replace_run_with_bidi_safe_chunks(run)
                    if row_index == 0:
                        for rr in paragraph.runs:
                            rr.bold = True


def configure_header_footer(paragraph) -> None:
    text = paragraph.text or ""
    set_paragraph_bidi(paragraph, bool(FA_RE.search(text)))
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT if FA_RE.search(text) else WD_ALIGN_PARAGRAPH.LEFT
    for run in list(paragraph.runs):
        direction = dominant_direction(run.text or "")
        set_run_direction(run._r, direction == "fa")


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
            configure_header_footer(paragraph)

    doc.save(path)
    print(f"Post-processed publication-grade Persian RTL/bilingual DOCX: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
