"""
Refactored Document Processing API - Clean, maintainable FastAPI application.

This module provides a comprehensive document processing pipeline with AI-powered search capabilities.
All business logic, models, and utilities have been extracted to separate modules for maintainability.
"""

# Apply nest_asyncio early to support nested event loops
import nest_asyncio
try:
    nest_asyncio.apply()
except (RuntimeError, ValueError) as e:
    print(f"Skipping nest_asyncio patch: {e}")

# Standard library imports
import os
import json
import re
from pathlib import Path as FilePath
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

# FastAPI imports
from fastapi import FastAPI, UploadFile, File, Body, HTTPException, status, Path, Query
from fastapi.responses import JSONResponse

# Local imports - Configuration
from config import (
    UPLOADED_FILE_PATH, 
    PARSED_FILE_PATH, 
    API_TITLE,
    API_VERSION,
    API_CONTACT,
    API_LICENSE,
    TAGS_METADATA,
    setup_logging
)

# Local imports - Models
from models import (
    ContentUpdate,
    SearchQuery,
    ErrorResponse,
    SuccessResponse,
    FileResponse,
    FilesListResponse
)

# Local imports - Utilities
from utils import (
    get_file_path,
    is_excel_or_csv_file,
    get_file_type,
    ensure_directories_exist,
    compare_and_rerank_results
)

# Local imports - API Documentation
from api_docs import (
    API_DESCRIPTION,
    HYBRID_SEARCH_DESCRIPTION,
    PANDAS_QUERY_DESCRIPTION
)

# External dependencies
from file_util_enhanced import get_file_manager, list_files as list_directory
from file_parser import parse_file_with_llama_parse
from doc_summarizer import summarize_text_content
from question_gen import generate_questions
from faq_gen import generate_faq
from excel_agent import create_excel_agent
from ingest_docs import ingest_documents_to_pinecone_and_bm25
from hybrid_search import execure_hybrid_chain

# Initialize logging and file manager
logger = setup_logging()
file_manager = get_file_manager()


def is_meaningful_document_result(document_result) -> tuple[bool, str]:
    """
    Determine if a document search result contains meaningful information.
    
    Args:
        document_result: The result from document search (could be string or dict)
        
    Returns:
        Tuple of (is_meaningful, reason) for debugging
    """
    if not document_result:
        return False, "No result returned"
    
    # Handle case where document_result is a dictionary
    if isinstance(document_result, dict):
        # Extract the answer from the dictionary if it exists
        if 'answer' in document_result:
            document_result = document_result['answer']
        elif 'result' in document_result:
            document_result = document_result['result']
        else:
            # Try to find any string value in the dictionary
            for key, value in document_result.items():
                if isinstance(value, str):
                    document_result = value
                    break
            else:
                return False, "Result is dictionary but no answer/result field found"
    
    # Ensure it's a string
    if not isinstance(document_result, str):
        return False, f"Result is not a string (type: {type(document_result)})"
    
    if not document_result.strip():
        return False, "Empty result"
    
    # Check for common "no results" indicators
    no_result_phrases = [
        "no relevant", "not found", "no information", "no results", 
        "unable to find", "no documents", "no match", "not available",
        "i don't have", "i cannot find", "could not find", "couldn't find",
        "no data", "insufficient information", "no content found", 
        "no matches found", "cannot locate", "not locate", "nothing found",
        "no such", "does not contain", "doesn't contain", "do not contain",
        "don't contain", "no mention", "not mentioned", "no details", 
        "no specific", "not specify", "does not provide", "not provide",
        "not include", "does not include", "not mentioned", "not available",
        "does not contain any information", "does not contain any", "no information about"
    ]
    
    result_lower = document_result.lower()
    for phrase in no_result_phrases:
        if phrase in result_lower:
            return False, f"Contains no-result phrase: '{phrase}'"
    
    # Ensure result has substantial content (more than just a short phrase)
    # But allow concise answers that are still meaningful
    if len(document_result.strip()) <= 15:
        return False, f"Result too short ({len(document_result.strip())} chars): '{document_result[:50]}'"
    
    return True, "Result appears meaningful"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup: initialize resources
    ensure_directories_exist()
    logger.info("Application started, directories initialized")
    yield
    # Shutdown: cleanup (if needed)
    logger.info("Application shutting down")


