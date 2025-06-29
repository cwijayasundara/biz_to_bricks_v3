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
from pydantic import BaseModel, Field
import os
from pathlib import Path as FilePath
import logging
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager
from ingest_docs import ingest_documents_to_pinecone_and_bm25
from hybrid_search import execure_hybrid_chain

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

class FilesListResponse(BaseModel):
    """Model for file listing responses"""
    files: List[str] = Field(..., description="List of file names")

# Define data models for search
class SearchQuery(BaseModel):
    """Model for search queries"""
    query: str = Field(..., description="The search query")

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

# API Routes
@app.post("/uploadfile/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the server.
    
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
        
        logger.info(f"File saved to {saved_path}")
        return {
            "filename": file.filename, 
            "file_path": saved_path
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
    Parse an uploaded file into markdown format.
    
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
        logger.error(f"Error during save and ingest for {filename}: {str(e)}")
        # Check if the error occurred during save or ingest
        if "ingest" in str(e).lower():
            error_detail = f"Content was saved but ingestion failed: {str(e)}"
        else:
            error_detail = f"Error during save and ingest: {str(e)}"
        
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
    """
    try:
        # Extract base filename without extension to ensure consistency
        base_filename = FilePath(filename).stem
        logger.info(f"Ingesting documents for base filename: {base_filename}")
        
        ingest_documents_to_pinecone_and_bm25(base_filename)
        return {"message": f"Documents ingested to Pinecone and BM25 index for {base_filename}"}
    except FileNotFoundError as e:
        logger.error(f"File not found for ingestion: {e}")
        base_filename = FilePath(filename).stem if filename else filename
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"File {base_filename} not found in server/parsed_files. Please parse the file first."}
        )
    except Exception as e:
        logger.error(f"Error during ingestion for {filename}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to ingest file: {str(e)}"}
        )

# Hybrid search
@app.post("/hybridsearch/")
async def hybrid_search(search_query: SearchQuery):
    """
    Perform a hybrid search using Pinecone and BM25.
    """
    try:
        result = execure_hybrid_chain(search_query.query)
        return {"result": result}
    except Exception as e:
        logger.error(f"Error during hybrid search: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to perform hybrid search: {str(e)}"}
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
        questions = generate_questions(text_content, number_of_questions)
        
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
