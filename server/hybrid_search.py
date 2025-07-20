import os
from dotenv import load_dotenv
import time
import json
import numpy as np
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
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

load_dotenv()

# Load environment variables
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

# Import configuration constants
from config import PINECONE_NAMESPACE, BM25_INDEXES_PATH, LLM_MODEL_NAME, LLM_PROVIDER, EMBEDDING_MODEL_NAME

# Initialize file manager
file_manager = get_file_manager()

# Initialize OpenAI LLM and embeddings
llm = init_chat_model(LLM_MODEL_NAME, 
                      model_provider=LLM_PROVIDER,
                      api_key=openai_api_key)
    
embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                              model=EMBEDDING_MODEL_NAME)

# Constants for configuration
BM25_ALPHA = 0.3  # Favor BM25 (sparse) for exact name matches
TOP_K_RESULTS = 10  # Retrieve more documents for better coverage
CHUNK_SIZE = 4000  # Text chunk size for processing
CHUNK_OVERLAP = 200  # Overlap between chunks

def load_bm25_encoder_from_file(file_content: str, file_name: str) -> BM25Encoder:
    """
    Load a BM25 encoder from file content.
    
    Args:
        file_content: JSON content of the encoder file
        file_name: Name of the file for logging
        
    Returns:
        BM25Encoder: The loaded encoder
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Load the JSON data and reconstruct the encoder
            encoder_data = json.loads(file_content)
            encoder = BM25Encoder()
            encoder.doc_freq = encoder_data['doc_freq']
            encoder.n_docs = encoder_data['n_docs']
            encoder.avgdl = encoder_data['avgdl']
            encoder.k1 = encoder_data['k1']
            encoder.b = encoder_data['b']
            logger.info(f"Successfully loaded encoder from {file_name}")
            return encoder
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error loading encoder from {file_name}: {e}")
        raise

def create_bm25_encoder():
    """
    Creates and returns a BM25Encoder by loading and merging all BM25 encoder files 
    from the bm25_indexes directory (works with both local and cloud storage).
    
    Returns:
        BM25Encoder: The loaded or default BM25 encoder
    """
    try:
        # Get list of BM25 index files using file manager (auto-detects local/cloud)
        logger.info(f"Loading BM25 indexes from directory: {BM25_INDEXES_PATH}")
        bm25_files = file_manager.list_files(BM25_INDEXES_PATH)
        json_files = [f for f in bm25_files if f.endswith('.json')]
        
        logger.info(f"Found {len(json_files)} BM25 index files: {json_files}")
        
        if not json_files:
            logger.warning("No BM25 index files found, using default encoder")
            return BM25Encoder().default()
        
        # Load the first encoder as base
        first_file = json_files[0]
        logger.info(f"Loading base encoder from: {first_file}")
        
        # Load the file content
        file_content = file_manager.load_file(BM25_INDEXES_PATH, first_file)
        base_encoder = load_bm25_encoder_from_file(file_content, first_file)
        
        # Merge additional encoders if any
        if len(json_files) > 1:
            logger.info(f"Merging {len(json_files) - 1} additional encoders")
            for file_name in json_files[1:]:
                try:
                    # Load additional encoder file
                    additional_content = file_manager.load_file(BM25_INDEXES_PATH, file_name)
                    additional_encoder = load_bm25_encoder_from_file(additional_content, file_name)
                    
                    # Merge encoders by updating vocabulary and document frequencies
                    base_encoder.merge_encoder(additional_encoder)
                    logger.info(f"Successfully merged encoder from {file_name}")
                    
                except Exception as e:
                    logger.error(f"Error loading encoder from {file_name}: {e}")
        
        logger.info("BM25 encoder created successfully with merged indexes")
        return base_encoder
            
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
            alpha=BM25_ALPHA,  # Favor BM25 (sparse) for exact name matches
            top_k=TOP_K_RESULTS,   # Retrieve more documents for better coverage
            namespace=PINECONE_NAMESPACE
        )
        
        logger.info("Hybrid search retriever created successfully")    
        return retriever
        
    except Exception as e:
        logger.error(f"Error creating retriever: {e}")
        raise

def get_filtered_documents(query: str, source_document: str) -> List[Any]:
    """
    Get documents filtered by source document using direct index query.
    
    Args:
        query: The search query
        source_document: The source document name to filter by
        
    Returns:
        List of LangChain Document objects
    """
    try:
        logger.info(f"Getting filtered documents for source: {source_document}")
        index = create_index()
        
        # Create query embedding
        query_embedding = embeddings.embed_query(query)
        
        # Query Pinecone with source filter
        query_response = index.query(
            vector=query_embedding,
            top_k=TOP_K_RESULTS,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE,
            filter={"source": source_document}
        )
        
        # Convert to LangChain Document objects
        from langchain_core.documents import Document
        docs = []
        
        for match in query_response.get('matches', []):
            metadata = match.get('metadata', {})
            # Get text content from metadata.text field
            text_content = metadata.get('text', '')
            
            doc = Document(
                page_content=text_content,
                metadata=metadata
            )
            docs.append(doc)
        
        logger.info(f"Retrieved {len(docs)} filtered documents for source: {source_document}")
        return docs
        
    except Exception as e:
        logger.error(f"Error getting filtered documents for {source_document}: {e}")
        raise

# Create the retriever (only once)
logger.info("Initializing hybrid search retriever...")
retriever = create_hybrid_retriever()

def format_docs(docs: List[Any]) -> str:
    """
    Format the documents into a string with enhanced context.
    
    Args:
        docs: List of LangChain Document objects
        
    Returns:
        Formatted string with document content
    """
    if not docs:
        return "No relevant documents found."
    
    formatted_docs = []
    for i, doc in enumerate(docs, 1):
        # Add document separator and source info if available
        doc_text = f"Document {i}"
        if hasattr(doc, 'metadata') and doc.metadata:
            source = doc.metadata.get('source', 'Unknown')
            doc_text += f" (Source: {source})"
        
        doc_text += f":\n{doc.page_content}\n"
        formatted_docs.append(doc_text)
    
    return "\n" + "="*50 + "\n".join(formatted_docs)

# Enhanced prompt template for better entity queries and structured data
template = """You are an AI assistant that answers questions based on the provided context. 