# Initialize FastAPI app with configuration
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    contact=API_CONTACT,
    license_info=API_LICENSE,
    tags_metadata=TAGS_METADATA
)


# ============================================================================
# File Management Endpoints
# ============================================================================

@app.post(
    "/uploadfile/", 
    response_model=FileResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["File Management"],
    summary="Upload a file to the server",
    description="Upload files for processing and analysis. Supports PDF, DOCX, TXT, XLSX, XLS, CSV formats with automatic file type detection."
)
async def upload_file(file: UploadFile = File(..., description="File to upload - supports PDF, DOCX, TXT, XLSX, XLS, CSV formats")):
    """Upload a file to the server with automatic file type detection."""
    logger.info(f"Received upload request for file: {file.filename}")
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename"
        )
    
    try:
        # Save the uploaded file
        content = await file.read()
        saved_path = file_manager.save_binary_file(UPLOADED_FILE_PATH, file.filename, content)
        
        # Detect file type
        is_excel_csv = is_excel_or_csv_file(file.filename)
        file_type = get_file_type(file.filename)
        
        logger.info(f"File saved to {saved_path}")
        
        if is_excel_csv:
            logger.info(f"Detected {file_type} file: {file.filename}")
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
    description="List all files in the specified directory (uploaded_files, parsed_files, or bm25_indexes)."
)
async def list_files(directory: str = Path(..., description="Directory name to list files from")):
    """List all files in the specified directory on the server."""
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
    """Delete a file from the specified directory."""
    logger.info(f"Deleting file: {directory}/{filename}")
    
    # Validate directory
    valid_directories = ["uploaded_files", "parsed_files", "bm25_indexes"]
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


# ============================================================================
# Document Processing Endpoints
# ============================================================================

