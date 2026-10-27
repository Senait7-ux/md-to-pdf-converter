#!/usr/bin/env python3
"""
Markdown to PDF Converter for CCDI Hub Release Notes

This script reads release notes from the CCDI Hub Static Contents GitHub file and
converts them into a professionally formatted PDF document with NIH branding and styling.

Features:
- Converts Markdown release notes to PDF format
- Includes NIH branding and proper formatting
- Handles Markdown headings, lists, links, and emphasis
- Professional layout with headers, sections, and styling
- Page numbering with total page count
- SVG logo support with proper aspect ratio maintenance
- Customizable PDF metadata (title, author, subject, creator)

Usage:
    python3 converter.py

Requirements:
    - Network access to the release notes file on GitHub
    - Portal_Logo.svg file (optional, for logo display)
"""

import html
import os
import sys
import urllib.request
from datetime import datetime
from io import BytesIO

# PDF generation libraries
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import Color, HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# HTML parsing for content formatting
from bs4 import BeautifulSoup
import markdown
import re

# SVG to PNG conversion
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
import io

class ReleaseNotesPDFGenerator:
    def __init__(self, markdown_file_path, output_path=None, pdf_metadata=None):
        """
        Initialize the PDF generator with the release notes Markdown file.
        
        Args:
            markdown_file_path (str): Path to releaseNotesData.md
            output_path (str): Path for the output PDF file (optional)
            pdf_metadata (dict): PDF metadata dictionary with keys:
                - Title: PDF title
                - Author: PDF author
                - Subject: PDF subject
                - Creator: Content creator
                - Producer: PDF producer (optional, defaults to 'ReportLab PDF Library')
        """
        self.markdown_file_path = markdown_file_path
        self.output_path = output_path or "CCDI_Hub_Release_Notes.pdf"
        self.release_notes = []
        self.total_pages = 0
        self.current_page = 0
        self.logo_drawing = None  # Cache for converted logo
        
        # Set default PDF metadata if not provided
        self.pdf_metadata = pdf_metadata or {
            'Title': 'CCDI Hub Release Notes',
            'Author': 'National Cancer Institute',
            'Subject': 'CCDI Hub Release Notes and Updates',
            'Creator': 'CCDI Hub Release Notes Generator',
            'Producer': 'ReportLab PDF Library',
        }

        print(self.pdf_metadata)
        
        # Define colors based on the screenshot
        self.nih_blue = HexColor('#2f5496')
        self.nih_red = HexColor('#BA1F40')
        self.dark_gray = HexColor('#606061')
        self.light_gray = HexColor('#f5f5f5')
        
        # Initialize styles
        self.setup_styles()
        
    def setup_styles(self):
        """Set up paragraph styles for the PDF."""
        self.styles = getSampleStyleSheet()
        
        # Title style (Update Title)
        self.styles.add(ParagraphStyle(
            name='ReleaseTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=self.nih_blue,
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Date style (Date of Release)
        self.styles.add(ParagraphStyle(
            name='ReleaseDate',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=20,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=self.nih_blue,
            spaceBefore=20,
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=self.nih_blue,
            spaceBefore=12,
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Normal paragraph style
        self.styles.add(ParagraphStyle(
            name='ReleaseContent',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=4,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leftIndent=0,
            rightIndent=0
        ))
        
        # List item style
        self.styles.add(ParagraphStyle(
            name='ListItem',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=2,
            alignment=TA_LEFT,
            fontName='Helvetica',
            leftIndent=20,
            bulletIndent=10
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Page number style
        self.styles.add(ParagraphStyle(
            name='PageNumber',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_RIGHT,
            fontName='Helvetica'
        ))

    def _fetch_markdown(self, source):
        """Read release notes from a local path or a GitHub URL."""
        if source.startswith(('http://', 'https://')):
            raw_url = self._github_blob_to_raw_url(source)
            print(f"Fetching release notes from {raw_url}")
            request = urllib.request.Request(
                raw_url,
                headers={'User-Agent': 'CCDI-Hub-Release-Notes'},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode('utf-8')

        with open(source, 'r', encoding='utf-8') as file:
            return file.read()

    def _github_blob_to_raw_url(self, url):
        """Turn a github.com blob page URL into the raw file URL."""
        match = re.match(r'https://github\.com/([^/]+)/([^/]+)/blob/(.+)', url)
        if not match:
            return url
        owner, repo, path = match.groups()
        return f'https://raw.githubusercontent.com/{owner}/{repo}/{path}'

    def load_markdown_data(self):
        """Load release notes from the configured Markdown source."""
        try:
            markdown_text = self._fetch_markdown(self.markdown_file_path)

            self.release_notes = self._parse_release_notes_markdown(markdown_text)
            if not self.release_notes:
                raise ValueError("No release notes found in Markdown file")

            print(f"Loaded {len(self.release_notes)} release notes entries")
        except Exception as e:
            print(f"Error loading Markdown file: {e}")
            sys.exit(1)

    def _parse_release_notes_markdown(self, markdown_text):
        """
        Split releaseNotesData.md into one note per top-level heading.

        Each note starts with '# Title', a '### Date | Release Notes' line,
        Markdown body, and a Property/Value table containing the version.
        """
        notes = []
        sections = re.split(r'(?m)^(?=# )', markdown_text)

        for section in sections:
            section = section.strip()
            if not section.startswith('# '):
                continue

            lines = section.splitlines()
            title = lines[0][2:].strip()
            date = 'Unknown Date'
            body_start = 1

            for index, line in enumerate(lines[1:], start=1):
                date_match = re.match(r'^###\s+(.+?)\s*\|\s*Release Notes\s*$', line)
                if date_match:
                    date = date_match.group(1).strip()
                    body_start = index + 1
                    break

            body = '\n'.join(lines[body_start:]).strip()
            version_match = re.search(r'(?m)^\|\s*version\s*\|\s*([^|]+?)\s*\|', body)
            if version_match:
                version = version_match.group(1).strip()
            else:
                title_version = re.search(r'(\d+\.\d+\.\d+)', title)
                version = f"v{title_version.group(1)}" if title_version else 'N/A'

            body = re.sub(r'(?ms)^\| Property \| Value \|\n.*\Z', '', body).strip()
            body = re.sub(r'(?i)<img\b[^>]*>', '', body).strip()
            full_text = markdown.markdown(body) if body else ''

            notes.append({
                'title': title,
                'date': date,
                'version': version,
                'fullText': full_text,
            })

        return notes

    def _inline_markup(self, element):
        """Convert inline HTML to ReportLab paragraph markup."""
        parts = []
        for child in element.children:
            if getattr(child, 'name', None) is None:
                parts.append(html.escape(str(child)))
                continue

            if child.name in ('strong', 'b'):
                parts.append(f"<b>{self._inline_markup(child)}</b>")
            elif child.name in ('em', 'i'):
                parts.append(f"<i>{self._inline_markup(child)}</i>")
            elif child.name == 'a':
                label = self._inline_markup(child)
                href = child.get('href', '')
                if href and label:
                    parts.append(f'<link href="{html.escape(href, quote=True)}">{label}</link>')
                else:
                    parts.append(label)
            elif child.name == 'br':
                parts.append('<br/>')
            elif child.name in ('ul', 'ol'):
                continue
            else:
                parts.append(self._inline_markup(child))

        return ''.join(parts).strip()

    def _append_list_item(self, elements, li, marker, indent=''):
        """Add a list item, then any lists nested inside it."""
        nested_lists = li.find_all(['ul', 'ol'], recursive=False)
        for nested in nested_lists:
            nested.extract()

        text = self._inline_markup(li)
        if text:
            elements.append(Paragraph(f"{indent}{marker} {text}", self.styles['ListItem']))

        for nested in nested_lists:
            if nested.name == 'ol':
                for index, nested_li in enumerate(nested.find_all('li', recursive=False), start=1):
                    self._append_list_item(elements, nested_li, f"{index}.", indent + '    ')
            else:
                for nested_li in nested.find_all('li', recursive=False):
                    self._append_list_item(elements, nested_li, '•', indent + '    ')

    def _append_html_element(self, elements, element):
        """Convert one block-level HTML element into PDF flowables."""
        if not getattr(element, 'name', None):
            return

        if element.name == 'p':
            text = self._inline_markup(element)
            if text:
                elements.append(Paragraph(text, self.styles['ReleaseContent']))
        elif element.name in ('h1', 'h3'):
            text = self._inline_markup(element)
            if text:
                elements.append(Paragraph(text, self.styles['SectionHeader']))
        elif element.name in ('h2', 'h4'):
            text = self._inline_markup(element)
            if text:
                elements.append(Paragraph(text, self.styles['SubsectionHeader']))
        elif element.name == 'ul':
            for li in element.find_all('li', recursive=False):
                self._append_list_item(elements, li, '•')
        elif element.name == 'ol':
            for index, li in enumerate(element.find_all('li', recursive=False), start=1):
                self._append_list_item(elements, li, f"{index}.")
        elif element.name in ('div', 'blockquote'):
            for child in element.children:
                self._append_html_element(elements, child)

    def parse_html_content(self, html_content):
        """
        Parse HTML content and convert to ReportLab elements.
        
        Args:
            html_content (str): HTML content to parse
            
        Returns:
            list: List of ReportLab elements
        """
        elements = []
        
        if not html_content:
            return elements
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            container = soup.body if soup.body else soup
            for child in container.children:
                self._append_html_element(elements, child)
        except Exception as e:
            print(f"Error parsing HTML content: {e}")
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            if plain_text.strip():
                elements.append(Paragraph(html.escape(plain_text.strip()), self.styles['ReleaseContent']))
        
        return elements

    def convert_svg_to_drawing(self, svg_path, target_height=50):
        """
        Convert SVG file to ReportLab Drawing object, maintaining original aspect ratio.
        
        Args:
            svg_path (str): Path to the SVG file
            target_height (int): Target height for the logo (width will be calculated to maintain aspect ratio)
            
        Returns:
            Drawing: ReportLab Drawing object or None if conversion fails
        """
        try:
            # Convert SVG to ReportLab Drawing
            drawing = svg2rlg(svg_path)
            
            if drawing:
                # Maintain original aspect ratio
                if drawing.width and drawing.height:
                    # Calculate scale factor based on target height
                    scale_factor = target_height / drawing.height
                    new_width = drawing.width * scale_factor
                    new_height = target_height
                    
                    # Apply scaling
                    drawing.scale(scale_factor, scale_factor)
                    drawing.width = new_width
                    drawing.height = new_height
                    
                    print(f"Successfully converted SVG to Drawing: {svg_path} (scaled to {new_width:.1f}x{new_height})")
                else:
                    # Fallback if dimensions not available
                    drawing.width = 400
                    drawing.height = target_height
                
                return drawing
            else:
                print(f"Failed to convert SVG: {svg_path}")
                return None
            
        except Exception as e:
            print(f"Error converting SVG to Drawing: {e}")
            return None

    def get_logo_drawing(self, target_height=50):
        """
        Get the logo drawing, converting from SVG if not already cached.
        
        Args:
            target_height (int): Target height for the logo (width will be calculated to maintain aspect ratio)
            
        Returns:
            Drawing: ReportLab Drawing object or None if conversion fails
        """
        if self.logo_drawing is None:
            svg_logo_path = os.path.join(os.path.dirname(__file__), 'Portal_Logo.svg')
            if os.path.exists(svg_logo_path):
                self.logo_drawing = self.convert_svg_to_drawing(svg_logo_path, target_height)
        return self.logo_drawing

    def create_table_of_contents(self):
        """Create an interactive table of contents with clickable links"""
        from reportlab.platypus import Paragraph
        
        # Create header row - simple black and white styling
        toc_data = [
            [Paragraph('<b>Version</b>', self.styles['ListItem']), 
             Paragraph('<b>Date</b>', self.styles['ListItem'])]
        ]
        
        for i, note in enumerate(self.release_notes):
            version = note.get('version', 'N/A')
            date = note.get('date', 'Unknown Date')
            
            # Create clickable link on the version number
            anchor_name = f"release_{i}"
            clickable_version = Paragraph(f'<link href="#{anchor_name}" color="blue">{version}</link>', self.styles['ListItem'])
            
            # Create date cell as paragraph
            date_para = Paragraph(date, self.styles['ListItem'])
            
            toc_data.append([clickable_version, date_para])
        
        # Create table with simple black and white styling and cell borders
        toc_table = Table(toc_data, colWidths=[1.5*inch, 2.5*inch], hAlign='LEFT')
        toc_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        return toc_table

    def create_header_footer(self, canvas, doc):
        """
        Create header and footer for each page.
        
        Args:
            canvas: ReportLab canvas object
            doc: Document object
        """
        # Get page dimensions
        page_width, page_height = letter
        
        # Header with NIH logo or text
        try:
            # Try to use SVG logo first (with caching)
            drawing = self.get_logo_drawing(target_height=50)
            if drawing:
                # Render the drawing to the canvas
                renderPDF.draw(drawing, canvas, 50, page_height - 80)
            else:
                # Fallback to PNG logo if SVG not found
                png_logo_path = os.path.join(os.path.dirname(__file__), 'nih_logo.png')
                if os.path.exists(png_logo_path):
                    canvas.drawImage(png_logo_path, 50, page_height - 80, width=400, height=50)
                else:
                    raise Exception("No logo files found")
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
            # Draw text header as fallback
            canvas.setFont("Helvetica-Bold", 16)
            canvas.setFillColor(self.nih_blue)
            canvas.drawString(50, page_height - 60, "NATIONAL CANCER INSTITUTE")
        
        # Draw horizontal line under header
        canvas.setStrokeColor(self.nih_blue)
        canvas.setLineWidth(1)
        canvas.line(50, page_height - 90, page_width - 50, page_height - 90)
        
        # Footer
        footer_y = 50
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.black)
        
        # Left footer text
        footer_text = "U.S. Department of Health and Human Services | National Institutes of Health | National Cancer Institute"
        canvas.drawString(50, footer_y, footer_text)
        
        # Right footer - page number
        page_num = canvas.getPageNumber()
        page_text = f"Page {page_num} of {self.total_pages}"
        text_width = canvas.stringWidth(page_text, "Helvetica", 9)
        canvas.drawString(page_width - 50 - text_width, footer_y, page_text)
        
        # Draw horizontal line above footer
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        canvas.line(50, footer_y + 15, page_width - 50, footer_y + 15)

    def _make_document(self, destination):
        """Create a PDF document with the shared page setup."""
        return SimpleDocTemplate(
            destination,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=100,
            bottomMargin=80
        )

    def _build_story(self):
        """Build the PDF flowables for the table of contents and each release."""
        story = []

        story.append(Paragraph("Table of Contents", self.styles['SectionHeader']))
        story.append(Spacer(1, 0.2*inch))
        story.append(self.create_table_of_contents())
        story.append(PageBreak())

        for i, note in enumerate(self.release_notes):
            title = note.get('title', 'Unknown Release')
            anchor_name = f"release_{i}"
            story.append(Paragraph(
                f'<a name="{anchor_name}"></a>{html.escape(title)}',
                self.styles['ReleaseTitle']
            ))

            date = note.get('date', 'Unknown Date')
            story.append(Paragraph(
                f"<b>DATE OF RELEASE:</b> {html.escape(date.upper())}",
                self.styles['ReleaseDate']
            ))
            story.append(Spacer(1, 0.05*inch))

            full_text = note.get('fullText', '')
            if full_text:
                story.extend(self.parse_html_content(full_text))

            if i < len(self.release_notes) - 1:
                story.append(PageBreak())

        return story

    def generate_pdf(self):
        """Generate the PDF document."""
        print("Generating PDF...")
        for i, note in enumerate(self.release_notes):
            print(f"Processing release note {i+1}/{len(self.release_notes)}: {note.get('title', 'Unknown')}")

        def count_pages(pdf_canvas, doc):
            self.total_pages = pdf_canvas.getPageNumber()

        self.total_pages = 0
        self._make_document(BytesIO()).build(
            self._build_story(),
            onFirstPage=count_pages,
            onLaterPages=count_pages,
        )

        def add_header_footer(pdf_canvas, doc):
            pdf_canvas.setTitle(self.pdf_metadata.get('Title', ''))
            pdf_canvas.setAuthor(self.pdf_metadata.get('Author', ''))
            pdf_canvas.setSubject(self.pdf_metadata.get('Subject', ''))
            pdf_canvas.setCreator(self.pdf_metadata.get('Creator', ''))
            pdf_canvas.setProducer(self.pdf_metadata.get('Producer', 'ReportLab PDF Library'))
            if 'Keywords' in self.pdf_metadata:
                pdf_canvas.setKeywords(self.pdf_metadata['Keywords'])

            self.create_header_footer(pdf_canvas, doc)

        self._make_document(self.output_path).build(
            self._build_story(),
            onFirstPage=add_header_footer,
            onLaterPages=add_header_footer,
        )

        print(f"PDF generated successfully: {self.output_path}")

def main():
    """Main function to run the script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    markdown_file = (
        'https://github.com/CBIIT/CCDI_Hub_Static_Contents/blob/dev/releaseNotesData.md'
    )
    output_file = os.path.join(script_dir, 'CCDI_Hub_Release_Notes.pdf')

    generator = ReleaseNotesPDFGenerator(markdown_file, output_file)
    generator.load_markdown_data()
    generator.generate_pdf()

    print("Done!")

if __name__ == "__main__":
    main()

#.venv/bin/python converter.py