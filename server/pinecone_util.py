from pinecone import Pinecone
from dotenv import load_dotenv
import os
from pinecone import ServerlessSpec
import time
from langchain_openai import OpenAIEmbeddings

load_dotenv()

pinecone_api_key = os.getenv("PINECONE_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
openai_api_key = os.getenv("OPENAI_API_KEY")

INDEX_NAME = "biz-to-bricks-vector-store-hybrid"

embeddings = OpenAIEmbeddings(api_key=openai_api_key, 
                              model="text-embedding-3-large")

pc = Pinecone(
    api_key=pinecone_api_key,
    environment=pinecone_env
)

def create_index():
    """
    This function creates a new Pinecone index if it doesn't exist.
    """
    try:
        # Check if index exists
        existing_indexes = pc.list_indexes()
        
        if INDEX_NAME not in existing_indexes.names():
            print(f"Creating new Pinecone index: {INDEX_NAME}")
            pc.create_index(
                name=INDEX_NAME,
                dimension=3072,
                metric="dotproduct",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for index to be ready
            while not pc.describe_index(INDEX_NAME).status['ready']:
                time.sleep(1)
            print(f"Index {INDEX_NAME} created successfully")
        else:
            print(f"Using existing index: {INDEX_NAME}")
            
        return pc.Index(INDEX_NAME)
    except Exception as e:
        print(f"Error creating/accessing index: {str(e)}")
        raise

def document_exists_in_pinecone(file_name: str) -> bool:
    """
    Check if a document exists in the Pinecone index.
    
    Args:
        file_name: The name of the file to check
        
    Returns:
        bool: True if the document exists, False otherwise
    """
    print(f"Checking if {file_name} exists in Pinecone")
    try:
        index = create_index()
        namespace = "biz-to-bricks-namespace"
        
        # Try to fetch metadata about the index
        stats = index.describe_index_stats()
        
        # Check if the namespace exists
        if namespace not in stats.get('namespaces', {}):
            print(f"Namespace '{namespace}' not found in index")
            return False
        
        # Query the index to see if vectors for this document exist
        # Use a simple query embedding to search
        query_embedding = embeddings.embed_query(f"filename:{file_name}")

        query_response = index.query(
            vector=query_embedding,
            top_k=1,
            include_metadata=True,
            namespace=namespace,
            filter={"source": file_name}
        )
        
        # If we get any matches, the document exists
        return len(query_response.get('matches', [])) > 0
    
    except Exception as e:
        print(f"Error checking if document exists: {e}")
        return False