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
    description="API for uploading, parsing, editing, and summarizing documents",
    version="1.0.0",
    lifespan=lifespan
)

# Define data models
class ContentUpdate(BaseModel):
    """Model for content update requests"""
    content: str = Field(..., description="The edited content to save")

class ErrorResponse(BaseModel):
    """Model for error responses"""
    error: str = Field(..., description="Error message")

class SuccessResponse(BaseModel):
    """Model for success responses"""
    status: str = Field("success", description="Status of the operation")
    message: str = Field(..., description="Success message")

class FileResponse(BaseModel):
    """Model for file-related responses"""
    filename: str = Field(..., description="Name of the file")
    file_path: str = Field(..., description="Path where the file is stored")
    file_type: str = Field(default="document", description="Type of file (excel, csv, or document)")
    is_excel_csv: bool = Field(default=False, description="Whether the file is Excel or CSV")
    message: str = Field(default="File uploaded successfully", description="Upload message")

class FilesListResponse(BaseModel):
    """Model for file listing responses"""
    files: List[str] = Field(..., description="List of file names")

# Define data models for search
class SearchQuery(BaseModel):
    """Model for search queries"""
    query: str = Field(..., description="The search query")
    debug: bool = Field(False, description="Include debug information in response")
    source_document: Optional[str] = Field(None, description="Optional source document to filter search results")



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
@app.post("/uploadfile/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the server.
    For Excel/CSV files, they will be handled by the Excel agent instead of parsing to vector database.
    
    Args:
        file: The file to upload
        
    Returns:
        Information about the uploaded file
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

@app.get("/listfiles/{directory}", response_model=FilesListResponse)
async def list_files(directory: str = Path(..., description="Directory to list files from")):
    """
    List all files in the specified directory.
    
    Args:
        directory: The directory to list files from
        
    Returns:
        List of files in the directory
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

@app.get("/parsefile/{filename}")
async def parse_uploaded_file(filename: str = Path(..., description="Name of the file to parse")):
    """
    Parse an uploaded file into markdown format using LlamaParse.
    Works for all file types including PDFs, Excel, and CSV files.
    
    Args:
        filename: Name of the file to parse
        
    Returns:
        Parsed text content and metadata
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

# Get available source documents
@app.get("/sourcedocuments/", response_model=FilesListResponse)
async def get_source_documents():
    """
    Get a list of all available source documents in the Pinecone index.
    These can be used to filter hybrid search results.
    
    Returns:
        List of unique source document names available for search filtering
    """
    try:
        logger.info("Getting available source documents from Pinecone")
        from pinecone_util import get_available_source_documents
        
        source_documents = get_available_source_documents()
        
        logger.info(f"Found {len(source_documents)} source documents")
        return {"files": source_documents}
        
    except Exception as e:
        logger.error(f"Error getting source documents: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get source documents: {str(e)}"}
        )

# Hybrid search
@app.post("/hybridsearch/")
async def hybrid_search(search_query: SearchQuery):
    """
    Perform a comprehensive search across all data sources:
    1. Document search (Pinecone/BM25) - includes parsed content from all file types
    2. Excel/CSV pandas agent search - for DataFrame-specific queries
    Provides unified results from both search methods.
    """
    try:
        logger.info(f"Performing comprehensive search for: {search_query.query}")
        
        # Search documents using Pinecone/BM25
        document_result = None
        document_error = None
        try:
            if search_query.debug:
                from hybrid_search import search_with_debug_info
                document_result = search_with_debug_info(search_query.query, search_query.source_document)
            else:
                document_result = execure_hybrid_chain(search_query.query, search_query.source_document)
        except Exception as e:
            document_error = str(e)
            logger.warning(f"Document search failed: {document_error}")
        
        # Search Excel/CSV files
        excel_results = []
        excel_errors = []
        
        try:
            # Get all uploaded files
            uploaded_files = file_manager.list_files(UPLOADED_FILE_PATH)
            excel_csv_files = [f for f in uploaded_files if is_excel_or_csv_file(f)]
            
            logger.info(f"Found {len(excel_csv_files)} Excel/CSV files to search: {excel_csv_files}")
            
            # Search each Excel/CSV file
            for filename in excel_csv_files:
                try:
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
                        logger.info(f"Successfully searched Excel/CSV file: {filename}")
                        
                except Exception as e:
                    error_msg = f"Error searching {filename}: {str(e)}"
                    excel_errors.append(error_msg)
                    logger.warning(error_msg)
        
        except Exception as e:
            excel_errors.append(f"Error accessing Excel/CSV files: {str(e)}")
            logger.warning(f"Excel/CSV search failed: {str(e)}")
        
        # Compile comprehensive results
        filter_description = f" (filtered by: {search_query.source_document})" if search_query.source_document else ""
        result = {
            "query": search_query.query,
            "source_filter": search_query.source_document,
            "document_search": {
                "description": f"Search results from Pinecone/BM25 (includes parsed content from all file types){filter_description}",
                "success": document_result is not None,
                "result": document_result if document_result else None,
                "error": document_error
            },
            "pandas_agent_search": {
                "description": "DataFrame-specific search results from Excel/CSV files using pandas agent",
                "files_searched": len(excel_csv_files) if 'excel_csv_files' in locals() else 0,
                "results": excel_results,
                "errors": excel_errors
            },
            "summary": {
                "total_sources": (1 if document_result else 0) + len(excel_results),
                "has_document_results": document_result is not None,
                "has_pandas_results": len(excel_results) > 0,
                "search_successful": document_result is not None or len(excel_results) > 0,
                "search_methods": {
                    "document_search": "Pinecone/BM25 hybrid search on parsed text content",
                    "pandas_search": "LangChain pandas agent for DataFrame operations"
                }
            }
        }
        
        if search_query.debug:
            result["debug_info"] = {
                "document_debug": document_result.get("debug") if isinstance(document_result, dict) else None,
                "excel_files_found": excel_csv_files if 'excel_csv_files' in locals() else []
            }
        
        logger.info(f"Comprehensive search completed. Document results: {document_result is not None}, Excel results: {len(excel_results)}")
        return result
        
    except Exception as e:
        logger.error(f"Error during comprehensive search: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to perform comprehensive search: {str(e)}"}
        )


@app.post("/querypandas/")
async def query_pandas_agent(search_query: SearchQuery):
    """
    Query Excel/CSV files directly using pandas agent for DataFrame operations.
    This endpoint provides direct access to pandas-based data analysis capabilities.
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
