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
    This function ingests documents to Pinecone.
    """
    try:
        logger.info(f"Loading content for file: {file_name}")
        text_content, metadata = load_edited_file_or_parsed_file(file_name)

        documents = [Document(page_content=text_content, metadata=metadata)]

        logger.info("Creating/accessing Pinecone index...")
        create_index()

        logger.info("Uploading documents to Pinecone...")
        
        vector_store = PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings,
            index_name=INDEX_NAME,
            namespace="biz-to-bricks-namespace"
        )
        logger.info("Successfully uploaded documents to Pinecone")
        return vector_store
    except Exception as e:
        logger.error(f"Error while ingesting documents: {str(e)}")
        raise

def create_bm25_index(file_name: str):
    """
    This function creates a new BM25 index and saves it using the file manager
    (works with both local storage and cloud storage).
    """
    try:
        logger.info(f"Creating BM25 index for file: {file_name}")
        
        # Create BM25 encoder
        bm25_encoder = BM25Encoder().default()

        # Load content from parsed/edited file
        text_content, metadata = load_edited_file_or_parsed_file(file_name)

        # Fit the encoder with the text content
        bm25_encoder.fit([text_content])

        # Use base filename without extension for consistency
        from pathlib import Path as FilePath
        base_filename = FilePath(file_name).stem
        index_filename = f"{base_filename}.json"

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
            saved_path = file_manager.save_file(BM25_INDEX_DIR, index_filename, index_content)
            logger.info(f"BM25 index saved successfully to: {saved_path}")
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

        logger.info(f"BM25 index created successfully for file: {file_name}")

    except Exception as e:
        logger.error(f"Error creating BM25 index for {file_name}: {str(e)}")
        raise

# function to ingest documents to pinecone and bm25 index
def ingest_documents_to_pinecone_and_bm25(file_name: str):
    """
    This function ingests documents to Pinecone and BM25 index.
    """
    logger.info(f"Starting ingestion process for file: {file_name}")
    
    try:
        ingest_documents_to_pinecone_hybrid(file_name)
        create_bm25_index(file_name)
        logger.info(f"Successfully completed ingestion for file: {file_name}")
    except Exception as e:
        logger.error(f"Error during ingestion process for {file_name}: {str(e)}")
        raise

# test
# if __name__ == "__main__":
#     file_name = "Sample1.md"
#     ingest_documents_to_pinecone_and_bm25(file_name)





