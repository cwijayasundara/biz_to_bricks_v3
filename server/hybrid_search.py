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
from excel_agent import create_excel_agent

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

# Lazy initialization of LLM and embeddings to avoid startup failures
_llm = None
_embeddings = None

def is_excel_or_csv_file(filename: str) -> bool:
    """
    Check if a filename represents an Excel or CSV file.
    
    Args:
        filename: The filename to check
        
    Returns:
        True if the file is Excel (.xlsx, .xls) or CSV (.csv), False otherwise
    """
    if not filename:
        return False
    
    # Get file extension and check if it's an Excel/CSV format
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return extension in ['xlsx', 'xls', 'csv']

def is_meaningful_semantic_result(result: str) -> bool:
    """
    Determine if a semantic search result contains meaningful information.
    
    Args:
        result: The search result string
        
    Returns:
        True if the result seems meaningful, False otherwise
    """
    if not result or not isinstance(result, str):
        return False
    
    # Clean up the result for analysis
    cleaned_result = result.strip().lower()
    
    # Check for common "no answer" patterns
    no_answer_patterns = [
        "no relevant documents found",
        "no information available",
        "not available in the context",
        "cannot find",
        "don't have information",
        "no answer",
        "information is not available",
        "not provided in the context",
        "i cannot answer",
        "not mentioned in the context"
    ]
    
    # If any no-answer pattern is found, consider it not meaningful
    for pattern in no_answer_patterns:
        if pattern in cleaned_result:
            return False
    
    # Check if result is too short (likely not meaningful)
    if len(cleaned_result) < 20:
        return False
    
    # If we get here, assume it's meaningful
    return True

