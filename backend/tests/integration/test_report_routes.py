"""Integration tests for report export routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestReportExportPDF:
    """Test PDF report export endpoint."""

    def test_export_pdf_success(self, client: TestClient):
        """Test successful PDF export."""
        response = client.get("/api/report/export/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert response.content[:4] == b"%PDF"  # PDF magic bytes

    def test_export_pdf_with_data(self, client: TestClient, sample_trade_records):
        """Test PDF export with sample trade data."""
        response = client.get("/api/report/export/pdf")
        assert response.status_code == 200
        assert len(response.content) > 1000  # Should have substantial content


class TestReportExportDOCX:
    """Test Word document export endpoint."""

    def test_export_docx_success(self, client: TestClient):
        """Test successful DOCX export."""
        response = client.get("/api/report/export/docx")
        assert response.status_code == 200
        assert "wordprocessingml" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")
        assert response.content[:2] == b"PK"  # ZIP magic bytes (DOCX is ZIP)

    def test_export_docx_with_data(self, client: TestClient, sample_trade_records):
        """Test DOCX export with sample trade data."""
        response = client.get("/api/report/export/docx")
        assert response.status_code == 200
        assert len(response.content) > 1000  # Should have substantial content
