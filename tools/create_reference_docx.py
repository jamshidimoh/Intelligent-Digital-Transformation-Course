from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "PUBLISH" / "reference-template.docx"

PERSIAN_FONT = "Noto Naskh Arabic"
LATIN_FONT = "Noto Sans"


def set_rtl(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    bidi = p_pr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        p_pr.append(bidi)


def set_run_font(run) -> None:
    run.font.name = LATIN_FONT
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


def configure_style(style, size: int, bold: bool = False, space_before: int = 0, space_after: int = 6) -> None:
    style.font.name = LATIN_FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    rpr = style._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)
    rfonts.set(qn("w:cs"), PERSIAN_FONT)
    ppr = style._element.get_or_add_pPr()
    spacing = ppr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        ppr.append(spacing)
    spacing.set(qn("w:before"), str(space_before * 20))
    spacing.set(qn("w:after"), str(space_after * 20))
    spacing.set(qn("w:line"), "312")
    spacing.set(qn("w:lineRule"), "auto")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.header_distance = Cm(1.2)
    section.footer_distance = Cm(1.2)

    styles = doc.styles
    configure_style(styles["Normal"], 12, False, 0, 7)
    styles["Normal"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    styles["Normal"].paragraph_format.line_spacing = 1.3

    configure_style(styles["Title"], 20, True, 0, 14)
    styles["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    configure_style(styles["Heading 1"], 16, True, 16, 8)
    configure_style(styles["Heading 2"], 14, True, 12, 6)
    configure_style(styles["Heading 3"], 13, True, 10, 5)
    configure_style(styles["Heading 4"], 12, True, 8, 4)
    if "Caption" in styles:
        configure_style(styles["Caption"], 10, False, 4, 8)
        styles["Caption"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for style_name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4", "Caption"):
        style = styles[style_name]
        ppr = style._element.get_or_add_pPr()
        bidi = ppr.find(qn("w:bidi"))
        if bidi is None:
            bidi = OxmlElement("w:bidi")
            ppr.append(bidi)

    # Header/footer defaults; chapter metadata is added by the renderer.
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_rtl(header)
    run = header.add_run("تحول دیجیتال ۲.۰")
    run.font.size = Pt(9)
    set_run_font(run)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_rtl(footer)
    run = footer.add_run("صفحه ")
    run.font.size = Pt(9)
    set_run_font(run)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer._p.append(fld)

    # Seed paragraphs so Pandoc imports the configured style definitions.
    p = doc.add_paragraph()
    p.style = styles["Normal"]
    set_rtl(p)
    r = p.add_run("")
    set_run_font(r)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
