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

logger = logging.getLogger(__name__)

load_dotenv()

pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

INDEX_NAME = "biz-to-bricks-vector-store-hybrid"
BM25_INDEX_DIR = "bm25_indexes"

# Initialize file manager
file_manager = get_file_manager()

embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                              model="text-embedding-3-large")

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
        
        # Update metadata to include source for filtering
        metadata["source"] = file_name
        
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
                    "source": file_name,
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                }
            
            # Create document and ID for this chunk
            doc = Document(page_content=chunk, metadata=chunk_metadata)
            documents.append(doc)
            document_ids.append(f"{base_filename}_chunk_{i}")

        logger.info("Creating/accessing Pinecone index...")
        index = create_index()

        # Check if document already exists and delete old vectors
        logger.info(f"Checking for existing document: {file_name}")
        try:
            # Delete any existing vectors for this document
            index.delete(
                filter={"source": file_name},
                namespace="biz-to-bricks-namespace"
            )
            logger.info(f"Deleted existing vectors for document: {file_name}")
        except Exception as e:
            logger.warning(f"Error deleting existing vectors (may not exist): {str(e)}")

        logger.info(f"Uploading {len(documents)} document chunks to Pinecone...")
        
        # Create vector store and add documents with consistent IDs
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace="biz-to-bricks-namespace"
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
        
        # Check if BM25 index already exists and log appropriately
        if file_manager.file_exists(BM25_INDEX_DIR, index_filename):
            logger.info(f"Overwriting existing BM25 index for file: {file_name}")
        else:
            logger.info(f"Creating new BM25 index for file: {file_name}")
        
        # Create BM25 encoder
        bm25_encoder = BM25Encoder().default()

        # Load content from parsed/edited file
        text_content, metadata = load_edited_file_or_parsed_file(file_name)

        # For BM25, we can use the full document or split into smaller sections
        # Split into paragraphs or sections for better BM25 performance
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,  # Smaller chunks for BM25
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ". ", " "]
        )
        
        text_chunks = text_splitter.split_text(text_content)
        logger.info(f"Created {len(text_chunks)} text chunks for BM25 indexing")

        # Fit the encoder with the text chunks
        bm25_encoder.fit(text_chunks)

        # Save the BM25 index using a temporary file and file manager
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # Dump to temporary file first
            bm25_encoder.dump(temp_file_path)
            
            # Read the temporary file content
            with open(temp_file_path, 'r') as f:
                index_content = f.read()
            
            # Save using file manager (auto-detects local/cloud storage)
            # This will overwrite any existing index with the same name
            saved_path = file_manager.save_file(BM25_INDEX_DIR, index_filename, index_content)
            logger.info(f"BM25 index saved successfully to: {saved_path}")
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

        logger.info(f"BM25 index created/updated successfully for file: {file_name}")

    except Exception as e:
        logger.error(f"Error creating BM25 index for {file_name}: {str(e)}")
        raise

# function to ingest documents to pinecone and bm25 index
def ingest_documents_to_pinecone_and_bm25(file_name: str):
    """
    This function ingests documents to Pinecone and BM25 index.
    If the document already exists, it will be updated/overwritten.
    """
    logger.info(f"Starting ingestion process for file: {file_name}")
    
    try:
        # Import the document existence check function
        from pinecone_util import document_exists_in_pinecone
        
        # Check if document already exists
        document_exists = document_exists_in_pinecone(file_name)
        if document_exists:
            logger.info(f"Document {file_name} already exists in Pinecone. It will be updated.")
        else:
            logger.info(f"Document {file_name} is new. Creating fresh vectors.")
        
        # Ingest to Pinecone (handles upsert automatically)
        ingest_documents_to_pinecone_hybrid(file_name)
        
        # Create/update BM25 index (automatically overwrites if exists)
        create_bm25_index(file_name)
        
        action = "updated" if document_exists else "created"
        logger.info(f"Successfully {action} document {file_name} in both Pinecone and BM25 index")
    except Exception as e:
        logger.error(f"Error during ingestion process for {file_name}: {str(e)}")
        raise

# test
# if __name__ == "__main__":
#     file_name = "Sample1.md"
#     ingest_documents_to_pinecone_and_bm25(file_name)





