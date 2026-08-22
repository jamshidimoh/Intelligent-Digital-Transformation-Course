from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "BOOK"
DIST = ROOT / "PUBLISH"

# Persian-first publishing policy. The source text remains Persian; English
# technical terms are allowed only where necessary and are rendered inside
# explicit RTL paragraphs with stable bidirectional markers.
PDF_CSS = ROOT / "tools" / "rtl.css"

def chapter_sections(chapter_dir: Path) -> list[Path]:
    sections_dir = chapter_dir / "sections"
    return sorted(sections_dir.glob("*.md"), key=lambda p: p.name)


def normalize_persian(text: str) -> str:
    # Keep the paragraph in RTL context and isolate Latin/number runs so that
    # mixed Persian-English lines do not reorder unpredictably.
    text = text.replace("\u200e", "").replace("\u200f", "")
    text = re.sub(r"([A-Za-z][A-Za-z0-9._+/#:-]*(?:\s+[A-Za-z][A-Za-z0-9._+/#:-]*)*)",
                  r"\u200e\1\u200e", text)
    return "\u200f" + text.strip() + "\u200f"


def build_chapter(chapter_dir: Path) -> Path:
    parts = [chapter_dir / "chapter.md"]
    parts += chapter_sections(chapter_dir)
    refs = chapter_dir / "references.md"
    if refs.exists():
        parts.append(refs)

    output = DIST / "markdown" / f"{chapter_dir.name}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    merged = "\n\n---\n\n".join(p.read_text(encoding="utf-8") for p in parts)
    output.write_text(merged, encoding="utf-8")
    return output


def render_with_pandoc(markdown_file: Path) -> None:
    out_dir = DIST / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = markdown_file.stem
    pdf = out_dir / f"{stem}.pdf"
    docx = out_dir / f"{stem}.docx"

    # Pandoc is retained as the assembly layer. Explicit direction and language
    # variables prevent default LTR layout from leaking into Persian output.
    base = [
        "pandoc", str(markdown_file), "--from", "markdown", "--standalone",
        "-V", "dir=rtl", "-V", "lang=fa-IR", "-V", "mainfont=Noto Naskh Arabic",
    ]

    pdf_cmd = base + ["--css", str(PDF_CSS), "-o", str(pdf)]
    docx_cmd = base + ["-o", str(docx)]

    for cmd, target in ((pdf_cmd, pdf), (docx_cmd, docx)):
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            print("Pandoc is not installed; Markdown build completed without binary rendering.")
            return
        except subprocess.CalledProcessError as exc:
            print(f"Pandoc failed for {target.name}: {exc}", file=sys.stderr)
            return


def main() -> int:
    chapter_dirs = sorted(p for p in BOOK.iterdir() if p.is_dir() and re.match(r"^\d{2}-", p.name))
    if not chapter_dirs:
        print("No chapter directories found.", file=sys.stderr)
        return 1

    for chapter in chapter_dirs:
        md = build_chapter(chapter)
        if chapter.name == "01-foundations":
            render_with_pandoc(md)
        print(f"Built {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
