#!/usr/bin/env python3
"""
tools/generate_pitch_deck.py
Generates PlantDiag Pitch Deck in both PowerPoint (.pptx) and PDF (.pdf) formats.
Built for Fhinovax™ with high-impact executive visual design.
"""

import os
import sys
from pathlib import Path

# PPTX Imports
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# ReportLab Imports
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

WORKSPACE = Path(__file__).resolve().parent.parent

PPTX_OUT = WORKSPACE / "PlantDiag_Pitch_Deck.pptx"
PDF_OUT = WORKSPACE / "PlantDiag_Pitch_Deck.pdf"

print("=====================================================")
print("  Generating PlantDiag™ Pitch Deck (PPTX & PDF)")
print("  Built by Fhinovax™")
print("=====================================================")

# ----------------------------------------------------------------------
# 1. GENERATE POWERPOINT (PPTX)
# ----------------------------------------------------------------------
def generate_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6] # completely blank layout

    # Color Palette
    C_BG_DARK = RGBColor(11, 19, 32)        # #0B1320
    C_CARD_BG = RGBColor(23, 37, 56)        # #172538
    C_EMERALD = RGBColor(0, 168, 89)        # #00A859
    C_PRIMARY = RGBColor(0, 104, 55)        # #006837
    C_GOLD = RGBColor(212, 175, 55)         # #D4AF37
    C_WHITE = RGBColor(255, 255, 255)       # #FFFFFF
    C_MUTED = RGBColor(148, 163, 184)       # #94A3B8

    slides_data = [
        {
            "badge": "EXECUTIVE PITCH DECK",
            "title": "PlantDiag™ by Fhinovax™",
            "subtitle": "100% Offline Edge-AI Crop Disease Diagnosis & Multilingual Voice Advisory",
            "type": "title",
            "points": [
                "Empowering 38M+ Smallholder Farmers Across Sub-Saharan Africa",
                "Instant Diagnostics in <200ms with Zero Internet or Cloud Reliance",
                "Built with Native Edge Silicon Acceleration & Multi-Dialect Voice Synthesis"
            ]
        },
        {
            "badge": "THE RURAL CRISIS",
            "title": "Smallholders Lose 40% of Harvest to Preventable Blights",
            "subtitle": "A systemic advisory deficit is crippling African food security.",
            "type": "cards",
            "cards": [
                ("1 : 5,000", "Extension Worker Deficit", "In rural Nigeria, there is only 1 government agronomist for every 5,000 farmers. By the time help arrives, entire fields are destroyed."),
                ("40% Loss", "Annual Harvest Destruction", "Cassava Mosaic, Maize Rust, and Rice Blight wipe out billions of naira in food value every season before reaching the market."),
                ("0% Signal", "Cloud AI Latency Failure", "Generic cloud-based AI tools are unusable in rural farming belts where cellular connectivity is nonexistent or unaffordable.")
            ]
        },
        {
            "badge": "THE SOLUTION",
            "title": "PlantDiag™ — The Pocket Agronomist",
            "subtitle": "An autonomous edge computer vision doctor that speaks the farmer's language.",
            "type": "cards",
            "cards": [
                ("< 200 ms", "Sub-Second Edge Vision", "Runs entirely on the phone's internal processor using lightweight, optimized TFLite neural networks with zero data usage."),
                ("5 Dialects", "Native Local Speech", "Translates remedies and reads them aloud in Hausa, Yoruba, Igbo, Nigerian Pidgin, and English to bridge the rural literacy divide."),
                ("Zero Risk", "Anti-Hallucination Gate", "Dual-stage chlorophyll colorimetry and Shannon entropy gates reject non-plants and unknown leaves rather than guessing false cures.")
            ]
        },
        {
            "badge": "HOW IT WORKS",
            "title": "End-to-End Edge Diagnostic Pipeline",
            "subtitle": "From raw leaf photo to vocalized agronomic prescription in 6 automated steps.",
            "type": "cards",
            "cards": [
                ("1. Capture & Gate", "Chlorophyll & Texture Filter", "Raw pixels are analyzed for live photosynthetic pigment and cellular gradient variation to reject walls, furniture, or non-plants."),
                ("2. Direct JNI Pass", "Memory-Mapped Tensor Bridge", "TFLiteInterpreterPlugin loads model via zero-copy memory maps and delivers normalized arrays directly to edge silicon."),
                ("3. Entropy & Voice", "Uncertainty Gate & Local Speech", "Evaluates statistical entropy to ensure confidence, pulls organic remedies from offline DB, and speaks aloud via TTS.")
            ]
        },
        {
            "badge": "TECHNICAL ARCHITECTURE",
            "title": "Engineered for Extreme Rural Resilience",
            "subtitle": "Zero cloud dependencies, zero recurring server overhead, instant battery-efficient loads.",
            "type": "cards",
            "cards": [
                ("Frontend Shell", "Capacitor 5 + Vanilla JS", "Pure ESModules and high-contrast responsive glassmorphism. Zero heavy framework bloat for instant 60fps responsiveness."),
                ("Native Bridge", "Android Java JNI + XNNPACK", "Direct ByteBuffer interfacing with TensorFlow Lite multi-threaded CPU acceleration on MediaTek & Snapdragon chipsets."),
                ("Field Registry", "Offline SQLite Database", "Logs farmer NINs, village GPS, disease history, and severity levels offline, ready for automated batch sync when signal returns.")
            ]
        },
        {
            "badge": "BASELINE SCOPE",
            "title": "Diagnostic Scope: 38 Crop-Disease Conditions",
            "subtitle": "Comprehensive commercial crop coverage validated on over 54,000 pathological leaf images.",
            "type": "cards",
            "cards": [
                ("Cereal Staples", "Corn (Maize) Suite", "Identifies Common Rust, Northern Leaf Blight, Gray Leaf Spot, and Healthy foliage with 95%+ precision."),
                ("Horticulture", "Tomato & Pepper Suite", "Diagnoses Early Blight, Late Blight, Bacterial Spot, Septoria, Leaf Mold, Spider Mites, TYLCV, and Mosaic Virus."),
                ("Tubers & Fruits", "Potato, Citrus & Fruits", "Covers Potato Early/Late Blights, Citrus Greening (HLB), Apple Scabs, Grape Esca, Strawberry Leaf Scorch, and Squash Mildew.")
            ]
        },
        {
            "badge": "PHASE 2 BREAKTHROUGH",
            "title": "Transfer Learning: Adding African Staples",
            "subtitle": "Fine-tuning missing regional varieties (Cassava & Rice) in under 10 minutes on CPU.",
            "type": "cards",
            "cards": [
                ("Balanced Data", "Eliminating Class Bias", "Capped dominant Cassava Mosaic images from 3,520 down to 280, equalizing distribution across all 9 target varieties."),
                ("8 Minutes", "Rapid Edge Fine-Tuning", "MobileNetV3 transfer learning trained on 2,501 balanced samples across 8 epochs with AdamW optimization on CPU."),
                ("80.7% Acc", "Production Edge Model", "Exported 3.25 MB TFLite model achieving 80.7% training accuracy and 76.9% validation accuracy on Cassava & Rice blights.")
            ]
        },
        {
            "badge": "MARKET & TRACTION",
            "title": "Dual-Model Architecture & Live Product Suite",
            "subtitle": "Both models are fully built, packaged, and operational on Web and Android.",
            "type": "cards",
            "cards": [
                ("Mobile APKs", "PlantDiag v1.7 & v2.0", "Two compiled standalone Android APKs ready for deployment across rural extension teams and agribusiness field agents."),
                ("Dual Web Suite", "Live Interactive Simulator", "High-performance Python TFLite server with live model toggle, 1-click test chips, and instant multilingual voice readout."),
                ("38M Farmers", "Market Opportunity", "Targeting B2B extension service licensing, NGO food security deployments, agricultural insurance underwriting, and agrochemical input partnerships.")
            ]
        },
        {
            "badge": "WHY WE WIN",
            "title": "Competitive Moat & Defensibility",
            "subtitle": "Why generic AI competitors cannot compete in African agricultural environments.",
            "type": "cards",
            "cards": [
                ("100% Offline", "No Cloud Infras Cost", "Zero API bills, zero server maintenance costs, and 100% operational uptime in deep rural areas without internet."),
                ("Local Voice", "Literacy-Agnostic", "Farmers don't need to read English or complex chemical names; the app speaks practical step-by-step remedies in their mother tongue."),
                ("Data Moat", "Proprietary African Data", "Every offline extension visit builds an exclusive, ground-truthed agricultural epidemiological database across Nigeria.")
            ]
        },
        {
            "badge": "ROADMAP & THE VISION",
            "title": "Protecting $2B+ in African Smallholder Harvests",
            "subtitle": "Scaling from diagnostic prototype to continental agricultural intelligence infrastructure.",
            "type": "cards",
            "cards": [
                ("Q1 - Pilots", "Benue, Kaduna, Oyo", "Deploy 1,000 extension kits with state ministries of agriculture, cooperative unions, and IITA regional hubs."),
                ("Q2 - Expansion", "Yam, Cowpea & Sorghum", "Expand transfer learning head to incorporate Yam Anthracnose, Cowpea Blight, and Fall Armyworm pest damage."),
                ("2028 Vision", "Pan-African Platform", "Protecting 5,000,000+ hectares of staple cropland and saving over $2B in food losses across Sub-Saharan Africa.")
            ]
        }
    ]

    for slide_idx, sdata in enumerate(slides_data):
        slide = prs.slides.add_slide(blank_layout)

        # 1. Background dark card
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = C_BG_DARK
        bg_shape.line.fill.background()

        # 2. Top Banner Accent Line
        top_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12)
        )
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = C_EMERALD
        top_bar.line.fill.background()

        # 3. Slide Number & Header Badge
        badge_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(8.0), Inches(0.35))
        tf_badge = badge_box.text_frame
        tf_badge.word_wrap = True
        p_badge = tf_badge.paragraphs[0]
        p_badge.text = f"PLANTDIAG™ BY FHINOVAX™  |  SLIDE {slide_idx + 1:02d} — {sdata['badge']}"
        p_badge.font.name = "Calibri"
        p_badge.font.size = Pt(10.5)
        p_badge.font.bold = True
        p_badge.font.color.rgb = C_GOLD

        # 4. Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = sdata["title"]
        p_title.font.name = "Calibri"
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE

        # 5. Slide Subtitle
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.65), Inches(11.7), Inches(0.55))
        tf_sub = sub_box.text_frame
        tf_sub.word_wrap = True
        p_sub = tf_sub.paragraphs[0]
        p_sub.text = sdata["subtitle"]
        p_sub.font.name = "Calibri"
        p_sub.font.size = Pt(13.5)
        p_sub.font.color.rgb = C_MUTED

        if sdata["type"] == "title":
            # Big Title Points Box
            content_box = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.6), Inches(11.733), Inches(3.6)
            )
            content_box.fill.solid()
            content_box.fill.fore_color.rgb = C_CARD_BG
            content_box.line.color.rgb = C_PRIMARY
            content_box.line.width = Pt(1.5)

            tf_c = content_box.text_frame
            tf_c.word_wrap = True
            tf_c.margin_left = Inches(0.6)
            tf_c.margin_right = Inches(0.6)
            tf_c.margin_top = Inches(0.5)

            p0 = tf_c.paragraphs[0]
            p0.text = "CORE VALUE PROPOSITION & CAPABILITIES"
            p0.font.name = "Calibri"
            p0.font.size = Pt(14)
            p0.font.bold = True
            p0.font.color.rgb = C_GOLD
            p0.space_after = Pt(16)

            for pt in sdata["points"]:
                p = tf_c.add_paragraph()
                p.text = f"✔  {pt}"
                p.font.name = "Calibri"
                p.font.size = Pt(14)
                p.font.color.rgb = C_WHITE
                p.space_after = Pt(14)

        elif sdata["type"] == "cards":
            card_w = Inches(3.7)
            card_h = Inches(4.2)
            gap = Inches(0.316)
            left_base = Inches(0.8)
            top_y = Inches(2.4)

            for c_idx, (c_stat, c_heading, c_desc) in enumerate(sdata["cards"]):
                c_left = left_base + c_idx * (card_w + gap)

                card = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE, c_left, top_y, card_w, card_h
                )
                card.fill.solid()
                card.fill.fore_color.rgb = C_CARD_BG
                card.line.color.rgb = C_PRIMARY if c_idx == 0 else RGBColor(40, 58, 82)
                card.line.width = Pt(1.2)

                tf = card.text_frame
                tf.word_wrap = True
                tf.margin_left = Inches(0.3)
                tf.margin_right = Inches(0.3)
                tf.margin_top = Inches(0.4)

                # Stat / Accent Top
                p_stat = tf.paragraphs[0]
                p_stat.text = c_stat
                p_stat.font.name = "Calibri"
                p_stat.font.size = Pt(22)
                p_stat.font.bold = True
                p_stat.font.color.rgb = C_GOLD
                p_stat.space_after = Pt(8)

                # Card Heading
                p_head = tf.add_paragraph()
                p_head.text = c_heading
                p_head.font.name = "Calibri"
                p_head.font.size = Pt(14)
                p_head.font.bold = True
                p_head.font.color.rgb = C_WHITE
                p_head.space_after = Pt(10)

                # Description
                p_desc = tf.add_paragraph()
                p_desc.text = c_desc
                p_desc.font.name = "Calibri"
                p_desc.font.size = Pt(11)
                p_desc.font.color.rgb = C_MUTED
                p_desc.line_spacing = 1.15

        # Bottom Footer on all slides
        foot_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.85), Inches(11.7), Inches(0.35))
        tf_foot = foot_box.text_frame
        p_foot = tf_foot.paragraphs[0]
        p_foot.text = "PlantDiag™ by Fhinovax™ · Built for Rural Agricultural Resilience in Sub-Saharan Africa"
        p_foot.font.name = "Calibri"
        p_foot.font.size = Pt(9.5)
        p_foot.font.color.rgb = RGBColor(100, 116, 139)

    prs.save(str(PPTX_OUT))
    print(f"Generated PowerPoint Presentation successfully at:\n  {PPTX_OUT}")


