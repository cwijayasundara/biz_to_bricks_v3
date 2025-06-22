import os
from dotenv import load_dotenv
import time
from langchain_community.retrievers import PineconeHybridSearchRetriever
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from pinecone_text.sparse import BM25Encoder
from langchain import hub
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from pinecone_util import create_index
from langchain.prompts import ChatPromptTemplate
from file_util_enhanced import get_file_manager
import tempfile
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Load environment variables
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

# Constants
BM25_INDEX_DIR = "bm25_indexes"

# Initialize file manager
file_manager = get_file_manager()

# Initialize OpenAI LLM and embeddings
llm = init_chat_model("gpt-4.1-mini", 
                      model_provider="openai",
                      api_key=openai_api_key)
    
embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                              model="text-embedding-3-large")

def create_bm25_encoder():
    """
    Creates and returns a BM25Encoder by loading and merging all BM25 encoder files 
    from the bm25_indexes directory (works with both local and cloud storage).
    
    Returns:
        BM25Encoder: The loaded or default BM25 encoder
    """
    try:
        # Get list of BM25 index files using file manager (auto-detects local/cloud)
        logger.info(f"Loading BM25 indexes from directory: {BM25_INDEX_DIR}")
        bm25_files = file_manager.list_files(BM25_INDEX_DIR)
        json_files = [f for f in bm25_files if f.endswith('.json')]
        
        logger.info(f"Found {len(json_files)} BM25 index files: {json_files}")
        
        if json_files:
            # Load the first encoder as base
            first_file = json_files[0]
            logger.info(f"Loading base encoder from: {first_file}")
            
            # Load the file content and create a temporary file for BM25Encoder
            file_content = file_manager.load_file(BM25_INDEX_DIR, first_file)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                base_encoder = BM25Encoder().load(temp_file_path)
                logger.info(f"Successfully loaded base encoder from {first_file}")
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
            
            # Merge additional encoders if any
            if len(json_files) > 1:
                logger.info(f"Merging {len(json_files) - 1} additional encoders")
                for file_name in json_files[1:]:
                    try:
                        # Load additional encoder file
                        additional_content = file_manager.load_file(BM25_INDEX_DIR, file_name)
                        
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                            temp_file.write(additional_content)
                            temp_file_path = temp_file.name
                        
                        try:
                            additional_encoder = BM25Encoder().load(temp_file_path)
                            # Merge encoders by updating vocabulary and document frequencies
                            base_encoder.merge_encoder(additional_encoder)
                            logger.info(f"Successfully merged encoder from {file_name}")
                        finally:
                            # Clean up temporary file
                            os.unlink(temp_file_path)
                            
                    except Exception as e:
                        logger.error(f"Error loading encoder from {file_name}: {e}")
            
            logger.info("BM25 encoder created successfully with merged indexes")
            return base_encoder
        else:
            logger.warning("No BM25 index files found, using default encoder")
            return BM25Encoder().default()
            
    except Exception as e:
        logger.error(f"Error loading BM25 encoders: {e}")
        logger.info("Falling back to default BM25 encoder")
        return BM25Encoder().default()

def create_hybrid_retriever():
    """
    Creates and returns a PineconeHybridSearchRetriever using all BM25 encoders in the directory.
    """
    try:
        logger.info("Creating Pinecone index...")
        index = create_index()
        
        logger.info("Creating BM25 encoder...")
        bm25_encoder = create_bm25_encoder()
    
        # Create the retriever with the correct namespace
        logger.info("Creating hybrid search retriever...")
        retriever = PineconeHybridSearchRetriever(
            embeddings=embeddings, 
            sparse_encoder=bm25_encoder, 
            index=index,
            text_key="text",
            alpha=0.5,
            top_k=3,
            namespace="biz-to-bricks-namespace"
        )
        
        logger.info("Hybrid search retriever created successfully")    
        return retriever
        
    except Exception as e:
        logger.error(f"Error creating retriever: {e}")
        raise

# Create the retriever (only once)
logger.info("Initializing hybrid search retriever...")
retriever = create_hybrid_retriever()

def format_docs(docs):
    """Format the documents into a string."""
    return "\n\n".join(doc.page_content for doc in docs)

# Prompt template
template = """Answer the question based only on the following context:
{context}

Question: {question}

"""

prompt = ChatPromptTemplate.from_template(template)

# Create the Langchain runnable pipeline
hybrid_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def execure_hybrid_chain(query):
    """Execute the hybrid chain."""
    logger.info(f"Executing hybrid search for query: {query}")
    try:
        result = hybrid_chain.invoke(query)
        logger.info("Hybrid search completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error executing hybrid search: {e}")
        raise
