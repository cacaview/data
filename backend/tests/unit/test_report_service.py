"""Tests for report generation service."""

from __future__ import annotations

from app.ai.report_service import generate_trade_report_docx, generate_trade_report_pdf


class TestPDFReportGeneration:
    """Test PDF report generation."""

    def test_generate_trade_report_pdf_returns_bytes(self):
        summary_data = {"total_trade": 1000000, "growth_rate": 5.2}
        trade_data = [
            {"country": "Vietnam", "value": 500000, "growth": 8.5},
            {"country": "Thailand", "value": 300000, "growth": 3.2},
        ]
        country_data = [
            {"name": "Vietnam", "value": 500000, "share": 50.0},
            {"name": "Thailand", "value": 300000, "share": 30.0},
        ]

        result = generate_trade_report_pdf(
            title="Test Report",
            summary_data=summary_data,
            trade_data=trade_data,
            country_data=country_data,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_trade_report_pdf_starts_with_pdf_header(self):
        summary_data = {"total_trade": 1000000}
        trade_data = []
        country_data = {}

        result = generate_trade_report_pdf(
            title="Test",
            summary_data=summary_data,
            trade_data=trade_data,
            country_data=country_data,
        )
        # PDF files start with %PDF
        assert result[:4] == b"%PDF"

    def test_generate_trade_report_pdf_with_empty_data(self):
        result = generate_trade_report_pdf(
            title="Empty Report",
            summary_data={},
            trade_data=[],
            country_data=[],
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_trade_report_pdf_with_long_title(self):
        long_title = "A" * 200
        result = generate_trade_report_pdf(
            title=long_title,
            summary_data={"total_trade": 1000000},
            trade_data=[],
            country_data={},
        )
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestDOCXReportGeneration:
    """Test Word document report generation."""

    def test_generate_trade_report_docx_returns_bytes(self):
        summary_data = {"total_trade": 1000000, "growth_rate": 5.2}
        trade_data = [
            {"country": "Vietnam", "value": 500000, "growth": 8.5},
            {"country": "Thailand", "value": 300000, "growth": 3.2},
        ]
        country_data = [
            {"name": "Vietnam", "value": 500000, "share": 50.0},
            {"name": "Thailand", "value": 300000, "share": 30.0},
        ]

        result = generate_trade_report_docx(
            title="Test Report",
            summary_data=summary_data,
            trade_data=trade_data,
            country_data=country_data,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_trade_report_docx_starts_with_zip_header(self):
        """DOCX files are ZIP archives, which start with PK."""
        summary_data = {"total_trade": 1000000}
        trade_data = []
        country_data = {}

        result = generate_trade_report_docx(
            title="Test",
            summary_data=summary_data,
            trade_data=trade_data,
            country_data=country_data,
        )
        # DOCX files are ZIP archives starting with PK
        assert result[:2] == b"PK"

    def test_generate_trade_report_docx_with_empty_data(self):
        result = generate_trade_report_docx(
            title="Empty Report",
            summary_data={},
            trade_data=[],
            country_data={},
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_trade_report_docx_with_special_characters(self):
        """Test with Unicode characters in title and data."""
        summary_data = {"total_trade": 1000000}
        trade_data = [{"country": "越南", "value": 500000, "growth": 8.5}]
        country_data = [{"name": "越南", "value": 500000, "share": 50.0}]

        result = generate_trade_report_docx(
            title="贸易分析报告",
            summary_data=summary_data,
            trade_data=trade_data,
            country_data=country_data,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0
