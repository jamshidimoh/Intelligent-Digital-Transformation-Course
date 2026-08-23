from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "BOOK"
DIST = ROOT / "PUBLISH"
REFERENCE_DOCX = DIST / "reference-template.docx"
PUBLICATION_MARKER = ".publish-enabled"


def chapter_sections(chapter_dir: Path) -> list[Path]:
    sections_dir = chapter_dir / "sections"
    return sorted(sections_dir.glob("*.md"), key=lambda p: p.name)


def eligible_chapters() -> list[Path]:
    chapters = sorted(
        p for p in BOOK.iterdir() if p.is_dir() and re.match(r"^\d{2}-", p.name)
    )
    return [p for p in chapters if (p / PUBLICATION_MARKER).exists()]


def normalize_assets(markdown: str) -> str:
    markdown = re.sub(r"\]\(\.\./figures/", "](figures/", markdown)
    markdown = re.sub(r"src=[\"']\.\./figures/", "src=\"figures/", markdown)
    return markdown


def build_chapter(chapter_dir: Path) -> Path:
    parts = [chapter_dir / "chapter.md"]
    parts += chapter_sections(chapter_dir)
    refs = chapter_dir / "references.md"
    if refs.exists():
        parts.append(refs)

    output = DIST / "markdown" / f"{chapter_dir.name}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    # Sections already begin with Heading 1 and the reference template applies
    # page-break-before there. Do not inject horizontal rules between sections.
    merged = "\n\n".join(
        normalize_assets(p.read_text(encoding="utf-8")) for p in parts
    )
    output.write_text(merged, encoding="utf-8")
    return output


def create_reference_docx() -> None:
    script = ROOT / "tools" / "create_reference_docx.py"
    REFERENCE_DOCX.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(script)], check=True)


def main() -> int:
    chapters = eligible_chapters()
    if not chapters:
        print("No publication-eligible chapters found.", file=sys.stderr)
        return 1

    markdown_dir = DIST / "markdown"
    if markdown_dir.exists():
        for old in markdown_dir.glob("*.md"):
            old.unlink()
    create_reference_docx()
    for chapter in chapters:
        md = build_chapter(chapter)
        print(f"Built {md}")
    print("Publication-eligible chapters:")
    for chapter in chapters:
        print(f"- {chapter.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
