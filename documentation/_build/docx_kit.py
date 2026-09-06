# -*- coding: utf-8 -*-
"""docx_kit - shared formatting toolkit for Palisade milestone documents.

Used by build.py to render one .docx per milestone. Keeping the generator in
the repo means every milestone document comes out with identical structure and
styling, and any of them can be regenerated from source.

Requires: pip install python-docx
"""
import re
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---------- palette ----------
INK        = RGBColor(0x1A, 0x1F, 0x2B)   # near-black body text
SLATE      = RGBColor(0x44, 0x50, 0x63)   # secondary text
TEAL       = RGBColor(0x0F, 0x62, 0x6B)   # H1
TEAL_D     = RGBColor(0x0B, 0x4A, 0x52)   # H2
AMBER      = RGBColor(0x8A, 0x5A, 0x00)
CRIMSON    = RGBColor(0x9B, 0x2C, 0x2C)
GREEN      = RGBColor(0x1E, 0x6B, 0x3A)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)

F_HDR      = "0F626B"   # table header fill
F_ZEBRA    = "F2F6F7"   # zebra row fill
F_CODE     = "F4F5F7"   # code block fill
F_NOTE     = "EAF3F4"   # info callout
F_WARN     = "FDF3E3"   # warning callout
F_DANGER   = "FBECEC"   # danger callout
F_OK       = "EBF5EE"   # success callout
F_COVER    = "0F626B"

BODY_FONT = "Calibri"
MONO_FONT = "Consolas"


# ---------- low-level xml ----------
def _shade(el, fill):
    pr = el.get_or_add_tcPr() if hasattr(el, "get_or_add_tcPr") else el.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def shade_cell(cell, fill):
    _shade(cell._tc, fill)


def shade_par(par, fill):
    _shade(par._p, fill)


def cell_borders(cell, color="D8DEE3", sz=4, edges=("top", "bottom", "left", "right")):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for e in edges:
        el = OxmlElement(f"w:{e}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), color)
        borders.append(el)
    tcPr.append(borders)


def left_accent(cell, color, sz=24):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    el = OxmlElement("w:left")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:color"), color)
    borders.append(el)
    tcPr.append(borders)


def set_col_widths(table, widths_in):
    table.autofit = False
    for row in table.rows:
        for i, w in enumerate(widths_in):
            if i < len(row.cells):
                row.cells[i].width = Inches(w)


def keep_with_next(par):
    par.paragraph_format.keep_with_next = True


def no_space(par, before=0, after=0):
    par.paragraph_format.space_before = Pt(before)
    par.paragraph_format.space_after = Pt(after)


# ---------- rich text mini-parser: **bold**, *italic*, __italic__, `code` (nestable) ----------
TOKEN = re.compile(r"(\*\*.+?\*\*|`[^`]+?`|__.+?__|\*[^*]+?\*)", re.S)


def _emit(par, text, size, color, bold=False, italic=False, mono=False):
    r = par.add_run(text)
    r.bold = bold
    r.italic = italic
    if mono:
        r.font.name = MONO_FONT
        r.font.size = Pt(size - 1.0)
        r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x57)
    else:
        r.font.name = BODY_FONT
        r.font.size = Pt(size)
        r.font.color.rgb = color
    return r


def add_rich(par, text, size=10.5, color=INK, base_bold=False, base_italic=False):
    """Render lightweight markdown into runs. Recurses so `code` nested inside
    **bold** (and vice versa) keeps both styles."""
    for chunk in TOKEN.split(text):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            add_rich(par, chunk[2:-2], size, color, True, base_italic)
        elif chunk.startswith("__") and chunk.endswith("__") and len(chunk) > 4:
            add_rich(par, chunk[2:-2], size, color, base_bold, True)
        elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
            _emit(par, chunk[1:-1], size, color, base_bold, base_italic, mono=True)
        elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
            add_rich(par, chunk[1:-1], size, color, base_bold, True)
        else:
            _emit(par, chunk, size, color, base_bold, base_italic)
    return par


