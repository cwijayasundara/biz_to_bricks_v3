# Apply nest_asyncio early to support nested event loops
import nest_asyncio
try:
    nest_asyncio.apply()
except (RuntimeError, ValueError) as e:
    # Skip if already applied or incompatible loop type (e.g., uvloop)
    print(f"Skipping nest_asyncio patch: {e}")
    pass

from fastapi import FastAPI, UploadFile, File, Body, HTTPException, status, Path, Query
from fastapi.responses import JSONResponse
from file_util_enhanced import get_file_manager, create_directory, list_files as list_directory, load_markdown_file
from file_parser import parse_file_with_llama_parse
from doc_summarizer import summarize_text_content
from question_gen import generate_questions
from faq_gen import generate_faq
from excel_agent import create_excel_agent
from pydantic import BaseModel, Field
import os
from pathlib import Path as FilePath
import logging
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager
from ingest_docs import ingest_documents_to_pinecone_and_bm25
from hybrid_search import execure_hybrid_chain
import json
from langchain_openai import ChatOpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define path constants
UPLOADED_FILE_PATH = "uploaded_files"
PARSED_FILE_PATH = "parsed_files"
GENERATED_QUESTIONS_PATH = "generated_questions"

# Initialize file manager
file_manager = get_file_manager()

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize resources
    ensure_directories_exist()
    logger.info("Application started, directories initialized")
    yield
    # Shutdown: cleanup (if needed)
    logger.info("Application shutting down")

app = FastAPI(
    title="Document Processing API",
    description="""
    🚀 **Comprehensive Document Processing & AI-Powered Search API**
    
    This API provides a complete document processing pipeline with AI-powered search capabilities:
    
    ## 📋 **Quick Start Workflow**
    
    1. **📤 Upload Files**: Upload PDFs, Excel files (.xlsx/.xls), CSV files, or text documents
    2. **📝 Parse Files**: Convert documents to structured markdown format using LlamaParse
    3. **📚 Ingest Documents**: Index parsed content for hybrid search (Pinecone + BM25)
    4. **🔍 Search & Query**: Use hybrid search for documents or pandas agent for Excel/CSV analysis
    
    ## 🎯 **Key Features**
    
    - **Multi-format Support**: PDF, Excel, CSV, DOCX, TXT files
    - **Hybrid Search**: Combines vector search (Pinecone) + keyword search (BM25)
    - **Excel/CSV Analysis**: Natural language queries on spreadsheet data
    - **AI Content Generation**: Summaries, questions, and FAQ generation
    - **Intelligent Search**: AI-powered result ranking and comparison
    
    ## 📊 **Search Capabilities**
    
    - **Document Search**: Semantic + keyword search across all document types
    - **Targeted Search**: Search within specific documents
    - **Excel/CSV Queries**: Natural language data analysis and calculations
    - **Intelligent Ranking**: AI compares and ranks results from multiple sources
    
    ## 🛠️ **Supported File Types**
    
    | Type | Extensions | Processing | Search Method |
    |------|------------|------------|---------------|
    | Documents | `.pdf`, `.docx`, `.txt` | LlamaParse → Markdown | Pinecone + BM25 |
    | Spreadsheets | `.xlsx`, `.xls` | LlamaParse + Pandas | AI Agent Queries |
    | Data Files | `.csv` | LlamaParse + Pandas | AI Agent Queries |
    
    ## 🔗 **API Workflow Examples**
    
    ### Basic Document Processing:
    ```
    POST /uploadfile/ → GET /parsefile/{filename} → POST /ingestdocuments/{filename} → POST /hybridsearch/
    ```
    
    ### Excel/CSV Analysis:
    ```
    POST /uploadfile/ → POST /querypandas/ (direct analysis)
    ```
    
    ### Content Generation:
    ```
    POST /uploadfile/ → GET /parsefile/{filename} → GET /summarizecontent/{filename}
    ```
    """,
    version="3.0.0",
    lifespan=lifespan,
    contact={
        "name": "Biz To Bricks Team",
        "email": "support@biztobricks.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    tags_metadata=[
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
)

# Define data models with enhanced documentation and examples
class ContentUpdate(BaseModel):
    """Model for content update requests - used to save edited parsed content"""
    content: str = Field(
        ..., 
        description="The edited markdown content to save to parsed files directory",
        example="# Sample Document\n\nThis is the edited content with **markdown formatting**.\n\n## Key Points\n- Point 1\n- Point 2"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "# Updated Document\n\nThis is the revised content after editing.\n\n## Summary\n- Updated information\n- Corrected data"
            }
        }

class ErrorResponse(BaseModel):
    """Model for standardized error responses"""
    error: str = Field(
        ..., 
        description="Detailed error message explaining what went wrong",
        example="File not found: sample.pdf does not exist in uploaded_files directory"
    )

class SuccessResponse(BaseModel):
    """Model for standardized success responses"""
    status: str = Field(
        "success", 
        description="Status of the operation (always 'success' for this model)",
        example="success"
    )
    message: str = Field(
        ..., 
        description="Detailed success message with operation results",
        example="Content for sample_document saved and ingested successfully. Document is now searchable in the hybrid search system."
    )

class FileResponse(BaseModel):
    """Model for file upload responses with file type detection"""
    filename: str = Field(
        ..., 
        description="Original name of the uploaded file",
        example="financial_report.xlsx"
    )
    file_path: str = Field(
        ..., 
        description="Server path where the file is stored",
        example="uploaded_files/financial_report.xlsx"
    )
    file_type: str = Field(
        default="document", 
        description="Detected file type: 'excel', 'csv', or 'document'",
        example="excel"
    )
    is_excel_csv: bool = Field(
        default=False, 
        description="True if file is Excel (.xlsx/.xls) or CSV, False for other documents",
        example=True
    )
    message: str = Field(
        default="File uploaded successfully", 
        description="Upload status message with next steps guidance",
        example="EXCEL file uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch for comprehensive search or /querypandas for DataFrame queries."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "sales_data.xlsx",
                "file_path": "uploaded_files/sales_data.xlsx",
                "file_type": "excel",
                "is_excel_csv": True,
                "message": "EXCEL file uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch for comprehensive search or /querypandas for DataFrame queries."
            }
        }

class FilesListResponse(BaseModel):
    """Model for file listing responses from various directories"""
    files: List[str] = Field(
        ..., 
        description="List of file names in the requested directory",
        example=["document1.pdf", "spreadsheet.xlsx", "data.csv", "report.docx"]
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "files": ["financial_report.pdf", "sales_data.xlsx", "customer_list.csv"]
            }
        }

# Define data models for search with comprehensive examples
class SearchQuery(BaseModel):
    """Model for search queries - supports both document search and Excel/CSV analysis"""
    query: str = Field(
        ..., 
        description="Natural language search query or question about the data",
        example="What is the average salary by department?"
    )
    debug: bool = Field(
        False, 
        description="Include debug information showing search process and retrieved documents",
        example=False
    )
    source_document: Optional[str] = Field(
        None, 
        description="Optional filename to search within specific document (omit for all documents)",
        example="sales_data.xlsx"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "General search across all documents",
                    "value": {
                        "query": "What are the main conclusions about market trends?",
                        "debug": False,
                        "source_document": None
                    }
                },
                {
                    "description": "Targeted document search",
                    "value": {
                        "query": "List all passengers in first class",
                        "debug": False,
                        "source_document": "titanic.csv"
                    }
                },
                {
                    "description": "Excel data analysis with debug",
                    "value": {
                        "query": "Calculate average age and survival rate by passenger class",
                        "debug": True,
                        "source_document": "passenger_data.xlsx"
                    }
                }
            ]
        }



# Helper functions
def ensure_directories_exist():
    """Ensure all required directories exist"""
    for directory in [UPLOADED_FILE_PATH, PARSED_FILE_PATH, GENERATED_QUESTIONS_PATH]:
        create_directory(directory)

