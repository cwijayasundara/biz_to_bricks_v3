from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone_text.sparse import BM25Encoder
from file_util_enhanced import load_edited_file_or_parsed_file, get_file_manager
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone_util import create_index
import tempfile
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

load_dotenv()

# Load environment variables with validation
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

# Clean up API keys by removing quotes if present (common deployment issue)
if pinecone_api_key:
    pinecone_api_key = pinecone_api_key.strip("\"'")
if openai_api_key:
    openai_api_key = openai_api_key.strip("\"'")

# Import configuration constants
from config import PINECONE_NAMESPACE, BM25_INDEXES_PATH, EMBEDDING_MODEL_NAME

# Initialize file manager
file_manager = get_file_manager()

def cleanup_duplicate_vectors(source_filename: str):
    """
    Utility function to clean up all duplicate vectors for a given source file.
    This can be called independently to clean up the database.
    
    Args:
        source_filename: The source filename to clean up (e.g., "Sample2.pdf")
    """
    try:
        logger.info(f"🧹 Starting comprehensive cleanup for: {source_filename}")
        index = create_index()
        
        # Get base filename without extension
        base_filename = source_filename.split(".")[0] if "." in source_filename else source_filename
        
        # Build comprehensive list of all possible source names
        possible_source_names = set()
        possible_source_names.add(source_filename)  # Full filename
        possible_source_names.add(base_filename)    # Base filename
        
        # Add variations with different extensions
        for ext in ['.pdf', '.docx', '.doc', '.txt', '.md', '.xlsx', '.xls', '.csv']:
            possible_source_names.add(f"{base_filename}{ext}")
        
        logger.info(f"Searching for vectors with source names: {list(possible_source_names)}")
        
        # Delete vectors for each possible source name
        total_deleted = 0
        for source_name in possible_source_names:
            try:
                # Query first to count existing vectors
                query_response = index.query(
                    vector=[0.0] * 1536,  # Dummy vector for OpenAI embeddings
                    top_k=10000,  # Large number to get all matches
                    filter={"source": source_name},
                    namespace=PINECONE_NAMESPACE,
                    include_metadata=False
                )
                
                if query_response.matches:
                    count = len(query_response.matches)
                    # Delete all vectors with this source
                    index.delete(
                        filter={"source": source_name},
                        namespace=PINECONE_NAMESPACE
                    )
                    total_deleted += count
                    logger.info(f"✅ Deleted {count} vectors for source: {source_name}")
                    
            except Exception as source_e:
                logger.debug(f"No vectors found with source '{source_name}': {source_e}")
        
        # Also clean up by ID patterns
        id_prefixes = {base_filename, source_filename.split(".")[0] if "." in source_filename else source_filename}
        for id_prefix in id_prefixes:
            try:
                # Generate potential IDs and delete them
                potential_ids = [f"{id_prefix}_chunk_{i}" for i in range(100)]  # Up to 100 chunks
                index.delete(ids=potential_ids, namespace=PINECONE_NAMESPACE)
                logger.info(f"🧹 Cleaned up ID patterns for: {id_prefix}")
            except Exception as id_e:
                logger.debug(f"ID cleanup for '{id_prefix}': {id_e}")
        
        logger.info(f"🎯 Cleanup complete! Total vectors deleted: {total_deleted}")
        return total_deleted
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                              model=EMBEDDING_MODEL_NAME)

def is_excel_csv_file(file_name: str) -> bool:
    """
    Check if a file is Excel or CSV based on its extension.
    
    Args:
        file_name: The filename to check
        
    Returns:
        True if file is Excel or CSV, False otherwise
    """
    if not file_name:
        return False
    
    extension = Path(file_name).suffix.lower()
    excel_csv_extensions = ['.xlsx', '.xls', '.csv']
    return extension in excel_csv_extensions

def calculate_metadata_size(metadata):
    """Calculate the size of metadata in bytes when JSON serialized."""
    return len(json.dumps(metadata).encode('utf-8'))

