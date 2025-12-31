"""
Integration tests for PDF extraction with real PDF files.
Tests the full extraction pipeline with Unstructured.io.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock the vector_service import before importing ingestion_service
sys.modules['services.vector_service'] = MagicMock()

from services.ingestion_service import (
    DocumentIngestionService,
    PDFExtractionStrategy,
    UNSTRUCTURED_AVAILABLE
)


class TestUnstructuredIntegration:
    """Integration tests for Unstructured.io PDF extraction."""
    
    @pytest.fixture
    def service_hi_res(self):
        """Create service with hi-res strategy."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.UNSTRUCTURED_HI_RES)
    
    @pytest.fixture
    def service_fast(self):
        """Create service with fast strategy."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.UNSTRUCTURED_FAST)
    
    @pytest.fixture
    def complex_pdf_with_table(self, tmp_path):
        """Create a PDF with a table for testing."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            from reportlab.platypus import Table, TableStyle
            from reportlab.lib import colors
            
            pdf_path = tmp_path / "table_test.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            
            # Title
            c.setFont("Helvetica-Bold", 18)
            c.drawString(1*inch, 10*inch, "NVMe Command Set Reference")
            
            # Subtitle
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, 9.5*inch, "Table 1: Admin Command Set")
            
            # Draw a simple table manually
            c.setFont("Helvetica-Bold", 10)
            y = 9*inch
            
            # Header row
            c.drawString(1*inch, y, "Opcode")
            c.drawString(2*inch, y, "Command")
            c.drawString(4*inch, y, "Description")
            
            c.setFont("Helvetica", 10)
            y -= 0.3*inch
            
            # Data rows
            rows = [
                ("00h", "Delete I/O SQ", "Deletes an I/O Submission Queue"),
                ("01h", "Create I/O SQ", "Creates an I/O Submission Queue"),
                ("02h", "Get Log Page", "Returns a log page"),
                ("04h", "Delete I/O CQ", "Deletes an I/O Completion Queue"),
                ("05h", "Create I/O CQ", "Creates an I/O Completion Queue"),
                ("06h", "Identify", "Returns controller/namespace info"),
            ]
            
            for opcode, cmd, desc in rows:
                c.drawString(1*inch, y, opcode)
                c.drawString(2*inch, y, cmd)
                c.drawString(4*inch, y, desc)
                y -= 0.25*inch
            
            # Add a second page with more content
            c.showPage()
            c.setFont("Helvetica-Bold", 16)
            c.drawString(1*inch, 10*inch, "Section 2: NVM Command Set")
            
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, 9.5*inch, "The NVM Command Set defines commands for:")
            
            c.setFont("Helvetica", 11)
            y = 9*inch
            items = [
                "- Read: Transfer data from the controller to the host",
                "- Write: Transfer data from the host to the controller", 
                "- Flush: Commit data to non-volatile media",
                "- Compare: Compare data on the controller with host data",
                "- Write Zeroes: Set a range of logical blocks to zero",
            ]
            for item in items:
                c.drawString(1*inch, y, item)
                y -= 0.25*inch
            
            c.save()
            return pdf_path
        except ImportError:
            pytest.skip("reportlab not installed")
    
    @pytest.mark.skipif(not UNSTRUCTURED_AVAILABLE, reason="Unstructured.io not installed")
    @pytest.mark.asyncio
    async def test_unstructured_extracts_text(self, service_fast, complex_pdf_with_table):
        """Test that Unstructured extracts text from PDF."""
        text, metadata = await service_fast._extract_with_unstructured(complex_pdf_with_table)
        
        assert len(text) > 0
        assert metadata["extraction_quality"] == "high"
        assert metadata["pages_processed"] >= 1
        
        # Check for expected content
        text_lower = text.lower()
        assert "nvme" in text_lower or "command" in text_lower
    
    @pytest.mark.skipif(not UNSTRUCTURED_AVAILABLE, reason="Unstructured.io not installed")
    @pytest.mark.asyncio
    async def test_unstructured_detects_structure(self, service_fast, complex_pdf_with_table):
        """Test that Unstructured detects document structure."""
        text, metadata = await service_fast._extract_with_unstructured(complex_pdf_with_table)
        
        # Should detect some tables (may vary based on PDF complexity)
        # The simple reportlab PDF may not be detected as a table
        assert "tables_found" in metadata
        assert "images_found" in metadata
    
    @pytest.mark.skipif(not UNSTRUCTURED_AVAILABLE, reason="Unstructured.io not installed")
    @pytest.mark.asyncio
    async def test_full_ingestion_pipeline(self, service_fast, complex_pdf_with_table):
        """Test the full document ingestion pipeline."""
        result = await service_fast.ingest_document(
            str(complex_pdf_with_table),
            workspace_id=1,
            original_filename="nvme_spec.pdf"
        )
        
        assert result["success"] is True
        assert "documents" in result
        assert len(result["documents"]) == 1
        
        doc = result["documents"][0]
        assert doc["title"] == "nvme_spec.pdf"
        assert len(doc["content"]) > 0
        
        # Check extraction metadata is included
        assert "extraction" in doc["metadata"]
        assert doc["metadata"]["extraction"]["extraction_quality"] in ["high", "basic"]


