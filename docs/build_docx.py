"""docs/REPORT.md → docs/REPORT.docx. 실행: python docs/build_docx.py
지원: 제목(#~###), 표, 글머리(들여쓰기 2단), 인용, 이미지 ![](path), **굵게**, `코드`."""
import re
from pathlib import Path
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

SRC = Path(__file__).parent / "REPORT.md"
DST = SRC.with_suffix(".docx")
FONT = "맑은 고딕"


def set_font(style, size=None, bold=None, color=None):
    style.font.name = FONT
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if size:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color:
        style.font.color.rgb = RGBColor.from_string(color)


def inline(p, text):
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**"):
            p.add_run(part[2:-2]).bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        else:
            p.add_run(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", part))  # 링크는 글자만


def shade(cell, hex_):
    tc = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear")
    s.set(qn("w:fill"), hex_)
    tc.append(s)


def table(doc, rows):
    rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = rows[0], [r for r in rows[2:]]
    t = doc.add_table(rows=1 + len(body), cols=len(head))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate([head] + body):
        for j, txt in enumerate(row[: len(head)]):
            c = t.cell(i, j)
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
            inline(c.paragraphs[0], txt)
            for r in c.paragraphs[0].runs:
                r.font.size = Pt(9)
                if i == 0:
                    r.bold = True
            if i == 0:
                shade(c, "DCE6F1")
    doc.add_paragraph()


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for m in ("left_margin", "right_margin"):
        setattr(sec, m, Cm(2.0))
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    set_font(doc.styles["Normal"], 10.5)
    for lvl, size in ((0, 20), (1, 15), (2, 12.5)):
        name = "Title" if lvl == 0 else f"Heading {lvl}"
        set_font(doc.styles[name], size, True, "1F3864")
        doc.styles[name].paragraph_format.keep_with_next = True

    lines = SRC.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("```"):  # 코드 블록
            j = i + 1
            while not lines[j].strip().startswith("```"):
                j += 1
            p = doc.add_paragraph()
            r = p.add_run("\n".join(lines[i + 1 : j]))
            r.font.name, r.font.size = "Consolas", Pt(8.5)
            i = j + 1
            continue
        if s.startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            table(doc, lines[i:j])
            i = j
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s)
        if m:
            doc.add_picture(str(SRC.parent / m.group(2)), width=Cm(17))
            doc.paragraphs[-1].alignment = 1
            if m.group(1):
                cap = doc.add_paragraph()
                cap.alignment = 1
                r = cap.add_run(m.group(1))
                r.italic, r.font.size = True, Pt(9)
        elif s.startswith("#"):
            n = len(s) - len(s.lstrip("#"))
            doc.add_heading(s.lstrip("# "), level=n - 1)
        elif s.startswith(">"):
            p = doc.add_paragraph()
            inline(p, s.lstrip("> "))
            for r in p.runs:
                r.italic = True
                r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
        elif re.match(r"^\s*(- |\d+\. )", ln):
            indent = (len(ln) - len(ln.lstrip())) // 2
            numbered = bool(re.match(r"^\s*\d+\. ", ln))
            style = ("List Number" if numbered else "List Bullet") + (" 2" if indent else "")
            p = doc.add_paragraph(style=style)
            inline(p, re.sub(r"^\s*(- |\d+\. )", "", ln))
        elif s:
            inline(doc.add_paragraph(), s)
        i += 1
    doc.save(DST)
    print(DST)


if __name__ == "__main__":
    main()
