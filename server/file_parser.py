import os
from dotenv import load_dotenv
import nest_asyncio
from llama_index.core.schema import TextNode
from typing import List, Tuple, Dict, Any
import json
from llama_parse import LlamaParse
import requests
import time
import re

_ = load_dotenv()

# Apply nest_asyncio to support nested event loops
# This is needed for LlamaParse operations in async web server contexts
try:
    nest_asyncio.apply()
    print("Applied nest_asyncio for nested event loop support")
except (RuntimeError, ValueError) as e:
    # Skip if already applied or incompatible loop type (e.g., uvloop)
    print(f"Skipping nest_asyncio patch: {e}")

llama_cloud_api_key = os.getenv("LLAMA_CLOUD_API_KEY")

def clean_parsed_content(text: str) -> str:
    """
    Clean up parsed content by removing NaN values and formatting issues.
    
    Args:
        text: Raw parsed text from LlamaParse
        
    Returns:
        Cleaned text content
    """
    import re
    
    # Remove common NaN representations
    nan_patterns = [
        r'\bnan\b',  # nan
        r'\bNaN\b',  # NaN
        r'\bNAN\b',  # NAN
        r'\bNone\b',  # None
        r'\bnull\b',  # null
        r'\bNULL\b',  # NULL
        r'\b#N/A\b',  # #N/A
        r'\b#N/A N/A\b',  # #N/A N/A
        r'\b#NA\b',  # #NA
        r'\b-1.#IND\b',  # -1.#IND
        r'\b-1.#QNAN\b',  # -1.#QNAN
        r'\b-#IND\b',  # -#IND
        r'\b-#QNAN\b',  # -#QNAN
        r'\b#DIV/0!\b',  # #DIV/0!
        r'\b#REF!\b',  # #REF!
        r'\b#VALUE!\b',  # #VALUE!
        r'\b#NAME?\b',  # #NAME?
        r'\b#NUM!\b',  # #NUM!
        r'\b#NULL!\b',  # #NULL!
    ]
    
    cleaned_text = text
    
    # Replace NaN patterns with empty string
    for pattern in nan_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
    
    # Remove empty table cells
    cleaned_text = re.sub(r'\|\s*\|\s*', '| | ', cleaned_text)
    
    # Remove excessive whitespace
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    
    # Remove empty lines at the beginning and end
    cleaned_text = cleaned_text.strip()
    
    # Clean up table formatting
    cleaned_text = re.sub(r'\|\s*\|', '| |', cleaned_text)
    cleaned_text = re.sub(r'\|\s*$', '|', cleaned_text, flags=re.MULTILINE)
    
    return cleaned_text

def convert_html_tables_to_markdown(text: str) -> str:
    """
    Convert HTML tables to Markdown tables in the given text.
    
    Args:
        text: Text that may contain HTML tables
        
    Returns:
        Text with HTML tables converted to Markdown
    """
    # Find all HTML tables
    table_pattern = r'<table[^>]*>(.*?)</table>'
    table_matches = re.findall(table_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for table_match in table_matches:
        # Extract rows
        rows = []
        tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_match, re.DOTALL | re.IGNORECASE)
        
        for tr_match in tr_matches:
            row = []
            # Extract cells (th and td)
            cell_matches = re.findall(r'<(th|td)[^>]*>(.*?)</\1>', tr_match, re.DOTALL | re.IGNORECASE)
            
            for cell_type, cell_content in cell_matches:
                # Clean cell content
                cell_content = re.sub(r'<[^>]*>', '', cell_content).strip()
                row.append(cell_content)
            
            if row:  # Only add non-empty rows
                rows.append(row)
        
        if not rows:
            continue
        
        # Convert to Markdown table
        markdown_lines = []
        
        # Add header row
        if rows:
            header_row = rows[0]
            markdown_lines.append('| ' + ' | '.join(header_row) + ' |')
            
            # Add separator
            separator = '|' + '---|' * len(header_row)
            markdown_lines.append(separator)
            
            # Add data rows
            for row in rows[1:]:
                # Pad row to match header length
                while len(row) < len(header_row):
                    row.append('')
                # Truncate row if longer than header
                row = row[:len(header_row)]
                markdown_lines.append('| ' + ' | '.join(row) + ' |')
        
        markdown_table = '\n'.join(markdown_lines)
        
        # Replace the HTML table with Markdown table
        text = text.replace(f'<table>{table_match}</table>', markdown_table)
        text = text.replace(f'<table border="1">{table_match}</table>', markdown_table)
    
    return text

def get_text_nodes(json_list: List[dict]) -> List[TextNode]:
    text_nodes = []
    for idx, page in enumerate(json_list):
        text_node = TextNode(text=page["md"], metadata={"page": page["page"]})
        text_nodes.append(text_node)
    return text_nodes

system_prompt = """
You are a helpful file parser that can parse a file into a list of text nodes without losing any information.
IMPORTANT: Preserve ALL content from the original document including:
- All text fields and values
- All table data and structure
- All headers, titles, and labels
- All formatting and layout information
- All metadata and field names
- All numerical values and units
- All special characters and symbols

Do not drop, summarize, or omit any content from the original document.
"""

