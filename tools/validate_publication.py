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


def validate_docx(path: Path, errors: list[str], report: list[str]) -> None:
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad:
                errors.append(f"DOCX archive is corrupt: {path} ({bad})")
            names = set(zf.namelist())
            if "word/document.xml" not in names:
                errors.append(f"DOCX missing word/document.xml: {path}")
                return
            document_xml = zf.read("word/document.xml")
            root = ET.fromstring(document_xml)
            paragraphs = root.findall(f".//{w('p')}")
            bidi_count = 0
            rtl_run_count = 0
            mixed_run_count = 0
            isolate_count = 0
            table_count = 0
            bidi_table_count = 0
            rotated_cell_count = 0
            text_parts: list[str] = []
            xml_text = document_xml.decode("utf-8", errors="ignore")

            for p in paragraphs:
                ppr = p.find(w("pPr"))
                if ppr is not None and has_child(ppr, "bidi"):
                    bidi_count += 1

                run_elements = p.findall(f".//{w('r')}")
                for run in run_elements:
                    rpr = run.find(w("rPr"))
                    if rpr is not None and has_child(rpr, "rtl"):
                        rtl_run_count += 1
                    for t in run.findall(f".//{w('t')}"):
                        value = t.text or ""
                        text_parts.append(value)
                        isolate_count += value.count("\u2066") + value.count("\u2069")

                ptext = "".join(t.text or "" for t in p.findall(f".//{w('t')}"))
                has_fa = bool(re.search(r"[\u0600-\u06FF]", ptext))
                has_lat = bool(re.search(r"[A-Za-z]", ptext))
                if has_fa and has_lat:
                    mixed_run_count += sum(
                        1
                        for run in run_elements
                        if run.find(w("rPr")) is not None
                        and (
                            has_child(run.find(w("rPr")), "rtl")
                            or has_child(run.find(w("rPr")), "lang")
                        )
                    )

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
            required_bidi = max(5, len(paragraphs) // 10)
            report.extend([
                f"DOCX: {path.name}",
                f"- size_bytes: {path.stat().st_size}",
                f"- paragraphs: {len(paragraphs)}",
                f"- bidi_paragraphs: {bidi_count}",
                f"- rtl_runs: {rtl_run_count}",
                f"- mixed_script_run_checks: {mixed_run_count}",
                f"- bidi_isolates: {isolate_count}",
                f"- tables: {table_count}",
                f"- bidi_tables: {bidi_table_count}",
                f"- rotated_text_cells: {rotated_cell_count}",
                f"- text_chars: {len(text.strip())}",
                f"- embedded_media: {len(image_parts)}",
                f"- persian_chars: {len(re.findall(r'[\u0600-\u06FF]', text))}",
                "",
            ])

            if len(text.strip()) < 10000:
                errors.append(f"DOCX text content is unexpectedly short: {path}")
            if bidi_count < required_bidi:
                errors.append(f"DOCX has insufficient RTL paragraph direction: {path} (bidi={bidi_count}, required>={required_bidi})")
            if rtl_run_count == 0 and re.search(r"[\u0600-\u06FF]", text):
                errors.append(f"DOCX contains Persian text but no explicit RTL runs: {path}")
            if mixed_run_count > 0 and isolate_count == 0:
                errors.append(f"DOCX contains mixed Persian/Latin paragraphs but no bidi isolation markers: {path}")
            if table_count and bidi_table_count != table_count:
                errors.append(f"DOCX has tables without bidiVisual RTL ordering: {path} (tables={table_count}, bidi_tables={bidi_table_count})")
            if rotated_cell_count:
                errors.append(f"DOCX contains rotated textDirection cells: {path} (count={rotated_cell_count})")
            if "Noto Naskh Arabic" not in xml_text:
                errors.append(f"DOCX does not declare the required Persian font: {path}")
            if "Noto Sans" not in xml_text:
                errors.append(f"DOCX does not declare the required Latin/technical font: {path}")
            if "filecite" in text or "sandbox:" in text or re.search(r"turn\d+(?:search|file|image)\d+", text):
                errors.append(f"DOCX contains internal/tooling markers: {path}")
            if len(image_parts) < 3:
                errors.append(f"DOCX contains fewer than 3 embedded figure assets: {path} (found={len(image_parts)})")
    except zipfile.BadZipFile:
        errors.append(f"DOCX is not a valid ZIP/OpenXML package: {path}")
    except ET.ParseError as exc:
        errors.append(f"DOCX XML is malformed: {path} ({exc})")


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
        if pages < 5:
            errors.append(f"PDF has unexpectedly few pages: {path} (pages={pages})")
        if persian < 1000:
            errors.append(f"PDF contains too little Persian text: {path} (chars={persian})")
        if latin < 500:
            errors.append(f"PDF contains too little Latin/technical text: {path} (chars={latin})")
        if not has_persian_font:
            errors.append(f"PDF does not embed/detect Noto Naskh Arabic: {path}")
        if not has_latin_font:
            errors.append(f"PDF does not embed/detect Noto Sans: {path}")
        if "filecite" in text or "sandbox:" in text or re.search(r"turn\d+(?:search|file|image)\d+", text):
            errors.append(f"PDF contains internal/tooling markers: {path}")

        with tempfile.TemporaryDirectory() as td:
            prefix = str(Path(td) / "page")
            subprocess.run(
                ["pdftoppm", "-png", str(path), prefix],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            rendered = sorted(Path(td).glob("page-*.png"))
            if len(rendered) != pages:
                errors.append(f"PDF full-page rendering count mismatch: {path} (expected={pages}, rendered={len(rendered)})")
            small = [p for p in rendered if p.stat().st_size < 5000]
            if small:
                errors.append(f"PDF has suspiciously small rendered pages: {path} (count={len(small)})")
    except subprocess.CalledProcessError as exc:
        errors.append(f"PDF validation command failed: {path} ({exc})")
    except FileNotFoundError as exc:
        errors.append(f"Required PDF QA utility missing: {exc}")


def main() -> int:
    enabled = sorted(ROOT.glob("BOOK/*/.publish-enabled"))
    if not enabled:
        print("No publish-enabled chapters found.")
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
        elif docx.stat().st_size < 20_000:
            errors.append(f"DOCX is unexpectedly small: {docx}")
        else:
            validate_docx(docx, errors, report)
        if not pdf.exists():
            errors.append(f"Missing PDF: {pdf}")
        elif pdf.stat().st_size < 20_000:
            errors.append(f"PDF is unexpectedly small: {pdf}")
        else:
            validate_pdf(pdf, errors, report)

    QA_DIR.mkdir(parents=True, exist_ok=True)
    report.extend(["## Result", "", "PASS" if not errors else "FAIL", ""])
    if errors:
        report.extend(["## Errors", ""] + [f"- {error}" for error in errors])
    else:
        report.append("All structural, paragraph-level RTL, run-level RTL, bilingual-text, table-direction, font, figure and full-page PDF-render checks passed.")
    (QA_DIR / "01-foundations-qa.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"QA report written to {QA_DIR / '01-foundations-qa.md'}")
    if errors:
        for error in errors:
            print(f"QA-ERROR: {error}")
    else:
        print(f"Validated {len(enabled)} publish-enabled chapter(s) with structural, RTL, bilingual-text, font, figure and full-page PDF-render checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
