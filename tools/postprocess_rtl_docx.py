from __future__ import annotations

from pathlib import Path
import re
import sys
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

PERSIAN_FONT = "Noto Naskh Arabic"
LATIN_FONT = "Noto Sans"


def add_bidi(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        p_pr.append(bidi)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT if paragraph.style.name == "Normal" else paragraph.alignment


def configure_run(run) -> None:
    run.font.name = LATIN_FONT
    if run.font.size is None:
        run.font.size = Pt(12)
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    rfonts.set(qn("w:cs"), PERSIAN_FONT)
    rfonts.set(qn("w:eastAsia"), LATIN_FONT)


def configure_table(table) -> None:
    for row in table.rows:
        for cell in row.cells:
            tc_pr = cell._tc.get_or_add_tcPr()
            text_dir = tc_pr.find(qn("w:textDirection"))
            if text_dir is None:
                text_dir = OxmlElement("w:textDirection")
                tc_pr.append(text_dir)
            text_dir.set(qn("w:val"), "tbRl")
            for paragraph in cell.paragraphs:
                add_bidi(paragraph)
                for run in paragraph.runs:
                    configure_run(run)


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
        add_bidi(paragraph)
        for run in paragraph.runs:
            configure_run(run)
    for table in doc.tables:
        configure_table(table)
    doc.save(path)
    print(f"Post-processed RTL DOCX: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
