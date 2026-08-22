from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "BOOK"
DIST = ROOT / "PUBLISH"


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
    output.write_text("\n\n---\n\n".join(p.read_text(encoding="utf-8") for p in parts), encoding="utf-8")
    return output


def render_with_pandoc(markdown_file: Path) -> None:
    out_dir = DIST / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = markdown_file.stem
    pdf = out_dir / f"{stem}.pdf"
    docx = out_dir / f"{stem}.docx"

    for target in (pdf, docx):
        cmd = ["pandoc", str(markdown_file), "-o", str(target), "--from", "markdown", "--standalone"]
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            print("Pandoc is not installed; Markdown build completed without PDF/DOCX rendering.")
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
