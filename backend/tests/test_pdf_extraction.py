"""
Unit tests for PDF extraction functionality.
Tests both Unstructured.io and PyPDF2 extraction strategies.
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


class TestPDFExtractionStrategy:
    """Tests for PDFExtractionStrategy class."""
    
    def test_strategy_constants(self):
        """Test that strategy constants are defined correctly."""
        assert PDFExtractionStrategy.UNSTRUCTURED_HI_RES == "unstructured_hi_res"
        assert PDFExtractionStrategy.UNSTRUCTURED_FAST == "unstructured_fast"
        assert PDFExtractionStrategy.PYPDF2_FALLBACK == "pypdf2_fallback"


class TestDocumentIngestionServiceInit:
    """Tests for DocumentIngestionService initialization."""
    
    def test_init_with_explicit_strategy(self):
        """Test initialization with explicit PDF strategy."""
        service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
        assert service.pdf_strategy == PDFExtractionStrategy.PYPDF2_FALLBACK
    
    def test_init_default_strategy_with_unstructured(self):
        """Test default strategy selection when Unstructured is available."""
        if UNSTRUCTURED_AVAILABLE:
            service = DocumentIngestionService()
            assert service.pdf_strategy == PDFExtractionStrategy.UNSTRUCTURED_HI_RES
        else:
            service = DocumentIngestionService()
            assert service.pdf_strategy == PDFExtractionStrategy.PYPDF2_FALLBACK
    
    def test_init_creates_upload_dir(self, tmp_path):
        """Test that upload directory is created on init."""
        with patch('services.ingestion_service.settings') as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path / "uploads")
            mock_settings.CHUNK_SIZE = 1000
            mock_settings.CHUNK_OVERLAP = 200
            service = DocumentIngestionService()
            assert Path(mock_settings.UPLOAD_DIR).exists()


class TestPyPDF2Extraction:
    """Tests for PyPDF2 fallback extraction."""
    
    @pytest.fixture
    def service(self):
        """Create service with PyPDF2 strategy."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
    
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a simple test PDF using reportlab."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = tmp_path / "test_document.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            
            # Page 1
            c.drawString(100, 750, "Test Document Title")
            c.drawString(100, 700, "This is the first paragraph of test content.")
            c.drawString(100, 650, "This contains important information for testing.")
            c.showPage()
            
            # Page 2
            c.drawString(100, 750, "Page 2 Header")
            c.drawString(100, 700, "Second page content goes here.")
            c.drawString(100, 650, "More test data for extraction validation.")
            c.showPage()
            
            c.save()
            return pdf_path
        except ImportError:
            pytest.skip("reportlab not installed")
    
    @pytest.mark.asyncio
    async def test_extract_with_pypdf2_basic(self, service, sample_pdf):
        """Test basic PyPDF2 extraction."""
        text, metadata = await service._extract_with_pypdf2(sample_pdf)
        
        assert text is not None
        assert len(text) > 0
        assert "Test Document Title" in text or "test" in text.lower()
        assert metadata["pages_processed"] == 2
        assert metadata["extraction_quality"] == "basic"
    
    @pytest.mark.asyncio
    async def test_extract_with_pypdf2_metadata(self, service, sample_pdf):
        """Test that PyPDF2 extraction returns correct metadata."""
        text, metadata = await service._extract_with_pypdf2(sample_pdf)
        
        assert "tables_found" in metadata
        assert "images_found" in metadata
        assert "pages_processed" in metadata
        assert "extraction_quality" in metadata
        assert metadata["tables_found"] == 0  # PyPDF2 doesn't detect tables
        assert metadata["images_found"] == 0  # PyPDF2 doesn't detect images
    
    @pytest.mark.asyncio
    async def test_extract_with_pypdf2_nonexistent_file(self, service, tmp_path):
        """Test PyPDF2 extraction with non-existent file."""
        fake_path = tmp_path / "nonexistent.pdf"
        text, metadata = await service._extract_with_pypdf2(fake_path)
        
        assert text == ""
        assert metadata["extraction_quality"] == "failed"
    
    @pytest.mark.asyncio
    async def test_extract_with_pypdf2_invalid_pdf(self, service, tmp_path):
        """Test PyPDF2 extraction with invalid PDF file."""
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a valid PDF file")
        
        text, metadata = await service._extract_with_pypdf2(invalid_pdf)
        
        assert text == ""
        assert metadata["extraction_quality"] == "failed"