def truncate_metadata(metadata, max_size=35000):  # Leave buffer under 40KB limit
    """Truncate metadata fields to fit within Pinecone's size limits."""
    # Create a copy to avoid modifying the original
    truncated_metadata = dict(metadata)
    
    # Remove or truncate large fields
    fields_to_check = ['content', 'text', 'summary', 'description']
    
    for field in fields_to_check:
        if field in truncated_metadata:
            field_value = str(truncated_metadata[field])
            # If this field exists and is large, truncate it
            if len(field_value) > 1000:  # If field is large
                truncated_metadata[field] = field_value[:500] + "... [truncated]"
    
    # Check final size and remove non-essential fields if still too large
    current_size = calculate_metadata_size(truncated_metadata)
    if current_size > max_size:
        # Keep only essential fields
        essential_fields = ['source', 'chunk_id', 'total_chunks']
        truncated_metadata = {k: v for k, v in truncated_metadata.items() 
                            if k in essential_fields}
    
    return truncated_metadata

def ingest_documents_to_pinecone_hybrid(file_name: str):
    """
    This function ingests documents to Pinecone with upsert functionality and proper chunking.
    If the document already exists, it will be updated with new content.
    Documents are split into chunks to avoid Pinecone metadata size limits.
    """
    try:
        logger.info(f"Loading content for file: {file_name}")
        text_content, metadata = load_edited_file_or_parsed_file(file_name)

        # Use consistent ID generation based on the source file
        base_filename = file_name.split(".")[0] if "." in file_name else file_name
        
        # Determine the original source filename with proper extension
        # Check if we have the original filename in uploaded_files to get the correct extension
        original_filename = None
        uploaded_files = file_manager.list_files("uploaded_files")
        
        # Look for the original file with any extension
        for uploaded_file in uploaded_files:
            if uploaded_file.startswith(base_filename + "."):
                original_filename = uploaded_file
                break
        
        # If we can't find the original file, use the base filename with .md extension
        # This handles cases where the original file might have been deleted
        if not original_filename:
            original_filename = f"{base_filename}.md"
            logger.warning(f"Could not find original uploaded file for {base_filename}, using {original_filename} as source")
        
        # Update metadata to include proper source for filtering
        # Always use the original filename (not temporary paths or base names)
        old_source = metadata.get("source", "NO_SOURCE")
        metadata["source"] = original_filename
        logger.info(f"Updated source metadata: '{old_source}' -> '{original_filename}'")
        
        # Initialize text splitter for large documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,  # Smaller chunks to avoid metadata size issues
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Split the document into chunks
        chunks = text_splitter.split_text(text_content)
        logger.info(f"Split document into {len(chunks)} chunks")
        
        # Create documents for each chunk with proper metadata
        documents = []
        document_ids = []
        
        for i, chunk in enumerate(chunks):
            # Create chunk-specific metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_id": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk)
            })
            
            # Truncate metadata to ensure it fits within Pinecone limits
            chunk_metadata = truncate_metadata(chunk_metadata)
            
            # Verify metadata size
            metadata_size = calculate_metadata_size(chunk_metadata)
            if metadata_size > 40000:  # 40KB limit
                logger.warning(f"Chunk {i} metadata still too large ({metadata_size} bytes), further truncating...")
                # Emergency truncation - keep only essential fields
                chunk_metadata = {
                    "source": original_filename,  # Use original_filename instead of file_name
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                }
            
            # Create document and ID for this chunk using consistent naming
            doc = Document(page_content=chunk, metadata=chunk_metadata)
            documents.append(doc)
            
            # Use original filename base for consistent ID generation
            id_base = original_filename.split(".")[0] if "." in original_filename else original_filename
            document_ids.append(f"{id_base}_chunk_{i}")

        logger.info("Creating/accessing Pinecone index...")
        index = create_index()

        # Enhanced duplicate prevention: Delete ALL possible variations of this document
        logger.info(f"Performing comprehensive cleanup for document: {file_name}")
        
        # Build list of all possible source names this document might have been stored under
        possible_source_names = set()
        
        # Add the current source name (with extension)
        possible_source_names.add(original_filename)
        
        # Add base filename (without extension) for legacy compatibility
        possible_source_names.add(base_filename)
        
        # Add the passed filename as-is
        if file_name not in possible_source_names:
            possible_source_names.add(file_name)
            
        # If original filename is different from file_name, add that too
        if original_filename != file_name:
            base_original = original_filename.split(".")[0] if "." in original_filename else original_filename
            possible_source_names.add(base_original)
        
        # Add common extensions that might have been used
        file_base = base_filename
        for ext in ['.pdf', '.docx', '.doc', '.txt', '.md', '.xlsx', '.xls', '.csv']:
            possible_source_names.add(f"{file_base}{ext}")
        
        logger.info(f"Checking for existing vectors with source names: {list(possible_source_names)}")
        
        # Delete vectors for each possible source name
        deleted_count = 0
        for source_name in possible_source_names:
            try:
                # Query first to see if vectors exist with this source
                query_response = index.query(
                    vector=[0.0] * 1536,  # Dummy vector for OpenAI embeddings
                    top_k=1,
                    filter={"source": source_name},
                    namespace=PINECONE_NAMESPACE,
                    include_metadata=True
                )
                
                if query_response.matches:
                    # Delete vectors with this source
                    index.delete(
                        filter={"source": source_name},
                        namespace=PINECONE_NAMESPACE
                    )
                    deleted_count += len(query_response.matches)
                    logger.info(f"✅ Deleted existing vectors for source: {source_name}")
                else:
                    logger.debug(f"No existing vectors found for source: {source_name}")
                    
            except Exception as source_e:
                logger.debug(f"No vectors found with source '{source_name}': {source_e}")
        
        if deleted_count > 0:
            logger.info(f"🧹 Total cleanup: Deleted {deleted_count} existing vector(s) to prevent duplicates")
        else:
            logger.info("No existing vectors found to delete")
            
        # Additionally, delete by consistent ID pattern to catch any missed vectors
        try:
            # Generate all possible IDs that might exist for this document
            possible_id_prefixes = set()
            possible_id_prefixes.add(base_filename)
            possible_id_prefixes.add(file_name.split(".")[0] if "." in file_name else file_name)
            if original_filename:
                possible_id_prefixes.add(original_filename.split(".")[0] if "." in original_filename else original_filename)
            
            for id_prefix in possible_id_prefixes:
                try:
                    # Generate potential IDs for chunks (assuming up to 50 chunks max)
                    potential_ids = [f"{id_prefix}_chunk_{i}" for i in range(50)]
                    
                    # Try to delete these IDs (Pinecone will ignore non-existent ones)
                    index.delete(ids=potential_ids, namespace=PINECONE_NAMESPACE)
                    logger.info(f"🧹 Attempted ID-based cleanup for prefix: {id_prefix}")
                    
                except Exception as id_e:
                    logger.debug(f"ID cleanup for prefix '{id_prefix}' completed: {id_e}")
                    
        except Exception as id_cleanup_e:
            logger.debug(f"ID-based cleanup failed: {id_cleanup_e}")

        logger.info(f"Uploading {len(documents)} document chunks to Pinecone...")
        
        # Create vector store and add documents with consistent IDs
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=PINECONE_NAMESPACE
        )
        
        # Add documents with consistent IDs to enable upsert behavior
        vector_store.add_documents(documents=documents, ids=document_ids)
        
        logger.info(f"Successfully uploaded/updated {len(documents)} chunks for document: {file_name}")
        return vector_store
    except Exception as e:
        logger.error(f"Error while ingesting documents: {str(e)}")
        raise

