import os
from dotenv import load_dotenv
import nest_asyncio
from llama_index.core.schema import TextNode
from typing import List, Tuple
import json
from llama_parse import LlamaParse
import requests
import time

_ = load_dotenv()

# Apply nest_asyncio to support nested event loops
# This is needed for LlamaParse operations in async web server contexts
try:
    nest_asyncio.apply()
    print("Applied nest_asyncio for nested event loop support")
except RuntimeError as e:
    # If already applied, that's fine
    print(f"nest_asyncio already configured: {str(e)}")

llama_cloud_api_key = os.getenv("LLAMA_CLOUD_API_KEY")

def get_text_nodes(json_list: List[dict]) -> List[TextNode]:
    text_nodes = []
    for idx, page in enumerate(json_list):
        text_node = TextNode(text=page["md"], metadata={"page": page["page"]})
        text_nodes.append(text_node)
    return text_nodes

system_prompt = """
You are a helpful file parser that can parse a file into a list of text nodes without losing any information.
"""

def initialize_parser():
    """
    Initialize the LlamaParse parser with proper error handling.
    """
    try:
        parser = LlamaParse(
            result_type="markdown",
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name="gemini-2.0-flash-001",
            invalidate_cache=True,
            system_prompt=system_prompt,
            llama_cloud_api_key=llama_cloud_api_key,
        )
        return parser
    except Exception as e:
        print(f"Failed to initialize LlamaParse: {str(e)}")
        raise ValueError(f"Failed to initialize LlamaParse: {str(e)}")

def parse_file_with_llama_parse(file_path: str, 
                max_retries: int = 3, 
                retry_delay: int = 2) -> Tuple[str, dict]:
    """
    Parse a file into a list of text nodes without losing any information.
    Includes retry logic and enhanced error handling.
    
    Args:
        file_path: Path to the file to parse
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        tuple: (text_content, metadata)
    """
    try:

        parser = initialize_parser()
        
        # Retry logic for parsing
        for attempt in range(max_retries):
            try:
                print(f"Parsing attempt {attempt + 1} of {max_retries}")
                json_objs = parser.get_json_result(file_path)
                
                if json_objs and isinstance(json_objs, list) and len(json_objs) > 0:
                    print(f"Successfully parsed file on attempt {attempt + 1}")
                    print(f"Number of pages found: {len(json_objs[0].get('pages', []))}")
                    
                    json_list = json_objs[0].get("pages", [])
                    if not json_list:
                        raise ValueError("No pages found in the parsed document")
                        
                    docs = get_text_nodes(json_list)
                    # get the text content
                    text_content = "\n".join([d.text for d in docs])
                    # remove ``````
                    text_content = text_content.replace("```text", "").replace("```", "")
                    # get the metadata
                    metadata = json_objs[0].get("metadata", {})
                    # return them separately as a tuple
                    return text_content, metadata
                
                if attempt < max_retries - 1:
                    print(f"No valid response received. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Network error occurred: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                raise
                
        raise ValueError(
            "Failed to get valid response from parser after multiple attempts. "
            "Please check your LLAMA_CLOUD_API_KEY, internet connection, and file format."
        )
        
    except Exception as e:
        print(f"Error parsing file '{file_path}': {str(e)}")
        print(f"LLAMA_CLOUD_API_KEY is {'set' if llama_cloud_api_key else 'not set'}")
        raise

