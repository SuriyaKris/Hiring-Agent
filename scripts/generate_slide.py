"""
Generate high-fidelity architecture slide for the AI Hiring Agent project.
Matches the structure, aesthetic, and layout of the SOW Agent reference slide.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def build_presentation(output_path="hiring_agent_architecture_slide.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # ── COLOR PALETTE ────────────────────────────────────────────────────────
    BG_COLOR = RGBColor(248, 250, 252)          # Slate 50
    CARD_BG = RGBColor(255, 255, 255)
    TEXT_MAIN = RGBColor(15, 23, 42)            # Slate 900
    TEXT_MUTED = RGBColor(100, 116, 139)        # Slate 500
    TEXT_DARK = RGBColor(30, 41, 59)            # Slate 800
    BORDER_DEFAULT = RGBColor(226, 232, 240)    # Slate 200
    
    # Process Column Colors
    COL_BLUE_BORDER = RGBColor(186, 230, 253)   # Sky 200
    COL_BLUE_BG = RGBColor(240, 249, 255)       # Light Sky
    COL_BLUE_ACCENT = RGBColor(2, 132, 199)     # Sky 600
    
    COL_PURPLE_BORDER = RGBColor(221, 214, 254) # Purple 200
    COL_PURPLE_BG = RGBColor(245, 243, 255)     # Light Purple
    COL_PURPLE_ACCENT = RGBColor(124, 58, 237)  # Purple 600
    
    COL_INDIGO_BORDER = RGBColor(199, 210, 254) # Indigo 200
    COL_INDIGO_BG = RGBColor(238, 242, 255)     # Light Indigo
    COL_INDIGO_ACCENT = RGBColor(79, 70, 229)   # Indigo 600
    
    COL_TEAL_BORDER = RGBColor(153, 246, 228)   # Teal 200
    COL_TEAL_BG = RGBColor(240, 253, 250)       # Light Teal
    COL_TEAL_ACCENT = RGBColor(13, 148, 136)    # Teal 600
    
    COL_ROSE_BORDER = RGBColor(254, 205, 211)   # Rose 200
    COL_ROSE_BG = RGBColor(255, 241, 242)       # Light Rose
    COL_ROSE_ACCENT = RGBColor(225, 29, 72)     # Rose 600
    
    COL_EMERALD_BORDER = RGBColor(167, 243, 208)# Emerald 200
    COL_EMERALD_BG = RGBColor(236, 253, 245)    # Light Emerald
    COL_EMERALD_ACCENT = RGBColor(5, 150, 105)  # Emerald 600

    # Background Canvas
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_COLOR
    bg.line.fill.background()

    # ── 1. HEADER ─────────────────────────────────────────────────────────────
    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.2), Inches(12.5), Inches(0.75))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    p = tf.paragraphs[0]
    p.text = "Autonomous AI Hiring & Sourcing Agent"
    p.font.name = "Segoe UI"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = RGBColor(24, 43, 98)     # Deep Navy
    
    p2 = tf.add_paragraph()
    p2.text = "From Raw Job Descriptions & Criteria to Verified, Precision-Ranked Candidates with Multi-Channel Outreach Packs"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = TEXT_MUTED
    p2.space_before = Pt(2)

    # ── 2. TOP WORKFLOW COLUMNS (6 Columns) ───────────────────────────────────
    col_width = Inches(1.97)
    col_gap = Inches(0.135)
    col_left_start = Inches(0.4)
    col_top = Inches(1.02)
    col_height = Inches(3.22)

    # Helper for adding formatted card
    def make_card(left, top, width, height, border_color, bg_color=CARD_BG):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        return card

    # ── COLUMN 1: Input Documents ─────────────────────────────────────────────
    c1_left = col_left_start
    col1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c1_left, col_top, col_width, col_height)
    col1.fill.solid()
    col1.fill.fore_color.rgb = COL_BLUE_BG
    col1.line.color.rgb = COL_BLUE_BORDER
    col1.line.width = Pt(1.5)

    # Badge 1
    b1 = slide.shapes.add_shape(MSO_SHAPE.OVAL, c1_left + Inches(0.08), col_top + Inches(0.08), Inches(0.28), Inches(0.28))
    b1.fill.solid()
    b1.fill.fore_color.rgb = COL_BLUE_ACCENT
    b1.line.fill.background()
    b1.text_frame.margin_left = b1.text_frame.margin_top = b1.text_frame.margin_right = b1.text_frame.margin_bottom = 0
    p = b1.text_frame.paragraphs[0]
    p.text = "1"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    t1 = slide.shapes.add_textbox(c1_left + Inches(0.4), col_top + Inches(0.06), Inches(1.5), Inches(0.35))
    t1.text_frame.margin_left = t1.text_frame.margin_top = t1.text_frame.margin_right = t1.text_frame.margin_bottom = 0
    p = t1.text_frame.paragraphs[0]
    p.text = "Input\nDocuments"
    p.font.name = "Segoe UI"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COL_BLUE_ACCENT

    # Inner Card: Supported Formats
    c1_card1 = make_card(c1_left + Inches(0.08), col_top + Inches(0.48), Inches(1.81), Inches(1.48), COL_BLUE_BORDER)
    tf1 = c1_card1.text_frame
    tf1.margin_left = tf1.margin_top = tf1.margin_right = Inches(0.06)
    p = tf1.paragraphs[0]
    p.text = "Supported Formats"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8.5)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p.space_after = Pt(4)

    # 3 mini format badges inside
    fmt_badges = [("PDF", RGBColor(239, 68, 68)), ("DOCX", RGBColor(37, 99, 235)), ("Text", RGBColor(16, 185, 129))]
    for fb_idx, (fmt_name, fmt_col) in enumerate(fmt_badges):
        fb_x = c1_left + Inches(0.12) + fb_idx * Inches(0.57)
        fb_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, fb_x, col_top + Inches(0.78), Inches(0.52), Inches(0.32))
        fb_shape.fill.solid()
        fb_shape.fill.fore_color.rgb = RGBColor(248, 250, 252)
        fb_shape.line.color.rgb = fmt_col
        fb_shape.line.width = Pt(1)
        fb_tf = fb_shape.text_frame
        fb_tf.margin_left = fb_tf.margin_top = fb_tf.margin_right = fb_tf.margin_bottom = 0
        fbp = fb_tf.paragraphs[0]
        fbp.text = fmt_name
        fbp.font.name = "Segoe UI"
        fbp.font.size = Pt(7)
        fbp.font.bold = True
        fbp.font.color.rgb = fmt_col
        fbp.alignment = PP_ALIGN.CENTER

    # Bullets below formats
    c1_sub = slide.shapes.add_textbox(c1_left + Inches(0.12), col_top + Inches(1.18), Inches(1.72), Inches(0.7))
    c1_sub_tf = c1_sub.text_frame
    c1_sub_tf.word_wrap = True
    c1_sub_tf.margin_left = c1_sub_tf.margin_top = c1_sub_tf.margin_right = c1_sub_tf.margin_bottom = 0
    p = c1_sub_tf.paragraphs[0]
    p.text = "• Job descriptions & specs\n• Experience & seniority level\n• Location & domain filters"
    p.font.name = "Segoe UI"
    p.font.size = Pt(7)
    p.font.color.rgb = RGBColor(71, 85, 105)

    # Inner Card 2: JD Intake Box
    c1_card2 = make_card(c1_left + Inches(0.08), col_top + Inches(2.04), Inches(1.81), Inches(1.08), COL_BLUE_BORDER)
    tf2 = c1_card2.text_frame
    tf2.margin_left = tf2.margin_top = tf2.margin_right = Inches(0.06)
    p = tf2.paragraphs[0]
    p.text = "Client JD / Job Requirements"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = COL_BLUE_ACCENT
    p.space_after = Pt(2)
    p2 = tf2.add_paragraph()
    p2.text = "• Role requirements & constraints\n• Hiring criteria & targets\n• Recruiter preferences"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(7)
    p2.font.color.rgb = RGBColor(71, 85, 105)

    # ── COLUMN 2: Document / JD Intelligence ──────────────────────────────────
    c2_left = col_left_start + 1 * (col_width + col_gap)
    col2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c2_left, col_top, col_width, col_height)
    col2.fill.solid()
    col2.fill.fore_color.rgb = COL_PURPLE_BG
    col2.line.color.rgb = COL_PURPLE_BORDER
    col2.line.width = Pt(1.5)

    b2 = slide.shapes.add_shape(MSO_SHAPE.OVAL, c2_left + Inches(0.08), col_top + Inches(0.08), Inches(0.28), Inches(0.28))
    b2.fill.solid()
    b2.fill.fore_color.rgb = COL_PURPLE_ACCENT
    b2.line.fill.background()
    b2.text_frame.margin_left = b2.text_frame.margin_top = b2.text_frame.margin_right = b2.text_frame.margin_bottom = 0
    p = b2.text_frame.paragraphs[0]
    p.text = "2"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    t2 = slide.shapes.add_textbox(c2_left + Inches(0.4), col_top + Inches(0.06), Inches(1.5), Inches(0.35))
    t2.text_frame.margin_left = t2.text_frame.margin_top = t2.text_frame.margin_right = t2.text_frame.margin_bottom = 0
    p = t2.text_frame.paragraphs[0]
    p.text = "JD Intelligence\n& Planner"
    p.font.name = "Segoe UI"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COL_PURPLE_ACCENT

    # Agent Card
    c2_card1 = make_card(c2_left + Inches(0.08), col_top + Inches(0.48), Inches(1.81), Inches(1.68), COL_PURPLE_BORDER)
    tf2_1 = c2_card1.text_frame
    tf2_1.word_wrap = True
    tf2_1.margin_left = tf2_1.margin_top = tf2_1.margin_right = Inches(0.06)
    p = tf2_1.paragraphs[0]
    p.text = "🤖 Gemini / OpenAI Agent"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p_sub = tf2_1.add_paragraph()
    p_sub.text = "(JD Understanding & Search Planner)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    p_sub.space_after = Pt(2)
    
    for bullet in [
        "• Parse role title, level & domain",
        "• Extract required & nice skills",
        "• Formulate Boolean queries",
        "• Multi-level query broadening (L0-L2)"
    ]:
        bp = tf2_1.add_paragraph()
        bp.text = bullet
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(7)
        bp.font.color.rgb = RGBColor(51, 65, 85)

    # Output Card
    c2_card2 = make_card(c2_left + Inches(0.08), col_top + Inches(2.22), Inches(1.81), Inches(0.9), COL_PURPLE_BORDER)
    tf2_2 = c2_card2.text_frame
    tf2_2.margin_left = tf2_2.margin_top = tf2_2.margin_right = Inches(0.06)
    p = tf2_2.paragraphs[0]
    p.text = "Output"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = COL_PURPLE_ACCENT
    p.space_after = Pt(1)
    for o in ["• Structured JDSearchSpec", "• Compiled Apollo query payload", "• Synonym & title expansions"]:
        op = tf2_2.add_paragraph()
        op.text = o
        op.font.name = "Segoe UI"
        op.font.size = Pt(6.8)
        op.font.color.rgb = RGBColor(71, 85, 105)

    # ── COLUMN 3: Discovery & Aggregation ─────────────────────────────────────
    c3_left = col_left_start + 2 * (col_width + col_gap)
    col3 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c3_left, col_top, col_width, col_height)
    col3.fill.solid()
    col3.fill.fore_color.rgb = COL_INDIGO_BG
    col3.line.color.rgb = COL_INDIGO_BORDER
    col3.line.width = Pt(1.5)

    b3 = slide.shapes.add_shape(MSO_SHAPE.OVAL, c3_left + Inches(0.08), col_top + Inches(0.08), Inches(0.28), Inches(0.28))
    b3.fill.solid()
    b3.fill.fore_color.rgb = COL_INDIGO_ACCENT
    b3.line.fill.background()
    b3.text_frame.margin_left = b3.text_frame.margin_top = b3.text_frame.margin_right = b3.text_frame.margin_bottom = 0
    p = b3.text_frame.paragraphs[0]
    p.text = "3"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    t3 = slide.shapes.add_textbox(c3_left + Inches(0.4), col_top + Inches(0.06), Inches(1.5), Inches(0.35))
    t3.text_frame.margin_left = t3.text_frame.margin_top = t3.text_frame.margin_right = t3.text_frame.margin_bottom = 0
    p = t3.text_frame.paragraphs[0]
    p.text = "Discovery &\nAggregation"
    p.font.name = "Segoe UI"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COL_INDIGO_ACCENT

    # Card 1: Apollo Discovery Agent
    c3_card1 = make_card(c3_left + Inches(0.08), col_top + Inches(0.48), Inches(1.81), Inches(0.78), COL_INDIGO_BORDER)
    tf3_1 = c3_card1.text_frame
    tf3_1.word_wrap = True
    tf3_1.margin_left = tf3_1.margin_top = tf3_1.margin_right = Inches(0.06)
    p = tf3_1.paragraphs[0]
    p.text = "🔍 Apollo Discovery Agent"
    p.font.name = "Segoe UI"
    p.font.size = Pt(7.5)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p_sub = tf3_1.add_paragraph()
    p_sub.text = "(People API Search & Overfetch)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    for b in ["• Query 275M+ B2B database", "• Overfetch for diversity balance"]:
        bp = tf3_1.add_paragraph()
        bp.text = b
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(6.8)
        bp.font.color.rgb = RGBColor(51, 65, 85)

    # Card 2: Candidate Normalizer
    c3_card2 = make_card(c3_left + Inches(0.08), col_top + Inches(1.3), Inches(1.81), Inches(0.86), COL_INDIGO_BORDER)
    tf3_2 = c3_card2.text_frame
    tf3_2.word_wrap = True
    tf3_2.margin_left = tf3_2.margin_top = tf3_2.margin_right = Inches(0.06)
    p = tf3_2.paragraphs[0]
    p.text = "⚡ Aggregator & Normalizer"
    p.font.name = "Segoe UI"
    p.font.size = Pt(7.5)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p_sub = tf3_2.add_paragraph()
    p_sub.text = "(Standardize Profiles & History)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    for b in ["• Normalize casing & titles", "• Combine search + URL imports"]:
        bp = tf3_2.add_paragraph()
        bp.text = b
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(6.8)
        bp.font.color.rgb = RGBColor(51, 65, 85)

    # Output Card
    c3_card3 = make_card(c3_left + Inches(0.08), col_top + Inches(2.22), Inches(1.81), Inches(0.9), COL_INDIGO_BORDER)
    tf3_3 = c3_card3.text_frame
    tf3_3.margin_left = tf3_3.margin_top = tf3_3.margin_right = Inches(0.06)
    p = tf3_3.paragraphs[0]
    p.text = "Output"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = COL_INDIGO_ACCENT
    p.space_after = Pt(1)
    for o in ["• Aggregated candidate list", "• Clean normalized profiles", "• Structured experience data"]:
        op = tf3_3.add_paragraph()
        op.text = o
        op.font.name = "Segoe UI"
        op.font.size = Pt(6.8)
        op.font.color.rgb = RGBColor(71, 85, 105)

    # ── COLUMN 4: Enrichment & Resolution ─────────────────────────────────────
    c4_left = col_left_start + 3 * (col_width + col_gap)
    col4 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c4_left, col_top, col_width, col_height)
    col4.fill.solid()
    col4.fill.fore_color.rgb = COL_TEAL_BG
    col4.line.color.rgb = COL_TEAL_BORDER
    col4.line.width = Pt(1.5)

    b4 = slide.shapes.add_shape(MSO_SHAPE.OVAL, c4_left + Inches(0.08), col_top + Inches(0.08), Inches(0.28), Inches(0.28))
    b4.fill.solid()
    b4.fill.fore_color.rgb = COL_TEAL_ACCENT
    b4.line.fill.background()
    b4.text_frame.margin_left = b4.text_frame.margin_top = b4.text_frame.margin_right = b4.text_frame.margin_bottom = 0
    p = b4.text_frame.paragraphs[0]
    p.text = "4"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    t4 = slide.shapes.add_textbox(c4_left + Inches(0.4), col_top + Inches(0.06), Inches(1.5), Inches(0.35))
    t4.text_frame.margin_left = t4.text_frame.margin_top = t4.text_frame.margin_right = t4.text_frame.margin_bottom = 0
    p = t4.text_frame.paragraphs[0]
    p.text = "Enrichment &\nResolution"
    p.font.name = "Segoe UI"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COL_TEAL_ACCENT

    # Card 1: Apollo Enrichment
    c4_card1 = make_card(c4_left + Inches(0.08), col_top + Inches(0.48), Inches(1.81), Inches(0.92), COL_TEAL_BORDER)
    tf4_1 = c4_card1.text_frame
    tf4_1.word_wrap = True
    tf4_1.margin_left = tf4_1.margin_top = tf4_1.margin_right = Inches(0.06)
    p = tf4_1.paragraphs[0]
    p.text = "📧 Apollo Enrichment Agent"
    p.font.name = "Segoe UI"
    p.font.size = Pt(7.5)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p_sub = tf4_1.add_paragraph()
    p_sub.text = "(Contact & Social Resolution)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    for b in [
        "• Resolve verified work emails",
        "• LinkedIn URLs & phone data",
        "• Open-to-work & intent flags"
    ]:
        bp = tf4_1.add_paragraph()
        bp.text = b
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(6.8)
        bp.font.color.rgb = RGBColor(51, 65, 85)

    # 2 Mini Side-by-Side Cards (Chroma DB + Postgres DB)
    mini_w = Inches(0.88)
    # Left Mini: Chroma Vector DB
    m1 = make_card(c4_left + Inches(0.08), col_top + Inches(1.44), mini_w, Inches(0.72), COL_TEAL_BORDER)
    m1_tf = m1.text_frame
    m1_tf.word_wrap = True
    m1_tf.margin_left = m1_tf.margin_top = m1_tf.margin_right = Inches(0.04)
    p = m1_tf.paragraphs[0]
    p.text = "Chroma DB"
    p.font.name = "Segoe UI"
    p.font.size = Pt(6.8)
    p.font.bold = True
    p.font.color.rgb = COL_TEAL_ACCENT
    p2 = m1_tf.add_paragraph()
    p2.text = "• Vector embeddings\n• Semantic dedup"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(6)
    p2.font.color.rgb = RGBColor(71, 85, 105)

    # Right Mini: Deduplication Service
    m2 = make_card(c4_left + Inches(1.01), col_top + Inches(1.44), mini_w, Inches(0.72), COL_TEAL_BORDER)
    m2_tf = m2.text_frame
    m2_tf.word_wrap = True
    m2_tf.margin_left = m2_tf.margin_top = m2_tf.margin_right = Inches(0.04)
    p = m2_tf.paragraphs[0]
    p.text = "Dedup Service"
    p.font.name = "Segoe UI"
    p.font.size = Pt(6.8)
    p.font.bold = True
    p.font.color.rgb = COL_TEAL_ACCENT
    p2 = m2_tf.add_paragraph()
    p2.text = "• Cross-source dedup\n• Exclusion filters"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(6)
    p2.font.color.rgb = RGBColor(71, 85, 105)

    # Output Card
    c4_card3 = make_card(c4_left + Inches(0.08), col_top + Inches(2.22), Inches(1.81), Inches(0.9), COL_TEAL_BORDER)
    tf4_3 = c4_card3.text_frame
    tf4_3.margin_left = tf4_3.margin_top = tf4_3.margin_right = Inches(0.06)
    p = tf4_3.paragraphs[0]
    p.text = "Output"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = COL_TEAL_ACCENT
    p.space_after = Pt(1)
    for o in ["• 360° candidate dossier", "• Verified contact channels", "• Deduplicated profile pool"]:
        op = tf4_3.add_paragraph()
        op.text = o
        op.font.name = "Segoe UI"
        op.font.size = Pt(6.8)
        op.font.color.rgb = RGBColor(71, 85, 105)

    # ── COLUMN 5: AI Fitment Scoring & Ranking ────────────────────────────────
    c5_left = col_left_start + 4 * (col_width + col_gap)
    col5 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c5_left, col_top, col_width, col_height)
    col5.fill.solid()
    col5.fill.fore_color.rgb = COL_ROSE_BG
    col5.line.color.rgb = COL_ROSE_BORDER
    col5.line.width = Pt(1.5)

    b5 = slide.shapes.add_shape(MSO_SHAPE.OVAL, c5_left + Inches(0.08), col_top + Inches(0.08), Inches(0.28), Inches(0.28))
    b5.fill.solid()
    b5.fill.fore_color.rgb = COL_ROSE_ACCENT
    b5.line.fill.background()
    b5.text_frame.margin_left = b5.text_frame.margin_top = b5.text_frame.margin_right = b5.text_frame.margin_bottom = 0
    p = b5.text_frame.paragraphs[0]
    p.text = "5"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    t5 = slide.shapes.add_textbox(c5_left + Inches(0.4), col_top + Inches(0.06), Inches(1.5), Inches(0.35))
    t5.text_frame.margin_left = t5.text_frame.margin_top = t5.text_frame.margin_right = t5.text_frame.margin_bottom = 0
    p = t5.text_frame.paragraphs[0]
    p.text = "AI Match &\nFitment Scoring"
    p.font.name = "Segoe UI"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COL_ROSE_ACCENT

    # Card 1: Smart Match Agent
    c5_card1 = make_card(c5_left + Inches(0.08), col_top + Inches(0.48), Inches(1.81), Inches(1.68), COL_ROSE_BORDER)
    tf5_1 = c5_card1.text_frame
    tf5_1.word_wrap = True
    tf5_1.margin_left = tf5_1.margin_top = tf5_1.margin_right = Inches(0.06)
    p = tf5_1.paragraphs[0]
    p.text = "🎯 Smart Match Agent"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p_sub = tf5_1.add_paragraph()
    p_sub.text = "(4-Tier Reasoning Rubric)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    p_sub.space_after = Pt(2)
    for b in [
        "• Title match (35%) & Skills (30%)",
        "• CRM / Domain expertise (20%)",
        "• Seniority & Stability fit (15%)",
        "• Feature engineering & pros/cons",
        "• Company diversity balancing"
    ]:
        bp = tf5_1.add_paragraph()
        bp.text = b
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(6.8)
        bp.font.color.rgb = RGBColor(51, 65, 85)

    # Output Card
    c5_card2 = make_card(c5_left + Inches(0.08), col_top + Inches(2.22), Inches(1.81), Inches(0.9), COL_ROSE_BORDER)
    tf5_2 = c5_card2.text_frame
    tf5_2.margin_left = tf5_2.margin_top = tf5_2.margin_right = Inches(0.06)
    p = tf5_2.paragraphs[0]
    p.text = "Output"
    p.font.name = "Segoe UI"
    p.font.size = Pt(8)
    p.font.bold = True
    p.font.color.rgb = COL_ROSE_ACCENT
    p.space_after = Pt(1)
    for o in ["• Fitment score (0–100)", "• Granular score breakdown", "• Audit trail & reasoning rationale"]:
        op = tf5_2.add_paragraph()
        op.text = o
        op.font.name = "Segoe UI"
        op.font.size = Pt(6.8)
        op.font.color.rgb = RGBColor(71, 85, 105)

    # ── COLUMN 6: Outreach & Recruiter Review ─────────────────────────────────
    c6_left = col_left_start + 5 * (col_width + col_gap)
    col6 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c6_left, col_top, col_width, col_height)
    col6.fill.solid()
    col6.fill.fore_color.rgb = COL_EMERALD_BG
    col6.line.color.rgb = COL_EMERALD_BORDER
    col6.line.width = Pt(1.5)

    b6 = slide.shapes.add_shape(MSO_SHAPE.OVAL, c6_left + Inches(0.08), col_top + Inches(0.08), Inches(0.28), Inches(0.28))
    b6.fill.solid()
    b6.fill.fore_color.rgb = COL_EMERALD_ACCENT
    b6.line.fill.background()
    b6.text_frame.margin_left = b6.text_frame.margin_top = b6.text_frame.margin_right = b6.text_frame.margin_bottom = 0
    p = b6.text_frame.paragraphs[0]
    p.text = "6"
    p.font.name = "Segoe UI"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    t6 = slide.shapes.add_textbox(c6_left + Inches(0.4), col_top + Inches(0.06), Inches(1.5), Inches(0.35))
    t6.text_frame.margin_left = t6.text_frame.margin_top = t6.text_frame.margin_right = t6.text_frame.margin_bottom = 0
    p = t6.text_frame.paragraphs[0]
    p.text = "Outreach &\nReview"
    p.font.name = "Segoe UI"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = COL_EMERALD_ACCENT

    # Card 1: Outreach Generator
    c6_card1 = make_card(c6_left + Inches(0.08), col_top + Inches(0.48), Inches(1.81), Inches(1.22), COL_EMERALD_BORDER)
    tf6_1 = c6_card1.text_frame
    tf6_1.word_wrap = True
    tf6_1.margin_left = tf6_1.margin_top = tf6_1.margin_right = Inches(0.06)
    p = tf6_1.paragraphs[0]
    p.text = "✉ AI Outreach Packs"
    p.font.name = "Segoe UI"
    p.font.size = Pt(7.8)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p_sub = tf6_1.add_paragraph()
    p_sub.text = "(Multi-Channel Copy Agent)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    for b in [
        "• 300-char LinkedIn note",
        "• Tailored InMail pitch",
        "• High-converting cold email",
        "• 2-stage follow-up sequence"
    ]:
        bp = tf6_1.add_paragraph()
        bp.text = b
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(6.8)
        bp.font.color.rgb = RGBColor(51, 65, 85)

    # Card 2: Recruiter Review Dashboard
    c6_card2 = make_card(c6_left + Inches(0.08), col_top + Inches(1.76), Inches(1.81), Inches(1.36), COL_EMERALD_BORDER)
    tf6_2 = c6_card2.text_frame
    tf6_2.word_wrap = True
    tf6_2.margin_left = tf6_2.margin_top = tf6_2.margin_right = Inches(0.06)
    p = tf6_2.paragraphs[0]
    p.text = "👤 Recruiter Review UI"
    p.font.name = "Segoe UI"
    p.font.size = Pt(7.8)
    p.font.bold = True
    p.font.color.rgb = COL_EMERALD_ACCENT
    p_sub = tf6_2.add_paragraph()
    p_sub.text = "(Human-in-the-Loop Control)"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(6.5)
    p_sub.font.color.rgb = TEXT_MUTED
    for b in [
        "• Recruiter verdicts & review",
        "• 1-click copy outreach text",
        "• Export candidates (CSV/JSON)",
        "• Team collaboration"
    ]:
        bp = tf6_2.add_paragraph()
        bp.text = b
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(6.8)
        bp.font.color.rgb = RGBColor(71, 85, 105)

    # ── 3. MIDDLE ORCHESTRATION LAYER (LangGraph Bar) ────────────────────────
    orch_top = Inches(4.34)
    orch_height = Inches(0.48)
    orch_box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, col_left_start, orch_top, Inches(12.53), orch_height
    )
    orch_box.fill.solid()
    orch_box.fill.fore_color.rgb = RGBColor(239, 246, 255)
    orch_box.line.color.rgb = RGBColor(96, 165, 250)
    orch_box.line.width = Pt(1.5)

    orch_title = slide.shapes.add_textbox(col_left_start + Inches(0.12), orch_top + Inches(0.08), Inches(3.2), Inches(0.32))
    otf = orch_title.text_frame
    otf.margin_left = otf.margin_top = otf.margin_right = otf.margin_bottom = 0
    op = otf.paragraphs[0]
    op.text = "⚙ LangGraph — Orchestration & Control Layer"
    op.font.name = "Segoe UI"
    op.font.size = Pt(8.5)
    op.font.bold = True
    op.font.color.rgb = RGBColor(30, 64, 175)

    orch_pills = [
        "✓ Graph DAG Execution",
        "✓ Context & State Passing",
        "✓ Dynamic Broadening",
        "✓ Exponential Retry",
        "✓ Semantic Dedup",
        "✓ Recruiter Verdicts"
    ]
    pill_start_x = col_left_start + Inches(3.3)
    pill_width = Inches(1.49)
    pill_gap = Inches(0.05)

    for idx, pill_text in enumerate(orch_pills):
        px = pill_start_x + idx * (pill_width + pill_gap)
        p_shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, px, orch_top + Inches(0.07), pill_width, Inches(0.34)
        )
        p_shape.fill.solid()
        p_shape.fill.fore_color.rgb = RGBColor(255, 255, 255)
        p_shape.line.color.rgb = RGBColor(191, 219, 254)
        p_shape.line.width = Pt(1)
        
        ptf = p_shape.text_frame
        ptf.margin_left = ptf.margin_top = ptf.margin_right = ptf.margin_bottom = 0
        ptf.word_wrap = True
        pp = ptf.paragraphs[0]
        pp.text = pill_text
        pp.font.name = "Segoe UI"
        pp.font.size = Pt(7.2)
        pp.font.bold = True
        pp.font.color.rgb = RGBColor(30, 58, 138)
        pp.alignment = PP_ALIGN.CENTER

    # ── 4. DATA FLOW CHEVRON ROW ──────────────────────────────────────────────
    flow_top = Inches(4.91)
    flow_height = Inches(0.68)
    flow_outer = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, col_left_start, flow_top, Inches(12.53), flow_height
    )
    flow_outer.fill.solid()
    flow_outer.fill.fore_color.rgb = RGBColor(255, 255, 255)
    flow_outer.line.color.rgb = RGBColor(203, 213, 225)
    flow_outer.line.width = Pt(1)

    flow_title = slide.shapes.add_textbox(col_left_start + Inches(0.12), flow_top + Inches(0.04), Inches(2.0), Inches(0.2))
    ftf = flow_title.text_frame
    ftf.margin_left = ftf.margin_top = ftf.margin_right = ftf.margin_bottom = 0
    fp = ftf.paragraphs[0]
    fp.text = "⚡ Data Flow"
    fp.font.name = "Segoe UI"
    fp.font.size = Pt(8.5)
    fp.font.bold = True
    fp.font.color.rgb = RGBColor(99, 102, 241)

    flow_steps = [
        {"num": "1", "title": "Ingest JD", "sub": "PDF / DOCX / Text", "desc": "Structured input"},
        {"num": "2", "title": "Extract & Parse", "sub": "Gemini / OpenAI", "desc": "Key skills & titles"},
        {"num": "3", "title": "Apollo Discovery", "sub": "People Search API", "desc": "Live sourcing & overfetch"},
        {"num": "4", "title": "Enrich & Dedup", "sub": "Apollo + Chroma", "desc": "Verified emails & dedup"},
        {"num": "5", "title": "Score & Rank", "sub": "Smart Match Agent", "desc": "4-tier fitment rubric"},
        {"num": "6", "title": "Deliver & Review", "sub": "Outreach Packs", "desc": "Recruiter dashboard UI"},
    ]

    f_step_width = Inches(1.95)
    f_step_gap = Inches(0.14)
    f_start_x = col_left_start + Inches(0.12)
    f_card_top = flow_top + Inches(0.22)

    for idx, fs in enumerate(flow_steps):
        fx = f_start_x + idx * (f_step_width + f_step_gap)
        
        f_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, fx, f_card_top, f_step_width, Inches(0.4)
        )
        f_box.fill.solid()
        f_box.fill.fore_color.rgb = RGBColor(248, 250, 252)
        f_box.line.color.rgb = RGBColor(226, 232, 240)
        f_box.line.width = Pt(1)
        
        # Circle badge
        f_circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, fx + Inches(0.06), f_card_top + Inches(0.08), Inches(0.24), Inches(0.24)
        )
        f_circle.fill.solid()
        f_circle.fill.fore_color.rgb = RGBColor(99, 102, 241)
        f_circle.line.fill.background()
        f_ctf = f_circle.text_frame
        f_ctf.margin_left = f_ctf.margin_top = f_ctf.margin_right = f_ctf.margin_bottom = 0
        fcp = f_ctf.paragraphs[0]
        fcp.text = fs["num"]
        fcp.font.name = "Segoe UI"
        fcp.font.size = Pt(8)
        fcp.font.bold = True
        fcp.font.color.rgb = RGBColor(255, 255, 255)
        fcp.alignment = PP_ALIGN.CENTER
        
        # Text
        f_txt = slide.shapes.add_textbox(fx + Inches(0.34), f_card_top + Inches(0.02), Inches(1.58), Inches(0.36))
        f_tt_f = f_txt.text_frame
        f_tt_f.word_wrap = True
        f_tt_f.margin_left = f_tt_f.margin_top = f_tt_f.margin_right = f_tt_f.margin_bottom = 0
        
        ftp1 = f_tt_f.paragraphs[0]
        ftp1.text = f"{fs['title']} ({fs['sub']})"
        ftp1.font.name = "Segoe UI"
        ftp1.font.size = Pt(7.2)
        ftp1.font.bold = True
        ftp1.font.color.rgb = TEXT_DARK
        
        ftp2 = f_tt_f.add_paragraph()
        ftp2.text = fs["desc"]
        ftp2.font.name = "Segoe UI"
        ftp2.font.size = Pt(6.5)
        ftp2.font.color.rgb = TEXT_MUTED

    # ── 5. BOTTOM THREE CARDS (Tech Stack | Input/Output | Key Benefits) ──────
    bot_top = Inches(5.69)
    bot_height = Inches(1.56)
    
    # Card 1: Technology Stack (Left, width 4.5 in)
    ts_left = col_left_start
    ts_width = Inches(4.5)
    ts_box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, ts_left, bot_top, ts_width, bot_height
    )
    ts_box.fill.solid()
    ts_box.fill.fore_color.rgb = RGBColor(255, 255, 255)
    ts_box.line.color.rgb = RGBColor(203, 213, 225)
    ts_box.line.width = Pt(1)
    
    ts_tf = ts_box.text_frame
    ts_tf.margin_left = Inches(0.12)
    ts_tf.margin_top = Inches(0.08)
    ts_tf.margin_right = Inches(0.12)
    ts_tf.margin_bottom = Inches(0.04)
    
    tsp = ts_tf.paragraphs[0]
    tsp.text = "💻 Technology Stack"
    tsp.font.name = "Segoe UI"
    tsp.font.size = Pt(9)
    tsp.font.bold = True
    tsp.font.color.rgb = RGBColor(30, 58, 138)
    tsp.space_after = Pt(4)
    
    # Render 6 modern tech items in 2 columns
    tech_chips = [
        ("LangGraph", "Stateful Graph Orchestration"),
        ("Gemini / OpenAI", "Reasoning & Match Scoring"),
        ("Apollo.io API", "275M+ People & Verified Contact Data"),
        ("Chroma DB", "Profile Embeddings & Semantic Dedup"),
        ("FastAPI + Pydantic", "High-Speed Async Backend & Validation"),
        ("React 18 + Tailwind", "Recruiter UI with 3-Tab Workflow")
    ]
    
    for t_name, t_desc in tech_chips:
        tp = ts_tf.add_paragraph()
        tp.text = f"• {t_name} — {t_desc}"
        tp.font.name = "Segoe UI"
        tp.font.size = Pt(7.2)
        tp.font.color.rgb = RGBColor(51, 65, 85)
        tp.space_before = Pt(1)

    # Card 2: Current Input / Output (Middle, width 3.8 in)
    io_left = ts_left + ts_width + Inches(0.14)
    io_width = Inches(3.8)
    io_box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, io_left, bot_top, io_width, bot_height
    )
    io_box.fill.solid()
    io_box.fill.fore_color.rgb = RGBColor(255, 255, 255)
    io_box.line.color.rgb = RGBColor(203, 213, 225)
    io_box.line.width = Pt(1)
    
    io_tf = io_box.text_frame
    io_tf.margin_left = Inches(0.12)
    io_tf.margin_top = Inches(0.08)
    io_tf.margin_right = Inches(0.12)
    io_tf.margin_bottom = Inches(0.04)
    
    iop = io_tf.paragraphs[0]
    iop.text = "🔄 Input / Output Scope"
    iop.font.name = "Segoe UI"
    iop.font.size = Pt(9)
    iop.font.bold = True
    iop.font.color.rgb = RGBColor(15, 118, 110)
    iop.space_after = Pt(2)
    
    # Input section
    inp_h = io_tf.add_paragraph()
    inp_h.text = "Input:"
    inp_h.font.name = "Segoe UI"
    inp_h.font.size = Pt(7.5)
    inp_h.font.bold = True
    inp_h.font.color.rgb = RGBColor(13, 148, 136)
    
    in1 = io_tf.add_paragraph()
    in1.text = "• PDF / DOCX / Raw text job descriptions"
    in1.font.name = "Segoe UI"
    in1.font.size = Pt(7)
    in1.font.color.rgb = RGBColor(71, 85, 105)
    
    in2 = io_tf.add_paragraph()
    in2.text = "• Seniority, location, and headcount criteria"
    in2.font.name = "Segoe UI"
    in2.font.size = Pt(7)
    in2.font.color.rgb = RGBColor(71, 85, 105)
    in2.space_after = Pt(2)
    
    # Output section
    out_h = io_tf.add_paragraph()
    out_h.text = "Output:"
    out_h.font.name = "Segoe UI"
    out_h.font.size = Pt(7.5)
    out_h.font.bold = True
    out_h.font.color.rgb = RGBColor(180, 83, 9)
    
    out1 = io_tf.add_paragraph()
    out1.text = "• Ranked candidates (0-100 fitment score + reasoning)"
    out1.font.name = "Segoe UI"
    out1.font.size = Pt(7)
    out1.font.color.rgb = RGBColor(71, 85, 105)
    
    out2 = io_tf.add_paragraph()
    out2.text = "• Verified emails, LinkedIn URLs & multi-channel drafts"
    out2.font.name = "Segoe UI"
    out2.font.size = Pt(7)
    out2.font.color.rgb = RGBColor(71, 85, 105)

    # Card 3: Key Benefits (Right, width 3.95 in)
    kb_left = io_left + io_width + Inches(0.14)
    kb_width = Inches(3.95)
    kb_box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, kb_left, bot_top, kb_width, bot_height
    )
    kb_box.fill.solid()
    kb_box.fill.fore_color.rgb = RGBColor(255, 255, 255)
    kb_box.line.color.rgb = RGBColor(203, 213, 225)
    kb_box.line.width = Pt(1)
    
    kb_tf = kb_box.text_frame
    kb_tf.margin_left = Inches(0.12)
    kb_tf.margin_top = Inches(0.08)
    kb_tf.margin_right = Inches(0.12)
    kb_tf.margin_bottom = Inches(0.04)
    
    kbp = kb_tf.paragraphs[0]
    kbp.text = "★ Key Benefits"
    kbp.font.name = "Segoe UI"
    kbp.font.size = Pt(9)
    kbp.font.bold = True
    kbp.font.color.rgb = RGBColor(190, 24, 93)
    kbp.space_after = Pt(2)
    
    benefits = [
        ("10x Sourcing Speed", "From days to under 2 minutes per role"),
        ("Deep Semantic Fit", "Evaluates real domain depth beyond keywords"),
        ("Verified Deliverability", "Direct corporate email & live LinkedIn URLs"),
        ("Personalized Outreach", "AI career hooks boost response rates"),
        ("Human-in-the-Loop", "Full recruiter review & approval control")
    ]
    
    for b_title, b_desc in benefits:
        bp = kb_tf.add_paragraph()
        bp.text = f"• {b_title}: {b_desc}"
        bp.font.name = "Segoe UI"
        bp.font.size = Pt(7)
        bp.font.color.rgb = RGBColor(51, 65, 85)
        bp.space_before = Pt(1)

    # Save
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    build_presentation("e:/hiring-agent-v2/hiring_agent_architecture_slide.pptx")