@app.get(
    "/parsefile/{filename}",
    tags=["Document Processing"],
    summary="Parse uploaded file to markdown format",
    description="Convert uploaded files to structured markdown format using LlamaParse. Supports all file types with advanced document understanding."
)
async def parse_uploaded_file(
    filename: str = Path(..., description="Name of the uploaded file to parse (include file extension)")
):
    """Parse an uploaded file into markdown format using LlamaParse AI."""
    logger.info(f"Parsing file: {filename}")
    
    try:
        # Check if the parsed file already exists
        base_filename = FilePath(filename).stem
        
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
    """Save edited content to the parsed files directory."""
    logger.info(f"Saving content for file: {filename}")
    
    try:
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
    """Save edited content and ingest the document to Pinecone and BM25 index."""
    logger.info(f"Saving content and ingesting for file: {filename}")
    
    try:
        base_filename = FilePath(filename).stem
        logger.info(f"Using base filename: {base_filename}")
        
        # Step 1: Save the content
        logger.info(f"Step 1: Saving content for {base_filename}")
        saved_path = file_manager.save_file(PARSED_FILE_PATH, f"{base_filename}.md", content_update.content)
        logger.info(f"Content saved to {saved_path}")
        
        # Step 2: Ingest the document to Pinecone and BM25
        logger.info(f"Step 2: Ingesting documents for {base_filename}")
        ingestion_result = ingest_documents_to_pinecone_and_bm25(base_filename)
        logger.info(f"Ingestion completed for {base_filename}")
        
        return {
            "status": "success", 
            "message": ingestion_result.get("message", f"Content for {base_filename} saved and processed successfully.")
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


@app.post("/ingestdocuments/{filename}")
async def ingest_documents(filename: str = Path(..., description="Name of the file to ingest")):
    """Ingest documents to Pinecone and BM25 index."""
    try:
        base_filename = FilePath(filename).stem
        logger.info(f"Ingesting documents for base filename: {base_filename}")
        
        ingestion_result = ingest_documents_to_pinecone_and_bm25(base_filename)
        return {"message": ingestion_result.get("message", f"Documents successfully processed for {base_filename}")}
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


# ============================================================================
# Search & Query Endpoints  
# ============================================================================

@app.post(
    "/hybridsearch/",
    tags=["Search & Query"],
    summary="Intelligent hybrid search across documents and data",
    description=HYBRID_SEARCH_DESCRIPTION
)
async def hybrid_search(search_query: SearchQuery):
    """Perform intelligent hybrid search with AI-powered result ranking."""
    try:
        logger.info(f"Performing targeted search for: {search_query.query}")
        
        # Get all uploaded files
        uploaded_files = file_manager.list_files(UPLOADED_FILE_PATH)
        
        # Determine search strategy
        search_strategy_info = determine_search_strategy(search_query.source_document, uploaded_files)
        search_documents = search_strategy_info["search_documents"]
        search_excel_csv = search_strategy_info["search_excel_csv"]
        target_excel_csv_files = search_strategy_info["target_excel_csv_files"]
        
        # Execute document search
        document_result, document_error = execute_document_search(search_query.query, search_query.source_document, search_query.debug)
        
        # Determine search behavior based on strategy
        if search_strategy_info["strategy"] == "sequential":
            # Sequential search: check if document results are meaningful, fallback to pandas if not
            has_meaningful_document_results, reason = is_meaningful_document_result(document_result)
            
            if not has_meaningful_document_results:
                search_excel_csv = True
                logger.info(f"📊 ACTIVATING PANDAS AGENT SEARCH as fallback - Reason: {reason}")
                if document_result:
                    logger.info(f"📊 Document search returned: '{document_result[:200]}{'...' if len(document_result) > 200 else ''}'")
            else:
                logger.info(f"⏭️  SKIPPING PANDAS AGENT SEARCH - Document search found meaningful results: {reason}")
        else:
            # Targeted search: also check if we should search Excel/CSV files as fallback
            has_meaningful_document_results, reason = is_meaningful_document_result(document_result)
            
            if not has_meaningful_document_results and target_excel_csv_files:
                search_excel_csv = True
                logger.info(f"📊 ACTIVATING PANDAS AGENT SEARCH as fallback for targeted search - Reason: {reason}")
                if document_result:
                    logger.info(f"📊 Document search returned: '{document_result[:200]}{'...' if len(document_result) > 200 else ''}'")
            else:
                logger.info(f"⏭️  SKIPPING PANDAS AGENT SEARCH - Document search found meaningful results or no Excel/CSV files available: {reason}")
        
        # Execute Excel/CSV search if needed
        excel_results, excel_errors = [], []
        if search_excel_csv:
            excel_results, excel_errors = execute_excel_csv_search(search_query.query, target_excel_csv_files)
        
        # Build response based on search strategy
        if search_strategy_info["strategy"] == "sequential":
            # Sequential search strategy response - use same meaningful results logic
            response = build_sequential_response(search_query.query, search_query.source_document, document_result, 
                                                document_error, excel_results, excel_errors, 
                                                target_excel_csv_files, search_query.debug)
        else:
            # Targeted search response - maintain original API structure
            response = build_targeted_response(search_query.query, search_query.source_document, document_result, 
                                              document_error, excel_results, excel_errors, 
                                              search_documents, search_excel_csv, search_query.debug)
        
        search_type = "Sequential smart" if search_strategy_info["strategy"] == "sequential" else "Targeted"
        logger.info(f"{search_type} search completed. Document results: {document_result is not None}, Excel results: {len(excel_results)}")
        return response
        
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
    description=PANDAS_QUERY_DESCRIPTION
)
async def query_pandas_agent(search_query: SearchQuery):
    """Analyze Excel/CSV files using natural language queries with AI-powered pandas agent."""
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


@app.get("/sourcedocuments/", response_model=FilesListResponse)
async def get_source_documents():
    """Get a list of all available source documents from parsed files and uploaded Excel/CSV files."""
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
        source_documents = []
        
        # Add parsed files (find original filenames with extensions)
        for parsed_file in parsed_files:
            if parsed_file.endswith('.md'):
                # Remove .md extension to get base name
                base_name = parsed_file[:-3]
                
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
        
        # Add Excel/CSV files that aren't already included
        for excel_csv_file in excel_csv_files:
            if excel_csv_file not in source_documents:
                source_documents.append(excel_csv_file)
        
        # Remove duplicates and sort
        source_documents = sorted(list(set(source_documents)))
        
        logger.info(f"Total source documents available: {len(source_documents)}")
        return {"files": source_documents}
        
    except Exception as e:
        logger.error(f"Error getting source documents: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to get source documents: {str(e)}"}
        )


