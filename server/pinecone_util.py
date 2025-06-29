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
    Check if a document exists in the Pinecone index by looking for vectors
    with the source metadata matching the file name.
    
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
        
        # Query the index with a proper embedding to find matching documents
        # Use a simple search to find any vectors with matching source metadata
        try:
            # Create a simple query embedding
            query_embedding = embeddings.embed_query("document check")
            
            query_response = index.query(
                vector=query_embedding,
                top_k=100,  # Get more results to ensure we find matches
                include_metadata=True,
                namespace=namespace,
                filter={"source": file_name}
            )
            
            # If we get any matches, the document exists
            document_exists = len(query_response.get('matches', [])) > 0
            print(f"Document {file_name} {'exists' if document_exists else 'does not exist'} in Pinecone")
            
            # Also check if there are vectors with the expected ID pattern
            base_filename = file_name.split(".")[0] if "." in file_name else file_name
            expected_id = f"{base_filename}_doc"
            
            # Try to fetch by ID as well
            try:
                fetch_response = index.fetch(ids=[expected_id], namespace=namespace)
                if hasattr(fetch_response, 'vectors') and fetch_response.vectors:
                    print(f"Found document by ID: {expected_id}")
                    return True
                elif hasattr(fetch_response, 'get') and fetch_response.get('vectors', {}):
                    print(f"Found document by ID: {expected_id}")
                    return True
            except Exception as fetch_error:
                print(f"Could not fetch by ID {expected_id}: {fetch_error}")
            
            return document_exists
            
        except Exception as query_error:
            print(f"Error querying for document {file_name}: {query_error}")
            return False
    
    except Exception as e:
        print(f"Error checking if document exists: {e}")
        return False


def delete_document_from_pinecone(file_name: str) -> bool:
    """
    Delete all vectors for a specific document from the Pinecone index.
    
    Args:
        file_name: The name of the file to delete from Pinecone
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    print(f"Deleting document {file_name} from Pinecone")
    try:
        index = create_index()
        namespace = "biz-to-bricks-namespace"
        
        # Delete vectors matching the source filter
        delete_response = index.delete(
            filter={"source": file_name},
            namespace=namespace
        )
        
        print(f"Successfully deleted document {file_name} from Pinecone")
        return True
        
    except Exception as e:
        print(f"Error deleting document {file_name} from Pinecone: {e}")
        return False