def create_bm25_index(file_name: str):
    """
    This function creates a new BM25 index and saves it using the file manager.
    If an index already exists for the file, it will be overwritten.
    BM25 works with the full document content (not chunked) for better keyword matching.
    """
    try:
        logger.info(f"Creating BM25 index for file: {file_name}")
        
        # Use base filename without extension for consistency
        from pathlib import Path as FilePath
        base_filename = FilePath(file_name).stem
        index_filename = f"{base_filename}.json"
        
        # Determine the original source filename (same logic as Pinecone ingestion)
        original_filename = None
        uploaded_files = file_manager.list_files("uploaded_files")
        
        # Look for the original file with any extension
        for uploaded_file in uploaded_files:
            if uploaded_file.startswith(base_filename + "."):
                original_filename = uploaded_file
                break
        
        # If we can't find the original file, use the base filename with .md extension
        if not original_filename:
            original_filename = f"{base_filename}.md"
            logger.warning(f"Could not find original uploaded file for {base_filename}, using {original_filename} as source")
        
        # Load the document content
        text_content, metadata = load_edited_file_or_parsed_file(file_name)
        
        # Update metadata to include proper source for filtering
        metadata["source"] = original_filename
        logger.info(f"Using source metadata: {original_filename}")
        
        # Create BM25 encoder with the document content
        encoder = BM25Encoder()
        
        # BM25Encoder expects a list of strings (the corpus)
        # We pass the text content directly as a list of strings
        corpus = [text_content]
        
        # Fit the encoder with the corpus
        encoder.fit(corpus)
        
        # Serialize the encoder to JSON
        encoder_data = {
            'doc_freq': encoder.doc_freq,
            'n_docs': encoder.n_docs,
            'avgdl': encoder.avgdl,
            'k1': encoder.k1,
            'b': encoder.b
        }
        
        # Convert to JSON string
        encoder_content = json.dumps(encoder_data, indent=2)
        
        # Save the encoder using the file manager
        saved_path = file_manager.save_file(BM25_INDEXES_PATH, index_filename, encoder_content)
        
        logger.info(f"Successfully created BM25 index for {file_name} and saved to {saved_path}")
        return encoder
        
    except Exception as e:
        logger.error(f"Error creating BM25 index for {file_name}: {str(e)}")
        raise