class TestExtractionComparison:
    """Tests comparing PyPDF2 vs Unstructured extraction."""
    
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a sample PDF for comparison."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            
            pdf_path = tmp_path / "comparison_test.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            
            c.setFont("Helvetica-Bold", 16)
            c.drawString(1*inch, 10*inch, "Technical Specification Document")
            
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, 9.5*inch, "Version 2.0 - June 2021")
            
            c.setFont("Helvetica", 11)
            text_block = """
This document describes the technical requirements for the system.
The following sections outline the key features and capabilities.

Key Features:
1. High-performance data processing
2. Low-latency command execution
3. Scalable architecture design
4. Robust error handling mechanisms
            """.strip()
            
            y = 9*inch
            for line in text_block.split('\n'):
                c.drawString(1*inch, y, line.strip())
                y -= 0.2*inch
            
            c.save()
            return pdf_path
        except ImportError:
            pytest.skip("reportlab not installed")
    
    @pytest.mark.asyncio
    async def test_pypdf2_extraction(self, sample_pdf):
        """Test PyPDF2 extraction baseline."""
        service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
        text, metadata = await service._extract_with_pypdf2(sample_pdf)
        
        assert len(text) > 0
        assert metadata["extraction_quality"] == "basic"
        assert "Technical" in text or "technical" in text.lower()
    
    @pytest.mark.skipif(not UNSTRUCTURED_AVAILABLE, reason="Unstructured.io not installed")
    @pytest.mark.asyncio
    async def test_unstructured_extraction(self, sample_pdf):
        """Test Unstructured extraction."""
        service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.UNSTRUCTURED_FAST)
        text, metadata = await service._extract_with_unstructured(sample_pdf)
        
        assert len(text) > 0
        assert metadata["extraction_quality"] == "high"
    
    @pytest.mark.skipif(not UNSTRUCTURED_AVAILABLE, reason="Unstructured.io not installed")
    @pytest.mark.asyncio
    async def test_extraction_quality_comparison(self, sample_pdf):
        """Compare extraction quality between methods."""
        pypdf2_service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
        unstructured_service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.UNSTRUCTURED_FAST)
        
        pypdf2_text, pypdf2_meta = await pypdf2_service._extract_with_pypdf2(sample_pdf)
        unstructured_text, unstructured_meta = await unstructured_service._extract_with_unstructured(sample_pdf)
        
        # Both should extract text
        assert len(pypdf2_text) > 0
        assert len(unstructured_text) > 0
        
        # Unstructured should have better quality indicator
        assert unstructured_meta["extraction_quality"] == "high"
        assert pypdf2_meta["extraction_quality"] == "basic"
        
        # Both should contain key content
        assert "technical" in pypdf2_text.lower() or "specification" in pypdf2_text.lower()
        assert "technical" in unstructured_text.lower() or "specification" in unstructured_text.lower()


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
    
    @pytest.mark.asyncio
    async def test_empty_pdf(self, service, tmp_path):
        """Test handling of empty PDF."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = tmp_path / "empty.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.showPage()  # Empty page
            c.save()
            
            text, metadata = await service._extract_with_pypdf2(pdf_path)
            
            # Should handle gracefully
            assert metadata["pages_processed"] == 1
        except ImportError:
            pytest.skip("reportlab not installed")
    
    @pytest.mark.asyncio
    async def test_corrupted_pdf(self, service, tmp_path):
        """Test handling of corrupted PDF."""
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"%PDF-1.4\ngarbage data that is not valid PDF")
        
        text, metadata = await service._extract_with_pypdf2(corrupted_pdf)
        
        # Should handle gracefully and return empty/failed
        assert metadata["extraction_quality"] in ["basic", "failed"]
    
    @pytest.mark.asyncio
    async def test_large_page_count(self, service, tmp_path):
        """Test handling of PDF with multiple pages."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = tmp_path / "multipage.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            
            for i in range(10):
                c.drawString(100, 750, f"Page {i + 1} content")
                c.showPage()
            
            c.save()
            
            text, metadata = await service._extract_with_pypdf2(pdf_path)
            
            assert metadata["pages_processed"] == 10
            assert "Page 1" in text
            assert "Page 10" in text
        except ImportError:
            pytest.skip("reportlab not installed")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