# ----------------------------------------------------------------------
# 2. GENERATE PDF (REPORTLAB)
# ----------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        # Top banner line
        self.setFillColor(colors.HexColor("#006837"))
        self.rect(0, 580, 792, 12, fill=1, stroke=0)

        # Footer
        self.setFillColor(colors.HexColor("#D4AF37"))
        self.rect(36, 32, 720, 1, fill=1, stroke=0)

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(36, 20, "PlantDiag™ by Fhinovax™ · Pitch Deck Dossier")

        page_str = f"Slide {self._pageNumber} of {page_count}"
        self.drawRightString(756, 20, page_str)
        self.restoreState()


def generate_pdf():
    # Landscape Letter page size: 11 x 8.5 inches (792 x 612 pt)
    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_badge = ParagraphStyle(
        "SlideBadge",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.HexColor("#D4AF37"),
        spaceAfter=4,
        textTransform="uppercase"
    )

    style_title = ParagraphStyle(
        "SlideTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#006837"),
        spaceAfter=6
    )

    style_subtitle = ParagraphStyle(
        "SlideSubtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=16
    )

    style_card_stat = ParagraphStyle(
        "CardStat",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=colors.HexColor("#D4AF37"),
        spaceAfter=4
    )

    style_card_head = ParagraphStyle(
        "CardHead",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6
    )

    style_card_body = ParagraphStyle(
        "CardBody",
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#334155")
    )

    style_bullet = ParagraphStyle(
        "TitleBullet",
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=10
    )

    slides_content = [
        {
            "badge": "Executive Pitch Deck",
            "title": "PlantDiag™ by Fhinovax™",
            "subtitle": "100% Offline Edge-AI Crop Disease Diagnosis & Multilingual Voice Advisory",
            "type": "title",
            "bullets": [
                "<b>Massive Market Need:</b> Empowering 38M+ smallholder farmers across Sub-Saharan Africa who currently lack agricultural extension worker access.",
                "<b>Sub-200ms Neural Diagnostics:</b> Operates completely without cellular signal or internet subscriptions using on-device TFLite edge models.",
                "<b>5-Language Voice Synthesis:</b> Speaks diagnosis and treatments aloud in English, Hausa, Yoruba, Igbo, and Nigerian Pidgin for low-literacy inclusion.",
                "<b>Autonomous Data Moat:</b> Every offline farm scan logs farmer profile, crop health, and disease vectors into local SQLite for national food security intelligence."
            ]
        },
        {
            "badge": "The Rural Crisis",
            "title": "Smallholders Lose 40% of Harvest to Preventable Blights",
            "subtitle": "A systemic advisory deficit is crippling food production in African agricultural belts.",
            "type": "cards",
            "cards": [
                ("1 : 5,000", "Extension Worker Deficit", "In rural Nigeria, there is only one government extension agent per 5,000 farmers. By the time an agronomist visits, crops are already lost."),
                ("40% Loss", "Annual Harvest Destruction", "Cassava Mosaic, Maize Rust, and Rice Blast destroy billions of naira in staple crop yields every single harvest season."),
                ("0% Signal", "Cloud AI Latency Failure", "Cloud-reliant AI tools fail completely in remote rural farms where cellular connectivity is nonexistent, unstable, or expensive.")
            ]
        },
        {
            "badge": "The Solution",
            "title": "PlantDiag™ — The Pocket Agronomist",
            "subtitle": "An autonomous edge computer vision doctor that speaks the farmer's native tongue.",
            "type": "cards",
            "cards": [
                ("< 200 ms", "On-Device Edge Vision", "Diagnoses leaf blights directly on local phone silicon using quantized neural networks with zero cloud API latency or ongoing costs."),
                ("5 Dialects", "Native Local Speech", "Reads disease names, severity levels, and treatment regimens aloud in Hausa, Yoruba, Igbo, Pidgin, and English."),
                ("Zero Risk", "Anti-Hallucination Gate", "Dual-stage chlorophyll colorimetry and Shannon entropy gates reject non-plants and unknown leaves rather than guessing false cures.")
            ]
        },
        {
            "badge": "Engineering Architecture",
            "title": "Built for Extreme Rural Resilience",
            "subtitle": "Zero cloud dependencies, zero recurring server bills, and instant battery-efficient execution.",
            "type": "cards",
            "cards": [
                ("Frontend Shell", "Capacitor 5 + Vanilla JS", "Pure ESModules and high-contrast responsive glassmorphic UI. Zero framework bloat ensures instant, smooth responsiveness."),
                ("Native Bridge", "Android Java JNI + XNNPACK", "Direct ByteBuffer interfacing with TensorFlow Lite multi-threaded CPU acceleration on budget MediaTek & Snapdragon devices."),
                ("Field Registry", "Offline SQLite Database", "Stores farmer NINs, village GPS, disease history, and severity levels offline, ready for automated batch sync when signal returns.")
            ]
        },
        {
            "badge": "Diagnostic Pipeline",
            "title": "End-to-End Edge Inference Workflow",
            "subtitle": "From raw leaf photo to vocalized agronomic prescription in 6 automated steps.",
            "type": "cards",
            "cards": [
                ("1. Capture & Gate", "Chlorophyll & Texture Filter", "Raw pixels are analyzed for live photosynthetic pigment and cellular gradient variation to reject walls, furniture, or non-plants."),
                ("2. Direct JNI Pass", "Memory-Mapped Tensor Bridge", "TFLiteInterpreterPlugin loads model via zero-copy memory maps and delivers normalized arrays directly to edge silicon."),
                ("3. Entropy & Voice", "Uncertainty Gate & Local Speech", "Evaluates statistical entropy to ensure confidence, pulls organic remedies from offline DB, and speaks aloud via TTS.")
            ]
        },
        {
            "badge": "Diagnostic Scope",
            "title": "Baseline Coverage: 38 Crop-Disease Conditions",
            "subtitle": "Comprehensive commercial crop coverage validated on over 54,000 pathological leaf images.",
            "type": "cards",
            "cards": [
                ("Cereal Staples", "Corn (Maize) Suite", "Identifies Common Rust, Northern Leaf Blight, Gray Leaf Spot, and Healthy foliage with 95%+ precision."),
                ("Horticulture", "Tomato & Pepper Suite", "Diagnoses Early Blight, Late Blight, Bacterial Spot, Septoria, Leaf Mold, Spider Mites, TYLCV, and Mosaic Virus."),
                ("Tubers & Fruits", "Potato, Citrus & Fruits", "Covers Potato Early/Late Blights, Citrus Greening (HLB), Apple Scabs, Grape Esca, Strawberry Leaf Scorch, and Squash Mildew.")
            ]
        },
        {
            "badge": "Phase 2 Breakthrough",
            "title": "Transfer Learning: Adding African Regional Staples",
            "subtitle": "Fine-tuning missing regional varieties (Cassava & Rice) in under 10 minutes on CPU.",
            "type": "cards",
            "cards": [
                ("Balanced Data", "Eliminating Class Bias", "Capped dominant Cassava Mosaic images from 3,520 down to 280, equalizing distribution across all 9 target varieties."),
                ("8 Minutes", "Rapid Edge Fine-Tuning", "MobileNetV3 transfer learning trained on 2,501 balanced samples across 8 epochs with AdamW optimization on CPU."),
                ("80.7% Acc", "Production Edge Model", "Exported 3.25 MB TFLite model achieving 80.7% training accuracy and 76.9% validation accuracy on Cassava & Rice blights.")
            ]
        },
        {
            "badge": "Product Suite & Traction",
            "title": "Dual-Model Architecture & Live Product Suite",
            "subtitle": "Both models are fully built, packaged, and operational on Web and Android.",
            "type": "cards",
            "cards": [
                ("Mobile APKs", "PlantDiag v1.7 & v2.0", "Two compiled standalone Android APKs ready for deployment across rural extension teams and agribusiness field agents."),
                ("Dual Web Suite", "Live Interactive Simulator", "High-performance Python TFLite server with live model toggle, 1-click test chips, and instant multilingual voice readout."),
                ("38M Farmers", "Market Opportunity", "Targeting B2B extension service licensing, NGO food security deployments, agricultural insurance underwriting, and agrochemical input partnerships.")
            ]
        },
        {
            "badge": "Competitive Moat",
            "title": "Why Generic AI Cannot Compete in Africa",
            "subtitle": "Our defensibility lies in edge autonomy, language accessibility, and ground data capture.",
            "type": "cards",
            "cards": [
                ("100% Offline", "No Cloud Infras Cost", "Zero API bills, zero server maintenance costs, and 100% operational uptime in deep rural areas without internet."),
                ("Local Voice", "Literacy-Agnostic", "Farmers don't need to read English or complex chemical names; the app speaks practical step-by-step remedies in their mother tongue."),
                ("Data Moat", "Proprietary African Data", "Every offline extension visit builds an exclusive, ground-truthed agricultural epidemiological database across Nigeria.")
            ]
        },
        {
            "badge": "Roadmap & Vision",
            "title": "Protecting $2B+ in African Smallholder Harvests",
            "subtitle": "Scaling from diagnostic prototype to continental agricultural intelligence infrastructure.",
            "type": "cards",
            "cards": [
                ("Q1 - Pilots", "Benue, Kaduna, Oyo", "Deploy 1,000 extension kits with state ministries of agriculture, cooperative unions, and IITA regional hubs."),
                ("Q2 - Expansion", "Yam, Cowpea & Sorghum", "Expand transfer learning head to incorporate Yam Anthracnose, Cowpea Blight, and Fall Armyworm pest damage."),
                ("2028 Vision", "Pan-African Platform", "Protecting 5,000,000+ hectares of staple cropland and saving over $2B in food losses across Sub-Saharan Africa.")
            ]
        }
    ]

    story = []

    for idx, sdata in enumerate(slides_content):
        story.append(Paragraph(f"PLANTDIAG™ BY FHINOVAX™  |  SLIDE {idx+1:02d} — {sdata['badge']}", style_badge))
        story.append(Paragraph(sdata["title"], style_title))
        story.append(Paragraph(sdata["subtitle"], style_subtitle))

        if sdata["type"] == "title":
            bullet_data = [[Paragraph(f"• {b}", style_bullet)] for b in sdata["bullets"]]
            t_bullets = Table(bullet_data, colWidths=[700])
            t_bullets.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor("#006837")),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 16),
                ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ]))
            story.append(t_bullets)

        elif sdata["type"] == "cards":
            col_w = 230
            card_cells = []
            for stat, head, desc in sdata["cards"]:
                cell_content = [
                    Paragraph(stat, style_card_stat),
                    Spacer(1, 4),
                    Paragraph(head, style_card_head),
                    Spacer(1, 4),
                    Paragraph(desc, style_card_body)
                ]
                card_cells.append(cell_content)

            t_cards = Table([card_cells], colWidths=[col_w, col_w, col_w])
            t_cards.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (0, 0), 1.5, colors.HexColor("#006837")),
                ('BOX', (1, 0), (1, 0), 1, colors.HexColor("#CBD5E1")),
                ('BOX', (2, 0), (2, 0), 1, colors.HexColor("#CBD5E1")),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 14),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
                ('LEFTPADDING', (0, 0), (-1, -1), 14),
                ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ]))
            story.append(t_cards)

        if idx < len(slides_content) - 1:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated PDF Presentation successfully at:\n  {PDF_OUT}")


if __name__ == "__main__":
    generate_pptx()
    generate_pdf()
