"""
resume_filler.py
================
Importable module to fill Projects section into a resume PDF.

USAGE:
------
from resume_filler import fill_resume

projects = [
    {
        "title": "My Project",
        "description": "What I built and why it matters.",
        "tech": "Python, FastAPI, PostgreSQL",
        "year": "2024",
    },
    # add more projects...
]

fill_resume(
    input_pdf  = r"D:/path/to/resume.pdf",
    output_pdf = r"D:/path/to/resume_filled.pdf",
    projects   = projects,
)

Requirements:
    pip install pypdf reportlab
"""

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import io


def fill_resume(input_pdf, output_pdf, projects):
    """
    Fills the Projects section of the resume PDF with the given data.
    Courses and Skills sections (headings + content) are left untouched.

    Parameters
    ----------
    input_pdf  : str  — path to the original resume PDF
    output_pdf : str  — path where the filled PDF will be saved
    projects   : list of dict, each with keys:
                    'title'       (str) — project name
                    'description' (str) — what you built / achieved
                    'tech'        (str) — technologies used
                    'year'        (str) — year of project
    """

    # ── Page layout ───────────────────────────────────────────────────────
    PAGE_INDEX  = 1          # 0-indexed → page 2 of the resume
    PAGE_WIDTH  = 595.5
    PAGE_HEIGHT = 842.25

    LEFT_MARGIN = 83.34
    INDENT      = LEFT_MARGIN + 10

    # ── Colors ────────────────────────────────────────────────────────────
    TEXT_COLOR   = (0.20, 0.20, 0.20)
    ITALIC_COLOR = (0.35, 0.35, 0.35)

    # ── Font sizes ────────────────────────────────────────────────────────
    SMALL     = 8
    NORMAL    = 9
    BOLD_SIZE = 9.5

    # ── Line heights ──────────────────────────────────────────────────────
    LH_SMALL  = 11   # description body lines
    LH_NORMAL = 14   # title lines

    # ── Gaps ──────────────────────────────────────────────────────────────
    GAP_BETWEEN_ITEMS = 7    # breathing room between project entries
    GAP_BELOW_HEADING = 12   # space between "Projects" heading and first item

    # Projects content starts just below the existing "Projects" heading
    PROJECTS_CONTENT_TOP = 68.61   # pdfplumber .bottom of the heading text

    # ── Helpers ───────────────────────────────────────────────────────────
    def to_rl(plumber_top):
        """Convert pdfplumber top-origin Y to ReportLab bottom-origin Y."""
        return PAGE_HEIGHT - plumber_top

    def wrap(text, max_chars=88):
        """Word-wrap text into lines of at most max_chars characters."""
        words = text.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 <= max_chars:
                cur = (cur + " " + w).strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ── Build overlay for page 2 ──────────────────────────────────────────
    def build_projects_overlay():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

        y = to_rl(PROJECTS_CONTENT_TOP) - GAP_BELOW_HEADING

        for idx, proj in enumerate(projects):

            # Project title + year
            c.setFillColorRGB(*TEXT_COLOR)
            c.setFont("Helvetica-Bold", BOLD_SIZE)
            c.drawString(LEFT_MARGIN, y, f"{proj['title']}  ({proj['year']})")
            y -= LH_NORMAL

            # Description — word-wrapped
            c.setFont("Helvetica", NORMAL)
            c.setFillColorRGB(*TEXT_COLOR)
            for line in wrap(proj["description"]):
                c.drawString(INDENT, y, line)
                y -= LH_SMALL

            # Tech stack — italic
            c.setFont("Helvetica-Oblique", SMALL)
            c.setFillColorRGB(*ITALIC_COLOR)
            c.drawString(INDENT, y, "Tech: " + proj["tech"])
            y -= LH_SMALL

            # Gap between projects (skip after last)
            if idx < len(projects) - 1:
                y -= GAP_BETWEEN_ITEMS

        # Overflow warning
        if y < 20:
            print(f"[resume_filler] WARNING: Projects content overflows the page "
                  f"(y={y:.1f}). Consider reducing projects or description length.")

        c.save()
        buf.seek(0)
        return buf

    # ── Merge overlay onto PDF ────────────────────────────────────────────
    reader          = PdfReader(input_pdf)
    writer          = PdfWriter()
    overlay_buf     = build_projects_overlay()
    overlay_page    = PdfReader(overlay_buf).pages[0]

    for i, page in enumerate(reader.pages):
        if i == PAGE_INDEX:
            page.merge_page(overlay_page)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"[resume_filler] Done → {output_pdf}")