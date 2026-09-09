# -*- coding: utf-8 -*-
import sys, os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfgen import canvas

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
        self.setFont('Helvetica-Bold', 8)
        self.setFillColor(colors.HexColor('#475569'))
        
        if self._pageNumber > 1:
            self.drawString(54, 750, 'RAZORPAY AGENTIC CHECKOUT — 360 DEGREE TECHNICAL ARCHITECTURE & INTERVIEW MASTER BIBLE')
            self.setFont('Helvetica', 8)
            self.drawRightString(558, 750, 'TRACK 01: AGENTIC COMMERCE')
            self.setStrokeColor(colors.HexColor('#cbd5e1'))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
        
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748b'))
        self.drawString(54, 32, 'Razorpay AI Buildathon 2026 | Technical Architecture & Code Reference Compendium')
        page_str = f'Page {self._pageNumber} of {page_count}'
        self.drawRightString(558, 32, page_str)
        self.restoreState()

print('NumberedCanvas configured')