# ============================================================================
# AI Content Generation Endpoints
# ============================================================================

@app.get("/summarizecontent/{filename}")
async def summarize_content(
    filename: str = Path(..., description="Name of the file to summarize")
):
    """Parse a file from the parsed_files directory and return its summary."""
    logger.info(f"Summarizing file: {filename}")
    
    try:
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


@app.get("/generatequestions/{filename}")
async def generate_questions_for_file(
    filename: str = Path(..., description="Name of the file to generate questions for"),
    number_of_questions: int = Query(10, description="Number of questions to generate", ge=1, le=50)
):
    """Generate questions from a file in the parsed_files directory."""
    logger.info(f"Generating questions for file: {filename}")
    
    try:
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
    """Generate FAQ (Frequently Asked Questions) from a file in the parsed_files directory."""
    logger.info(f"Generating FAQ for file: {filename}")
    
    try:
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


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with standardized error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with logging and standardized error responses."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An unexpected error occurred"}
    ) 

# Add these helper functions before the hybrid_search function

def format_source_filter_display(source_document: str) -> str:
    """
    Format the source document filter for display in responses.
    
    Args:
        source_document: The source document filter value
        
    Returns:
        Formatted display string
    """
    if not source_document or source_document.lower() in ["all", "none", ""]:
        return "all documents"
    return source_document


def determine_search_strategy(source_document: str, uploaded_files: list) -> dict:
    """
    Determine the search strategy based on source document and available files.
    
    Args:
        source_document: Optional source document to filter by (use "all" to search all documents)
        uploaded_files: List of uploaded files
        
    Returns:
        Dictionary with search strategy information
    """
    if source_document and source_document.lower() not in ["all", "none", ""]:
        # Check if source document is Excel/CSV
        is_excel_csv = is_excel_or_csv_file(source_document)
        
        if is_excel_csv:
            return {
                "search_documents": False,
                "search_excel_csv": True,
                "target_excel_csv_files": [source_document],
                "strategy": "targeted_excel_csv",
                "description": f"Targeting Excel/CSV file: {source_document}"
            }
        else:
            return {
                "search_documents": True,
                "search_excel_csv": False,
                "target_excel_csv_files": [],
                "strategy": "targeted_document",
                "description": f"Targeting document file: {source_document}"
            }
    else:
        # No source specified or "all" specified - sequential search strategy
        target_excel_csv_files = [f for f in uploaded_files if is_excel_or_csv_file(f)]
        return {
            "search_documents": True,
            "search_excel_csv": False,  # Will be determined later based on document results
            "target_excel_csv_files": target_excel_csv_files,
            "strategy": "sequential",
            "description": "Sequential search strategy (all documents)"
        }

def execute_document_search(query: str, source_document: str, debug: bool) -> tuple:
    """
    Execute document search using hybrid search.
    
    Args:
        query: Search query
        source_document: Optional source document filter (use "all" to search all documents)
        debug: Whether to include debug information
        
    Returns:
        Tuple of (result, error)
    """
    try:
        logger.info(f"🔍 EXECUTING DOCUMENT SEARCH for query: {query}")
        
        # Convert "all" to None for the hybrid search function
        search_filter = None if (source_document and source_document.lower() in ["all", "none", ""]) else source_document
        
        if debug:
            from hybrid_search import search_with_debug_info
            result = search_with_debug_info(query, search_filter)
        else:
            result = execure_hybrid_chain(query, search_filter)
            
        logger.info("✅ DOCUMENT SEARCH COMPLETED")
        return result, None
        
    except Exception as e:
        error = str(e)
        logger.warning(f"❌ Document search failed: {error}")
        return None, error

