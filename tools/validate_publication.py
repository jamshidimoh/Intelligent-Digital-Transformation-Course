from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "PUBLISH" / "CHAPTERS"
QA_DIR = ROOT / "PUBLISH" / "QA"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def run_capture(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout


def has_child(parent, tag: str) -> bool:
    return parent.find(w(tag)) is not None


def is_code_like(p) -> bool:
    text = "".join(t.text or "" for t in p.findall(f".//{w('t')}"))
    ppr = p.find(w("pPr"))
    style_id = ""
    if ppr is not None:
        style = ppr.find(w("pStyle"))
        if style is not None:
            style_id = style.attrib.get(w("val"), "").lower()
    return "code" in style_id or text.strip().startswith(("```", "$ ", ">> "))


def is_right_aligned(p) -> bool:
    ppr = p.find(w("pPr"))
    if ppr is None:
        return False
    jc = ppr.find(w("jc"))
    return jc is not None and jc.attrib.get(w("val")) == "right"


def validate_docx(path: Path, errors: list[str], report: list[str]) -> None:
    try:
        with zipfile.ZipFile(path) as zf:
            if zf.testzip():
                errors.append(f"DOCX archive is corrupt: {path}")
            names = set(zf.namelist())
            if "word/document.xml" not in names:
                errors.append(f"DOCX missing word/document.xml: {path}")
                return
            root = ET.fromstring(zf.read("word/document.xml"))
            paragraphs = root.findall(f".//{w('p')}")
            content_paragraphs = 0
            bidi_content_paragraphs = 0
            right_aligned_content_paragraphs = 0
            rtl_run_count = 0
            ltr_run_count = 0
            mixed_paragraphs = 0
            mixed_direction_paragraphs = 0
            bidi_control_count = 0
            table_count = 0
            bidi_table_count = 0
            rotated_cell_count = 0
            text_parts: list[str] = []
            xml_text = zf.read("word/document.xml").decode("utf-8", errors="ignore")

            for p in paragraphs:
                ptext = "".join(t.text or "" for t in p.findall(f".//{w('t')}"))
                content = bool(ptext.strip()) and not is_code_like(p)
                if content:
                    content_paragraphs += 1
                ppr = p.find(w("pPr"))
                if content and ppr is not None and has_child(ppr, "bidi"):
                    bidi_content_paragraphs += 1
                if content and is_right_aligned(p):
                    right_aligned_content_paragraphs += 1

                has_fa = bool(re.search(r"[\u0600-\u06FF]", ptext))
                has_lat = bool(re.search(r"[A-Za-z0-9]", ptext))
                rtl_here = 0
                ltr_here = 0
                for run in p.findall(f".//{w('r')}"):
                    rpr = run.find(w("rPr"))
                    is_rtl = rpr is not None and has_child(rpr, "rtl")
                    if is_rtl:
                        rtl_run_count += 1
                        rtl_here += 1
                    else:
                        ltr_run_count += 1
                        ltr_here += 1
                    for t in run.findall(f".//{w('t')}"):
                        value = t.text or ""
                        text_parts.append(value)
                        bidi_control_count += sum(ord(ch) in {0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069} for ch in value)
                if has_fa and has_lat:
                    mixed_paragraphs += 1
                    if rtl_here and ltr_here:
                        mixed_direction_paragraphs += 1

            for table in root.findall(f".//{w('tbl')}"):
                table_count += 1
                tbl_pr = table.find(w("tblPr"))
                if tbl_pr is not None and has_child(tbl_pr, "bidiVisual"):
                    bidi_table_count += 1
                for tcpr in table.findall(f".//{w('tcPr')}"):
                    if tcpr.find(w("textDirection")) is not None:
                        rotated_cell_count += 1

            text = " ".join(text_parts)
            image_parts = [n for n in names if n.startswith("word/media/")]
            png_images = [n for n in image_parts if n.lower().endswith(".png")]
            svg_images = [n for n in image_parts if n.lower().endswith(".svg")]
            report.extend([
                f"DOCX: {path.name}",
                f"- size_bytes: {path.stat().st_size}",
                f"- paragraphs: {len(paragraphs)}",
                f"- content_paragraphs: {content_paragraphs}",
                f"- bidi_content_paragraphs: {bidi_content_paragraphs}",
                f"- right_aligned_content_paragraphs: {right_aligned_content_paragraphs}",
                f"- rtl_runs: {rtl_run_count}",
                f"- ltr_runs: {ltr_run_count}",
                f"- mixed_script_paragraphs: {mixed_paragraphs}",
                f"- mixed_direction_paragraphs: {mixed_direction_paragraphs}",
                f"- bidi_control_chars: {bidi_control_count}",
                f"- tables: {table_count}",
                f"- bidi_tables: {bidi_table_count}",
                f"- rotated_text_cells: {rotated_cell_count}",
                f"- embedded_media: {len(image_parts)}",
                f"- png_media: {len(png_images)}",
                f"- svg_media: {len(svg_images)}",
                f"- text_chars: {len(text.strip())}",
                f"- persian_chars: {len(re.findall(r'[\u0600-\u06FF]', text))}",
                "",
            ])
            if len(text.strip()) < 10000:
                errors.append(f"DOCX text content is unexpectedly short: {path}")
            if content_paragraphs and bidi_content_paragraphs < int(content_paragraphs * 0.98):
                errors.append(f"DOCX is not predominantly whole-document RTL: {path} (bidi={bidi_content_paragraphs}, content={content_paragraphs})")
            if content_paragraphs and right_aligned_content_paragraphs < int(content_paragraphs * 0.98):
                errors.append(f"DOCX content paragraphs are not predominantly right-aligned: {path} (right={right_aligned_content_paragraphs}, content={content_paragraphs})")
            if mixed_paragraphs and mixed_direction_paragraphs < int(mixed_paragraphs * 0.9):
                errors.append(f"DOCX mixed-script paragraphs lack explicit RTL/LTR run separation: {path}")
            if bidi_control_count:
                errors.append(f"DOCX contains Unicode bidi control characters: {path} (count={bidi_control_count})")
            if table_count and bidi_table_count != table_count:
                errors.append(f"DOCX has tables without bidiVisual RTL ordering: {path}")
            if rotated_cell_count:
                errors.append(f"DOCX contains rotated textDirection cells: {path}")
            if "Noto Naskh Arabic" not in xml_text or "Noto Sans" not in xml_text:
                errors.append(f"DOCX font declarations are incomplete: {path}")
            if svg_images:
                errors.append(f"DOCX still contains SVG media; deterministic PNG figure conversion failed: {path}")
            if len(image_parts) < 3:
                errors.append(f"DOCX contains fewer than 3 figure assets: {path}")
    except (zipfile.BadZipFile, ET.ParseError) as exc:
        errors.append(f"Invalid DOCX/OpenXML: {path} ({exc})")


def validate_pdf(path: Path, errors: list[str], report: list[str]) -> None:
    try:
        info = run_capture(["pdfinfo", str(path)])
        m = re.search(r"^Pages:\s+(\d+)", info, flags=re.MULTILINE)
        pages = int(m.group(1)) if m else 0
        text = run_capture(["pdftotext", "-enc", "UTF-8", str(path), "-"])
        persian = len(re.findall(r"[\u0600-\u06FF]", text))
        latin = len(re.findall(r"[A-Za-z]", text))
        fonts = run_capture(["pdffonts", str(path)])
        has_persian_font = bool(re.search(r"NotoNaskh|Noto Naskh", fonts, flags=re.IGNORECASE))
        has_latin_font = bool(re.search(r"NotoSans|Noto Sans", fonts, flags=re.IGNORECASE))
        report.extend([
            f"PDF: {path.name}",
            f"- size_bytes: {path.stat().st_size}",
            f"- pages: {pages}",
            f"- text_chars: {len(text.strip())}",
            f"- persian_chars: {persian}",
            f"- latin_chars: {latin}",
            f"- embedded_persian_font: {has_persian_font}",
            f"- embedded_latin_font: {has_latin_font}",
            "",
        ])
        if pages < 5 or persian < 1000 or latin < 500:
            errors.append(f"PDF content thresholds failed: {path}")
        if not has_persian_font or not has_latin_font:
            errors.append(f"PDF font detection failed: {path}")
        if "filecite" in text or "sandbox:" in text or re.search(r"turn\d+(?:search|file|image)\d+", text):
            errors.append(f"PDF contains internal/tooling markers: {path}")
        with tempfile.TemporaryDirectory() as td:
            prefix = str(Path(td) / "page")
            subprocess.run(["pdftoppm", "-png", str(path), prefix], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            rendered = sorted(Path(td).glob("page-*.png"))
            if len(rendered) != pages:
                errors.append(f"PDF full-page rendering count mismatch: {path} (expected={pages}, rendered={len(rendered)})")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        errors.append(f"PDF validation command failed: {path} ({exc})")


def main() -> int:
    enabled = sorted(ROOT.glob("BOOK/*/.publish-enabled"))
    if not enabled:
        return 0
    errors: list[str] = []
    report: list[str] = ["# Publication QA Report", "", f"Enabled chapters: {len(enabled)}", ""]
    for marker in enabled:
        chapter = marker.parent.name
        out_dir = OUTPUT / chapter
        docx = out_dir / f"{chapter}.docx"
        pdf = out_dir / f"{chapter}.pdf"
        if not docx.exists():
            errors.append(f"Missing DOCX: {docx}")
        else:
            validate_docx(docx, errors, report)
        if not pdf.exists():
            errors.append(f"Missing PDF: {pdf}")
        else:
            validate_pdf(pdf, errors, report)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    report.extend(["## Result", "", "PASS" if not errors else "FAIL", ""])
    if errors:
        report.extend(["## Errors", ""] + [f"- {e}" for e in errors])
    else:
        report.append("Publication satisfies whole-document RTL, whole-document right alignment, mixed-script run direction, table direction, font, deterministic figure and full-page rendering checks.")
    (QA_DIR / "01-foundations-qa.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