def get_file_path(directory: str, filename: str, extension: Optional[str] = None) -> str:
    """Construct file path with proper handling"""
    if extension:
        # Use pathlib to properly extract base filename without extension
        base_name = FilePath(filename).stem
        return str(FilePath(directory) / f"{base_name}{extension}")
    return str(FilePath(directory) / filename)

def is_excel_or_csv_file(filename: str) -> bool:
    """Check if a file is an Excel or CSV file based on its extension."""
    if not filename:
        return False
    
    extension = FilePath(filename).suffix.lower()
    return extension in ['.csv', '.xlsx', '.xls']

def get_file_type(filename: str) -> str:
    """Get the file type (csv or excel) based on extension."""
    if not filename:
        return "unknown"
    
    extension = FilePath(filename).suffix.lower()
    if extension == '.csv':
        return "csv"
    elif extension in ['.xlsx', '.xls']:
        return "excel"
    else:
        return "unknown"

# API Routes
@app.post(
    "/uploadfile/", 
    response_model=FileResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["File Management"],
    summary="Upload a file to the server",
    description="""
    📤 **Upload files for processing and analysis**
    
    Accepts multiple file formats and automatically detects file type for appropriate processing:
    
    ## 📋 **Supported Formats**
    - **Documents**: PDF, DOCX, TXT → Processed with LlamaParse for text extraction
    - **Spreadsheets**: XLSX, XLS → Processed for both text search and data analysis  
    - **Data Files**: CSV → Processed for both text search and data analysis
    
    ## 🔄 **Processing Pipeline**
    
    **For Documents (PDF, DOCX, TXT):**
    1. Upload → Parse → Ingest → Search with hybrid search
    
    **For Excel/CSV:**
    1. Upload → Parse (optional) → Query directly with pandas agent
    2. OR: Upload → Parse → Ingest → Search with hybrid search
    
    ## ⚠️ **File Size Limits**
    - Maximum file size: 200MB
    - Files are stored in `uploaded_files/` directory
    
    ## 🎯 **Next Steps After Upload**
    - **All files**: Use `/parsefile/{filename}` to convert to markdown
    - **Documents**: Use `/ingestdocuments/{filename}` to enable search
    - **Excel/CSV**: Use `/querypandas/` for immediate data analysis
    """,
    responses={
        201: {
            "description": "File uploaded successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "excel_file": {
                            "summary": "Excel file upload",
                            "value": {
                                "filename": "sales_data.xlsx",
                                "file_path": "uploaded_files/sales_data.xlsx",
                                "file_type": "excel",
                                "is_excel_csv": True,
                                "message": "EXCEL file uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch for comprehensive search or /querypandas for DataFrame queries."
                            }
                        },
                        "pdf_file": {
                            "summary": "PDF document upload",
                            "value": {
                                "filename": "research_paper.pdf",
                                "file_path": "uploaded_files/research_paper.pdf",
                                "file_type": "document",
                                "is_excel_csv": False,
                                "message": "Document uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch to query."
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Bad request - invalid file or missing filename",
            "content": {
                "application/json": {
                    "example": {
                        "error": "File must have a filename"
                    }
                }
            }
        },
        500: {
            "description": "Server error during file upload",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Error saving file: disk space full"
                    }
                }
            }
        }
    }
)
async def upload_file(file: UploadFile = File(..., description="File to upload - supports PDF, DOCX, TXT, XLSX, XLS, CSV formats")):
    """
    Upload a file to the server with automatic file type detection.
    For Excel/CSV files, they can be analyzed directly or processed for text search.
    
    Args:
        file: The file to upload (PDF, DOCX, TXT, XLSX, XLS, CSV)
        
    Returns:
        FileResponse: Information about the uploaded file including type and next steps
    """
    logger.info(f"Received upload request for file: {file.filename}")
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )
    
    file_path = get_file_path(UPLOADED_FILE_PATH, file.filename)
    
    try:
        # Save the uploaded file
        content = await file.read()
        saved_path = file_manager.save_binary_file(UPLOADED_FILE_PATH, file.filename, content)
        
        # Check if this is an Excel or CSV file
        is_excel_csv = is_excel_or_csv_file(file.filename)
        file_type = get_file_type(file.filename)
        
        logger.info(f"File saved to {saved_path}")
        
        if is_excel_csv:
            logger.info(f"Detected {file_type} file: {file.filename}. Will be processed with LlamaParse and pandas agent.")
            return {
                "filename": file.filename, 
                "file_path": saved_path,
                "file_type": file_type,
                "is_excel_csv": True,
                "message": f"{file_type.upper()} file uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch for comprehensive search or /querypandas for DataFrame queries."
            }
        else:
            return {
                "filename": file.filename, 
                "file_path": saved_path,
                "file_type": "document",
                "is_excel_csv": False,
                "message": "Document uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch to query."
            }
    except Exception as e:
        logger.error(f"Error saving file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )

@app.get(
    "/listfiles/{directory}", 
    response_model=FilesListResponse,
    tags=["File Management"],
    summary="List files in a directory",
    description="""
    📋 **List all files in the specified directory**
    
    ## 📁 **Available Directories**
    - **`uploaded_files`**: Original uploaded files (PDF, Excel, CSV, etc.)
    - **`parsed_files`**: Converted markdown files from parsing
    - **`generated_questions`**: AI-generated questions and FAQ files
    
    ## 🔍 **Use Cases**
    - Check which files have been uploaded
    - Verify parsing results before ingestion
    - Browse generated content files
    - Get filenames for other API operations
    
    ## 📊 **Response Format**
    Returns an array of filenames without full paths for easy reference in other endpoints.
    """,
    responses={
        200: {
            "description": "List of files in the directory",
            "content": {
                "application/json": {
                    "examples": {
                        "uploaded_files": {
                            "summary": "Files in uploaded_files directory",
                            "value": {
                                "files": ["sales_report.pdf", "employee_data.xlsx", "customer_survey.csv", "product_manual.docx"]
                            }
                        },
                        "parsed_files": {
                            "summary": "Files in parsed_files directory",
                            "value": {
                                "files": ["sales_report.md", "employee_data.md", "customer_survey.md"]
                            }
                        },
                        "empty_directory": {
                            "summary": "Empty directory",
                            "value": {
                                "files": []
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid directory name",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Invalid directory: invalid_dir. Must be one of: uploaded_files, parsed_files, generated_questions"
                    }
                }
            }
        }
    }
)
async def list_files(
    directory: str = Path(
        ..., 
        description="Directory name to list files from",
        example="uploaded_files"
    )
):
    """
    List all files in the specified directory on the server.
    
    Args:
        directory: The directory to list files from (uploaded_files, parsed_files, or generated_questions)
        
    Returns:
        FilesListResponse: Array of filenames in the specified directory
    """
    logger.info(f"Listing files in directory: {directory}")
    
    try:
        files = list_directory(directory)
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )

@app.delete("/deletefile/{directory}/{filename}", response_model=SuccessResponse)
async def delete_file(
    directory: str = Path(..., description="Directory containing the file"),
    filename: str = Path(..., description="Name of the file to delete")
):
    """
    Delete a file from the specified directory.
    
    Args:
        directory: The directory containing the file
        filename: Name of the file to delete
        
    Returns:
        Success message if file was deleted
    """
    logger.info(f"Deleting file: {directory}/{filename}")
    
    # Validate directory
    valid_directories = ["uploaded_files", "parsed_files", "bm25_indexes", "generated_questions"]
    if directory not in valid_directories:
        logger.error(f"Invalid directory: {directory}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid directory. Must be one of: {', '.join(valid_directories)}"
        )
    
    try:
        # Check if file exists before attempting deletion
        if not file_manager.file_exists(directory, filename):
            logger.error(f"File not found: {directory}/{filename}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {filename} not found in {directory}"
            )
        
        # Delete the file
        success = file_manager.delete_file(directory, filename)
        
        if success:
            logger.info(f"Successfully deleted file: {directory}/{filename}")
            return {
                "status": "success",
                "message": f"File {filename} deleted successfully from {directory}"
            }
        else:
            logger.error(f"Failed to delete file: {directory}/{filename}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file {filename}"
            )
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error deleting file {directory}/{filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )

@app.get(
    "/parsefile/{filename}",
    tags=["Document Processing"],
    summary="Parse uploaded file to markdown format",
    description="""
    📝 **Convert uploaded files to structured markdown format using LlamaParse**
    
    This endpoint transforms raw files into searchable, structured markdown content that can be:
    - Edited before ingestion
    - Summarized using AI
    - Indexed for hybrid search
    - Used for content generation
    
    ## 🔄 **Processing Details**
    
    **LlamaParse Technology:**
    - Advanced document understanding with context preservation
    - Table extraction and formatting
    - Image description and analysis
    - Structured output with proper headings and lists
    
    **File Type Handling:**
    - **PDF**: Text extraction with layout preservation
    - **Excel/CSV**: Both tabular data and text content extraction
    - **DOCX**: Full document structure with formatting
    - **TXT**: Direct conversion with structure detection
    
    ## 💾 **Storage**
    - Parsed content saved as `{filename_without_extension}.md` in `parsed_files/`
    - Original formatting preserved where possible
    - Metadata includes file information and parsing details
    
    ## ⚡ **Performance**
    - First parse: Processes file and saves result
    - Subsequent calls: Returns cached parsed content instantly
    - Large files may take 30-60 seconds for initial processing
    """,
    responses={
        200: {
            "description": "File parsed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "pdf_document": {
                            "summary": "Parsed PDF document",
                            "value": {
                                "text_content": "# Financial Report Q3 2024\n\n## Executive Summary\n\nThis quarter shows significant growth...\n\n## Key Metrics\n\n- Revenue: $2.5M (+15%)\n- Profit: $450K (+22%)\n- Customers: 1,200 (+8%)",
                                "metadata": {
                                    "file_name": "financial_report",
                                    "file_path": "parsed_files/financial_report",
                                    "parsing_time": "45.2s",
                                    "pages_processed": 12
                                }
                            }
                        },
                        "excel_file": {
                            "summary": "Parsed Excel spreadsheet",
                            "value": {
                                "text_content": "# Sales Data Analysis\n\n## Sales by Region\n\n| Region | Q1 | Q2 | Q3 | Q4 |\n|--------|----|----|----|----||\n| North  | 150| 160| 175| 190|\n| South  | 120| 135| 140| 155|\n\n## Summary Statistics\n\nTotal sales increased by 12% year over year...",
                                "metadata": {
                                    "file_name": "sales_data",
                                    "file_path": "parsed_files/sales_data",
                                    "sheets_processed": 3,
                                    "tables_extracted": 5
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "File report.pdf not found in uploaded_files directory"
                    }
                }
            }
        },
        500: {
            "description": "Parsing error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Error parsing file: corrupted PDF format"
                    }
                }
            }
        }
    }
)
async def parse_uploaded_file(
    filename: str = Path(
        ..., 
        description="Name of the uploaded file to parse (include file extension)",
        example="financial_report.pdf"
    )
):
    """
    Parse an uploaded file into markdown format using LlamaParse AI.
    Works for all supported file types and preserves document structure.
    
    Args:
        filename: Name of the file to parse (must exist in uploaded_files directory)
        
    Returns:
        Dict: Parsed text content in markdown format plus metadata about the parsing process
    """
    logger.info(f"Parsing file: {filename}")
    
    try:
        # Check if the parsed file already exists
        # Use pathlib to properly extract base filename without extension
        base_filename = FilePath(filename).stem
        parsed_file_path = get_file_path(PARSED_FILE_PATH, base_filename, extension=".md")
        uploaded_file_path = get_file_path(UPLOADED_FILE_PATH, filename)
        
        text_content = ""
        metadata: Dict[str, Any] = {}
        
        if file_manager.file_exists(PARSED_FILE_PATH, f"{base_filename}.md"):
            logger.info(f"Using existing parsed file: {base_filename}.md")
            text_content = file_manager.load_file(PARSED_FILE_PATH, f"{base_filename}.md")
            metadata = {
                "file_name": base_filename, 
                "file_path": f"{PARSED_FILE_PATH}/{base_filename}"
            }
        else:
            logger.info(f"Parsing new file: {filename}")
            # Get the uploaded file path for parsing
            uploaded_file_local_path = file_manager.get_file_path(UPLOADED_FILE_PATH, filename)
            text_content, metadata = parse_file_with_llama_parse(uploaded_file_local_path)
            metadata["file_name"] = base_filename
            metadata["file_path"] = f"{PARSED_FILE_PATH}/{base_filename}"
            
            # Save the parsed content
            saved_path = file_manager.save_file(PARSED_FILE_PATH, f"{base_filename}.md", text_content)
            logger.info(f"Saved parsed content to {saved_path}")
            
        return {"text_content": text_content, "metadata": metadata}
        
    except FileNotFoundError:
        logger.error(f"File not found for parsing: {filename}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {filename} not found"
        )
    except Exception as e:
        logger.error(f"Error parsing file {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing file: {str(e)}"
        )

