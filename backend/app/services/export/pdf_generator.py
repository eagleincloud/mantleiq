"""
PDF report generation using ReportLab.
Creates professional prospectivity analysis briefings with maps, scores, and attribution.
"""

from datetime import datetime
from typing import Optional, Dict, List
from io import BytesIO
import logging

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """
    Generate professional PDF reports for prospectivity zones.

    Report includes:
    - Title page with zone name and score
    - Zone location map (placeholder)
    - Score breakdown (6 factors)
    - Feature attribution table
    - Missing data caveats
    - Recommendations
    """

    def __init__(self, page_size=letter, title="MantleIQ Prospectivity Analysis"):
        """
        Initialize PDF generator.

        Args:
            page_size: Page size (letter or A4)
            title: Document title
        """
        self.page_size = page_size
        self.title = title
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        # Standard margins
        self.left_margin = 0.75 * inch
        self.right_margin = 0.75 * inch
        self.top_margin = 0.75 * inch
        self.bottom_margin = 0.75 * inch

    def _setup_custom_styles(self):
        """Define custom paragraph styles."""
        # Title style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=28,
                textColor=colors.HexColor("#0F4C75"),  # Dark teal
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Score highlight style
        self.styles.add(
            ParagraphStyle(
                name="ScoreHighlight",
                parent=self.styles["Normal"],
                fontSize=24,
                textColor=colors.HexColor("#D94848"),  # Red for high scores
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
        )

        # Section heading
        self.styles.add(
            ParagraphStyle(
                name="SectionHeading",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#087F8C"),  # Medium teal
                spaceAfter=6,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )
        )

    def generate_report(
        self,
        zone_name: str,
        basin_name: str,
        final_score: float,
        final_rank: int,
        score_class: str,
        score_components: Dict[str, float],
        top_features: List[Dict],
        missing_data_caveats: List[str],
        narrative_summary: str,
        recommended_actions: List[str],
        confidence_score: float = 0.8,
    ) -> bytes:
        """
        Generate complete PDF report.

        Args:
            zone_name: Zone name
            basin_name: Basin name
            final_score: Score [0, 1]
            final_rank: Percentile rank [0-100]
            score_class: Score interpretation
            score_components: {f_generation, f_fluid_interaction, ...}
            top_features: List of top contributing features
            missing_data_caveats: Data quality caveats
            narrative_summary: Human-readable summary
            recommended_actions: List of recommendations
            confidence_score: Confidence [0.5, 1.0]

        Returns:
            PDF file as bytes
        """
        # Create PDF in memory
        pdf_buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=self.page_size,
            leftMargin=self.left_margin,
            rightMargin=self.right_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin,
        )

        # Build document story
        story = []

        # Page 1: Title page
        story.extend(self._create_title_page(zone_name, basin_name, final_score, final_rank, score_class))

        story.append(PageBreak())

        # Page 2: Score breakdown and narrative
        story.extend(self._create_score_breakdown(score_components, confidence_score, narrative_summary))

        story.append(PageBreak())

        # Page 3: Feature attribution and recommendations
        story.extend(self._create_attribution_page(top_features, missing_data_caveats, recommended_actions))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()

    def _create_title_page(
        self,
        zone_name: str,
        basin_name: str,
        final_score: float,
        final_rank: int,
        score_class: str,
    ) -> List:
        """Create title page content."""
        story = []

        # Spacer
        story.append(Spacer(1, 1.5 * inch))

        # Report title
        story.append(
            Paragraph(self.title, self.styles["CustomTitle"])
        )

        story.append(Spacer(1, 0.25 * inch))

        # Zone name
        story.append(
            Paragraph(f"<b>{zone_name}</b>", self.styles["Heading2"])
        )

        story.append(Spacer(1, 0.1 * inch))

        # Basin name
        story.append(
            Paragraph(f"Basin: {basin_name}", self.styles["Normal"])
        )

        story.append(Spacer(1, 0.5 * inch))

        # Score highlight
        score_text = f"{final_score * 100:.1f}th Percentile"
        story.append(
            Paragraph(score_text, self.styles["ScoreHighlight"])
        )

        story.append(Spacer(1, 0.1 * inch))

        # Score interpretation
        story.append(
            Paragraph(
                f"<b>{score_class}</b>",
                self.styles["Heading3"]
            )
        )

        story.append(Spacer(1, 0.25 * inch))

        # Quick stats
        stats_text = f"Rank: {final_rank}th percentile"
        story.append(
            Paragraph(stats_text, self.styles["Normal"])
        )

        story.append(Spacer(1, 0.5 * inch))

        # Generated date
        generated_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        story.append(
            Paragraph(
                f"<i>Generated: {generated_date}</i>",
                self.styles["Normal"]
            )
        )

        return story

    def _create_score_breakdown(
        self,
        score_components: Dict[str, float],
        confidence_score: float,
        narrative_summary: str,
    ) -> List:
        """Create score breakdown and narrative section."""
        story = []

        # Section heading
        story.append(
            Paragraph("Score Analysis", self.styles["SectionHeading"])
        )

        story.append(Spacer(1, 0.15 * inch))

        # Narrative
        story.append(
            Paragraph(narrative_summary, self.styles["Normal"])
        )

        story.append(Spacer(1, 0.25 * inch))

        # Score components table
        story.append(
            Paragraph("Factor Contributions", self.styles["Heading3"])
        )

        story.append(Spacer(1, 0.1 * inch))

        # Create table data
        table_data = [
            ["Factor", "Score", "Interpretation"]
        ]

        factor_interpretations = {
            "f_generation": "Hydrogen Generation",
            "f_fluid_interaction": "Fluid Circulation",
            "f_structural_pathways": "Structural Pathways",
            "f_trap_retention": "Trap Retention",
            "f_surface_indicators": "Surface Indicators",
            "f_thermodynamic": "Thermodynamic Window",
        }

        for factor, score in score_components.items():
            label = factor_interpretations.get(factor, factor.replace("_", " "))
            score_pct = f"{score * 100:.1f}%"

            # Interpretation
            if score >= 0.8:
                interp = "Excellent"
            elif score >= 0.6:
                interp = "Good"
            elif score >= 0.4:
                interp = "Moderate"
            else:
                interp = "Poor"

            table_data.append([label, score_pct, interp])

        # Create table
        factor_table = Table(table_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch])
        factor_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#087F8C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        story.append(factor_table)

        story.append(Spacer(1, 0.25 * inch))

        # Confidence note
        story.append(
            Paragraph("Confidence & Data Quality", self.styles["Heading3"])
        )

        story.append(Spacer(1, 0.1 * inch))

        conf_text = f"Confidence Score: <b>{confidence_score:.1%}</b>"
        story.append(
            Paragraph(conf_text, self.styles["Normal"])
        )

        return story

    def _create_attribution_page(
        self,
        top_features: List[Dict],
        missing_data_caveats: List[str],
        recommended_actions: List[str],
    ) -> List:
        """Create feature attribution and recommendations section."""
        story = []

        # Top features section
        story.append(
            Paragraph("Contributing Factors", self.styles["SectionHeading"])
        )

        story.append(Spacer(1, 0.1 * inch))

        for idx, feature in enumerate(top_features[:4], 1):
            label = feature.get("label", feature.get("name", "Unknown"))
            contribution = feature.get("contribution", 0)
            text = f"<b>{idx}. {label}</b> — {contribution:.1f}% contribution"
            story.append(
                Paragraph(text, self.styles["Normal"])
            )

        story.append(Spacer(1, 0.25 * inch))

        # Missing data section
        if missing_data_caveats:
            story.append(
                Paragraph("Data Quality Notes", self.styles["SectionHeading"])
            )

            story.append(Spacer(1, 0.1 * inch))

            for caveat in missing_data_caveats:
                text = f"⚠️ {caveat}"
                story.append(
                    Paragraph(text, self.styles["Normal"])
                )

            story.append(Spacer(1, 0.25 * inch))

        # Recommendations section
        if recommended_actions:
            story.append(
                Paragraph("Recommended Next Steps", self.styles["SectionHeading"])
            )

            story.append(Spacer(1, 0.1 * inch))

            for action in recommended_actions[:6]:
                text = f"• {action}"
                story.append(
                    Paragraph(text, self.styles["Normal"])
                )

            story.append(Spacer(1, 0.15 * inch))

        # Footer note
        story.append(Spacer(1, 0.5 * inch))

        footer_text = (
            "<i>This report is based on prospectivity modeling. "
            "Recommended actions should be validated through field surveys and "
            "additional data acquisition.</i>"
        )
        story.append(
            Paragraph(footer_text, self.styles["Normal"])
        )

        return story
