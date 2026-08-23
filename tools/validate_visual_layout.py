from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "PUBLISH" / "CHAPTERS"
BOOK_DIR = ROOT / "BOOK"
W = "http://www.xpdfreader.com/pdfxml/"


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("‌", "")


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout


def source_headings(chapter: Path) -> list[str]:
    heads: list[str] = []
    for md in sorted(chapter.rglob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^#{1,4}\s+(.+?)\s*$", line)
            if m:
                value = re.sub(r"[`*_]", "", m.group(1)).strip()
                if value:
                    heads.append(value)
    return heads


def pdf_lines(pdf: Path):
    xml = run(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(pdf), "-"])
    root = ET.fromstring(xml)
    result = []
    for page in root.iter("page"):
        width = float(page.attrib.get("width", "0"))
        for line in page.iter("line"):
            words = list(line.iter("word"))
            text = " ".join((w.text or "") for w in words)
            if not text.strip() or not words:
                continue
            xmax = max(float(w.attrib.get("xMax", "0")) for w in words)
            xmin = min(float(w.attrib.get("xMin", "0")) for w in words)
            result.append((width, xmin, xmax, text))
    return result


def main() -> int:
    errors: list[str] = []
    notes: list[str] = ["# Visual Layout QA", ""]
    enabled = sorted(BOOK_DIR.glob("*/*.publish-enabled"))
    for marker in enabled:
        chapter = marker.parent
        slug = chapter.name
        pdf = PDF_DIR / slug / f"{slug}.pdf"
        if not pdf.exists():
            errors.append(f"Missing PDF: {pdf}")
            continue
        lines = pdf_lines(pdf)
        headings = source_headings(chapter)
        matched = 0
        aligned = 0
        page_width = 0.0
        details = []
        for heading in headings:
            target = norm(heading)
            found = None
            for width, xmin, xmax, text in lines:
                cleaned = norm(text)
                if target and (target in cleaned or cleaned in target):
                    found = (width, xmin, xmax, text)
                    break
            if not found:
                details.append(f"- NOT FOUND: {heading}")
                continue
            matched += 1
            width, xmin, xmax, text = found
            page_width = max(page_width, width)
            # A4 right margin is 2.35 cm ~= 66.5 pt. Permit 26 pt of renderer
            # drift, but reject headings that are visibly left/center aligned.
            expected_right = width - 66.5
            delta = abs(xmax - expected_right)
            ok = delta <= 26.0
            if ok:
                aligned += 1
            else:
                errors.append(
                    f"Heading is not right-aligned in PDF: '{heading}' "
                    f"(xMax={xmax:.1f}, expected≈{expected_right:.1f})"
                )
            details.append(
                f"- {heading}: {'RIGHT' if ok else 'FAIL'}; xMax={xmax:.1f}; expected≈{expected_right:.1f}"
            )

        notes.extend([
            f"## {slug}",
            f"- source_headings: {len(headings)}",
            f"- pdf_heading_matches: {matched}",
            f"- right_aligned_matches: {aligned}",
            "",
        ])
        notes.extend(details)
        notes.append("")

    notes.extend(["## Result", "", "PASS" if not errors else "FAIL", ""])
    if errors:
        notes.extend(["## Errors", ""] + [f"- {e}" for e in errors])
    out = ROOT / "PUBLISH" / "QA" / "visual-layout-qa.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(notes), encoding="utf-8")
    print("\n".join(notes))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