@app.post("/savecontent/{filename}", response_model=SuccessResponse)
async def save_content(
    filename: str = Path(..., description="Name of the file to save content for"),
    content_update: ContentUpdate = Body(..., description="Content to save")
):
    """
    Save edited content to the parsed files directory, overwriting the original parsed file.
    
    Args:
        filename: Name of the file to save content for (can be with or without extension)
        content_update: The content to save
        
    Returns:
        Success message
    """
    logger.info(f"Saving content for file: {filename}")
    
    try:
        # Extract base filename without extension to ensure consistency
        base_filename = FilePath(filename).stem
        logger.info(f"Using base filename: {base_filename}")
        
        saved_path = file_manager.save_file(PARSED_FILE_PATH, f"{base_filename}.md", content_update.content)
            
        logger.info(f"Content saved to {saved_path}")
        return {
            "status": "success", 
            "message": f"Content for {base_filename} saved successfully"
        }
    except Exception as e:
        logger.error(f"Error saving content for {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving content: {str(e)}"
        )

@app.post("/saveandingst/{filename}", response_model=SuccessResponse)
async def save_content_and_ingest(
    filename: str = Path(..., description="Name of the file to save content for and ingest"),
    content_update: ContentUpdate = Body(..., description="Content to save")
):
    """
    Save edited content to the parsed files directory and then ingest the document 
    to Pinecone and BM25 index in a single operation.
    
    Args:
        filename: Name of the file to save content for (can be with or without extension)
        content_update: The content to save
        
    Returns:
        Success message with details of both operations
    """
    logger.info(f"Saving content and ingesting for file: {filename}")
    
    try:
        # Extract base filename without extension to ensure consistency
        base_filename = FilePath(filename).stem
        logger.info(f"Using base filename: {base_filename}")
        
        # Step 1: Save the content
        logger.info(f"Step 1: Saving content for {base_filename}")
        saved_path = file_manager.save_file(PARSED_FILE_PATH, f"{base_filename}.md", content_update.content)
        logger.info(f"Content saved to {saved_path}")
        
        # Step 2: Ingest the document to Pinecone and BM25
        logger.info(f"Step 2: Ingesting documents for {base_filename}")
        ingest_documents_to_pinecone_and_bm25(base_filename)
        logger.info(f"Documents ingested to Pinecone and BM25 index for {base_filename}")
        
        return {
            "status": "success", 
            "message": f"Content for {base_filename} saved and ingested successfully. Document is now searchable in the hybrid search system."
        }
        
    except FileNotFoundError as e:
        logger.error(f"File not found during save and ingest for {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {base_filename if 'base_filename' in locals() else filename} not found during ingestion process"
        )
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error during save and ingest for {filename}: {error_str}")
        
        # Provide specific guidance for common errors
        if "ingest" in error_str.lower():
            if "Metadata size" in error_str and "exceeds the limit" in error_str:
                error_detail = f"Content was saved successfully, but ingestion failed due to document size. The document will be automatically chunked on retry. Please try ingesting again."
            elif "400" in error_str and "Bad Request" in error_str:
                error_detail = f"Content was saved successfully, but Pinecone ingestion failed. Document chunking has been improved to resolve this issue. Please try again."
            else:
                error_detail = f"Content was saved successfully, but ingestion failed: {error_str}"
        else:
            error_detail = f"Error during save and ingest: {error_str}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

