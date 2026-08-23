from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "PUBLISH" / "CHAPTERS"


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
        if not pdf.exists():
            errors.append(f"Missing PDF: {pdf}")
        elif pdf.stat().st_size < 20_000:
            errors.append(f"PDF is unexpectedly small: {pdf}")

    if errors:
        print("Publication validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(enabled)} publish-enabled chapter(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