# ---------- document scaffolding ----------
class Doc:
    def __init__(self):
        self.d = Document()
        self._setup()

    def _setup(self):
        s = self.d.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)   # A4
        s.left_margin = s.right_margin = Inches(0.85)
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.75)

        n = self.d.styles["Normal"]
        n.font.name = BODY_FONT
        n.font.size = Pt(10.5)
        n.font.color.rgb = INK
        n.paragraph_format.space_after = Pt(7)
        n.paragraph_format.line_spacing = 1.13

        for name, sz, col, sb, sa in (
            ("Heading 1", 19, TEAL,   20, 8),
            ("Heading 2", 14, TEAL_D, 15, 6),
            ("Heading 3", 11.5, SLATE, 11, 4),
        ):
            st = self.d.styles[name]
            st.font.name = BODY_FONT
            st.font.size = Pt(sz)
            st.font.color.rgb = col
            st.font.bold = True
            st.paragraph_format.space_before = Pt(sb)
            st.paragraph_format.space_after = Pt(sa)
            st.paragraph_format.keep_with_next = True

    # -- structural --
    def h1(self, t, page_break=True):
        if page_break:
            self.d.add_page_break()
        p = self.d.add_heading(t, 1)
        pb = OxmlElement("w:pBdr"); bot = OxmlElement("w:bottom")
        bot.set(qn("w:val"), "single"); bot.set(qn("w:sz"), "8")
        bot.set(qn("w:space"), "6"); bot.set(qn("w:color"), "0F626B")
        pb.append(bot); p._p.get_or_add_pPr().append(pb)
        return p

    def h2(self, t):
        return self.d.add_heading(t, 2)

    def h3(self, t):
        return self.d.add_heading(t, 3)

    def p(self, t="", size=10.5, color=INK, bold=False, after=7, align=None):
        par = self.d.add_paragraph()
        add_rich(par, t, size=size, color=color, base_bold=bold)
        par.paragraph_format.space_after = Pt(after)
        if align:
            par.alignment = align
        return par

    def bullet(self, t, size=10.5, level=0):
        par = self.d.add_paragraph(style="List Bullet")
        par.paragraph_format.left_indent = Inches(0.26 + 0.24 * level)
        par.paragraph_format.space_after = Pt(3.5)
        add_rich(par, t, size=size)
        return par

    def num(self, t, size=10.5):
        par = self.d.add_paragraph(style="List Number")
        par.paragraph_format.left_indent = Inches(0.30)
        par.paragraph_format.space_after = Pt(4)
        add_rich(par, t, size=size)
        return par

    def code(self, text, size=8.2):
        par = self.d.add_paragraph()
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.space_after = Pt(9)
        par.paragraph_format.left_indent = Inches(0.08)
        par.paragraph_format.line_spacing = 1.0
        shade_par(par, F_CODE)
        r = par.add_run(text)
        r.font.name = MONO_FONT
        r.font.size = Pt(size)
        r.font.color.rgb = RGBColor(0x22, 0x2A, 0x33)
        return par

    def callout(self, label, body, kind="note"):
        fill, accent, lab_col = {
            "note":   (F_NOTE,   "0F626B", TEAL),
            "warn":   (F_WARN,   "B8791A", AMBER),
            "danger": (F_DANGER, "9B2C2C", CRIMSON),
            "ok":     (F_OK,     "1E6B3A", GREEN),
        }[kind]
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.rows[0].cells[0]
        c.width = Inches(6.6)
        shade_cell(c, fill)
        left_accent(c, accent)
        c.text = ""
        p1 = c.paragraphs[0]
        no_space(p1, 3, 2)
        r = p1.add_run(label.upper())
        r.bold = True; r.font.size = Pt(8.5); r.font.name = BODY_FONT
        r.font.color.rgb = lab_col
        p2 = c.add_paragraph()
        no_space(p2, 0, 4)
        add_rich(p2, body, size=10)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def table(self, headers, rows, widths=None, header_fill=F_HDR, zebra=True, size=9.5):
        t = self.d.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0]
        hdr.cells[0].paragraphs[0]
        for i, h in enumerate(headers):
            c = hdr.cells[i]
            shade_cell(c, header_fill)
            c.text = ""
            par = c.paragraphs[0]; no_space(par, 2, 2)
            r = par.add_run(h)
            r.bold = True; r.font.size = Pt(9.2); r.font.name = BODY_FONT
            r.font.color.rgb = WHITE
        tr = hdr._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader"); tr.append(th)

        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for ci, val in enumerate(row):
                c = cells[ci]
                if zebra and ri % 2 == 1:
                    shade_cell(c, F_ZEBRA)
                c.text = ""
                par = c.paragraphs[0]; no_space(par, 2, 2)
                add_rich(par, str(val), size=size)
        if widths:
            set_col_widths(t, widths)
        self.d.add_paragraph().paragraph_format.space_after = Pt(3)
        return t

    def spacer(self, pts=6):
        p = self.d.add_paragraph()
        p.paragraph_format.space_after = Pt(pts)
        return p

    def footer_page_numbers(self, left_text):
        f = self.d.sections[0].footer
        par = f.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = par.add_run(left_text + "   |   Page ")
        r.font.size = Pt(8); r.font.name = BODY_FONT
        r.font.color.rgb = SLATE
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), "PAGE")
        par._p.append(fld)

    def save(self, path):
        self.d.save(path)