@app.get("/summarizecontent/{filename}")
async def summarize_content(
    filename: str = Path(..., description="Name of the file to summarize")
):
    """
    Parse a file from the parsed_files directory and return its summary.
    Summary is generated fresh each time without saving to disk.
    
    Args:
        filename: Name of the file to summarize (can be with or without extension)
        
    Returns:
        Summary of the file content and metadata
    """
    logger.info(f"Summarizing file: {filename}")
    
    try:
        # Extract base filename without extension to ensure consistency
        # This handles both "Sample1.pdf" and "Sample1" as input
        base_filename = FilePath(filename).stem
        logger.info(f"Using base filename: {base_filename}")
        
        # Load content from parsed file
        if file_manager.file_exists(PARSED_FILE_PATH, f"{base_filename}.md"):
            logger.info(f"Loading parsed file for summarization: {base_filename}.md")
            text_content = file_manager.load_file(PARSED_FILE_PATH, f"{base_filename}.md")
        else:
            raise FileNotFoundError(f"No file found for {base_filename} in parsed_files")
        
        logger.info(f"Generating fresh summary for {base_filename}")
        summary = summarize_text_content(text_content)
        
        metadata = {
            "file_name": base_filename,
            "source": "parsed_file",
            "generated_fresh": True
        }
            
        logger.info(f"Summary generated successfully for {base_filename}")
        return {"summary": summary, "metadata": metadata}
        
    except FileNotFoundError as e:
        logger.error(f"File not found for summarization: {e}")
        # Use base_filename if it was extracted, otherwise use original filename
        display_filename = FilePath(filename).stem if filename else filename
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"File {display_filename} not found in parsed_files directory"}
        )
    except Exception as e:
        logger.error(f"Error during summarization for {filename}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to summarize file: {str(e)}"}
        )

@app.post("/ingestdocuments/{filename}")
async def ingest_documents(filename: str = Path(..., description="Name of the file to ingest")):
    """
    Ingest documents to Pinecone and BM25 index.
    All file types (PDF, Excel, CSV) are processed through the same pipeline.
    Documents are automatically chunked to avoid metadata size limits.
    """
    
    try:
        # Extract base filename without extension to ensure consistency
        base_filename = FilePath(filename).stem
        logger.info(f"Ingesting documents for base filename: {base_filename}")
        
        ingest_documents_to_pinecone_and_bm25(base_filename)
        return {"message": f"Documents successfully ingested to Pinecone and BM25 index for {base_filename}"}
    except FileNotFoundError as e:
        logger.error(f"File not found for ingestion: {e}")
        base_filename = FilePath(filename).stem if filename else filename
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"File {base_filename} not found in server/parsed_files. Please parse the file first."}
        )
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error during ingestion for {filename}: {error_str}")
        
        # Provide specific guidance for common errors
        if "Metadata size" in error_str and "exceeds the limit" in error_str:
            error_msg = f"Document too large for Pinecone (metadata limit exceeded). The document has been automatically chunked to resolve this issue. Please try again."
        elif "400" in error_str and "Bad Request" in error_str:
            error_msg = f"Pinecone API error: {error_str}. Document chunking has been improved to avoid this issue."
        else:
            error_msg = f"Failed to ingest file: {error_str}"
            
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": error_msg}
        )

# Initialize LLM for result comparison
llm_openai = ChatOpenAI(model="gpt-4.1-mini", api_key=os.getenv("OPENAI_API_KEY"))

def compare_and_rerank_results(query: str, document_result: str, pandas_results: List[Dict]) -> Dict[str, Any]:
    """
    Compare results from document search and pandas agent, then return the most suitable result.
    
    Args:
        query: The original search query
        document_result: Result from Pinecone/BM25 document search
        pandas_results: List of results from pandas agent search
        
    Returns:
        Dictionary with the best result and explanation
    """
    try:
        logger.info(f"🤖 Comparing and reranking results for query: {query}")
        
        # Handle case where we have no results
        if not document_result and not pandas_results:
            logger.info("❌ No results from either search method")
            return {
                "best_result": "No results found for your query.",
                "source": "none",
                "explanation": "Neither document search nor data analysis found relevant information.",
                "comparison_performed": True
            }
        
        # Handle case where we only have document results
        if document_result and not pandas_results:
            logger.info("📄 Only document search results available")
            return {
                "best_result": document_result,
                "source": "document_search",
                "explanation": "Only document search found relevant information.",
                "comparison_performed": False
            }
        
        # Handle case where we only have pandas results
        if not document_result and pandas_results:
            logger.info("📊 Only pandas agent results available")
            # If multiple pandas results, combine them
            combined_pandas = "\n\n".join([
                f"**{result['filename']} ({result['file_type'].upper()}):**\n{result['answer']}"
                for result in pandas_results
            ])
            return {
                "best_result": combined_pandas,
                "source": "pandas_agent",
                "explanation": "Only data analysis found relevant information.",
                "comparison_performed": False
            }
        
        # We have both types of results - perform intelligent comparison
        logger.info("🤖 Both search methods found results - performing AI comparison")
        
        # Prepare pandas results for comparison
        pandas_summary = "\n\n".join([
            f"**{result['filename']} ({result['file_type'].upper()}):**\n{result['answer']}"
            for result in pandas_results
        ])
        
        # Create comparison prompt
        comparison_prompt = f"""
You are an AI assistant that evaluates search results to determine which is most relevant and useful for answering a user's query.

**User Query:** {query}

**Document Search Result (from text documents):**
{document_result}

**Data Analysis Result (from Excel/CSV files):**
{pandas_summary}

**Task:** Analyze both results and determine which one better answers the user's query. Consider:
1. Relevance to the specific question asked
2. Accuracy and specificity of the answer
3. Completeness of the information provided
4. Whether the query is better suited for text analysis or data analysis

**Instructions:**
- If the query is asking for specific data, calculations, or statistical information, prefer the data analysis result
- If the query is asking for conceptual information, explanations, or general knowledge, prefer the document search result
- If both are equally relevant, choose the one that provides more specific and actionable information
- If one result is clearly irrelevant or doesn't answer the query, choose the other

**Response Format:**
Choose one of: "document_search", "pandas_agent", or "combined"

If "combined", merge the best parts of both results.
If "document_search" or "pandas_agent", return the chosen result.

**Your Choice:** [document_search/pandas_agent/combined]

**Best Answer:** [Provide the best answer based on your choice]

**Explanation:** [Brief explanation of why you chose this result]
"""
        
        # Get LLM comparison
        response = llm_openai.invoke(comparison_prompt)
        response_text = response.content
        
        # Parse the response
        lines = response_text.strip().split('\n')
        choice = "document_search"  # default
        best_answer = document_result  # default
        explanation = "Default selection"
        
        for i, line in enumerate(lines):
            if "**Your Choice:**" in line:
                choice_line = line.split("**Your Choice:**")[1].strip()
                if "pandas_agent" in choice_line.lower():
                    choice = "pandas_agent"
                elif "combined" in choice_line.lower():
                    choice = "combined"
                elif "document_search" in choice_line.lower():
                    choice = "document_search"
            
            elif "**Best Answer:**" in line:
                # Get everything after this line until "**Explanation:**"
                answer_parts = []
                for j in range(i + 1, len(lines)):
                    if "**Explanation:**" in lines[j]:
                        break
                    answer_parts.append(lines[j])
                if answer_parts:
                    best_answer = "\n".join(answer_parts).strip()
            
            elif "**Explanation:**" in line:
                explanation = line.split("**Explanation:**")[1].strip()
        
        # Apply the choice
        if choice == "pandas_agent":
            final_result = pandas_summary
            source = "pandas_agent"
        elif choice == "combined":
            final_result = best_answer if best_answer != document_result else f"{document_result}\n\n**Data Analysis:**\n{pandas_summary}"
            source = "combined"
        else:  # document_search
            final_result = document_result
            source = "document_search"
        
        logger.info(f"🎯 AI chose: {choice} | Source: {source}")
        
        return {
            "best_result": final_result,
            "source": source,
            "explanation": explanation,
            "comparison_performed": True,
            "ai_choice": choice
        }
        
    except Exception as e:
        logger.error(f"❌ Error in result comparison: {str(e)}")
        # Fallback to document result or pandas result
        if document_result:
            return {
                "best_result": document_result,
                "source": "document_search",
                "explanation": "Comparison failed, defaulting to document search result.",
                "comparison_performed": False,
                "error": str(e)
            }
        elif pandas_results:
            combined_pandas = "\n\n".join([
                f"**{result['filename']} ({result['file_type'].upper()}):**\n{result['answer']}"
                for result in pandas_results
            ])
            return {
                "best_result": combined_pandas,
                "source": "pandas_agent", 
                "explanation": "Comparison failed, defaulting to data analysis result.",
                "comparison_performed": False,
                "error": str(e)
            }
        else:
            return {
                "best_result": "No results found for your query.",
                "source": "none",
                "explanation": "Comparison failed and no results available.",
                "comparison_performed": False,
                "error": str(e)
            }

