"""
resume_filler.py
================
Importable module to fill Projects and About sections into a resume PDF.

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
]

about = "Experienced software engineer with a passion for NLP and ML..."

fill_resume(
    input_pdf  = r"D:/path/to/resume.pdf",
    output_pdf = r"D:/path/to/resume_filled.pdf",
    projects   = projects,
    about      = about,
)

Requirements:
    pip install pypdf reportlab
"""

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import io


def fill_resume(input_pdf, output_pdf, projects, about):
    """
    Fills the Projects and About sections of the resume PDF.

    Parameters
    ----------
    input_pdf  : str        - path to the original resume PDF
    output_pdf : str        - path where the filled PDF will be saved
    projects   : list of dict, each with keys:
                    'title'       (str) - project name
                    'description' (str) - what you built / achieved
                    'tech'        (str) - technologies used
                    'year'        (str) - year of project
    about      : str        - About section text (plain string)
    """

    # ── Page layout ───────────────────────────────────────────────────────
    PAGE_INDEX  = 1
    PAGE_WIDTH  = 595.5
    PAGE_HEIGHT = 842.25

    LEFT_MARGIN = 83.34
    INDENT      = LEFT_MARGIN + 10

    # ── Colors ────────────────────────────────────────────────────────────
    TEXT_COLOR    = (0.20, 0.20, 0.20)
    ITALIC_COLOR  = (0.35, 0.35, 0.35)
    HEADING_COLOR = (0.55, 0.55, 0.55)

    # ── Font sizes ────────────────────────────────────────────────────────
    SMALL        = 8
    NORMAL       = 9
    BOLD_SIZE    = 9.5
    HEADING_SIZE = 12

    # ── Line heights ──────────────────────────────────────────────────────
    LH_SMALL  = 11
    LH_NORMAL = 14
    LH_LARGE  = 20

    # ── Gaps ──────────────────────────────────────────────────────────────
    GAP_BETWEEN_ITEMS    = 7
    GAP_BELOW_HEADING    = 12
    GAP_BETWEEN_SECTIONS = 22

    # Projects content starts just below the existing "Projects" heading
    PROJECTS_CONTENT_TOP = 68.61

    # About heading coordinates (same as old "Courses :" heading in original PDF)
    ABOUT_HEADING_TOP    = 574.96
    ABOUT_HEADING_BOTTOM = 589.31

    # ── Helpers ───────────────────────────────────────────────────────────
    def to_rl(plumber_top):
        return PAGE_HEIGHT - plumber_top

    def wrap(text, max_chars=88):
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

    def draw_heading(c, y, label):
        c.setFillColorRGB(*HEADING_COLOR)
        c.setFont("Helvetica", HEADING_SIZE)
        c.drawString(LEFT_MARGIN, y, label)
        c.setStrokeColorRGB(*HEADING_COLOR)
        c.setLineWidth(0.5)
        c.line(LEFT_MARGIN, y - 2, PAGE_WIDTH - 30, y - 2)
        return y - LH_LARGE

    # ── Build overlay ─────────────────────────────────────────────────────
    def build_overlay():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

        # White-out the existing "About" heading baked into the PDF
        # (coordinates are same as old "Courses :" heading)
        y_bottom = to_rl(ABOUT_HEADING_BOTTOM)
        y_top    = to_rl(ABOUT_HEADING_TOP)
        c.setFillColorRGB(1, 1, 1)
        c.rect(80, y_bottom - 2, 200, (y_top - y_bottom) + 4, fill=1, stroke=0)

        # ── PROJECTS ──────────────────────────────────────────────────────
        y = to_rl(PROJECTS_CONTENT_TOP) - GAP_BELOW_HEADING

        for idx, proj in enumerate(projects):
            c.setFillColorRGB(*TEXT_COLOR)
            c.setFont("Helvetica-Bold", BOLD_SIZE)
            c.drawString(LEFT_MARGIN, y, f"{proj['title']}  ({proj['year']})")
            y -= LH_NORMAL

            c.setFont("Helvetica", NORMAL)
            c.setFillColorRGB(*TEXT_COLOR)
            for line in wrap(proj["description"]):
                c.drawString(INDENT, y, line)
                y -= LH_SMALL

            c.setFont("Helvetica-Oblique", SMALL)
            c.setFillColorRGB(*ITALIC_COLOR)
            c.drawString(INDENT, y, "Tech: " + proj["tech"])
            y -= LH_SMALL

            if idx < len(projects) - 1:
                y -= GAP_BETWEEN_ITEMS

        # ── ABOUT ─────────────────────────────────────────────────────────
        y -= GAP_BETWEEN_SECTIONS
        y = draw_heading(c, y, "About :")
        y -= GAP_BELOW_HEADING

        c.setFillColorRGB(*TEXT_COLOR)
        c.setFont("Helvetica", NORMAL)
        for line in wrap(about):
            c.drawString(LEFT_MARGIN, y, line)
            y -= LH_NORMAL

        if y < 20:
            print(f"[resume_filler] WARNING: Content overflows the page "
                  f"(y={y:.1f}). Consider shortening projects or about text.")

        c.save()
        buf.seek(0)
        return buf

    # ── Merge overlay onto PDF ────────────────────────────────────────────
    reader       = PdfReader(input_pdf)
    writer       = PdfWriter()
    overlay_page = PdfReader(build_overlay()).pages[0]

    for i, page in enumerate(reader.pages):
        if i == PAGE_INDEX:
            page.merge_page(overlay_page)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"[resume_filler] Done -> {output_pdf}")