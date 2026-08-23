from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_DIR = ROOT / "PUBLISH" / "markdown"
OUTPUT_DIR = ROOT / "PUBLISH" / "CHAPTERS"
REFERENCE_DOCX = ROOT / "PUBLISH" / "reference-template.docx"
POSTPROCESS = ROOT / "tools" / "postprocess_rtl_docx.py"
FINALIZER = ROOT / "tools" / "finalize_docx_rtl.py"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def prepare_render_assets(chapter_md: Path, resource_path: Path, workdir: Path) -> tuple[Path, Path]:
    staging = workdir / resource_path.name
    staging.mkdir(parents=True, exist_ok=True)
    source_figures = resource_path / "figures"
    target_figures = staging / "figures"
    if source_figures.exists():
        target_figures.mkdir(parents=True, exist_ok=True)
        for asset in source_figures.iterdir():
            if not asset.is_file():
                continue
            if asset.suffix.lower() == ".svg":
                png = target_figures / f"{asset.stem}.png"
                run(["rsvg-convert", "-f", "png", "-o", str(png), str(asset)])
            else:
                shutil.copy2(asset, target_figures / asset.name)

    text = chapter_md.read_text(encoding="utf-8")
    text = re.sub(r"(?P<path>figures/[^)\"']+)\.svg", r"\g<path>.png", text, flags=re.IGNORECASE)
    staged_md = workdir / chapter_md.name
    staged_md.write_text(text, encoding="utf-8")
    return staged_md, staging


def normalize_docx_image_layout(docx: Path) -> None:
    doc = Document(docx)
    for paragraph in doc.paragraphs:
        has_drawing = bool(paragraph._p.xpath(".//w:drawing"))
        if has_drawing:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = 0
            paragraph.paragraph_format.space_before = 8
            paragraph.paragraph_format.space_after = 5
    doc.save(docx)


def render_one(md: Path) -> None:
    slug = md.stem
    chapter_dir = OUTPUT_DIR / slug
    chapter_dir.mkdir(parents=True, exist_ok=True)
    resource_path = ROOT / "BOOK" / slug

    with tempfile.TemporaryDirectory(prefix="book-render-") as td:
        workdir = Path(td)
        staged_md, staged_resource = prepare_render_assets(md, resource_path, workdir)
        docx = chapter_dir / f"{slug}.docx"
        pdf = chapter_dir / f"{slug}.pdf"
        run([
            "pandoc", str(staged_md),
            "--from", "markdown",
            "--standalone",
            "--resource-path", str(staged_resource),
            "--reference-doc", str(REFERENCE_DOCX),
            "--metadata", "dir=rtl",
            "--metadata", "lang=fa-IR",
            "--metadata", f"title=تحول دیجیتال هوشمند - {slug}",
            "-o", str(docx),
        ])

    run([sys.executable, str(POSTPROCESS), str(docx)])
    normalize_docx_image_layout(docx)
    # Final XML-level pass removes any ambiguity between Word paragraph
    # alignment/Bidi semantics and LibreOffice's DOCX renderer. It runs last,
    # after image layout normalization, while preserving figure paragraphs as
    # centered exceptions.
    run([sys.executable, str(FINALIZER), str(docx)])

    lo_out = chapter_dir / "_lo"
    if lo_out.exists():
        shutil.rmtree(lo_out)
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
    for child in OUTPUT_DIR.iterdir() if OUTPUT_DIR.exists() else []:
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for md in files:
        render_one(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