# Get available source documents
@app.get("/sourcedocuments/", response_model=FilesListResponse)
async def get_source_documents():
    """
    Get a list of all available source documents from parsed files and uploaded Excel/CSV files.
    These can be used to filter hybrid search results.
    
    Returns:
        List of document names available for search filtering (both parsed documents and Excel/CSV files)
    """
    try:
        logger.info("Getting available source documents from parsed files and uploaded files")
        
        # Get parsed files (these are searchable through document search)
        parsed_files = file_manager.list_files(PARSED_FILE_PATH)
        logger.info(f"Found {len(parsed_files)} parsed files")
        
        # Get uploaded Excel/CSV files (these are searchable through pandas agent)
        uploaded_files = file_manager.list_files(UPLOADED_FILE_PATH)
        excel_csv_files = [f for f in uploaded_files if is_excel_or_csv_file(f)]
        logger.info(f"Found {len(excel_csv_files)} Excel/CSV files")
        
        # Combine both types of source documents
        # For parsed files, we need to find the corresponding original filenames
        source_documents = []
        
        # Add parsed files (find original filenames with extensions)
        for parsed_file in parsed_files:
            if parsed_file.endswith('.md'):
                # Remove .md extension to get base name
                base_name = parsed_file[:-3]  # Remove .md
                
                # Find the corresponding original file in uploaded_files
                original_file = None
                for uploaded_file in uploaded_files:
                    if FilePath(uploaded_file).stem == base_name:
                        original_file = uploaded_file
                        break
                
                # Use original filename if found, otherwise use base name
                if original_file:
                    source_documents.append(original_file)
                else:
                    source_documents.append(base_name)
            else:
                source_documents.append(parsed_file)
        
        # Add Excel/CSV files that aren't already included (in case some weren't parsed)
        for excel_csv_file in excel_csv_files:
            if excel_csv_file not in source_documents:
                source_documents.append(excel_csv_file)
        
        # Remove duplicates and sort
        source_documents = sorted(list(set(source_documents)))
        
        logger.info(f"Total source documents available: {len(source_documents)}")
        logger.info(f"Source documents: {source_documents}")
        
        return {"files": source_documents}
        
    except Exception as e:
        logger.error(f"Error getting source documents: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get source documents: {str(e)}"}
        )

