import os
from dotenv import load_dotenv
import pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Load environment variables
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")

# Import configuration constants
from config import PINECONE_INDEX_NAME, PINECONE_NAMESPACE, EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                              model=EMBEDDING_MODEL_NAME)

def create_index():
    """
    Creates or connects to a Pinecone index for document storage.
    Uses generic configuration constants for index name and namespace.
    """
    try:
        # Initialize Pinecone
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        
        # Check if index exists
        existing_indexes = pc.list_indexes()
        
        if PINECONE_INDEX_NAME not in existing_indexes.names():
            print(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
            
            # Create index with proper spec configuration for hybrid search
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=int(EMBEDDING_DIMENSION),  # OpenAI text-embedding-3-large dimension
                metric="dotproduct",  # Required for hybrid search (dense + sparse)
                spec=pinecone.ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            
            # Wait for index to be ready
            while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
                import time
                time.sleep(1)
            print(f"Index {PINECONE_INDEX_NAME} created successfully")
        else:
            print(f"Using existing index: {PINECONE_INDEX_NAME}")
        
        return pc.Index(PINECONE_INDEX_NAME)
        
    except Exception as e:
        logger.error(f"Error creating/connecting to Pinecone index: {e}")
        raise

def test_pinecone_connection():
    """
    Test the connection to Pinecone and verify index accessibility.
    """
    try:
        index = create_index()
        
        # Get index statistics
        stats = index.describe_index_stats()
        print(f"Index statistics: {stats}")
        
        # Test namespace access
        namespace = PINECONE_NAMESPACE
        
        # Check if the namespace exists
        if namespace not in stats.get('namespaces', {}):
            print(f"Namespace '{namespace}' not found in index")
            print(f"Available namespaces: {list(stats.get('namespaces', {}).keys())}")
            return False
        
        print(f"Successfully connected to Pinecone index: {PINECONE_INDEX_NAME}")
        print(f"Using namespace: {namespace}")
        return True
        
    except Exception as e:
        logger.error(f"Error testing Pinecone connection: {e}")
        return False

def test_vector_operations():
    """
    Test basic vector operations to ensure the index is working correctly.
    """
    try:
        index = create_index()
        
        # Test vector
        test_vector = [0.1] * int(EMBEDDING_DIMENSION)  # OpenAI text-embedding-3-large dimension
        test_id = "test_vector_001"
        namespace = PINECONE_NAMESPACE
        
        # Upsert test vector
        index.upsert(
            vectors=[(test_id, test_vector, {"test": "data"})],
            namespace=namespace
        )
        print(f"Successfully upserted test vector to namespace: {namespace}")
        
        # Fetch test vector
        fetch_response = index.fetch(ids=[test_id], namespace=namespace)
        if test_id in fetch_response['vectors']:
            print("Successfully fetched test vector")
        else:
            print("Failed to fetch test vector")
            return False
        
        # Delete test vector
        index.delete(ids=[test_id], namespace=namespace)
        print("Successfully deleted test vector")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing vector operations: {e}")
        return False

def list_all_vectors():
    """
    List all vectors in the index with their metadata.
    """
    try:
        index = create_index()
        
        # Get index statistics
        stats = index.describe_index_stats()
        namespace = PINECONE_NAMESPACE
        
        # Check if the namespace exists
        if namespace not in stats.get('namespaces', {}):
            print(f"Namespace '{namespace}' not found in index")
            return []
        
        namespace_stats = stats['namespaces'][namespace]
        print(f"Namespace '{namespace}' contains {namespace_stats['vector_count']} vectors")
        
        # Query to get all vectors (limited to avoid memory issues)
        query_response = index.query(
            vector=[0.0] * int(EMBEDDING_DIMENSION),  # Dummy vector for query
            top_k=1000,  # Limit results
            include_metadata=True,
            namespace=namespace
        )
        
        vectors = []
        for match in query_response.get('matches', []):
            vector_info = {
                'id': match['id'],
                'score': match['score'],
                'metadata': match.get('metadata', {})
            }
            vectors.append(vector_info)
        
        return vectors
        
    except Exception as e:
        logger.error(f"Error listing vectors: {e}")
        return []

def delete_all_vectors():
    """
    Delete all vectors from the index (use with caution).
    """
    try:
        index = create_index()
        namespace = PINECONE_NAMESPACE
        
        # Delete all vectors in the namespace
        index.delete(
            delete_all=True,
            namespace=namespace
        )
        
        print(f"Successfully deleted all vectors from namespace: {namespace}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting all vectors: {e}")
        return False