class TestUnstructuredExtraction:
    """Tests for Unstructured.io extraction."""
    
    @pytest.fixture
    def service(self):
        """Create service with Unstructured hi-res strategy."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.UNSTRUCTURED_HI_RES)
    
    @pytest.mark.skipif(not UNSTRUCTURED_AVAILABLE, reason="Unstructured.io not installed")
    @pytest.mark.asyncio
    async def test_extract_with_unstructured_mock(self, service):
        """Test Unstructured extraction with mocked elements."""
        from unittest.mock import AsyncMock
        
        # Create mock elements
        mock_title = Mock()
        mock_title.text = "Document Title"
        mock_title.__class__.__name__ = "Title"
        
        mock_text = Mock()
        mock_text.text = "This is narrative text content."
        mock_text.__class__.__name__ = "NarrativeText"
        
        with patch('services.ingestion_service.partition_pdf') as mock_partition:
            # Mock the partition_pdf to return our mock elements
            mock_partition.return_value = [mock_title, mock_text]
            
            # We need to patch isinstance checks
            with patch('services.ingestion_service.Title', type(mock_title)):
                with patch('services.ingestion_service.NarrativeText', type(mock_text)):
                    text, metadata = await service._extract_with_unstructured(Path("/fake/path.pdf"))
        
        # Verify the function was called
        mock_partition.assert_called_once()


class TestTableToMarkdown:
    """Tests for table to markdown conversion."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
    
    def test_html_table_to_markdown_simple(self, service):
        """Test simple HTML table conversion."""
        html = """
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Cell 1</td><td>Cell 2</td></tr>
            <tr><td>Cell 3</td><td>Cell 4</td></tr>
        </table>
        """
        
        result = service._html_table_to_markdown(html)
        
        assert "| Header 1 | Header 2 |" in result
        assert "| --- | --- |" in result
        assert "| Cell 1 | Cell 2 |" in result
        assert "| Cell 3 | Cell 4 |" in result
    
    def test_html_table_to_markdown_empty(self, service):
        """Test conversion with no table element."""
        html = "<div>No table here</div>"
        result = service._html_table_to_markdown(html)
        assert result == html
    
    def test_html_table_to_markdown_empty_rows(self, service):
        """Test conversion with empty table."""
        html = "<table></table>"
        result = service._html_table_to_markdown(html)
        assert result == html
    
    def test_table_to_markdown_with_text_fallback(self, service):
        """Test table conversion fallback to plain text."""
        mock_table = Mock()
        mock_table.text = "Row1Col1 Row1Col2\nRow2Col1 Row2Col2"
        mock_table.metadata = None
        
        result = service._table_to_markdown(mock_table)
        
        assert "[Table]" in result
        assert "Row1Col1" in result
        assert "[/Table]" in result


class TestIngestDocument:
    """Tests for the main ingest_document method."""
    
    @pytest.fixture
    def service(self):
        """Create service with PyPDF2 strategy for predictable testing."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
    
    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a simple test PDF."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = tmp_path / "test_ingest.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 750, "Ingestion Test Document")
            c.drawString(100, 700, "Content for ingestion testing.")
            c.save()
            return pdf_path
        except ImportError:
            pytest.skip("reportlab not installed")
    
    @pytest.mark.asyncio
    async def test_ingest_document_success(self, service, sample_pdf):
        """Test successful document ingestion."""
        result = await service.ingest_document(
            str(sample_pdf),
            workspace_id=1,
            original_filename="test.pdf"
        )
        
        assert result["success"] is True
        assert "documents" in result
        assert len(result["documents"]) == 1
        
        doc = result["documents"][0]
        assert doc["title"] == "test.pdf"
        assert doc["source_type"] == "document"
        assert doc["file_type"] == ".pdf"
        assert doc["workspace_id"] == 1
        assert "content" in doc
        assert len(doc["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_ingest_document_with_extraction_metadata(self, service, sample_pdf):
        """Test that extraction metadata is included in result."""
        result = await service.ingest_document(
            str(sample_pdf),
            workspace_id=1
        )
        
        assert result["success"] is True
        assert "extraction_metadata" in result
        
        metadata = result["extraction_metadata"]
        assert "strategy_used" in metadata
        assert "pages_processed" in metadata
        assert metadata["strategy_used"] == PDFExtractionStrategy.PYPDF2_FALLBACK
    
    @pytest.mark.asyncio
    async def test_ingest_document_file_not_found(self, service, tmp_path):
        """Test ingestion with non-existent file."""
        result = await service.ingest_document(
            str(tmp_path / "nonexistent.pdf"),
            workspace_id=1
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_ingest_document_text_file(self, service, tmp_path):
        """Test ingestion of plain text file."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("This is plain text content for testing.")
        
        result = await service.ingest_document(
            str(text_file),
            workspace_id=1,
            original_filename="test.txt"
        )
        
        assert result["success"] is True
        assert "documents" in result
        assert "plain text content" in result["documents"][0]["content"]


