"""
Configuration constants and settings for the Document Processing API.
"""

import logging
import os

# Directory constants
UPLOADED_FILE_PATH = "uploaded_files"
PARSED_FILE_PATH = "parsed_files"
GENERATED_QUESTIONS_PATH = "generated_questions"
BM25_INDEXES_PATH = "bm25_indexes"

# Pinecone Configuration - Generic and configurable
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "biz-to-bricks-vector-store")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "document-namespace")

# LLM Configuration
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Embedding Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-large")
EMBEDDING_DIMENSION = os.getenv("EMBEDDING_DIMENSION", "3072")  # OpenAI text-embedding-3-large dimension

# API Configuration
API_TITLE = "Document Processing API"
API_VERSION = "3.0.0"
API_CONTACT = {
    "name": "Document Processing Team",
    "email": "support@documentprocessing.com"
}
API_LICENSE = {
    "name": "MIT License",
    "url": "https://opensource.org/licenses/MIT"
}

# File type configuration
EXCEL_EXTENSIONS = ['.xlsx', '.xls']
CSV_EXTENSIONS = ['.csv']
DOCUMENT_EXTENSIONS = ['.pdf', '.docx', '.txt']
SUPPORTED_EXTENSIONS = EXCEL_EXTENSIONS + CSV_EXTENSIONS + DOCUMENT_EXTENSIONS

# Logging configuration
def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

# Tags metadata for API documentation
TAGS_METADATA = [
    {
        "name": "File Management",
        "description": "Upload, list, and delete files. Supports PDFs, Excel, CSV, DOCX, and TXT files."
    },
    {
        "name": "Document Processing", 
        "description": "Parse files to markdown format, edit content, and prepare for search indexing."
    },
    {
        "name": "Search & Query",
        "description": "Hybrid search across documents and natural language queries on Excel/CSV data."
    },
    {
        "name": "AI Content Generation",
        "description": "Generate summaries, questions, and FAQ from processed documents using AI."
    },
    {
        "name": "Index Management",
        "description": "Manage search indexes and document ingestion for hybrid search capabilities."
    }
] 