def ingest_documents_to_pinecone_and_bm25(file_name: str):
    """
    Main function to ingest documents to both Pinecone and BM25 indexes.
    This function orchestrates the ingestion process for both vector and keyword search.
    
    Note: Excel/CSV files are parsed and saved but NOT indexed to BM25/Pinecone
    since they use the Pandas agent for queries instead.
    """
    try:
        logger.info(f"Starting ingestion process for file: {file_name}")
        
        # Check if this is an Excel/CSV file by looking at the original uploaded file
        # The file_name parameter might not have extension, so we need to find the original file
        base_filename = file_name.split(".")[0] if "." in file_name else file_name
        
        # Look for the original uploaded file to determine its type
        uploaded_files = file_manager.list_files("uploaded_files")
        original_filename = None
        
        # Look for the original file with any extension
        for uploaded_file in uploaded_files:
            if uploaded_file.startswith(base_filename + "."):
                original_filename = uploaded_file
                break
        
        # Check if the original file is Excel/CSV
        if original_filename and is_excel_csv_file(original_filename):
            logger.info(f"📊 Detected Excel/CSV file: {original_filename} (parsed as {file_name})")
            logger.info("📊 Excel/CSV files are parsed and saved but NOT indexed to BM25/Pinecone")
            logger.info("📊 These files use the Pandas agent for natural language queries instead")
            logger.info("📊 File is ready for use with /querypandas endpoint")
            
            return {
                "pinecone_result": None,
                "bm25_result": None,
                "status": "success",
                "file_type": "excel_csv",
                "message": f"Excel/CSV file {original_filename} parsed and saved. Use /querypandas for data analysis queries."
            }
        
        # For non-Excel/CSV files, proceed with normal indexing
        logger.info(f"📄 Processing document file: {file_name}")
        
        # Step 1: Ingest to Pinecone (vector search)
        logger.info("Step 1: Ingesting to Pinecone for vector search...")
        pinecone_result = ingest_documents_to_pinecone_hybrid(file_name)
        logger.info("✅ Pinecone ingestion completed successfully")
        
        # Step 2: Create BM25 index (keyword search)
        logger.info("Step 2: Creating BM25 index for keyword search...")
        bm25_result = create_bm25_index(file_name)
        logger.info("✅ BM25 index creation completed successfully")
        
        logger.info(f"🎉 Complete ingestion process finished for {file_name}")
        logger.info("Document is now searchable via both vector (Pinecone) and keyword (BM25) search")
        
        return {
            "pinecone_result": pinecone_result,
            "bm25_result": bm25_result,
            "status": "success",
            "file_type": "document",
            "message": f"Document {file_name} indexed and ready for hybrid search."
        }
        
    except Exception as e:
        logger.error(f"Error during complete ingestion process for {file_name}: {str(e)}")
        raise

# test
# if __name__ == "__main__":
#     file_name = "Sample1.md"
#     ingest_documents_to_pinecone_and_bm25(file_name)





