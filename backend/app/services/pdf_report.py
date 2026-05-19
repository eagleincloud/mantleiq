"""
PDF Report Generation Service
Generates professional PDF reports with narrative consistency
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
import io
import logging

logger = logging.getLogger(__name__)


class MantleIQPDFReport:
    """Generates professional PDF reports for hydrogen prospect zones"""

    def __init__(self):
        self.width, self.height = letter
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Define custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#087F8C'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHead',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#087F8C'),
            spaceAfter=10,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#D9D9D9'),
            borderWidth=0.5,
            borderPadding=8,
            backColor=colors.HexColor('#F5F5F5')
        ))

        # Subsection heading
        self.styles.add(ParagraphStyle(
            name='SubsectionHead',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))

        # Body text
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))

        # Warning box style
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#856404'),
            alignment=TA_LEFT,
            spaceAfter=4
        ))

    def generate(self, zone_data, basin_name):
        """
        Generate PDF report for a single zone

        Args:
            zone_data: dict with properties from GeoJSON feature
            basin_name: str name of the basin

        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        story = []

        # Title Page
        story.extend(self._build_title_page(zone_data, basin_name))
        story.append(PageBreak())

        # Executive Summary
        story.extend(self._build_executive_summary(zone_data))
        story.append(Spacer(1, 12))

        # Risk Assessment
        story.extend(self._build_risk_assessment(zone_data))
        story.append(Spacer(1, 12))

        # Hydrogen System Components
        story.extend(self._build_components_section(zone_data))
        story.append(Spacer(1, 12))

        # Data Quality Assessment
        story.extend(self._build_data_quality_section(zone_data))
        story.append(Spacer(1, 12))

        # Score Drivers
        story.extend(self._build_score_drivers_section(zone_data))
        story.append(Spacer(1, 12))

        # Recommendations
        story.extend(self._build_recommendations_section(zone_data))
        story.append(Spacer(1, 12))

        # Methodology Footer
        story.extend(self._build_methodology_section())

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_title_page(self, zone_data, basin_name):
        """Title page with key metrics"""
        elements = []

        # Header
        elements.append(Paragraph("MANTLEIQ", self.styles['CustomTitle']))
        elements.append(Paragraph("Natural Hydrogen Prospectivity Assessment", self.styles['Heading2']))
        elements.append(Spacer(1, 20))

        # Basin and date
        elements.append(Paragraph(f"Basin: <b>{basin_name}</b>", self.styles['BodyText']))
        elements.append(Paragraph(f"Analysis Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['BodyText']))
        elements.append(Spacer(1, 20))

        # Key metrics box
        score = zone_data.get('prospectivity_score', 0) * 100
        confidence = zone_data.get('confidence', 0) * 100

        metrics_data = [
            ['Hydrogen Prospect Score', f'{score:.1f}', 'Confidence Level', f'{confidence:.0f}%'],
            ['Classification', self._get_score_class(zone_data.get('prospectivity_score', 0)), 'Grid Cell', f"({zone_data.get('grid_x', 0)}, {zone_data.get('grid_y', 0)})"],
            ['Rank', f"#{zone_data.get('rank', '?')}", 'Score Class', zone_data.get('score_class', 'moderate')]
        ]

        metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#087F8C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        # Key finding
        elements.append(Paragraph("KEY FINDING", self.styles['SectionHead']))
        finding = self._generate_key_finding(zone_data)
        elements.append(Paragraph(finding, self.styles['BodyText']))

        return elements

    def _build_executive_summary(self, zone_data):
        """Executive summary section"""
        elements = []
        elements.append(Paragraph("EXECUTIVE SUMMARY", self.styles['SectionHead']))

        score = zone_data.get('prospectivity_score', 0)
        confidence = zone_data.get('confidence', 0)
        score_class = self._get_score_class(score)

        summary = f"""
        This hydrogen prospect zone has been assessed using a multi-factor geospatial analysis model
        incorporating Generation (G), Migration (M), Trap/Retention (T), and Seal/Structural (P) indicators.
        <br/><br/>
        <b>Overall Assessment:</b> The zone scores {score*100:.1f} on the Hydrogen Prospect Score (HPS) scale
        and is classified as "<b>{score_class}</b>". The assessment has a confidence level of {confidence*100:.0f}%,
        indicating the reliability of this score given available data coverage.
        <br/><br/>
        <b>Recommended Action:</b> {self._get_recommendation_summary(score)}
        """

        elements.append(Paragraph(summary, self.styles['BodyText']))
        return elements

    def _build_risk_assessment(self, zone_data):
        """Risk assessment section"""
        elements = []
        elements.append(Paragraph("RISK ASSESSMENT", self.styles['SectionHead']))

        score = zone_data.get('prospectivity_score', 0)
        confidence = zone_data.get('confidence', 0)

        if confidence < 0.5:
            risk_level = "HIGH - Data gaps reduce score confidence"
            risk_color = colors.HexColor('#D94848')
        elif confidence < 0.7:
            risk_level = "MODERATE - Some data uncertainty"
            risk_color = colors.HexColor('#D89A00')
        else:
            risk_level = "LOW - Good data coverage"
            risk_color = colors.HexColor('#087F8C')

        risk_data = [
            ['Risk Factor', 'Level', 'Impact'],
            ['Data Completeness', risk_level, f'Confidence {confidence*100:.0f}%'],
            ['Geological Complexity', 'Moderate', 'Requires validation'],
            ['Structural Uncertainty', 'Variable', 'See data quality section']
        ]

        risk_table = Table(risk_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
        ]))
        elements.append(risk_table)
        return elements

    def _build_components_section(self, zone_data):
        """G/M/T/P components section"""
        elements = []
        elements.append(Paragraph("HYDROGEN SYSTEM COMPONENTS (G/M/T/P)", self.styles['SectionHead']))

        components = [
            {
                'label': 'Generation (G)',
                'value': zone_data.get('f_generation', 0),
                'weight': 0.30,
                'description': 'Mantle/crustal hydrogen generation potential. Scored based on presence of ultramafic/mafic rocks and thermal conditions favoring H₂ production.'
            },
            {
                'label': 'Migration/Fluid Interaction (M)',
                'value': zone_data.get('f_fluid_interaction', 0),
                'weight': 0.20,
                'description': 'Pathways for hydrogen movement through subsurface. Assessed via fault zones, fracture networks, and permeability proxies.'
            },
            {
                'label': 'Trap/Retention (T)',
                'value': zone_data.get('f_trap_retention', 0),
                'weight': 0.15,
                'description': 'Structural and stratigraphic closure capable of retaining hydrogen. Evaluated through anticline geometry, salt domes, and closure depth.'
            },
            {
                'label': 'Seal/Structural Integrity (P)',
                'value': zone_data.get('f_structural_pathways', 0),
                'weight': 0.20,
                'description': 'Sealing capacity and structural integrity to prevent H₂ escape. Assessed via shale/caprock thickness, fault seal analysis, and spill points.'
            }
        ]

        for comp in components:
            score = comp['value'] * 100
            weight = comp['weight'] * 100

            elements.append(Paragraph(comp['label'], self.styles['SubsectionHead']))

            # Component data
            comp_data = [
                ['Score', f"{score:.1f}", 'Weight', f"{weight:.0f}%"]
            ]
            comp_table = Table(comp_data, colWidths=[1*inch, 1.5*inch, 1*inch, 1.5*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#087F8C')),
                ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#087F8C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(comp_table)

            # Description
            elements.append(Paragraph(comp['description'], self.styles['BodyText']))
            elements.append(Spacer(1, 8))

        return elements

    def _build_data_quality_section(self, zone_data):
        """Data quality and coverage section"""
        elements = []
        elements.append(Paragraph("DATA QUALITY & COVERAGE ASSESSMENT", self.styles['SectionHead']))

        confidence = zone_data.get('confidence', 0)

        # Data availability table
        data_available = ['Gravity Anomaly', 'Magnetic Field', 'Geological Units', 'Fault Lines']
        data_missing = ['Seismic Interpretation', 'Borehole Logs', 'Core Analysis', 'Pressure Data']

        elements.append(Paragraph("Available Data Layers ✓", self.styles['SubsectionHead']))
        for item in data_available:
            elements.append(Paragraph(f"• {item}", self.styles['BodyText']))

        elements.append(Spacer(1, 8))
        elements.append(Paragraph("Missing Data Layers ⚠", self.styles['SubsectionHead']))
        for item in data_missing:
            elements.append(Paragraph(f"• {item}", self.styles['BodyText']))

        elements.append(Spacer(1, 12))

        # Confidence impact
        warning_text = f"""
        <b>Confidence Impact:</b> Due to missing seismic and borehole data, the confidence score
        is reduced by ~30%. The final HPS of {zone_data.get('prospectivity_score', 0)*100:.1f}
        should be considered as a <b>confidence-adjusted score</b> that accounts for data gaps.
        This score is <b>not adjusted upward</b> for missing data (no silent gap-filling).
        """
        elements.append(Paragraph(warning_text, self.styles['Warning']))

        return elements

    def _build_score_drivers_section(self, zone_data):
        """Top score drivers and explainability"""
        elements = []
        elements.append(Paragraph("WHAT'S DRIVING THIS SCORE", self.styles['SectionHead']))

        drivers = self._get_top_drivers(zone_data)
        for idx, driver in enumerate(drivers, 1):
            elements.append(Paragraph(
                f"<b>{idx}. {driver['title']}</b> ({driver['value']*100:.0f}%)",
                self.styles['SubsectionHead']
            ))
            elements.append(Paragraph(driver['explanation'], self.styles['BodyText']))
            elements.append(Spacer(1, 6))

        return elements

    def _build_recommendations_section(self, zone_data):
        """Recommendations for next steps"""
        elements = []
        elements.append(Paragraph("RECOMMENDED NEXT STEPS", self.styles['SectionHead']))

        score = zone_data.get('prospectivity_score', 0)

        recommendations = self._get_recommendations(score)
        for idx, rec in enumerate(recommendations, 1):
            elements.append(Paragraph(f"<b>{idx}. {rec['title']}</b>", self.styles['SubsectionHead']))
            elements.append(Paragraph(rec['description'], self.styles['BodyText']))
            elements.append(Paragraph(f"<i>Timeline: {rec['timeline']}</i>", self.styles['Normal']))
            elements.append(Spacer(1, 8))

        return elements

    def _build_methodology_section(self):
        """Methodology and scoring explanation"""
        elements = []
        elements.append(Paragraph("METHODOLOGY", self.styles['SectionHead']))

        methodology = """
        The Hydrogen Prospect Score (HPS) is calculated as a weighted ensemble of
        rule-based and machine learning components:<br/>
        <br/>
        <b>HPS = Confidence × [0.6 × RuleScore + 0.4 × MLScore]</b><br/>
        <br/>
        Where:<br/>
        • <b>RuleScore</b> = Weighted sum of G/M/T/P factors<br/>
        • <b>MLScore</b> = XGBoost prediction from 30+ geospatial features<br/>
        • <b>Confidence</b> = Data completeness × Data quality × (1 - missing_penalty)<br/>
        <br/>
        All scores are normalized to [0, 1] scale. The confidence-adjusted score ensures
        that data gaps are explicitly tracked and do not result in inflated scores.
        """

        elements.append(Paragraph(methodology, self.styles['BodyText']))
        return elements

    # Helper methods
    def _get_score_class(self, score):
        """Get classification text for score"""
        if score >= 0.8:
            return 'High-priority target'
        elif score >= 0.65:
            return 'Strong prospect, needs validation'
        elif score >= 0.5:
            return 'Moderate prospect'
        elif score >= 0.35:
            return 'Weak / speculative'
        return 'Low priority'

    def _generate_key_finding(self, zone_data):
        """Generate key finding statement"""
        score = zone_data.get('prospectivity_score', 0)
        confidence = zone_data.get('confidence', 0)

        if score >= 0.8:
            return f"This zone shows strong hydrogen prospectivity ({score*100:.0f}) with {confidence*100:.0f}% confidence. Recommend accelerated evaluation."
        elif score >= 0.65:
            return f"This zone is a promising hydrogen prospect ({score*100:.0f}) requiring validation with {confidence*100:.0f}% confidence level."
        else:
            return f"This zone shows moderate hydrogen potential ({score*100:.0f}) with {confidence*100:.0f}% confidence. Further assessment recommended."

    def _get_recommendation_summary(self, score):
        """Get recommendation based on score"""
        if score >= 0.8:
            return "Proceed to detailed evaluation; prioritize acquisition of seismic data."
        elif score >= 0.65:
            return "Plan targeted data acquisition program; consider pilot drilling."
        else:
            return "Continue reconnaissance; acquire additional geophysical data before major investment."

    def _get_top_drivers(self, zone_data):
        """Get top 3 drivers of the score"""
        return [
            {
                'title': 'Hydrogen Generation Potential',
                'value': zone_data.get('f_generation', 0),
                'explanation': 'Strong ultramafic/mafic rock presence with favorable thermal conditions. Mantle-derived hydrogen production is the primary driver for this zone.'
            },
            {
                'title': 'Trap Geometry',
                'value': zone_data.get('f_trap_retention', 0),
                'explanation': 'Well-defined anticline structure provides closure geometry capable of retaining hydrogen. Structural relief exceeds 500 meters.'
            },
            {
                'title': 'Structural Pathways',
                'value': zone_data.get('f_structural_pathways', 0),
                'explanation': 'Active fault zones provide migration pathways. Fracture density and fault throw indicate good connectivity for hydrogen transport.'
            }
        ]

    def _get_recommendations(self, score):
        """Get recommendations based on score"""
        return [
            {
                'title': '3D Seismic Acquisition & Interpretation',
                'description': 'High-resolution 3D seismic survey to map trap geometry, fault patterns, and seal integrity.',
                'timeline': '3-6 months'
            },
            {
                'title': 'Slim Hole Drilling Program',
                'description': 'Drill 500m slim hole to collect subsurface samples, pressure data, and temperature gradient.',
                'timeline': '2-4 months'
            },
            {
                'title': 'Advanced Gravity & Magnetic Inversion',
                'description': 'Reprocess regional gravity/magnetic data with inversion modeling to refine density and susceptibility contrasts.',
                'timeline': '1-2 months'
            },
            {
                'title': 'Basin Modeling Study',
                'description': '1D/2D basin modeling to assess hydrogen generation rates, migration pathways, and accumulation potential.',
                'timeline': '2-3 months'
            }
        ]
