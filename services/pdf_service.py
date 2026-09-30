"""Builds a polished study-guide PDF from a VideoAnalysis record using ReportLab."""

import html
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#2B2D6E")
AMBER = colors.HexColor("#E8A33D")
CHARCOAL = colors.HexColor("#1F2430")
MUTED = colors.HexColor("#6B7280")


def _safe_text(value):
    """
    Escape AI/user-generated text so ReportLab does not interpret
    <, >, &, etc. as HTML/XML markup.
    """
    if value is None:
        return ""

    return html.escape(str(value))


def _styles():
    base = getSampleStyleSheet()

    styles = {
        "Title": ParagraphStyle(
            "TitleCustom",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=INK,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),

        "Meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=MUTED,
            spaceAfter=16,
        ),

        "H2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=INK,
            spaceBefore=18,
            spaceAfter=8,
        ),

        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            textColor=CHARCOAL,
            leading=15,
        ),

        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            textColor=CHARCOAL,
            leading=15,
        ),

        "CardFront": ParagraphStyle(
            "CardFront",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            textColor=INK,
            leading=14,
        ),

        "CardBack": ParagraphStyle(
            "CardBack",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=CHARCOAL,
            leading=14,
        ),
    }

    return styles


def build_pdf(analysis, output_path: str) -> str:

    # Make sure the export folder exists
    output_dir = os.path.dirname(output_path)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        title=_safe_text(analysis.video_title),
    )

    s = _styles()
    story = []

    # ================================================================
    # HEADER
    # ================================================================

    story.append(
        Paragraph(
            "AI Learning Companion — Study Guide",
            s["Meta"],
        )
    )

    story.append(
        Paragraph(
            _safe_text(analysis.video_title),
            s["Title"],
        )
    )

    meta_bits = []

    if analysis.channel_name:
        meta_bits.append(
            _safe_text(analysis.channel_name)
        )

    if analysis.video_url:
        meta_bits.append(
            _safe_text(analysis.video_url)
        )

    if meta_bits:
        story.append(
            Paragraph(
                " &nbsp;•&nbsp; ".join(meta_bits),
                s["Meta"],
            )
        )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1.2,
            color=AMBER,
            spaceAfter=10,
        )
    )

    # ================================================================
    # SUMMARY
    # ================================================================

    if analysis.summary:

        story.append(
            Paragraph(
                "Summary",
                s["H2"],
            )
        )

        story.append(
            Paragraph(
                _safe_text(analysis.summary),
                s["Body"],
            )
        )

    # ================================================================
    # KEY POINTS
    # ================================================================

    if analysis.key_points:

        story.append(
            Paragraph(
                "Key Points",
                s["H2"],
            )
        )

        items = []

        for kp in analysis.key_points:

            safe_kp = _safe_text(kp)

            items.append(
                ListItem(
                    Paragraph(
                        safe_kp,
                        s["Bullet"],
                    ),
                    bulletColor=AMBER,
                )
            )

        story.append(
            ListFlowable(
                items,
                bulletType="bullet",
                start="circle",
                leftIndent=14,
            )
        )

    # ================================================================
    # GLOSSARY
    # ================================================================

    if analysis.glossary:

        story.append(
            Paragraph(
                "Glossary",
                s["H2"],
            )
        )

        rows = []

        for g in analysis.glossary:

            term = _safe_text(
                g.get("term", "")
            )

            definition = _safe_text(
                g.get("definition", "")
            )

            rows.append(
                [
                    Paragraph(
                        f"<b>{term}</b>",
                        s["Body"],
                    ),
                    Paragraph(
                        definition,
                        s["Body"],
                    ),
                ]
            )

        table = Table(
            rows,
            colWidths=[
                1.6 * inch,
                4.5 * inch,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LINEBELOW",
                        (0, 0),
                        (-1, -2),
                        0.5,
                        colors.HexColor("#E5E7EB"),
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(table)

    # ================================================================
    # FLASHCARDS
    # ================================================================

    if analysis.flashcards:

        story.append(PageBreak())

        story.append(
            Paragraph(
                "Flashcards",
                s["H2"],
            )
        )

        for i, card in enumerate(
            analysis.flashcards,
            start=1,
        ):

            front = _safe_text(
                card.get("front", "")
            )

            back = _safe_text(
                card.get("back", "")
            )

            row = Table(
                [
                    [
                        Paragraph(
                            f"Q{i}. {front}",
                            s["CardFront"],
                        )
                    ],
                    [
                        Paragraph(
                            back,
                            s["CardBack"],
                        )
                    ],
                ],
                colWidths=[
                    6.1 * inch
                ],
            )

            row.setStyle(
                TableStyle(
                    [
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.75,
                            colors.HexColor("#E5E7EB"),
                        ),
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#F4F1EA"),
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            10,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            10,
                        ),
                    ]
                )
            )

            story.append(row)

            story.append(
                Spacer(1, 8)
            )

    # ================================================================
    # QUIZ
    # ================================================================

    if analysis.quiz:

        story.append(PageBreak())

        story.append(
            Paragraph(
                "Practice Quiz",
                s["H2"],
            )
        )

        for i, q in enumerate(
            analysis.quiz,
            start=1,
        ):

            # ----------------------------
            # Question
            # ----------------------------

            question = _safe_text(
                q.get("question", "")
            )

            story.append(
                Paragraph(
                    f"{i}. {question}",
                    s["Body"],
                )
            )

            # ----------------------------
            # Options
            # ----------------------------

            options = q.get(
                "options",
                []
            )

            correct_idx = q.get(
                "correct_index",
                -1
            )

            opt_items = []

            for idx, opt in enumerate(options):

                if idx < 4:
                    prefix = "ABCD"[idx]
                else:
                    prefix = str(idx)

                safe_option = _safe_text(opt)

                # Our own formatting tags are added AFTER escaping
                text = (
                    f"<b>{prefix}.</b> "
                    f"{safe_option}"
                )

                if idx == correct_idx:

                    text += (
                        "  "
                        "<font color='#1a7f37'>"
                        "<b>&#10003; correct</b>"
                        "</font>"
                    )

                opt_items.append(
                    ListItem(
                        Paragraph(
                            text,
                            s["Bullet"],
                        )
                    )
                )

            if opt_items:

                story.append(
                    ListFlowable(
                        opt_items,
                        bulletType="bullet",
                        leftIndent=14,
                    )
                )

            # ----------------------------
            # Explanation
            # ----------------------------

            explanation = q.get(
                "explanation",
                ""
            )

            if explanation:

                safe_explanation = _safe_text(
                    explanation
                )

                story.append(
                    Paragraph(
                        f"<i>Why: {safe_explanation}</i>",
                        s["Meta"],
                    )
                )

            story.append(
                Spacer(1, 6)
            )

    # ================================================================
    # BUILD PDF
    # ================================================================

    doc.build(story)

    return output_path