from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
ET.register_namespace("w", W)
PERSIAN_FONT = "Noto Naskh Arabic"
LATIN_FONT = "Noto Sans"
FA_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def w(tag: str) -> str:
    return f"{{{W}}}{tag}"


def ensure(parent, tag: str):
    node = parent.find(w(tag))
    if node is None:
        node = ET.SubElement(parent, w(tag))
    return node


def set_bool(parent, tag: str, enabled: bool) -> None:
    node = parent.find(w(tag))
    if enabled and node is None:
        ET.SubElement(parent, w(tag))
    elif not enabled and node is not None:
        parent.remove(node)


def set_jc(ppr, value: str) -> None:
    jc = ensure(ppr, "jc")
    jc.set(w("val"), value)


def set_ind(ppr, first_line_twips: int = 0, left: int | None = None, right: int | None = None) -> None:
    ind = ensure(ppr, "ind")
    for attr in ("left", "right", "start", "end", "firstLine", "hanging"):
        ind.attrib.pop(w(attr), None)
    ind.set(w("firstLine"), str(first_line_twips))
    if left is not None:
        ind.set(w("left"), str(left))
    if right is not None:
        ind.set(w("right"), str(right))


def paragraph_text(p) -> str:
    return "".join((t.text or "") for t in p.findall(".//" + w("t")))


def style_id(p) -> str:
    ppr = p.find(w("pPr"))
    if ppr is None:
        return ""
    pstyle = ppr.find(w("pStyle"))
    return (pstyle.get(w("val"), "") if pstyle is not None else "")


def is_code(p) -> bool:
    sid = style_id(p).lower()
    text = paragraph_text(p).strip()
    return "code" in sid or text.startswith(("```", "$ ", ">> "))


def has_drawing(p) -> bool:
    return p.find(".//" + w("drawing")) is not None


def fix_paragraph(p) -> None:
    ppr = ensure(p, "pPr")
    sid = style_id(p)
    sid_l = sid.lower()
    text = paragraph_text(p)
    code = is_code(p)
    caption = sid_l == "caption"
    drawing = has_drawing(p)

    set_bool(ppr, "bidi", not code)
    set_bool(ppr, "widowControl", True)
    if sid_l.startswith("heading"):
        set_bool(ppr, "keepNext", True)

    if code:
        set_jc(ppr, "left")
        set_ind(ppr, 0)
    elif caption or drawing:
        set_jc(ppr, "center")
        set_ind(ppr, 0)
    else:
        set_jc(ppr, "right")
        if sid_l.startswith("heading") or sid_l.startswith("list"):
            set_ind(ppr, 0, left=110, right=310)
        else:
            set_ind(ppr, 238)

    for r in p.findall(".//" + w("r")):
        txt = "".join((t.text or "") for t in r.findall(".//" + w("t")))
        rpr = ensure(r, "rPr")
        rtl = bool(FA_RE.search(txt))
        set_bool(rpr, "rtl", rtl)
        lang = ensure(rpr, "lang")
        lang.set(w("val"), "fa-IR" if rtl else "en-US")
        rfonts = ensure(rpr, "rFonts")
        rfonts.set(w("ascii"), LATIN_FONT)
        rfonts.set(w("hAnsi"), LATIN_FONT)
        rfonts.set(w("cs"), PERSIAN_FONT if rtl else LATIN_FONT)
        rfonts.set(w("eastAsia"), LATIN_FONT)


def fix_xml(data: bytes) -> bytes:
    root = ET.fromstring(data)
    for p in root.findall(".//" + w("p")):
        fix_paragraph(p)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def finalize(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="docx-finalize-") as td:
        tmp = Path(td) / path.name
        with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml" or item.filename.startswith("word/header") or item.filename.startswith("word/footer"):
                    data = fix_xml(data)
                zout.writestr(item, data)
        tmp.replace(path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: finalize_docx_rtl.py <docx>")
    p = Path(sys.argv[1])
    if not p.exists():
        raise SystemExit(f"Missing DOCX: {p}")
    finalize(p)
    print(f"Finalized deterministic Persian RTL layout: {p}")
