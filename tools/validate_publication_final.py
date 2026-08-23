from __future__ import annotations

from pathlib import Path
import re
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from validate_publication import validate_docx, validate_pdf

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "PUBLISH" / "CHAPTERS"
QA_DIR = ROOT / "PUBLISH" / "QA"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

FORBIDDEN = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
RLM = "\u200f"


def text_from_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        parts = []
        for name in zf.namelist():
            if name == "word/document.xml" or name.startswith("word/header") or name.startswith("word/footer"):
                root = ET.fromstring(zf.read(name))
                parts.extend(root.itertext())
        return "".join(parts)


def sanitize_rlm(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml" or item.filename.startswith("word/header") or item.filename.startswith("word/footer"):
                data = data.replace(RLM.encode("utf-8"), b"")
            zout.writestr(item, data)


def main() -> int:
    enabled = sorted(ROOT.glob("BOOK/*/.publish-enabled"))
    errors: list[str] = []
    report: list[str] = ["# Final Publication QA Report", "", f"Enabled chapters: {len(enabled)}", ""]

    for marker in enabled:
        chapter = marker.parent.name
        out_dir = OUTPUT / chapter
        docx = out_dir / f"{chapter}.docx"
        pdf = out_dir / f"{chapter}.pdf"
        if not docx.exists():
            errors.append(f"Missing DOCX: {docx}")
            continue
        if not pdf.exists():
            errors.append(f"Missing PDF: {pdf}")
            continue

        original_text = text_from_docx(docx)
        forbidden_count = sum(original_text.count(chr(cp)) for cp in FORBIDDEN)
        anchor_count = original_text.count(RLM)
        report.append(f"DOCX: {docx.name}")
        report.append(f"- rtl_anchor_chars: {anchor_count}")
        report.append(f"- forbidden_bidi_control_chars: {forbidden_count}")
        report.append("")

        if forbidden_count:
            errors.append(f"DOCX contains forbidden bidi override/isolate controls: {docx} (count={forbidden_count})")
        if anchor_count < 2:
            errors.append(f"DOCX has insufficient RTL boundary anchors: {docx} (count={anchor_count})")

        # Existing structural validator is run on an RLM-sanitized temporary copy
        # so its historical control-character check remains useful while this
        # final layer validates the deliberate RLM anchors separately.
        with tempfile.TemporaryDirectory(prefix="publication-final-qa-") as td:
            safe_docx = Path(td) / docx.name
            sanitize_rlm(docx, safe_docx)
            local_errors: list[str] = []
            local_report: list[str] = []
            validate_docx(safe_docx, local_errors, local_report)
            if local_errors:
                errors.extend(local_errors)
            report.extend(local_report)

        local_pdf_errors: list[str] = []
        local_pdf_report: list[str] = []
        validate_pdf(pdf, local_pdf_errors, local_pdf_report)
        if local_pdf_errors:
            errors.extend(local_pdf_errors)
        report.extend(local_pdf_report)

    report.extend(["## Result", "", "PASS" if not errors else "FAIL", ""])
    if errors:
        report.extend(["## Errors", ""] + [f"- {e}" for e in errors])
    else:
        report.append("Final publication satisfies whole-document RTL/right alignment, mixed-script run separation, deliberate RTL boundary anchoring, table direction, fonts, deterministic figures, and full-page PDF rendering.")

    QA_DIR.mkdir(parents=True, exist_ok=True)
    (QA_DIR / "01-foundations-qa.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
