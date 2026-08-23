from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "PUBLISH" / "reference.docx"


def set_bidi(paragraph) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    bidi = ppr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        ppr.append(bidi)
    bidi.set(qn("w:val"), "1")


def set_font(style, name_fa="Noto Naskh Arabic", name_latin="Noto Sans", size=12, bold=None):
    style.font.name = name_fa
    style._element.rPr.rFonts.set(qn("w:ascii"), name_latin)
    style._element.rPr.rFonts.set(qn("w:hAnsi"), name_latin)
    style._element.rPr.rFonts.set(qn("w:cs"), name_fa)
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold


def set_style_bidi(style):
    ppr = style._element.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    ppr.append(bidi)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)
    sec.header_distance = Cm(1.2)
    sec.footer_distance = Cm(1.2)

    styles = doc.styles
    normal = styles["Normal"]
    set_font(normal, size=12)
    set_style_bidi(normal)
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    specs = {
        "Title": (20, True, 1.1, 14),
        "Heading 1": (17, True, 1.15, 10),
        "Heading 2": (14, True, 1.15, 8),
        "Heading 3": (12.5, True, 1.15, 6),
        "Caption": (10.5, False, 1.1, 4),
    }
    for sname, (size, bold, spacing, after) in specs.items():
        if sname in styles:
            st = styles[sname]
            set_font(st, size=size, bold=bold)
            set_style_bidi(st)
            st.paragraph_format.line_spacing = spacing
            st.paragraph_format.space_after = Pt(after)
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    for sname in ["List Bullet", "List Number"]:
        if sname in styles:
            st = styles[sname]
            set_font(st, size=11.5)
            set_style_bidi(st)
            st.paragraph_format.line_spacing = 1.25
            st.paragraph_format.space_after = Pt(3)
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    header = sec.header.paragraphs[0]
    set_bidi(header)
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("تحول دیجیتال هوشمند - جزوه دانشگاهی")
    run.font.name = "Noto Naskh Arabic"
    run._r.rPr.rFonts.set(qn("w:cs"), "Noto Naskh Arabic")
    run.font.size = Pt(9.5)

    footer = sec.footer.paragraphs[0]
    set_bidi(footer)
    add_page_number(footer)
    for run in footer.runs:
        run.font.name = "Noto Sans"
        run.font.size = Pt(9)

    # Sample table style with explicit repeating header support via Word style.
    if "Light Shading Accent 1" in styles:
        table_style = styles["Light Shading Accent 1"]
        set_font(table_style, size=10.5)

    # Store a compact self-describing sample block for deterministic style inheritance.
    p = doc.add_paragraph()
    set_bidi(p)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("RTL reference template - Persian first, English technical text LTR-aware")
    r.font.name = "Noto Naskh Arabic"
    r._r.rPr.rFonts.set(qn("w:cs"), "Noto Naskh Arabic")
    r.font.size = Pt(10)

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
