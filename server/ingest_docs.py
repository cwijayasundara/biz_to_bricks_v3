from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone_text.sparse import BM25Encoder
from file_util_enhanced import load_edited_file_or_parsed_file, get_file_manager
from langchain_core.documents import Document
from pinecone_util import create_index
import tempfile
import logging

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

def ingest_documents_to_pinecone_hybrid(file_name: str):
    """
    This function ingests documents to Pinecone with upsert functionality.
    If the document already exists, it will be updated with new content.
    """
    try:
        logger.info(f"Loading content for file: {file_name}")
        text_content, metadata = load_edited_file_or_parsed_file(file_name)

        # Use consistent ID generation based on the source file
        # This ensures the same document gets the same ID for upsert behavior
        base_filename = file_name.split(".")[0] if "." in file_name else file_name
        document_id = f"{base_filename}_doc"
        
        # Update metadata to include source for filtering
        metadata["source"] = file_name
        
        documents = [Document(page_content=text_content, metadata=metadata)]

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

        logger.info("Uploading documents to Pinecone with consistent IDs...")
        
        # Create vector store and add documents with consistent IDs
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace="biz-to-bricks-namespace"
        )
        
        # Add documents with consistent ID to enable upsert behavior
        vector_store.add_documents(documents=documents, ids=[document_id])
        
        logger.info("Successfully uploaded/updated documents in Pinecone")
        return vector_store
    except Exception as e:
        logger.error(f"Error while ingesting documents: {str(e)}")
        raise

def create_bm25_index(file_name: str):
    """
    This function creates a new BM25 index and saves it using the file manager.
    If an index already exists for the file, it will be overwritten.
    (works with both local storage and cloud storage).
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

        # Fit the encoder with the text content
        bm25_encoder.fit([text_content])

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





