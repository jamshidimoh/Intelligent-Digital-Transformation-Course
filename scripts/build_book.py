from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "BOOK"
OUT = ROOT / "PUBLISH"


def assemble_chapter(chapter_dir: Path) -> str:
    sections = chapter_dir / "sections"
    files = sorted(sections.glob("*.md"))
    parts = []
    for path in files:
        parts.append(path.read_text(encoding="utf-8").strip())
    refs = chapter_dir / "references.md"
    if refs.exists():
        parts.append(refs.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(p for p in parts if p)


def main():
    parser = argparse.ArgumentParser(description="Assemble the textbook chapters into Markdown.")
    parser.add_argument("--chapter", default="01-foundations", help="Chapter directory name")
    args = parser.parse_args()

    chapter_dir = BOOK / args.chapter
    if not chapter_dir.exists():
        raise SystemExit(f"Chapter not found: {chapter_dir}")

    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / f"{args.chapter}.md"
    output.write_text(assemble_chapter(chapter_dir) + "\n", encoding="utf-8")
    print(f"Built: {output}")


if __name__ == "__main__":
    main()