def execute_excel_csv_search(query: str, target_files: list) -> tuple:
    """
    Execute Excel/CSV search using pandas agent.
    
    Args:
        query: Search query
        target_files: List of Excel/CSV files to search
        
    Returns:
        Tuple of (results, errors)
    """
    logger.info(f"📊 EXECUTING PANDAS AGENT SEARCH for query: {query}")
    logger.info(f"📊 Searching {len(target_files)} Excel/CSV files: {target_files}")
    
    results = []
    errors = []
    
    for filename in target_files:
        try:
            logger.info(f"📊 Processing file: {filename}")
            file_path = file_manager.get_file_path(UPLOADED_FILE_PATH, filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                errors.append(error_msg)
                logger.warning(f"❌ {error_msg}")
                continue
            
            logger.info(f"📊 File exists, creating pandas agent for: {file_path}")
            with create_excel_agent(file_path) as agent:
                logger.info(f"📊 Querying pandas agent for: {query}")
                answer = agent.query(query)
                data_summary = agent.get_data_summary()
                
                # Validate that we got a meaningful answer
                if answer and answer.strip():
                    logger.info(f"✅ Pandas agent returned answer: {len(answer)} characters")
                    logger.info(f"✅ Answer preview: {answer[:200]}...")
                else:
                    logger.warning(f"⚠️ Pandas agent returned empty answer for {filename}")
                    answer = "No specific data found for this query in this file."
                
                results.append({
                    "filename": filename,
                    "file_type": get_file_type(filename),
                    "answer": answer,
                    "data_summary": data_summary
                })
                logger.info(f"✅ Successfully searched Excel/CSV file: {filename}")
                
        except Exception as e:
            error_msg = f"Error searching {filename}: {str(e)}"
            errors.append(error_msg)
            logger.warning(f"❌ {error_msg}")
            # Add a fallback result even if there's an error
            results.append({
                "filename": filename,
                "file_type": get_file_type(filename),
                "answer": f"Error processing this file: {str(e)}",
                "data_summary": {"error": str(e)}
            })
    
    logger.info(f"✅ PANDAS AGENT SEARCH COMPLETED with {len(results)} results")
    if errors:
        logger.warning(f"⚠️ Pandas agent search completed with {len(errors)} errors: {errors}")
    
    return results, errors

def build_sequential_response(query: str, source_document: str, document_result: str, 
                           document_error: str, excel_results: list, excel_errors: list,
                           target_files: list, debug: bool) -> dict:
    """
    Build response for sequential search strategy.
    
    Args:
        query: Search query
        source_document: Source document filter
        document_result: Document search result
        document_error: Document search error
        excel_results: Excel/CSV search results
        excel_errors: Excel/CSV search errors
        target_files: Target Excel/CSV files
        debug: Whether to include debug information
        
    Returns:
        Response dictionary
    """
    # Evaluate document results
    has_hybrid_results, result_reason = is_meaningful_document_result(document_result)
    
    logger.info(f"🔍 Final result evaluation: has_meaningful_results={has_hybrid_results}, reason='{result_reason}'")
    logger.info(f"🔍 Excel results count: {len(excel_results)}")
    
    if has_hybrid_results:
        return {
            "query": query,
            "source_filter": format_source_filter_display(source_document),
            "best_result": {
                "answer": document_result,
                "source": "document_search",
                "explanation": "Found relevant results in document search (Pinecone/BM25)",
                "search_strategy": "sequential_hybrid_first"
            },
            "document_search": {
                "description": "Search results from Pinecone/BM25 (includes parsed content from document files)",
                "success": True,
                "result": document_result,
                "error": document_error,
                "searched": True
            },
            "pandas_agent_search": {
                "description": "DataFrame-specific search - skipped since hybrid search found results",
                "files_searched": 0,
                "results": [],
                "errors": [],
                "searched": False
            },
            "summary": {
                "total_sources": 1,
                "search_strategy": "sequential_hybrid_first",
                "search_successful": True,
                "has_document_results": True,
                "has_pandas_results": False,
                "search_methods": {
                    "document_search": "Pinecone/BM25 hybrid search found results",
                    "pandas_search": "Skipped - hybrid search was successful"
                }
            }
        }
    elif len(excel_results) > 0:
        # Check if pandas agent results are meaningful
        meaningful_pandas_results = []
        for result in excel_results:
            answer = result['answer']
            is_meaningful, reason = is_meaningful_document_result(answer)
            if is_meaningful:
                meaningful_pandas_results.append(result)
        
        if meaningful_pandas_results:
            # Create a more detailed combined result with better formatting
            combined_pandas_parts = []
            for result in meaningful_pandas_results:
                filename = result['filename']
                file_type = result['file_type']
                answer = result['answer']
                
                # Add detailed formatting for each result
                combined_pandas_parts.append(f"**File: {filename} ({file_type.upper()})**\n{answer}")
            
            combined_pandas = "\n\n---\n\n".join(combined_pandas_parts)
            
            # Log the results for debugging
            logger.info(f"📊 PANDAS AGENT MEANINGFUL RESULTS FOUND: {len(meaningful_pandas_results)} results")
            for i, result in enumerate(meaningful_pandas_results):
                logger.info(f"📊 Result {i+1}: {result['filename']} - Answer length: {len(result['answer'])}")
                logger.info(f"📊 Answer preview: {result['answer'][:200]}...")
            
            response = {
                "query": query,
                "source_filter": format_source_filter_display(source_document),
                "best_result": {
                    "answer": combined_pandas,
                    "source": "pandas_agent",
                    "explanation": f"Found relevant data in {len(meaningful_pandas_results)} Excel/CSV file(s) using pandas agent",
                    "search_strategy": "sequential_pandas_fallback"
                },
                "document_search": {
                    "description": "Search results from Pinecone/BM25 - no relevant results found",
                    "success": False,
                    "result": document_result,
                    "error": document_error,
                    "searched": True
                },
                "pandas_agent_search": {
                    "description": "DataFrame-specific search results from Excel/CSV files using pandas agent",
                    "files_searched": len(target_files),
                    "results": meaningful_pandas_results,
                    "errors": excel_errors,
                    "searched": True
                },
                "summary": {
                    "total_sources": len(meaningful_pandas_results),
                    "search_strategy": "sequential_pandas_fallback",
                    "search_successful": True,
                    "has_document_results": False,
                    "has_pandas_results": True,
                    "search_methods": {
                        "document_search": "Pinecone/BM25 hybrid search - no results",
                        "pandas_search": f"LangChain pandas agent found results in {len(meaningful_pandas_results)} file(s)"
                    }
                }
            }
            
            # Add debug info if requested
            if debug:
                response["debug_info"] = {
                    "excel_results_count": len(meaningful_pandas_results),
                    "excel_errors_count": len(excel_errors),
                    "target_files": target_files,
                    "combined_pandas_length": len(combined_pandas),
                    "search_strategy": "sequential_pandas_fallback"
                }
            
            return response
        else:
            # Both document search and pandas agent failed to find meaningful results
            logger.info(f"📊 BOTH SEARCHES FAILED - Document search and pandas agent found no meaningful results")
            return {
                "query": query,
                "source_filter": format_source_filter_display(source_document),
                "best_result": {
                    "answer": "No results found for your query. Please try rephrasing your question or check if relevant documents have been uploaded and processed.",
                    "source": "none",
                    "explanation": "Neither document search nor data analysis found relevant information",
                    "search_strategy": "sequential_no_results"
                },
                "document_search": {
                    "description": "Search results from Pinecone/BM25 - no relevant results found",
                    "success": False,
                    "result": document_result,
                    "error": document_error,
                    "searched": True
                },
                "pandas_agent_search": {
                    "description": "DataFrame-specific search - no relevant results found",
                    "files_searched": len(target_files),
                    "results": excel_results,
                    "errors": excel_errors,
                    "searched": True
                },
                "summary": {
                    "total_sources": 0,
                    "search_strategy": "sequential_no_results",
                    "search_successful": False,
                    "has_document_results": False,
                    "has_pandas_results": False,
                    "search_methods": {
                        "document_search": "Pinecone/BM25 hybrid search - no results",
                        "pandas_search": "LangChain pandas agent - no results"
                    }
                }
            }
    else:
        return {
            "query": query,
            "source_filter": format_source_filter_display(source_document),
            "best_result": {
                "answer": "No results found for your query. Please try rephrasing your question or check if relevant documents have been uploaded and processed.",
                "source": "none",
                "explanation": "Neither document search nor data analysis found relevant information",
                "search_strategy": "sequential_no_results"
            },
            "document_search": {
                "description": "Search results from Pinecone/BM25 - no relevant results found",
                "success": False,
                "result": document_result,
                "error": document_error,
                "searched": True
            },
            "pandas_agent_search": {
                "description": "DataFrame-specific search - no relevant results found",
                "files_searched": len(target_files),
                "results": excel_results,
                "errors": excel_errors,
                "searched": True
            },
            "summary": {
                "total_sources": 0,
                "search_strategy": "sequential_no_results",
                "search_successful": False,
                "has_document_results": False,
                "has_pandas_results": False,
                "search_methods": {
                    "document_search": "Pinecone/BM25 hybrid search - no results",
                    "pandas_search": "LangChain pandas agent - no results"
                }
            }
        }

def build_targeted_response(query: str, source_document: str, document_result: str,
                          document_error: str, excel_results: list, excel_errors: list,
                          search_documents: bool, search_excel_csv: bool, debug: bool) -> dict:
    """
    Build response for targeted search strategy.
    
    Args:
        query: Search query
        source_document: Source document filter
        document_result: Document search result
        document_error: Document search error
        excel_results: Excel/CSV search results
        excel_errors: Excel/CSV search errors
        search_documents: Whether document search was performed
        search_excel_csv: Whether Excel/CSV search was performed
        debug: Whether to include debug information
        
    Returns:
        Response dictionary
    """
    filter_description = f" (filtered by: {format_source_filter_display(source_document)})"
    
    # Determine the best result
    best_result = None
    
    # Check if document result is meaningful
    has_meaningful_document_result, document_reason = is_meaningful_document_result(document_result)
    
    # Check if pandas results are meaningful
    meaningful_pandas_results = []
    for result in excel_results:
        answer = result.get('answer', '')
        is_meaningful, reason = is_meaningful_document_result(answer)
        if is_meaningful:
            meaningful_pandas_results.append(result)
    
    # Prioritize pandas agent results if they contain meaningful data
    if meaningful_pandas_results:
        # Combine all meaningful pandas results
        combined_pandas_parts = []
        for result in meaningful_pandas_results:
            filename = result.get('filename', 'Unknown file')
            file_type = result.get('file_type', 'Unknown type')
            answer = result.get('answer', '')
            combined_pandas_parts.append(f"**File: {filename} ({file_type.upper()})**\n{answer}")
        
        combined_pandas = "\n\n---\n\n".join(combined_pandas_parts)
        best_result = {
            "answer": combined_pandas,
            "source": "pandas_agent",
            "explanation": f"Found relevant data in {len(meaningful_pandas_results)} Excel/CSV file(s) using pandas agent",
            "search_strategy": "targeted"
        }
    elif has_meaningful_document_result:
        best_result = {
            "answer": document_result,
            "source": "document_search",
            "explanation": f"Found relevant information in document search{filter_description}",
            "search_strategy": "targeted"
        }
    else:
        best_result = {
            "answer": "No results found for your query. Please try rephrasing your question or check if relevant documents have been uploaded and processed.",
            "source": "none",
            "explanation": "Neither document search nor data analysis found relevant information",
            "search_strategy": "targeted"
        }
    
    response = {
        "query": query,
        "source_filter": format_source_filter_display(source_document),
        "best_result": best_result,
        "document_search": {
            "description": f"Search results from Pinecone/BM25 (includes parsed content from document files){filter_description}",
            "success": document_result is not None,
            "result": document_result if document_result else None,
            "error": document_error,
            "searched": search_documents
        },
        "pandas_agent_search": {
            "description": "DataFrame-specific search results from Excel/CSV files using pandas agent",
            "files_searched": len(excel_results) if search_excel_csv else 0,
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
    
    if debug:
        response["debug_info"] = {
            "document_debug": document_result.get("debug") if isinstance(document_result, dict) else None,
            "excel_files_found": excel_results,
            "search_strategy": {
                "search_documents": search_documents,
                "search_excel_csv": search_excel_csv,
                "sequential_search": True,
                "hybrid_first": True
            }
        }
    
    return response 