# Hybrid search
@app.post(
    "/hybridsearch/",
    tags=["Search & Query"],
    summary="Intelligent hybrid search across documents and data",
    description="""
    🔍 **Advanced AI-powered search combining multiple search strategies**
    
    This endpoint provides intelligent search across your documents with three distinct modes:
    
    ## 🎯 **Search Modes**
    
    ### 1. **Comprehensive Search** (no source_document)
    - Searches both document index (Pinecone + BM25) AND Excel/CSV files
    - AI compares and ranks results from all sources
    - Returns the most relevant single answer
    - Best for: General questions when you're unsure of the source
    
    ### 2. **Document-Targeted Search** (PDF/DOCX source)
    - Searches only within the specified document using hybrid search
    - Combines semantic similarity (Pinecone) + keyword matching (BM25)
    - Best for: Specific questions about a particular document
    
    ### 3. **Data-Targeted Search** (Excel/CSV source)
    - Queries only the specified Excel/CSV file using pandas agent
    - Performs calculations, filtering, and data analysis
    - Best for: Statistical questions and data calculations
    
    ## 🧠 **AI Intelligence Features**
    
    **Intelligent Result Ranking:**
    - When searching multiple sources, AI analyzes all results
    - Determines which source provides the best answer for your query
    - Provides reasoning for the choice
    - Shows alternative results in expandable sections
    
    **Query Understanding:**
    - Semantic search for concept-based queries
    - Keyword search for exact matches and names
    - Data analysis for numerical and statistical questions
    
    ## 🔧 **Debug Mode**
    
    Enable `debug: true` to see:
    - Retrieved document chunks and scores
    - Search execution logs
    - Performance metrics
    - Raw results from each search method
    
    ## 📊 **Performance**
    - Document search: ~2-5 seconds
    - Excel/CSV analysis: ~3-8 seconds  
    - Comprehensive search: ~5-10 seconds (parallel execution)
    """,
    responses={
        200: {
            "description": "Search completed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "intelligent_search": {
                            "summary": "AI-ranked comprehensive search result",
                            "value": {
                                "best_result": {
                                    "answer": "Based on the sales data, the average revenue per customer is $2,083. This is calculated from total revenue of $2.5M divided by 1,200 customers.",
                                    "source": "pandas_agent",
                                    "explanation": "This query requires numerical calculation which is best handled by data analysis rather than document search."
                                },
                                "summary": {
                                    "search_strategy": "intelligent_reranking",
                                    "ai_choice": "pandas_agent",
                                    "documents_searched": 5,
                                    "excel_files_analyzed": 1
                                },
                                "document_search": {
                                    "searched": True,
                                    "success": True,
                                    "result": "Customer information is available in our database..."
                                },
                                "pandas_agent_search": {
                                    "searched": True,
                                    "results": [
                                        {
                                            "filename": "sales_data.xlsx",
                                            "answer": "Average revenue per customer: $2,083",
                                            "file_type": "excel"
                                        }
                                    ]
                                }
                            }
                        },
                        "targeted_document": {
                            "summary": "Search within specific PDF document",
                            "value": {
                                "summary": {
                                    "search_strategy": "targeted",
                                    "source_document": "research_paper.pdf",
                                    "search_methods": {
                                        "document_search": True,
                                        "pandas_search": False
                                    }
                                },
                                "document_search": {
                                    "searched": True,
                                    "success": True,
                                    "result": "The study concluded that implementation of the new methodology resulted in a 23% improvement in efficiency metrics..."
                                }
                            }
                        },
                        "excel_analysis": {
                            "summary": "Direct Excel/CSV data analysis",
                            "value": {
                                "summary": {
                                    "search_strategy": "targeted",
                                    "source_document": "employee_data.xlsx"
                                },
                                "pandas_agent_search": {
                                    "searched": True,
                                    "results": [
                                        {
                                            "filename": "employee_data.xlsx",
                                            "answer": "Department breakdown:\n- Engineering: 45 employees (avg salary: $95K)\n- Sales: 32 employees (avg salary: $78K)\n- Marketing: 23 employees (avg salary: $72K)",
                                            "file_type": "excel"
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid search query",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Search query cannot be empty"
                    }
                }
            }
        },
        500: {
            "description": "Search execution error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Error during hybrid search: connection to search index failed"
                    }
                }
            }
        }
    }
)
async def hybrid_search(search_query: SearchQuery):
    """
    Perform intelligent hybrid search with AI-powered result ranking.
    Automatically selects the best search strategy based on query and source document.
    
    Args:
        search_query: SearchQuery object containing query text, debug flag, and optional source document
        
    Returns:
        Dict: Search results with intelligent ranking, source information, and metadata
    """
    try:
        logger.info(f"Performing targeted search for: {search_query.query}")
        
        # Determine search strategy based on source document
        source_document = search_query.source_document
        search_documents = True
        search_excel_csv = True
        target_excel_csv_files = []
        
        if source_document:
            # Check if source document is Excel/CSV
            logger.info(f"Checking file type for source document: {source_document}")
            is_excel_csv = is_excel_or_csv_file(source_document)
            logger.info(f"Is Excel/CSV file: {is_excel_csv}")
            
            if is_excel_csv:
                # Only search the specific Excel/CSV file
                search_documents = False
                search_excel_csv = True
                target_excel_csv_files = [source_document]
                logger.info(f"✅ TARGETING EXCEL/CSV FILE ONLY: {source_document}")
                logger.info(f"✅ Document search: DISABLED, Excel/CSV search: ENABLED")
            else:
                # Only search documents (skip Excel/CSV)
                search_documents = True
                search_excel_csv = False
                logger.info(f"✅ TARGETING DOCUMENT FILE ONLY: {source_document}")
                logger.info(f"✅ Document search: ENABLED, Excel/CSV search: DISABLED")
        else:
            # No source specified - search all sources
            uploaded_files = file_manager.list_files(UPLOADED_FILE_PATH)
            target_excel_csv_files = [f for f in uploaded_files if is_excel_or_csv_file(f)]
            logger.info("✅ NO SOURCE FILTER - SEARCHING ALL SOURCES")
            logger.info(f"✅ Document search: ENABLED, Excel/CSV search: ENABLED")
        
        # Search documents using Pinecone/BM25
        document_result = None
        document_error = None
        if search_documents:
            logger.info(f"🔍 EXECUTING DOCUMENT SEARCH for query: {search_query.query}")
            try:
                if search_query.debug:
                    from hybrid_search import search_with_debug_info
                    document_result = search_with_debug_info(search_query.query, search_query.source_document)
                else:
                    document_result = execure_hybrid_chain(search_query.query, search_query.source_document)
                logger.info(f"✅ DOCUMENT SEARCH COMPLETED")
            except Exception as e:
                document_error = str(e)
                logger.warning(f"❌ Document search failed: {document_error}")
        else:
            logger.info(f"⏭️  SKIPPING DOCUMENT SEARCH (targeting Excel/CSV file)")
        
        # Search Excel/CSV files
        excel_results = []
        excel_errors = []
        if search_excel_csv:
            logger.info(f"📊 EXECUTING PANDAS AGENT SEARCH for query: {search_query.query}")
            try:
                logger.info(f"📊 Searching {len(target_excel_csv_files)} Excel/CSV files: {target_excel_csv_files}")
                
                # Search each target Excel/CSV file
                for filename in target_excel_csv_files:
                    try:
                        logger.info(f"📊 Processing file: {filename}")
                        file_path = file_manager.get_file_path(UPLOADED_FILE_PATH, filename)
                        with create_excel_agent(file_path) as agent:
                            answer = agent.query(search_query.query)
                            data_summary = agent.get_data_summary()
                            
                            excel_results.append({
                                "filename": filename,
                                "file_type": get_file_type(filename),
                                "answer": answer,
                                "data_summary": data_summary
                            })
                            logger.info(f"✅ Successfully searched Excel/CSV file: {filename}")
                            
                    except Exception as e:
                        error_msg = f"Error searching {filename}: {str(e)}"
                        excel_errors.append(error_msg)
                        logger.warning(f"❌ {error_msg}")
                
                logger.info(f"✅ PANDAS AGENT SEARCH COMPLETED with {len(excel_results)} results")
            
            except Exception as e:
                excel_errors.append(f"Error accessing Excel/CSV files: {str(e)}")
                logger.warning(f"❌ Excel/CSV search failed: {str(e)}")
        else:
            logger.info(f"⏭️  SKIPPING EXCEL/CSV SEARCH (targeting document file)")
        
        # If no source document is selected, perform intelligent result comparison
        if not search_query.source_document:
            logger.info("🤖 No source filter - performing intelligent result comparison and reranking")
            
            # Compare and rerank results
            comparison_result = compare_and_rerank_results(
                search_query.query, 
                document_result, 
                excel_results
            )
            
            # Create enhanced response with best result
            result = {
                "query": search_query.query,
                "source_filter": search_query.source_document,
                "best_result": {
                    "answer": comparison_result["best_result"],
                    "source": comparison_result["source"],
                    "explanation": comparison_result["explanation"],
                    "comparison_performed": comparison_result["comparison_performed"]
                },
                "document_search": {
                    "description": "Search results from Pinecone/BM25 (includes parsed content from document files)",
                    "success": document_result is not None,
                    "result": document_result if document_result else None,
                    "error": document_error,
                    "searched": search_documents
                },
                "pandas_agent_search": {
                    "description": "DataFrame-specific search results from Excel/CSV files using pandas agent",
                    "files_searched": len(target_excel_csv_files) if search_excel_csv else 0,
                    "results": excel_results,
                    "errors": excel_errors,
                    "searched": search_excel_csv
                },
                "summary": {
                    "total_sources": (1 if document_result else 0) + len(excel_results),
                    "has_document_results": document_result is not None,
                    "has_pandas_results": len(excel_results) > 0,
                    "search_successful": comparison_result["source"] != "none",
                    "search_strategy": "intelligent_reranking",
                    "ai_choice": comparison_result.get("ai_choice", "none"),
                    "search_methods": {
                        "document_search": "Pinecone/BM25 hybrid search on parsed text content" if search_documents else "Skipped (not targeting documents)",
                        "pandas_search": "LangChain pandas agent for DataFrame operations" if search_excel_csv else "Skipped (not targeting Excel/CSV)",
                        "result_comparison": "AI-powered result comparison and reranking"
                    }
                }
            }
            
            if search_query.debug:
                result["debug_info"] = {
                    "document_debug": document_result.get("debug") if isinstance(document_result, dict) else None,
                    "excel_files_found": target_excel_csv_files,
                    "comparison_details": comparison_result,
                    "search_strategy": {
                        "search_documents": search_documents,
                        "search_excel_csv": search_excel_csv,
                        "target_files": target_excel_csv_files,
                        "comparison_performed": True
                    }
                }
        else:
            # Targeted search (existing behavior)
            filter_description = f" (filtered by: {search_query.source_document})"
            result = {
                "query": search_query.query,
                "source_filter": search_query.source_document,
                "document_search": {
                    "description": f"Search results from Pinecone/BM25 (includes parsed content from document files){filter_description}",
                    "success": document_result is not None,
                    "result": document_result if document_result else None,
                    "error": document_error,
                    "searched": search_documents
                },
                "pandas_agent_search": {
                    "description": "DataFrame-specific search results from Excel/CSV files using pandas agent",
                    "files_searched": len(target_excel_csv_files) if search_excel_csv else 0,
                    "results": excel_results,
                    "errors": excel_errors,
                    "searched": search_excel_csv
                },
                "summary": {
                    "total_sources": (1 if document_result else 0) + len(excel_results),
                    "has_document_results": document_result is not None,
                    "has_pandas_results": len(excel_results) > 0,
                    "search_successful": document_result is not None or len(excel_results) > 0,
                    "search_strategy": "targeted",
                    "search_methods": {
                        "document_search": "Pinecone/BM25 hybrid search on parsed text content" if search_documents else "Skipped (not targeting documents)",
                        "pandas_search": "LangChain pandas agent for DataFrame operations" if search_excel_csv else "Skipped (not targeting Excel/CSV)"
                    }
                }
            }
            
            if search_query.debug:
                result["debug_info"] = {
                    "document_debug": document_result.get("debug") if isinstance(document_result, dict) else None,
                    "excel_files_found": target_excel_csv_files,
                    "search_strategy": {
                        "search_documents": search_documents,
                        "search_excel_csv": search_excel_csv,
                        "target_files": target_excel_csv_files
                    }
                }
        
        search_type = "Intelligent reranked" if not search_query.source_document else "Targeted"
        logger.info(f"{search_type} search completed. Document results: {document_result is not None}, Excel results: {len(excel_results)}")
        return result
        
    except Exception as e:
        logger.error(f"Error during comprehensive search: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to perform comprehensive search: {str(e)}"}
        )


