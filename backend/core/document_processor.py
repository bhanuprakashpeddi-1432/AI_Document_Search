import os
import tempfile
import hashlib
from typing import List, Optional, Tuple
import httpx
import pypdf
import camelot
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from models.schemas import DocumentChunk
from .config import settings
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document downloading, parsing, and chunking"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def download_document(self, url: str) -> str:
        """
        Download document from URL and save to temporary file
        
        Args:
            url: Document URL
            
        Returns:
            str: Path to the downloaded file
            
        Raises:
            Exception: If download fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Create temporary file
                suffix = ".pdf"  # Assuming PDF for now
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(response.content)
                temp_file.close()
                
                logger.info(f"Downloaded document to {temp_file.name}")
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Failed to download document from {url}: {str(e)}")
            raise Exception(f"Document download failed: {str(e)}")
    
    def extract_text_from_pdf(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Extract text from PDF using pypdf
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List[Tuple[str, int]]: List of (text, page_number) tuples
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text_pages = []
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():  # Only add non-empty pages
                        text_pages.append((text, page_num))
                
                logger.info(f"Extracted text from {len(text_pages)} pages")
                return text_pages
                
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise Exception(f"Text extraction failed: {str(e)}")
    
    def extract_tables_from_pdf(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Extract tables from PDF using camelot and convert to Markdown
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List[Tuple[str, int]]: List of (markdown_table, page_number) tuples
        """
        try:
            # Extract tables from all pages
            tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')
            
            markdown_tables = []
            
            for table in tables:
                if table.df is not None and not table.df.empty:
                    # Convert DataFrame to Markdown
                    markdown_table = self._dataframe_to_markdown(table.df)
                    page_num = table.page
                    markdown_tables.append((markdown_table, page_num))
            
            logger.info(f"Extracted {len(markdown_tables)} tables")
            return markdown_tables
            
        except Exception as e:
            logger.warning(f"Failed to extract tables from PDF: {str(e)}")
            # Return empty list if table extraction fails
            return []
    
    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """
        Convert pandas DataFrame to Markdown format
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            str: Markdown formatted table
        """
        # Clean up the DataFrame
        df = df.fillna('')  # Replace NaN with empty string
        
        # Create markdown table
        markdown_lines = []
        
        # Header
        headers = [str(col) for col in df.columns]
        markdown_lines.append('| ' + ' | '.join(headers) + ' |')
        markdown_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        
        # Rows
        for _, row in df.iterrows():
            values = [str(val).strip() for val in row.values]
            markdown_lines.append('| ' + ' | '.join(values) + ' |')
        
        return '\n'.join(markdown_lines)
    
    def chunk_content(self, content: str, page_number: int, chunk_type: str = "text") -> List[DocumentChunk]:
        """
        Split content into chunks
        
        Args:
            content: Text content to chunk
            page_number: Page number of the content
            chunk_type: Type of content ("text" or "table")
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        chunks = self.text_splitter.split_text(content)
        
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            chunk_id = hashlib.md5(f"{chunk_text}_{page_number}_{i}".encode()).hexdigest()
            
            document_chunk = DocumentChunk(
                id=chunk_id,
                text=chunk_text,
                page_number=page_number,
                chunk_type=chunk_type,
                metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "character_count": len(chunk_text)
                }
            )
            document_chunks.append(document_chunk)
        
        return document_chunks
    
    async def process_document(self, url: str) -> List[DocumentChunk]:
        """
        Complete document processing pipeline
        
        Args:
            url: Document URL
            
        Returns:
            List[DocumentChunk]: List of processed document chunks
        """
        temp_file_path = None
        
        try:
            # Download document
            temp_file_path = await self.download_document(url)
            
            # Extract text
            text_pages = self.extract_text_from_pdf(temp_file_path)
            
            # Extract tables
            table_pages = self.extract_tables_from_pdf(temp_file_path)
            
            # Process all chunks
            all_chunks = []
            
            # Process text chunks
            for text, page_num in text_pages:
                text_chunks = self.chunk_content(text, page_num, "text")
                all_chunks.extend(text_chunks)
            
            # Process table chunks
            for table_markdown, page_num in table_pages:
                table_chunks = self.chunk_content(table_markdown, page_num, "table")
                all_chunks.extend(table_chunks)
            
            logger.info(f"Processed document into {len(all_chunks)} chunks")
            return all_chunks
            
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
    
    def get_document_hash(self, url: str) -> str:
        """
        Generate a hash for document URL for caching
        
        Args:
            url: Document URL
            
        Returns:
            str: SHA-256 hash of the URL
        """
        return hashlib.sha256(url.encode()).hexdigest()
