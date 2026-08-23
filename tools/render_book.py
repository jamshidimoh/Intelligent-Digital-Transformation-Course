from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_DIR = ROOT / "PUBLISH" / "markdown"
OUTPUT_DIR = ROOT / "PUBLISH" / "CHAPTERS"
REFERENCE_DOCX = ROOT / "PUBLISH" / "reference.docx"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def render_one(md: Path) -> None:
    slug = md.stem
    chapter_dir = OUTPUT_DIR / slug
    chapter_dir.mkdir(parents=True, exist_ok=True)

    docx = chapter_dir / f"{slug}.docx"
    pdf = chapter_dir / f"{slug}.pdf"

    resource_path = ROOT / "BOOK" / slug
    cmd = [
        "pandoc", str(md),
        "--from", "markdown",
        "--standalone",
        "--resource-path", str(resource_path),
        "--reference-doc", str(REFERENCE_DOCX),
        "--metadata", f"title=تحول دیجیتال هوشمند - {slug}",
        "-o", str(docx),
    ]
    run(cmd)

    lo_out = chapter_dir / "_lo"
    lo_out.mkdir(exist_ok=True)
    run([
        "libreoffice", "--headless", "--convert-to", "pdf",
        "--outdir", str(lo_out), str(docx),
    ])
    produced = lo_out / f"{docx.stem}.pdf"
    if not produced.exists():
        raise RuntimeError(f"LibreOffice did not produce {produced}")
    shutil.move(str(produced), str(pdf))
    shutil.rmtree(lo_out, ignore_errors=True)
    print(f"Published: {docx}")
    print(f"Published: {pdf}")


def main() -> int:
    if not MARKDOWN_DIR.exists():
        print("Markdown build directory does not exist.", file=sys.stderr)
        return 1
    if not REFERENCE_DOCX.exists():
        print("Reference DOCX template does not exist. Run tools/build_book.py first.", file=sys.stderr)
        return 1
    files = sorted(MARKDOWN_DIR.glob("*.md"))
    if not files:
        print("No built chapter Markdown files found.", file=sys.stderr)
        return 1
    for md in files:
        render_one(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