class TestExtractionStrategySelection:
    """Tests for extraction strategy selection logic."""
    
    @pytest.mark.asyncio
    async def test_strategy_fallback_on_unstructured_failure(self, tmp_path):
        """Test that PyPDF2 is used when Unstructured fails."""
        # Create a valid PDF
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = tmp_path / "fallback_test.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 750, "Fallback Test")
            c.save()
        except ImportError:
            pytest.skip("reportlab not installed")
        
        service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.UNSTRUCTURED_HI_RES)
        
        # Mock Unstructured to fail (return empty string which triggers fallback)
        async def mock_unstructured_fail(path):
            return "", {"extraction_quality": "failed"}
        
        # Also need to patch UNSTRUCTURED_AVAILABLE to ensure the branch is taken
        with patch('services.ingestion_service.UNSTRUCTURED_AVAILABLE', True):
            with patch.object(service, '_extract_with_unstructured', side_effect=mock_unstructured_fail):
                text, metadata = await service._extract_pdf_text(pdf_path)
        
        # Should have fallen back to PyPDF2 - check the strategy_used was updated
        assert metadata["strategy_used"] == PDFExtractionStrategy.PYPDF2_FALLBACK
        assert len(text) > 0
    
    @pytest.mark.asyncio
    async def test_pypdf2_strategy_skips_unstructured(self, tmp_path):
        """Test that PyPDF2 strategy doesn't try Unstructured."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            pdf_path = tmp_path / "pypdf2_only.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 750, "PyPDF2 Only Test")
            c.save()
        except ImportError:
            pytest.skip("reportlab not installed")
        
        service = DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
        
        # Mock Unstructured - should NOT be called
        with patch.object(service, '_extract_with_unstructured') as mock_unstructured:
            text, metadata = await service._extract_pdf_text(pdf_path)
        
        # Unstructured should not have been called
        mock_unstructured.assert_not_called()
        assert metadata["strategy_used"] == PDFExtractionStrategy.PYPDF2_FALLBACK


class TestComplexPDFScenarios:
    """Tests for complex PDF scenarios."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return DocumentIngestionService(pdf_strategy=PDFExtractionStrategy.PYPDF2_FALLBACK)
    
    @pytest.fixture
    def multi_page_pdf(self, tmp_path):
        """Create a multi-page PDF with various content."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            
            pdf_path = tmp_path / "multipage.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            
            # Page 1 - Title and intro
            c.setFont("Helvetica-Bold", 24)
            c.drawString(1*inch, 10*inch, "Technical Specification")
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, 9.5*inch, "Version 1.0")
            c.drawString(1*inch, 9*inch, "This document describes the technical requirements.")
            c.showPage()
            
            # Page 2 - Section 1
            c.setFont("Helvetica-Bold", 16)
            c.drawString(1*inch, 10*inch, "Section 1: Overview")
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, 9.5*inch, "The system shall support the following features:")
            c.drawString(1*inch, 9*inch, "- Feature A: Data processing")
            c.drawString(1*inch, 8.5*inch, "- Feature B: User management")
            c.drawString(1*inch, 8*inch, "- Feature C: Reporting")
            c.showPage()
            
            # Page 3 - Section 2
            c.setFont("Helvetica-Bold", 16)
            c.drawString(1*inch, 10*inch, "Section 2: Requirements")
            c.setFont("Helvetica", 12)
            c.drawString(1*inch, 9.5*inch, "REQ-001: The system shall process data in real-time.")
            c.drawString(1*inch, 9*inch, "REQ-002: The system shall support 1000 concurrent users.")
            c.drawString(1*inch, 8.5*inch, "REQ-003: The system shall generate PDF reports.")
            c.showPage()
            
            c.save()
            return pdf_path
        except ImportError:
            pytest.skip("reportlab not installed")
    
    @pytest.mark.asyncio
    async def test_multi_page_extraction(self, service, multi_page_pdf):
        """Test extraction from multi-page PDF."""
        text, metadata = await service._extract_with_pypdf2(multi_page_pdf)
        
        assert metadata["pages_processed"] == 3
        assert "Technical Specification" in text or "specification" in text.lower()
        assert "Section 1" in text or "section" in text.lower()
        assert "REQ-001" in text or "req" in text.lower()
    
    @pytest.mark.asyncio
    async def test_page_markers_in_output(self, service, multi_page_pdf):
        """Test that page markers are included in output."""
        text, metadata = await service._extract_with_pypdf2(multi_page_pdf)
        
        assert "--- Page 1 ---" in text
        assert "--- Page 2 ---" in text
        assert "--- Page 3 ---" in text


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