Context Information:
{context}

Instructions:
- Answer the question using ONLY the information provided in the context above
- If asked about specific people, entities, or data points, provide ALL relevant details found
- For tabular data, present information in a clear, organized format
- If the question asks for "all details" or "everything" about someone/something, include all available attributes
- If the information is not in the context, clearly state that it's not available
- Be comprehensive and specific in your answers

Question: {question}

Answer:"""

prompt = ChatPromptTemplate.from_template(template)

# Create the Langchain runnable pipeline
hybrid_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def execure_hybrid_chain(query: str, source_document: Optional[str] = None) -> str:
    """
    Execute the hybrid chain with enhanced logging and debugging.
    
    Args:
        query: The search query
        source_document: Optional source document to filter by
        
    Returns:
        Search result as string
    """
    filter_info = f" (filtered by: {source_document})" if source_document else ""
    logger.info(f"Executing hybrid search for query: {query}{filter_info}")
    
    try:
        # Log the retrieval process for debugging
        logger.info("Retrieving relevant documents...")
        
        if source_document:
            # Get filtered documents for specific source
            docs = get_filtered_documents(query, source_document)
        else:
            # Use the global retriever for all documents
            docs = retriever.invoke(query)
            
        logger.info(f"Retrieved {len(docs)} documents{filter_info}")
        
        # Log the documents for debugging (first 100 chars of each)
        for i, doc in enumerate(docs):
            preview = doc.page_content[:100].replace('\n', ' ')
            logger.info(f"Doc {i+1} preview: {preview}...")
            if hasattr(doc, 'metadata') and doc.metadata:
                logger.info(f"Doc {i+1} metadata: {doc.metadata}")
        
        # Create context from documents and generate response
        context = format_docs(docs)
        
        # Create the prompt with context and question
        formatted_prompt = prompt.format(context=context, question=query)
        
        # Generate response using LLM
        result = llm.invoke(formatted_prompt)
        
        # Extract content if it's wrapped in AIMessage
        if hasattr(result, 'content'):
            result = result.content
            
        logger.info("Hybrid search completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error executing hybrid search: {e}")
        raise

def search_with_debug_info(query: str, source_document: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute search and return both result and debug information.
    
    Args:
        query: The search query
        source_document: Optional source document to filter by
        
    Returns:
        Dictionary with result and debug information
    """
    filter_info = f" (filtered by: {source_document})" if source_document else ""
    logger.info(f"Executing debug search for query: {query}{filter_info}")
    
    try:
        # Get documents for debugging
        if source_document:
            docs = get_filtered_documents(query, source_document)
        else:
            docs = retriever.invoke(query)
        
        # Format debug info
        debug_info = {
            "query": query,
            "source_filter": source_document,
            "documents_found": len(docs),
            "documents": []
        }
        
        for i, doc in enumerate(docs):
            doc_info = {
                "index": i + 1,
                "preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
            }
            debug_info["documents"].append(doc_info)
        
        # Create context and generate response
        context = format_docs(docs)
        formatted_prompt = prompt.format(context=context, question=query)
        result = llm.invoke(formatted_prompt)
        
        # Extract content if it's wrapped in AIMessage
        if hasattr(result, 'content'):
            result = result.content
        
        return {
            "result": result,
            "debug": debug_info
        }
        
    except Exception as e:
        logger.error(f"Error in debug search: {e}")
        raise