def execute_pandas_agent_search(query: str, source_document: str = None) -> str:
    """
    Execute search using pandas agent for Excel/CSV files.
    
    Args:
        query: The search query
        source_document: Optional specific Excel/CSV file to search, or None to search all
        
    Returns:
        Search result as string
    """
    try:
        logger.info(f"Executing pandas agent search for query: {query}")
        
        # Get uploaded files path from config
        from config import UPLOADED_FILE_PATH
        
        # Get all uploaded files
        uploaded_files = file_manager.list_files(UPLOADED_FILE_PATH)
        excel_csv_files = [f for f in uploaded_files if is_excel_or_csv_file(f)]
        
        if not excel_csv_files:
            return "No Excel or CSV files found for analysis."
        
        # Filter by specific source document if provided
        if source_document and source_document != "all":
            excel_csv_files = [f for f in excel_csv_files if f == source_document]
            if not excel_csv_files:
                return f"Specified Excel/CSV file '{source_document}' not found."
        
        logger.info(f"Found {len(excel_csv_files)} Excel/CSV files to search: {excel_csv_files}")
        
        # Try to search each file and collect results
        results = []
        for file_name in excel_csv_files:
            try:
                # Get full file path
                file_path = file_manager.get_file_path(UPLOADED_FILE_PATH, file_name)
                
                logger.info(f"Searching in file: {file_name}")
                
                # Create excel agent and query
                with create_excel_agent(file_path) as agent:
                    result = agent.query(query)
                    if result and result.strip():
                        results.append(f"From {file_name}:\n{result}")
                        logger.info(f"Got result from {file_name}: {result[:100]}...")
                    else:
                        logger.info(f"No result from {file_name}")
                        
            except Exception as file_error:
                error_msg = f"Error searching {file_name}: {str(file_error)}"
                logger.error(error_msg)
                results.append(error_msg)
        
        # Combine results
        if results:
            combined_result = "\n\n".join(results)
            logger.info("Pandas agent search completed successfully")
            return combined_result
        else:
            return "No results found in the Excel/CSV files for your query."
            
    except Exception as e:
        error_msg = f"Error executing pandas agent search: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_llm():
    """Get the LLM instance with lazy initialization."""
    global _llm
    if _llm is None:
        try:
            _llm = init_chat_model(LLM_MODEL_NAME, 
                                  model_provider=LLM_PROVIDER,
                                  api_key=openai_api_key)
            logger.info("LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
    return _llm

def get_embeddings():
    """Get the embeddings instance with lazy initialization."""
    global _embeddings
    if _embeddings is None:
        try:
            _embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                                          model=EMBEDDING_MODEL_NAME)
            logger.info("Embeddings initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
    return _embeddings

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
            embeddings=get_embeddings(), 
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
        query_embedding = get_embeddings().embed_query(query)
        
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

# Lazy initialization of retriever to avoid startup failures
_retriever = None

def get_retriever():
    """Get the retriever instance with lazy initialization."""
    global _retriever
    if _retriever is None:
        try:
            logger.info("Initializing hybrid search retriever...")
            _retriever = create_hybrid_retriever()
            logger.info("Retriever initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}")
            raise
    return _retriever

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

# Create the Langchain runnable pipeline (lazy initialization)
def get_hybrid_chain():
    """Get the hybrid chain with lazy initialization."""
    return (
        {"context": get_retriever() | format_docs, "question": RunnablePassthrough()}
        | prompt
        | get_llm()
        | StrOutputParser()
    )

def execure_hybrid_chain(query: str, source_document: Optional[str] = None) -> str:
    """
    Execute the hybrid chain with new logic for Excel/CSV vs semantic search.
    
    Search Logic:
    - If specific source is selected and it's Excel/CSV: use pandas agent
    - If specific source is selected and it's not Excel/CSV: use semantic search
    - If source="all": try semantic search first, if no good answer then try pandas agent
    
    Args:
        query: The search query
        source_document: Optional source document to filter by (or "all" for all sources)
        
    Returns:
        Search result as string
    """
    filter_info = f" (source: {source_document})" if source_document else " (all sources)"
    logger.info(f"🔍 Executing new hybrid search for query: '{query}'{filter_info}")
    
    try:
        # Case 1: User selected a specific source document
        if source_document and source_document.lower() not in ["all", "none", ""]:
            logger.info(f"📋 CASE: Selected specific source - {source_document}")
            
            # Check if the selected source is an Excel/CSV file
            if is_excel_or_csv_file(source_document):
                logger.info(f"📊 Source is Excel/CSV file, using pandas agent")
                return execute_pandas_agent_search(query, source_document)
            else:
                logger.info(f"📄 Source is regular document, using semantic search")
                # Get filtered documents for specific source using semantic search
                docs = get_filtered_documents(query, source_document)
                
                if not docs:
                    return f"No documents found for source '{source_document}'."
                
                # Generate response using semantic search
                context = format_docs(docs)
                formatted_prompt = prompt.format(context=context, question=query)
                result = get_llm().invoke(formatted_prompt)
                
                if hasattr(result, 'content'):
                    result = result.content
                
                return result
        
        # Case 2: User selected "all" sources (sequential search)
        else:
            logger.info(f"🌐 CASE: Search all sources (sequential approach)")
            
            # Step 1: Try semantic search first on all documents
            logger.info(f"🔍 STEP 1: Trying semantic search on all documents")
            try:
                docs = get_retriever().invoke(query)
                logger.info(f"Retrieved {len(docs)} documents from semantic search")
                
                if docs:
                    # Generate response using semantic search
                    context = format_docs(docs)
                    formatted_prompt = prompt.format(context=context, question=query)
                    semantic_result = get_llm().invoke(formatted_prompt)
                    
                    if hasattr(semantic_result, 'content'):
                        semantic_result = semantic_result.content
                    
                    # Step 2: Check if semantic result is meaningful
                    if is_meaningful_semantic_result(semantic_result):
                        logger.info(f"✅ STEP 1 SUCCESS: Semantic search found good answer")
                        return semantic_result
                    else:
                        logger.info(f"⚠️ STEP 1 PARTIAL: Semantic search result not meaningful")
                        logger.info(f"📊 STEP 2: Trying pandas agent as fallback")
                else:
                    logger.info(f"⚠️ STEP 1 NO DOCS: No documents retrieved from semantic search")
                    logger.info(f"📊 STEP 2: Trying pandas agent as fallback")
                    
            except Exception as semantic_error:
                logger.warning(f"⚠️ STEP 1 ERROR: Semantic search failed: {semantic_error}")
                logger.info(f"📊 STEP 2: Trying pandas agent as fallback")
            
            # Step 3: Try pandas agent as fallback
            try:
                pandas_result = execute_pandas_agent_search(query)
                
                # Check if pandas agent found a meaningful result
                if pandas_result and not pandas_result.startswith("No Excel or CSV files found") and not pandas_result.startswith("Error"):
                    logger.info(f"✅ STEP 2 SUCCESS: Pandas agent found answer")
                    return pandas_result
                else:
                    logger.info(f"⚠️ STEP 2 NO RESULTS: Pandas agent didn't find meaningful results")
                    
            except Exception as pandas_error:
                logger.warning(f"⚠️ STEP 2 ERROR: Pandas agent failed: {pandas_error}")
            
            # Step 4: If both failed, return appropriate message
            logger.info(f"❌ BOTH APPROACHES FAILED: No good results from semantic search or pandas agent")
            return "No answer found. I searched through both the document database and Excel/CSV files but couldn't find relevant information for your query."
            
    except Exception as e:
        logger.error(f"❌ Error executing hybrid search: {e}")
        raise

def search_with_debug_info(query: str, source_document: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute search with new logic and return both result and debug information.
    
    Args:
        query: The search query
        source_document: Optional source document to filter by
        
    Returns:
        Dictionary with result and debug information
    """
    filter_info = f" (source: {source_document})" if source_document else " (all sources)"
    logger.info(f"🐛 Executing debug search for query: '{query}'{filter_info}")
    
    try:
        debug_info = {
            "query": query,
            "source_filter": source_document,
            "search_strategy": None,
            "semantic_search": None,
            "pandas_search": None,
            "final_result_source": None
        }
        
        # Case 1: User selected a specific source document
        if source_document and source_document.lower() not in ["all", "none", ""]:
            debug_info["search_strategy"] = f"targeted_source_{source_document}"
            
            # Check if the selected source is an Excel/CSV file
            if is_excel_or_csv_file(source_document):
                debug_info["search_strategy"] = "targeted_pandas_only"
                debug_info["final_result_source"] = "pandas_agent"
                result = execute_pandas_agent_search(query, source_document)
                debug_info["pandas_search"] = {"attempted": True, "result_preview": result[:200] + "..." if len(result) > 200 else result}
            else:
                debug_info["search_strategy"] = "targeted_semantic_only" 
                debug_info["final_result_source"] = "semantic_search"
                # Get filtered documents for specific source using semantic search
                docs = get_filtered_documents(query, source_document)
                
                debug_info["semantic_search"] = {
                    "attempted": True,
                    "documents_found": len(docs),
                    "documents": []
                }
                
                for i, doc in enumerate(docs):
                    doc_info = {
                        "index": i + 1,
                        "preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                    }
                    debug_info["semantic_search"]["documents"].append(doc_info)
                
                if not docs:
                    result = f"No documents found for source '{source_document}'."
                else:
                    # Generate response using semantic search
                    context = format_docs(docs)
                    formatted_prompt = prompt.format(context=context, question=query)
                    result = get_llm().invoke(formatted_prompt)
                    
                    if hasattr(result, 'content'):
                        result = result.content
        
        # Case 2: User selected "all" sources (sequential search)
        else:
            debug_info["search_strategy"] = "sequential_all_sources"
            
            # Step 1: Try semantic search first
            try:
                docs = get_retriever().invoke(query)
                debug_info["semantic_search"] = {
                    "attempted": True,
                    "documents_found": len(docs),
                    "documents": []
                }
                
                for i, doc in enumerate(docs):
                    doc_info = {
                        "index": i + 1,
                        "preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                    }
                    debug_info["semantic_search"]["documents"].append(doc_info)
                
                if docs:
                    # Generate response using semantic search
                    context = format_docs(docs)
                    formatted_prompt = prompt.format(context=context, question=query)
                    semantic_result = get_llm().invoke(formatted_prompt)
                    
                    if hasattr(semantic_result, 'content'):
                        semantic_result = semantic_result.content
                    
                    debug_info["semantic_search"]["result_preview"] = semantic_result[:200] + "..." if len(semantic_result) > 200 else semantic_result
                    debug_info["semantic_search"]["meaningful"] = is_meaningful_semantic_result(semantic_result)
                    
                    # Check if semantic result is meaningful
                    if is_meaningful_semantic_result(semantic_result):
                        debug_info["final_result_source"] = "semantic_search"
                        result = semantic_result
                    else:
                        # Try pandas agent as fallback
                        pandas_result = execute_pandas_agent_search(query)
                        debug_info["pandas_search"] = {"attempted": True, "result_preview": pandas_result[:200] + "..." if len(pandas_result) > 200 else pandas_result}
                        
                        if pandas_result and not pandas_result.startswith("No Excel or CSV files found") and not pandas_result.startswith("Error"):
                            debug_info["final_result_source"] = "pandas_agent_fallback"
                            result = pandas_result
                        else:
                            debug_info["final_result_source"] = "no_good_results"
                            result = "No answer found. I searched through both the document database and Excel/CSV files but couldn't find relevant information for your query."
                else:
                    # No semantic docs, try pandas
                    pandas_result = execute_pandas_agent_search(query)
                    debug_info["pandas_search"] = {"attempted": True, "result_preview": pandas_result[:200] + "..." if len(pandas_result) > 200 else pandas_result}
                    
                    if pandas_result and not pandas_result.startswith("No Excel or CSV files found") and not pandas_result.startswith("Error"):
                        debug_info["final_result_source"] = "pandas_agent_fallback"
                        result = pandas_result
                    else:
                        debug_info["final_result_source"] = "no_good_results"
                        result = "No answer found. I searched through both the document database and Excel/CSV files but couldn't find relevant information for your query."
                        
            except Exception as semantic_error:
                debug_info["semantic_search"] = {"attempted": True, "error": str(semantic_error)}
                # Try pandas agent as fallback
                pandas_result = execute_pandas_agent_search(query)
                debug_info["pandas_search"] = {"attempted": True, "result_preview": pandas_result[:200] + "..." if len(pandas_result) > 200 else pandas_result}
                
                if pandas_result and not pandas_result.startswith("No Excel or CSV files found") and not pandas_result.startswith("Error"):
                    debug_info["final_result_source"] = "pandas_agent_fallback"
                    result = pandas_result
                else:
                    debug_info["final_result_source"] = "no_good_results"
                    result = "No answer found. I searched through both the document database and Excel/CSV files but couldn't find relevant information for your query."
        
        return {
            "result": result,
            "debug": debug_info
        }
        
    except Exception as e:
        logger.error(f"Error in debug search: {e}")
        raise
