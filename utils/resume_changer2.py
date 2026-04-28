"""
Resume PDF Section Filler
=========================
Edit the data section below, then run:
    python add_resume_sections.py

Requirements:
    pip install pypdf reportlab
"""

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
import io

# ══════════════════════════════════════════════════════
#  ✏️  EDIT YOUR DATA HERE
# ══════════════════════════════════════════════════════

# Job title shown below your name on page 1
JOB_TITLE = "Data Scientist"

PROJECTS = [
    {
        "title": "Paraphrase Generation System",
        "description": "Built a transformer-based paraphrase generation system using vMF loss, achieving superior diversity scores compared to standard log-likelihood models.",
        "tech": "Python, PyTorch, HuggingFace Transformers",
        "year": "2020",
    },
    {
        "title": "AR Text-to-Scene Composer",
        "description": "Developed a mobile AR app that converts natural language descriptions into 3D scenes using object size/position prediction from textual features.",
        "tech": "Unity, ARKit, Python, NLP",
        "year": "2019",
    },
    {
        "title": "Cognitive Text Parser",
        "description": "Created a cognitive text parser combining syntactic and semantic approaches to produce structural representations for downstream NLP tasks.",
        "tech": "Python, NLP, Stanford CoreNLP",
        "year": "2017",
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
    "Languages":  "Python, Java, C++, JavaScript, TypeScript",
    "Frameworks": "PyTorch, TensorFlow, React, Node.js",
    "Tools":      "Git, Docker, Kubernetes, GCP, Web Assembly, Emscripten",
    "NLP / ML":   "Transformers, BERT, GPT, HuggingFace, spaCy, scikit-learn",
    "Other":      "j2Cl, Bazel, Protocol Buffers, REST APIs",
}

# ══════════════════════════════════════════════════════
#  FILE PATHS  —  update to your local paths
# ══════════════════════════════════════════════════════
INPUT_PDF  = r"D:\LANGCHAIN\langchain_Resume_Builder\resume(2.0).pdf"
OUTPUT_PDF = r"D:\LANGCHAIN\langchain_Resume_Builder\resume_filled3.pdf"

# ══════════════════════════════════════════════════════
#  LAYOUT CONSTANTS  —  tweak spacing here if needed
# ══════════════════════════════════════════════════════
PAGE_INDEX  = 1        # 0-indexed page that has Projects/Courses/Skills
PAGE_WIDTH  = 595.5
PAGE_HEIGHT = 842.25

LEFT_MARGIN = 83.34
INDENT      = LEFT_MARGIN + 10

TEXT_COLOR    = (0.20, 0.20, 0.20)
HEADING_COLOR = (0.55, 0.55, 0.55)
ITALIC_COLOR  = (0.35, 0.35, 0.35)

SMALL        = 8
NORMAL       = 9
BOLD_SIZE    = 9.5
HEADING_SIZE = 12

LH_SMALL  = 11   # line height for body/description text
LH_NORMAL = 14   # line height for normal text
LH_LARGE  = 20   # space consumed after drawing a section heading

GAP_BETWEEN_ITEMS    = 7    # gap between each project entry
GAP_BETWEEN_SECTIONS = 22   # gap before a new section heading
GAP_BELOW_HEADING    = 6    # gap between heading and first item

# Where Projects content starts (just below the existing "Projects" heading)
PROJECTS_CONTENT_TOP = 68.61   # pdfplumber .bottom of the heading text


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def to_rl(plumber_top):
    """pdfplumber uses top-origin; ReportLab uses bottom-origin."""
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
    """Draw a grey section heading with a horizontal rule."""
    c.setFillColorRGB(*HEADING_COLOR)
    c.setFont("Helvetica", HEADING_SIZE)
    c.drawString(LEFT_MARGIN, y, label)
    c.setStrokeColorRGB(*HEADING_COLOR)
    c.setLineWidth(0.5)
    c.line(LEFT_MARGIN, y - 2, PAGE_WIDTH - 30, y - 2)
    return y - LH_LARGE


# ══════════════════════════════════════════════════════
#  OVERLAY BUILDERS
# ══════════════════════════════════════════════════════

def build_title_overlay():
    """Page 1: white-out old job title, write new JOB_TITLE."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    # Original title coords from pdfplumber (top=42.8, bottom=57.15)
    y_bottom = to_rl(57.15)
    y_top    = to_rl(42.8)
    height   = y_top - y_bottom

    # White-out old title
    c.setFillColorRGB(1, 1, 1)
    c.rect(LEFT_MARGIN - 2, y_bottom - 1, 420, height + 3, fill=1, stroke=0)

    # Write new title
    c.setFillColorRGB(0.40, 0.40, 0.40)
    c.setFont("Helvetica", 12)
    c.drawString(LEFT_MARGIN, y_bottom + 1, JOB_TITLE)

    c.save()
    buf.seek(0)
    return buf


def build_sections_overlay():
    """Page 2: dynamically render Projects → Courses → Skills."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    y = to_rl(PROJECTS_CONTENT_TOP) - 4

    # ── PROJECTS ──────────────────────────────────────
    for idx, proj in enumerate(PROJECTS):
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

        if idx < len(PROJECTS) - 1:
            y -= GAP_BETWEEN_ITEMS

    # ── COURSES ───────────────────────────────────────
    y -= GAP_BETWEEN_SECTIONS
    y = draw_heading(c, y, "Courses :")
    y -= GAP_BELOW_HEADING

    c.setFillColorRGB(*TEXT_COLOR)
    c.setFont("Helvetica", NORMAL)
    rows = [COURSES[i:i + 3] for i in range(0, len(COURSES), 3)]
    for idx, row in enumerate(rows):
        c.drawString(LEFT_MARGIN, y, "  •  ".join(row))
        y -= LH_NORMAL
        if idx < len(rows) - 1:
            y -= GAP_BETWEEN_ITEMS * 0.3

    # ── SKILLS ────────────────────────────────────────
    y -= GAP_BETWEEN_SECTIONS
    y = draw_heading(c, y, "Skills :")
    y -= GAP_BELOW_HEADING

    for idx, (category, items) in enumerate(SKILLS.items()):
        c.setFillColorRGB(*TEXT_COLOR)
        c.setFont("Helvetica-Bold", BOLD_SIZE)
        c.drawString(LEFT_MARGIN, y, category + ":")
        c.setFont("Helvetica", NORMAL)
        c.drawString(LEFT_MARGIN + 65, y, items)
        y -= LH_NORMAL
        if idx < len(SKILLS) - 1:
            y -= GAP_BETWEEN_ITEMS * 0.4

    # ── OVERFLOW WARNING ──────────────────────────────
    if y < 20:
        print(f"WARNING: Content overflows the page (y={y:.1f}). "
              "Reduce content or decrease spacing constants.")

    c.save()
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

def main():
    reader = PdfReader(INPUT_PDF)
    writer = PdfWriter()

    title_buf    = build_title_overlay()
    sections_buf = build_sections_overlay()

    for i, page in enumerate(reader.pages):
        if i == 0:
            page.merge_page(PdfReader(title_buf).pages[0])
        elif i == PAGE_INDEX:
            page.merge_page(PdfReader(sections_buf).pages[0])
        writer.add_page(page)

    with open(OUTPUT_PDF, "wb") as f:
        writer.write(f)

    print(f"Done!  ->  {OUTPUT_PDF}")


if __name__ == "__main__":
    main()