def initialize_parser(file_path: str = None):
    """
    Initialize the LlamaParse parser with proper error handling.
    Optimized for maximum content preservation and cleaning.
    
    Args:
        file_path: Optional file path to determine appropriate parser settings
    """
    try:
        print(f"🔧 Using LlamaParse for all file types: {file_path}")
        parser = LlamaParse(
            result_type="text",  # Use text instead of markdown to avoid validation issues
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name="gemini-2.0-flash-001",
            invalidate_cache=True,
            system_prompt=system_prompt,
            # Optimized settings for content preservation and cleaning
            num_workers=1,  # Use single worker for better consistency
            verbose=True,    # Enable verbose logging for debugging
            language="en",   # Specify language for better parsing
        )
        return parser
    except Exception as e:
        print(f"Failed to initialize LlamaParse: {str(e)}")
        raise ValueError(f"Failed to initialize LlamaParse: {str(e)}")

def parse_excel_csv_with_pandas(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse Excel/CSV files using pandas to avoid LlamaParse validation issues.
    
    Args:
        file_path: Path to the Excel/CSV file
        
    Returns:
        Tuple of (parsed_content, metadata)
    """
    try:
        import pandas as pd
        from pathlib import Path
        
        print(f"📊 Using pandas to parse Excel/CSV file: {file_path}")
        
        # Load the data with pandas
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            file_type = "CSV"
        else:  # Excel files
            df = None
            engines_to_try = ['openpyxl', 'xlrd']
            
            for engine in engines_to_try:
                try:
                    df = pd.read_excel(file_path, engine=engine)
                    print(f"✅ Successfully read with {engine} engine")
                    break
                except Exception as e:
                    print(f"Failed to read with {engine} engine: {e}")
                    continue
            
            if df is None:
                try:
                    df = pd.read_csv(file_path)
                    print("✅ Successfully read as CSV despite Excel extension")
                    file_type = "CSV"
                except Exception as csv_error:
                    raise Exception(f"Could not read file as Excel or CSV: {csv_error}")
            else:
                file_type = "Excel"
        
        # Convert all data to strings to avoid any type issues
        df = df.astype(str)
        
        # Replace NaN values with empty strings
        df = df.fillna('')
        
        # Convert DataFrame to markdown table
        markdown_content = df.to_markdown(index=False)
        
        # Create comprehensive content format
        content = f"""# {Path(file_path).name}

## Data Content

{markdown_content}

## File Information
- **File Name:** {Path(file_path).name}
- **Total Rows:** {df.shape[0]:,}
- **Total Columns:** {df.shape[1]}
- **File Type:** {file_type}
- **Columns:** {', '.join(df.columns.tolist())}

## Data Summary
- **File Size:** {os.path.getsize(file_path):,} bytes
- **Parsing Method:** Pandas
- **Data Types:** All values converted to strings for consistency
"""
        
        # Clean the content
        content = clean_parsed_content(content)
        
        # Create metadata
        metadata = {
            "file_name": Path(file_path).stem,
            "file_path": file_path,
            "file_type": "excel_csv",
            "parsing_method": "pandas",
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": df.columns.tolist(),
            "file_size_bytes": os.path.getsize(file_path)
        }
        
        print(f"✅ Successfully parsed {file_type} file with pandas: {len(content)} characters")
        return content, metadata
        
    except Exception as e:
        print(f"❌ Pandas parsing failed: {e}")
        raise Exception(f"Failed to parse Excel/CSV file with pandas: {e}")

def parse_file_with_llama_parse(file_path: str, 
                max_retries: int = 3, 
                retry_delay: int = 2) -> Tuple[str, dict]:
    """
    Parse a file into markdown format using LlamaParse.
    Uses the proper LlamaParse API methods and converts HTML tables to Markdown.
    Cleans up NaN values and formatting issues from the output.
    
    Args:
        file_path: Path to the file to parse
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        tuple: (text_content, metadata)
    """
    # Check file extension first
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # For Excel/CSV files, use pandas directly to avoid LlamaParse validation issues
    if file_ext in ['.xlsx', '.xls', '.csv']:
        print(f"📊 Using pandas for Excel/CSV file: {file_path}")
        return parse_excel_csv_with_pandas(file_path)
    
    try:
        # Use LlamaParse for other file types
        parser = initialize_parser(file_path)
        
        # Retry logic for parsing
        for attempt in range(max_retries):
            try:
                print(f"Parsing attempt {attempt + 1} of {max_retries}")
                
                # Use the proper LlamaParse API method to get documents
                result = parser.parse(file_path)
                
                # Get text documents and convert to markdown
                documents = result.get_text_documents(split_by_page=True)
                
                if documents and len(documents) > 0:
                    print(f"Successfully parsed file on attempt {attempt + 1}")
                    print(f"Number of documents found: {len(documents)}")
                    
                    # Extract text content from documents
                    text_content = "\n\n".join([doc.text for doc in documents])
                    
                    # Clean up any remaining artifacts
                    text_content = text_content.replace("```text", "").replace("```", "")
                    
                    # Convert HTML tables to Markdown tables
                    text_content = convert_html_tables_to_markdown(text_content)
                    
                    # Clean up NaN values and formatting issues
                    text_content = clean_parsed_content(text_content)
                    
                    # Get metadata from the result
                    metadata = result.metadata if hasattr(result, 'metadata') else {}
                    
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



