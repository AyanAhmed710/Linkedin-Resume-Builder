"""
Resume PDF Section Filler
=========================
This script adds Projects, Courses, and Skills content to the resume PDF.
Edit the data dictionaries below, then run the script.

Requirements: pypdf, reportlab
Install: pip install pypdf reportlab
"""

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import io

# ─────────────────────────────────────────────
# ✏️  EDIT YOUR DATA HERE
# ─────────────────────────────────────────────

PROJECTS = [
    {
        "title": "Paraphrase Generation System",
        "description": "Built a transformer-based paraphrase generation system using vMF loss, achieving superior diversity scores compared to standard log-likelihood models.",
        "tech": "Python, PyTorch, HuggingFace Transformers",
        "year": "2020"
    },
    {
        "title": "AR Text-to-Scene Composer",
        "description": "Developed a mobile AR app that converts natural language descriptions into 3D scenes using object size/position prediction from textual features.",
        "tech": "Unity, ARKit, Python, NLP",
        "year": "2019"
    },
    {
        "title": "Cognitive Text Parser",
        "description": "Created a cognitive text parser combining syntactic and semantic approaches to produce structural representations for downstream NLP tasks.",
        "tech": "Python, NLP, Stanford CoreNLP",
        "year": "2017"
    },
]

COURSES = [
    "Natural Language Processing",
    "Machine Learning",
    "Deep Learning",
    "Data Structures and Algorithms",
    "Computer Vision",
    "Distributed Systems",
    "Advanced Algorithms",
    "Compiler Design",
]

SKILLS = {
    "Languages":    "Python, Java, C++, JavaScript, TypeScript",
    "Frameworks":   "PyTorch, TensorFlow, React, Node.js",
    "Tools":        "Git, Docker, Kubernetes, GCP, Web Assembly, Emscripten",
    "NLP / ML":     "Transformers, BERT, GPT, HuggingFace, spaCy, scikit-learn",
    "Other":        "j2Cl, Bazel, Protocol Buffers, REST APIs",
}

# ─────────────────────────────────────────────
# PDF coordinates (page 2, 0-indexed)
# Based on pdfplumber extraction from the original resume
# ─────────────────────────────────────────────
PAGE_INDEX = 1          # 0-indexed → page 2
PAGE_WIDTH  = 595.5
PAGE_HEIGHT = 842.25    # points

# Y position where the FIRST section (Projects) starts — just below its heading
PROJECTS_START_TOP = 68.61   # pdfplumber "top" of heading bottom edge

LEFT_MARGIN  = 83.34
INDENT       = LEFT_MARGIN + 10   # indented content
TEXT_COLOR   = (0.2, 0.2, 0.2)

# Font sizes
SMALL        = 8
NORMAL       = 9
BOLD_SIZE    = 9.5
HEADING_SIZE = 12   # matches resume section headings

# Line heights
LH_SMALL  = 11    # tight lines (description body)
LH_NORMAL = 14    # normal lines
LH_LARGE  = 18    # after a section heading

# Gaps
GAP_AFTER_ITEM    = 6    # space after each project/skill/course row
GAP_AFTER_SECTION = 20   # space between sections (Projects→Courses→Skills)
GAP_BELOW_HEADING = 8    # space between a section heading and its first item

# Section heading appearance — matches resume style
HEADING_COLOR = (0.55, 0.55, 0.55)   # grey, like "Projects", "Courses :", "Skills :"


def rl_y(plumber_top):
    """Convert pdfplumber top coordinate to ReportLab y (bottom-origin)."""
    return PAGE_HEIGHT - plumber_top