@app.post(
    "/querypandas/",
    tags=["Search & Query"],
    summary="Direct Excel/CSV data analysis with AI",
    description="""
    📊 **Natural language queries on Excel and CSV files using AI-powered pandas agent**
    
    This endpoint provides direct access to spreadsheet data analysis without requiring document indexing.
    Perfect for immediate data exploration, calculations, and statistical analysis.
    
    ## 🎯 **Key Features**
    
    **Natural Language Processing:**
    - Ask questions in plain English about your data
    - Automatic code generation and execution
    - Smart interpretation of column names and data types
    
    **Advanced Data Analysis:**
    - Statistical calculations (mean, median, sum, count, etc.)
    - Data filtering and grouping operations
    - Cross-tabulation and pivot table operations
    - Data visualization insights
    
    **Multi-file Support:**
    - Automatically processes ALL Excel/CSV files in uploaded_files
    - Returns results from each file separately
    - Compares data across multiple files when relevant
    
    ## 📋 **Supported Operations**
    
    ### Statistical Analysis:
    - `"What is the average salary by department?"`
    - `"Calculate the total revenue for each quarter"`
    - `"Show the distribution of customer ages"`
    
    ### Data Exploration:
    - `"What columns are in this dataset?"`
    - `"How many rows of data do we have?"`
    - `"Show me the first 10 records"`
    - `"What are the unique values in the category column?"`
    
    ### Filtering & Grouping:
    - `"Show all employees with salary > 50000"`
    - `"List customers from California"`
    - `"Group sales by region and month"`
    
    ### Comparisons:
    - `"Which department has the highest average salary?"`
    - `"Compare Q1 vs Q4 performance"`
    - `"Find the top 5 customers by revenue"`
    
    ## 🔧 **Debug Mode**
    
    Enable `debug: true` to see:
    - Dataset summary (rows, columns, data types)
    - Generated pandas code
    - Execution steps and intermediate results
    - Performance metrics
    
    ## ⚡ **Performance**
    - Small files (<1MB): 1-3 seconds
    - Medium files (1-10MB): 3-8 seconds
    - Large files (10-50MB): 8-15 seconds
    - Processes multiple files in parallel
    
    ## 📤 **No Upload Required**
    Works directly with uploaded Excel/CSV files - no parsing or ingestion needed!
    """,
    responses={
        200: {
            "description": "Data analysis completed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "statistical_analysis": {
                            "summary": "Statistical calculation across Excel file",
                            "value": {
                                "results": [
                                    {
                                        "filename": "employee_data.xlsx",
                                        "file_type": "excel",
                                        "answer": "Average salary by department:\n- Engineering: $95,250\n- Sales: $78,400\n- Marketing: $72,100\n- HR: $65,800\n\nOverall average salary: $77,888",
                                        "data_summary": {
                                            "total_rows": 150,
                                            "total_columns": 8,
                                            "column_info": {
                                                "Name": "object",
                                                "Department": "object", 
                                                "Salary": "int64",
                                                "Age": "int64"
                                            }
                                        }
                                    }
                                ],
                                "summary": {
                                    "total_files_processed": 1,
                                    "files_with_results": 1,
                                    "files_with_errors": 0,
                                    "execution_time": "2.3s"
                                }
                            }
                        },
                        "data_exploration": {
                            "summary": "Dataset structure exploration",
                            "value": {
                                "results": [
                                    {
                                        "filename": "sales_data.csv",
                                        "file_type": "csv",
                                        "answer": "Dataset Overview:\n- Total rows: 1,250\n- Total columns: 12\n- Date range: 2023-01-01 to 2024-12-31\n\nColumns:\n1. Order_ID (unique identifier)\n2. Customer_Name (text)\n3. Product_Category (text)\n4. Revenue (numeric)\n5. Quantity (numeric)\n6. Order_Date (datetime)\n...",
                                        "data_summary": {
                                            "total_rows": 1250,
                                            "total_columns": 12,
                                            "missing_values": {
                                                "Customer_Phone": 45,
                                                "Notes": 120
                                            }
                                        }
                                    }
                                ],
                                "summary": {
                                    "total_files_processed": 1,
                                    "files_with_results": 1,
                                    "files_with_errors": 0,
                                    "execution_time": "1.8s"
                                }
                            }
                        },
                        "multi_file_analysis": {
                            "summary": "Analysis across multiple files",
                            "value": {
                                "results": [
                                    {
                                        "filename": "q1_sales.xlsx",
                                        "file_type": "excel",
                                        "answer": "Q1 2024 Total Revenue: $1,250,000 (125 transactions)"
                                    },
                                    {
                                        "filename": "q2_sales.xlsx", 
                                        "file_type": "excel",
                                        "answer": "Q2 2024 Total Revenue: $1,430,000 (142 transactions)"
                                    }
                                ],
                                "summary": {
                                    "total_files_processed": 2,
                                    "files_with_results": 2,
                                    "files_with_errors": 0,
                                    "execution_time": "3.7s"
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "No Excel/CSV files found",
            "content": {
                "application/json": {
                    "example": {
                        "error": "No Excel or CSV files found. Please upload Excel/CSV files first."
                    }
                }
            }
        },
        500: {
            "description": "Data analysis error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Error analyzing employee_data.xlsx: column 'Salary' not found"
                    }
                }
            }
        }
    }
)
async def query_pandas_agent(search_query: SearchQuery):
    """
    Analyze Excel/CSV files using natural language queries with AI-powered pandas agent.
    Processes all uploaded Excel/CSV files and returns analysis results from each.
    
    Args:
        search_query: SearchQuery containing the natural language question about the data
        
    Returns:
        Dict: Analysis results from each Excel/CSV file with data summaries and execution metadata
    """
    try:
        logger.info(f"Performing pandas agent query: {search_query.query}")
        
        # Get all uploaded Excel/CSV files
        uploaded_files = file_manager.list_files(UPLOADED_FILE_PATH)
        excel_csv_files = [f for f in uploaded_files if is_excel_or_csv_file(f)]
        
        if not excel_csv_files:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "No Excel or CSV files found. Please upload Excel/CSV files first."}
            )
        
        logger.info(f"Found {len(excel_csv_files)} Excel/CSV files for pandas queries: {excel_csv_files}")
        
        # Query each Excel/CSV file with pandas agent
        results = []
        errors = []
        
        for filename in excel_csv_files:
            try:
                file_path = file_manager.get_file_path(UPLOADED_FILE_PATH, filename)
                with create_excel_agent(file_path) as agent:
                    answer = agent.query(search_query.query)
                    data_summary = agent.get_data_summary()
                    
                    results.append({
                        "filename": filename,
                        "file_type": get_file_type(filename),
                        "answer": answer,
                        "data_summary": data_summary if search_query.debug else {
                            "total_rows": data_summary.get("total_rows"),
                            "total_columns": data_summary.get("total_columns"),
                            "columns": data_summary.get("columns")
                        }
                    })
                    logger.info(f"Successfully queried pandas agent for: {filename}")
                    
            except Exception as e:
                error_msg = f"Error querying {filename}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # Compile results
        response = {
            "query": search_query.query,
            "files_queried": len(excel_csv_files),
            "successful_queries": len(results),
            "results": results,
            "errors": errors,
            "summary": {
                "query_successful": len(results) > 0,
                "files_with_results": len(results),
                "files_with_errors": len(errors)
            }
        }
        
        if search_query.debug:
            response["debug_info"] = {
                "available_files": excel_csv_files,
                "query_method": "pandas_agent_direct"
            }
        
        logger.info(f"Pandas query completed. Successful: {len(results)}, Errors: {len(errors)}")
        return response
        
    except Exception as e:
        logger.error(f"Error during pandas query: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to perform pandas query: {str(e)}"}
        )



