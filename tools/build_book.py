from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "BOOK"
DIST = ROOT / "PUBLISH"
REFERENCE_DOCX = DIST / "reference.docx"


def chapter_sections(chapter_dir: Path) -> list[Path]:
    sections_dir = chapter_dir / "sections"
    return sorted(sections_dir.glob("*.md"), key=lambda p: p.name)


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


def create_reference_docx() -> None:
    script = ROOT / "tools" / "create_reference_docx.py"
    REFERENCE_DOCX.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(script)], check=True)


def main() -> int:
    chapter_dirs = sorted(
        p for p in BOOK.iterdir() if p.is_dir() and re.match(r"^\d{2}-", p.name)
    )
    if not chapter_dirs:
        print("No chapter directories found.", file=sys.stderr)
        return 1

    create_reference_docx()
    for chapter in chapter_dirs:
        md = build_chapter(chapter)
        print(f"Built {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