def wrap_text(text, max_chars=88):
    """Simple word-wrap returning list of lines."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_section_heading(c, y, title):
    """Draw a section heading that visually matches the resume style."""
    c.setFillColorRGB(*HEADING_COLOR)
    c.setFont("Helvetica", HEADING_SIZE)
    c.drawString(LEFT_MARGIN, y, title)
    # Underline / rule — draw a thin line below the heading text
    c.setStrokeColorRGB(*HEADING_COLOR)
    c.setLineWidth(0.5)
    c.line(LEFT_MARGIN, y - 2, PAGE_WIDTH - 30, y - 2)
    return y - LH_LARGE   # return y after heading + gap


def build_overlay():
    """
    Render all three sections dynamically.
    Each section starts right after the previous one ends,
    with GAP_AFTER_SECTION spacing between them.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    # Start just below the existing "Projects" heading in the PDF
    y = rl_y(PROJECTS_START_TOP) - 4

    # ── PROJECTS ──────────────────────────────────────────────────────────
    for idx, proj in enumerate(PROJECTS):
        # Project title + year
        c.setFillColorRGB(*TEXT_COLOR)
        c.setFont("Helvetica-Bold", BOLD_SIZE)
        c.drawString(LEFT_MARGIN, y, f"{proj['title']}  ({proj['year']})")
        y -= LH_NORMAL

        # Description — wrapped
        c.setFont("Helvetica", NORMAL)
        for line in wrap_text(proj["description"]):
            c.drawString(INDENT, y, line)
            y -= LH_SMALL

        # Tech stack in italics
        c.setFont("Helvetica-Oblique", SMALL)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawString(INDENT, y, "Tech: " + proj["tech"])
        y -= LH_SMALL

        # Gap between project items (skip after last)
        if idx < len(PROJECTS) - 1:
            y -= GAP_AFTER_ITEM

    # ── GAP + COURSES HEADING ─────────────────────────────────────────────
    y -= GAP_AFTER_SECTION
    y = draw_section_heading(c, y, "Courses :")
    y -= GAP_BELOW_HEADING

    # Courses — 3 per row separated by bullet
    c.setFillColorRGB(*TEXT_COLOR)
    c.setFont("Helvetica", NORMAL)
    rows = [COURSES[i:i + 3] for i in range(0, len(COURSES), 3)]
    for idx, row in enumerate(rows):
        c.drawString(LEFT_MARGIN, y, "  •  ".join(row))
        y -= LH_NORMAL
        if idx < len(rows) - 1:
            y -= GAP_AFTER_ITEM * 0.3   # subtle gap between course rows

    # ── GAP + SKILLS HEADING ──────────────────────────────────────────────
    y -= GAP_AFTER_SECTION
    y = draw_section_heading(c, y, "Skills :")
    y -= GAP_BELOW_HEADING

    # Skills — Category: items
    for idx, (category, items) in enumerate(SKILLS.items()):
        c.setFillColorRGB(*TEXT_COLOR)
        c.setFont("Helvetica-Bold", BOLD_SIZE)
        c.drawString(LEFT_MARGIN, y, category + ":")

        c.setFont("Helvetica", NORMAL)
        c.drawString(LEFT_MARGIN + 65, y, items)
        y -= LH_NORMAL

        if idx < len(SKILLS) - 1:
            y -= GAP_AFTER_ITEM * 0.4   # small breathe between skill rows

    c.save()
    buf.seek(0)
    return buf


def stamp_overlay_on_page(reader, writer, page_index, overlay_buf):
    """Merge the overlay onto the target page."""
    overlay_reader = PdfReader(overlay_buf)
    overlay_page   = overlay_reader.pages[0]

    target_page = reader.pages[page_index]
    target_page.merge_page(overlay_page)
    return target_page


def main():
    input_path  = r"D:\LANGCHAIN\langchain_Resume_Builder\resume(2.0).pdf"
    output_path = "resume_filled2.pdf"

    reader = PdfReader(input_path)
    writer = PdfWriter()

    overlay_buf = build_overlay()

    for i, page in enumerate(reader.pages):
        if i == PAGE_INDEX:
            stamped = stamp_overlay_on_page(reader, writer, i, overlay_buf)
            writer.add_page(stamped)
        else:
            writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"✅  Done! Saved to: {output_path}")


if __name__ == "__main__":
    main()