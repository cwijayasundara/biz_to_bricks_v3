#!/usr/bin/env python3
"""
Debug script to check environment variables in production
"""
import os
from dotenv import load_dotenv

load_dotenv()

def debug_environment():
    """Debug environment variables and API connectivity."""
    print("🔍 Debugging environment variables...")
    
    # Check all environment variables
    env_vars = [
        "PINECONE_API_KEY",
        "OPENAI_API_KEY", 
        "PINECONE_ENVIRONMENT",
        "PINECONE_INDEX_NAME",
        "PINECONE_NAMESPACE"
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Show first 8 characters for API keys, full value for others
            if "API_KEY" in var:
                print(f"✅ {var}: {value[:8]}... (length: {len(value)})")
                
                # Clean up quotes
                cleaned_value = value.strip("\"'")
                if cleaned_value != value:
                    print(f"   ⚠️  Quotes detected! Cleaned: {cleaned_value[:8]}... (length: {len(cleaned_value)})")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
    
    # Test Pinecone connection
    print("\n🔗 Testing Pinecone connection...")
    try:
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if pinecone_api_key:
            pinecone_api_key = pinecone_api_key.strip("\"'")
        
        import pinecone
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        indexes = pc.list_indexes()
        print(f"✅ Pinecone connection successful! Found indexes: {indexes.names()}")
        
        # Test specific index
        index_name = os.getenv("PINECONE_INDEX_NAME", "biz-to-bricks-vector-store")
        if index_name in indexes.names():
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            print(f"✅ Index stats: {stats}")
        else:
            print(f"❌ Index '{index_name}' not found!")
            
    except Exception as e:
        print(f"❌ Pinecone connection failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    debug_environment()