@app.get("/generatequestions/{filename}")
async def generate_questions_for_file(
    filename: str = Path(..., description="Name of the file to generate questions for"),
    number_of_questions: int = Query(10, description="Number of questions to generate", ge=1, le=50)
):
    """
    Generate questions from a file in the parsed_files directory.
    Questions are generated fresh each time without saving to disk.
    
    Args:
        filename: Name of the file to generate questions for (can be with or without extension)
        number_of_questions: Number of questions to generate (default: 10, max: 50)
        
    Returns:
        Generated questions and metadata
    """
    logger.info(f"Generating questions for file: {filename}")
    
    try:
        # Extract base filename without extension to ensure consistency
        # This handles both "Sample1.pdf" and "Sample1" as input
        base_filename = FilePath(filename).stem
        logger.info(f"Using base filename: {base_filename}")
        
        # Load content from parsed file
        if file_manager.file_exists(PARSED_FILE_PATH, f"{base_filename}.md"):
            logger.info(f"Loading parsed file for question generation: {base_filename}.md")
            text_content = file_manager.load_file(PARSED_FILE_PATH, f"{base_filename}.md")
        else:
            raise FileNotFoundError(f"No file found for {base_filename} in parsed_files")
        
        logger.info(f"Generating fresh {number_of_questions} questions for {base_filename}")
        questions_raw = generate_questions(text_content, number_of_questions)

        # Try to parse as JSON array first
        questions = []
        try:
            questions = json.loads(questions_raw)
            if not isinstance(questions, list):
                questions = []
        except Exception:
            # Fallback: parse as numbered lines
            import re
            for line in questions_raw.splitlines():
                match = re.match(r"^\s*\d+\.\s*(.+)$", line)
                if match:
                    questions.append(match.group(1).strip())
            # Fallback: if parsing fails, return the raw string as a single-item list
            if not questions and questions_raw.strip():
                questions = [questions_raw.strip()]

        metadata = {
            "file_name": base_filename,
            "source": "parsed_file",
            "number_of_questions": number_of_questions,
            "generated_fresh": True
        }
        logger.info(f"Questions generated successfully for {base_filename}")
        return {"questions": questions, "metadata": metadata}
        
    except FileNotFoundError as e:
        logger.error(f"File not found for question generation: {e}")
        # Use base_filename if it was extracted, otherwise use original filename
        display_filename = FilePath(filename).stem if filename else filename
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"File {display_filename} not found in parsed_files directory"}
        )
    except Exception as e:
        logger.error(f"Error during question generation for {filename}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to generate questions for file: {str(e)}"}
        )


@app.get("/generatefaq/{filename}")
async def generate_faq_for_file(
    filename: str = Path(..., description="Name of the file to generate FAQ for"),
    number_of_faqs: int = Query(5, description="Number of FAQ items to generate", ge=1, le=20)
):
    """
    Generate FAQ (Frequently Asked Questions) from a file in the parsed_files directory.
    FAQ items are generated fresh each time without saving to disk.
    
    Args:
        filename: Name of the file to generate FAQ for (can be with or without extension)
        number_of_faqs: Number of FAQ items to generate (default: 5, max: 20)
        
    Returns:
        Generated FAQ items and metadata
    """
    logger.info(f"Generating FAQ for file: {filename}")
    
    try:
        # Extract base filename without extension to ensure consistency
        # This handles both "Sample1.pdf" and "Sample1" as input
        base_filename = FilePath(filename).stem
        logger.info(f"Using base filename: {base_filename}")
        
        # Load content from parsed file
        if file_manager.file_exists(PARSED_FILE_PATH, f"{base_filename}.md"):
            logger.info(f"Loading parsed file for FAQ generation: {base_filename}.md")
            text_content = file_manager.load_file(PARSED_FILE_PATH, f"{base_filename}.md")
        else:
            raise FileNotFoundError(f"No file found for {base_filename} in parsed_files")
        
        logger.info(f"Generating fresh {number_of_faqs} FAQ items for {base_filename}")
        faq_content = generate_faq(text_content, number_of_faqs)
        
        # Parse the FAQ content into structured format
        import re
        faq_items = []
        
        # Split by question markers and process each FAQ item
        parts = re.split(r'\*\*Q\d+:', faq_content)
        for i, part in enumerate(parts[1:], 1):  # Skip the first empty part
            if part.strip():
                # Extract question and answer
                lines = part.strip().split('\n')
                if lines:
                    question = lines[0].replace('**', '').strip()
                    # Find the answer part (starts with A{number}:)
                    answer_start = None
                    for j, line in enumerate(lines[1:], 1):
                        if re.match(r'^A\d+:', line):
                            answer_start = j
                            break
                    
                    if answer_start is not None:
                        answer = lines[answer_start].replace(f'A{i}:', '').strip()
                        # Join any additional answer lines
                        for k in range(answer_start + 1, len(lines)):
                            if not re.match(r'^\*\*Q\d+:', lines[k]):
                                answer += ' ' + lines[k].strip()
                            else:
                                break
                        
                        faq_items.append({
                            "question": question,
                            "answer": answer
                        })
        
        # Fallback: if parsing fails, return the raw content
        if not faq_items and faq_content.strip():
            faq_items = [{"question": "Generated FAQ", "answer": faq_content.strip()}]
        
        metadata = {
            "file_name": base_filename,
            "source": "parsed_file",
            "number_of_faqs": number_of_faqs,
            "generated_fresh": True
        }
            
        logger.info(f"FAQ generated successfully for {base_filename}")
        return {"faq_items": faq_items, "metadata": metadata}
        
    except FileNotFoundError as e:
        logger.error(f"File not found for FAQ generation: {e}")
        # Use base_filename if it was extracted, otherwise use original filename
        display_filename = FilePath(filename).stem if filename else filename
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"File {display_filename} not found in parsed_files directory"}
        )
    except Exception as e:
        logger.error(f"Error during FAQ generation for {filename}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to generate FAQ for file: {str(e)}"}
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An unexpected error occurred"}
    )
