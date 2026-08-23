from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "PUBLISH" / "CHAPTERS"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def run_capture(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout


def validate_docx(path: Path, errors: list[str]) -> None:
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
            paragraphs = root.findall(f".//{{{W_NS}}}p")
            bidi_count = 0
            rtl_count = 0
            text_parts: list[str] = []
            xml_text = document_xml.decode("utf-8", errors="ignore")
            for p in paragraphs:
                ppr = p.find(f"{{{W_NS}}}pPr")
                if ppr is not None and ppr.find(f"{{{W_NS}}}bidi") is not None:
                    bidi_count += 1
                if ppr is not None and ppr.find(f"{{{W_NS}}}rtl") is not None:
                    rtl_count += 1
                for t in p.findall(f".//{{{W_NS}}}t"):
                    text_parts.append(t.text or "")
            text = " ".join(text_parts)
            if len(text.strip()) < 10000:
                errors.append(f"DOCX text content is unexpectedly short: {path}")
            if bidi_count < max(5, len(paragraphs) // 10):
                errors.append(f"DOCX has insufficient RTL paragraph direction: {path} (bidi={bidi_count}, paragraphs={len(paragraphs)})")
            if "Noto Naskh Arabic" not in xml_text:
                errors.append(f"DOCX does not declare the required Persian font: {path}")
            if "filecite" in text or "sandbox:" in text or re.search(r"turn\d+(?:search|file|image)\d+", text):
                errors.append(f"DOCX contains internal/tooling markers: {path}")
            image_parts = [n for n in names if n.startswith("word/media/")]
            if len(image_parts) < 3:
                errors.append(f"DOCX contains fewer than 3 embedded figure assets: {path} (found={len(image_parts)})")
    except zipfile.BadZipFile:
        errors.append(f"DOCX is not a valid ZIP/OpenXML package: {path}")
    except ET.ParseError as exc:
        errors.append(f"DOCX XML is malformed: {path} ({exc})")


def validate_pdf(path: Path, errors: list[str]) -> None:
    try:
        info = run_capture(["pdfinfo", str(path)])
        m = re.search(r"^Pages:\s+(\d+)", info, flags=re.MULTILINE)
        pages = int(m.group(1)) if m else 0
        if pages < 5:
            errors.append(f"PDF has unexpectedly few pages: {path} (pages={pages})")
        text = run_capture(["pdftotext", "-enc", "UTF-8", str(path), "-"])
        persian = len(re.findall(r"[\u0600-\u06FF]", text))
        latin = len(re.findall(r"[A-Za-z]", text))
        if persian < 1000:
            errors.append(f"PDF contains too little Persian text: {path} (chars={persian})")
        if latin < 500:
            errors.append(f"PDF contains too little Latin/technical text: {path} (chars={latin})")
        if "filecite" in text or "sandbox:" in text or re.search(r"turn\d+(?:search|file|image)\d+", text):
            errors.append(f"PDF contains internal/tooling markers: {path}")
        with tempfile.TemporaryDirectory() as td:
            prefix = str(Path(td) / "page")
            subprocess.run(["pdftoppm", "-f", "1", "-singlefile", "-png", str(path), prefix], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if not Path(prefix + ".png").exists():
                errors.append(f"PDF first-page rendering failed: {path}")
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
            validate_docx(docx, errors)
        if not pdf.exists():
            errors.append(f"Missing PDF: {pdf}")
        elif pdf.stat().st_size < 20_000:
            errors.append(f"PDF is unexpectedly small: {pdf}")
        else:
            validate_pdf(pdf, errors)

    if errors:
        print("Publication validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(enabled)} publish-enabled chapter(s) with structural, RTL, bilingual-text, figure and PDF-render checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
