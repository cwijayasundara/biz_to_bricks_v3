#!/usr/bin/env python3
"""
Document Processing Client
==========================

A professional Streamlit application for interacting with the Document Processing API.
Provides a comprehensive interface for uploading, parsing, editing, summarizing,
and querying documents using AI-powered tools.

Author: Biz To Bricks Team
Version: 3.0.0
"""

import streamlit as st
import requests
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import sys
from datetime import datetime
import pandas as pd
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Application configuration settings"""
    
    # API Configuration
    # BASE_URL = "http://localhost:8004"
    BASE_URL = "https://document-processing-service-38231329931.us-central1.run.app"
    
    # API Endpoints
    ENDPOINTS = {
        'upload': f"{BASE_URL}/uploadfile/",
        'list_uploaded': f"{BASE_URL}/listfiles/uploaded_files",
        'list_parsed': f"{BASE_URL}/listfiles/parsed_files",
        'parse': f"{BASE_URL}/parsefile/",
        'save_content': f"{BASE_URL}/savecontent/",
        'summarize': f"{BASE_URL}/summarizecontent",
        'generate_questions': f"{BASE_URL}/generatequestions",
        'generate_faq': f"{BASE_URL}/generatefaq",
        'save_and_ingest': f"{BASE_URL}/saveandingst/",
        'hybrid_search': f"{BASE_URL}/hybridsearch/",
        'pandas_query': f"{BASE_URL}/querypandas/",
        'source_documents': f"{BASE_URL}/sourcedocuments/",
    }
    
    # File Configuration
    SAMPLE_FILES_DIR = Path("../docs")
    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.xlsx', '.xls', '.csv']
    
    # UI Configuration
    MAX_FILE_SIZE_MB = 200
    PAGE_TITLE = "Document Processor 📄"
    PAGE_SUBTITLE = "Upload, view, parse, and summarize documents using FastAPI backend."

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_file_type_info(filename: str) -> Dict[str, str]:
    """
    Get file type information for display purposes.
    
    Args:
        filename: Name of the file to analyze
        
    Returns:
        Dictionary with file type information including icon and type
    """
    # Check if there's a corresponding original file
    uploaded_files = fetch_files(Config.ENDPOINTS['list_uploaded'], "")
    
    # Remove .md extension from parsed filename to get base name
    base_name = filename.replace('.md', '') if filename.endswith('.md') else filename
    
    # Look for original file with same base name
    for uploaded_file in uploaded_files:
        if Path(uploaded_file).stem == base_name:
            extension = Path(uploaded_file).suffix.lower()
            if extension in ['.xlsx', '.xls']:
                return {'type': 'Excel', 'icon': '📊', 'original': uploaded_file}
            elif extension == '.csv':
                return {'type': 'CSV', 'icon': '📋', 'original': uploaded_file}
            elif extension == '.pdf':
                return {'type': 'PDF', 'icon': '📄', 'original': uploaded_file}
    
    # Default fallback
    return {'type': 'Document', 'icon': '📄', 'original': filename}

def get_enhanced_file_list(files: List[str]) -> List[Dict[str, str]]:
    """
    Get enhanced file list with type information for better UX.
    
    Args:
        files: List of filenames
        
    Returns:
        List of dictionaries with enhanced file information
    """
    enhanced_files = []
    for filename in files:
        file_info = get_file_type_info(filename)
        display_name = filename.replace('.md', '') if filename.endswith('.md') else filename
        enhanced_files.append({
            'filename': filename,
            'display': f"{file_info['icon']} {display_name} ({file_info['type']})",
            'type': file_info['type'],
            'icon': file_info['icon']
        })
    return enhanced_files

def make_api_request(
    url: str, 
    method: str = "get", 
    data: Optional[Dict] = None, 
    files: Optional[Dict] = None, 
    handle_error: bool = True
) -> Dict[str, Any]:
    """
    Make API request with proper error handling and logging.
    
    Args:
        url: API endpoint URL
        method: HTTP method (get, post, delete)
        data: Request data for POST requests
        files: Files for upload requests
        handle_error: Whether to handle errors with Streamlit UI
        
    Returns:
        API response as dictionary
    """
    try:
        if method.lower() == "post":
            if files:
                response = requests.post(url, files=files)
            else:
                response = requests.post(url, json=data)
        elif method.lower() == "delete":
            response = requests.delete(url)
        else:  # GET
            response = requests.get(url)
        
        if 200 <= response.status_code < 300:
            return response.json()
        else:
            error_msg = f"API Error {response.status_code}: {response.text}"
            if handle_error:
                st.error(error_msg)
            return {"error": error_msg}
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Connection Error: {str(e)}"
        if handle_error:
            st.error(error_msg)
        return {"error": error_msg}
    except json.JSONDecodeError:
        error_msg = "Invalid JSON response from server"
        if handle_error:
            st.error(error_msg)
        return {"error": error_msg}

def fetch_files(url: str, message: str = "Fetching files...") -> List[str]:
    """
    Fetch files from API endpoint with loading indicator.
    
    Args:
        url: API endpoint URL
        message: Loading message to display
        
    Returns:
        List of filenames
    """
    with st.spinner(message):
        result = make_api_request(url)
        return result.get("files", []) if "error" not in result else []

def show_success_message(message: str, details: Optional[str] = None) -> None:
    """Show success message with optional details"""
    st.success(message)
    if details:
        with st.expander("Details", expanded=False):
            st.write(details)

def show_error_message(message: str, error_details: Optional[str] = None) -> None:
    """Show error message with optional details"""
    st.error(message)
    if error_details:
        with st.expander("Error Details", expanded=False):
            st.code(error_details)

def create_file_selector(
    files: List[str], 
    label: str, 
    help_text: str = "", 
    key: str = ""
) -> str:
    """
    Create a professional file selector with enhanced display.
    
    Args:
        files: List of files to display
        label: Label for the selector
        help_text: Help text for the selector
        key: Unique key for the selector
        
    Returns:
        Selected filename or "None" if no selection
    """
    if not files:
        st.info("No files available. Please upload and parse files first.")
        return "None"
    
    enhanced_files = get_enhanced_file_list(files)
    display_options = ["None"] + [item['display'] for item in enhanced_files]
    
    selected_display = st.selectbox(
        label,
        display_options,
        key=key,
        help=help_text
    )
    
    if selected_display == "None":
        return "None"
    
    # Get the actual filename
    for item in enhanced_files:
        if item['display'] == selected_display:
            return item['filename']
    
    return "None"

def check_server_connectivity() -> bool:
    """
    Check if the server is accessible.
    
    Returns:
        True if server is accessible, False otherwise
    """
    try:
        response = requests.get(f"{Config.BASE_URL}/", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def display_server_status() -> None:
    """Display server connectivity status in the sidebar"""
    with st.sidebar:
        st.subheader("🔌 Server Status")
        if check_server_connectivity():
            st.success("✅ Connected")
            st.write(f"Server: {Config.BASE_URL}")
        else:
            st.error("❌ Disconnected")
            st.write("Please check server connection")

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def create_info_box(title: str, content: str, icon: str = "ℹ️") -> None:
    """
    Create a styled information box.
    
    Args:
        title: Title of the info box
        content: Content to display
        icon: Icon to display (default: ℹ️)
    """
    with st.expander(f"{icon} {title}", expanded=False):
        st.markdown(content)

def parse_questions_to_table(questions_data: Union[str, List[str]]) -> pd.DataFrame:
    """
    Parse questions from text or list and convert to DataFrame for table display.
    
    Args:
        questions_data: Raw questions data from API response (string or list)
        
    Returns:
        DataFrame with questions formatted for table display
    """
    if not questions_data:
        return pd.DataFrame({"Question #": [], "Question": []})
    
    # Handle different input types
    if isinstance(questions_data, list):
        # If it's already a list, use it directly
        questions_list = [str(q).strip() for q in questions_data if str(q).strip()]
    elif isinstance(questions_data, str):
        if questions_data == "No questions available.":
            return pd.DataFrame({"Question #": [], "Question": []})
        # Split by lines and filter out empty lines
        questions_list = [line.strip() for line in questions_data.split('\n') if line.strip()]
    else:
        # Convert to string if it's neither string nor list
        questions_list = [str(questions_data).strip()]
    
    questions_table_data = []
    question_number = 1
    
    for question in questions_list:
        if not question:
            continue
            
        # Check if question starts with a number (like "1.", "2.", etc.)
        if re.match(r'^\d+\.', question):
            # Extract the question text after the number
            question_text = re.sub(r'^\d+\.\s*', '', question)
            questions_table_data.append({
                "Question #": question_number,
                "Question": question_text
            })
        else:
            # Handle questions that might not be numbered
            questions_table_data.append({
                "Question #": question_number,
                "Question": question
            })
        question_number += 1
    
    # If no questions were parsed and it's a string, try to split by common patterns
    if not questions_table_data and isinstance(questions_data, str):
        # Try splitting by question marks or other patterns
        potential_questions = re.split(r'[?]\s*', questions_data)
        for i, q in enumerate(potential_questions):
            if q.strip():
                questions_table_data.append({
                    "Question #": i + 1,
                    "Question": q.strip() + ("?" if not q.strip().endswith("?") else "")
                })
    
    # Create DataFrame
    df = pd.DataFrame(questions_table_data)
    return df if not df.empty else pd.DataFrame({"Question #": [1], "Question": [str(questions_data)]})

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def apply_custom_styling() -> None:
    """Apply custom CSS styling to the application"""
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 1rem;
        }
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stAlert {
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        .stExpander {
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

def main() -> None:
    """Main application entry point"""
    # Page configuration
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom styling
    apply_custom_styling()
    
    # Display server status
    display_server_status()
    
    # Header
    st.title(Config.PAGE_TITLE)
    st.markdown(f"*{Config.PAGE_SUBTITLE}*")
    
    # Show app info in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("""
        **📱 App Info**
        - Version: 3.0.0
        - Built with Streamlit
        - FastAPI Backend
        """)
        
        st.markdown("---")
        st.markdown("""
        **🔗 Quick Links**
        - [API Docs](http://localhost:8004/docs)
        - [Health Check](http://localhost:8004/)
        """)
    
    # Create tabs for different functionality
    tab_names = [
        "📤 Upload", "📋 View Files", "📝 Parse Files", "📊 Summarize", 
        "❓ Generate Questions", "📋 Generate FAQ", 
        "🔍 Hybrid Search", "📊 Excel Search"
    ]
    
    tabs = st.tabs(tab_names)
    
    # Tab implementations
    with tabs[0]:
        upload_files_tab()
    
    with tabs[1]:
        view_files_tab()
        
    with tabs[2]:
        parse_files_tab()
        
    with tabs[3]:
        summarize_files_tab()
    
    with tabs[4]:
        generate_questions_tab()

    with tabs[5]:
        generate_faq_tab()

    with tabs[6]:
        hybrid_search_tab()

    with tabs[7]:
        excel_search_tab()

# =============================================================================
# TAB IMPLEMENTATIONS
# =============================================================================

def upload_files_tab() -> None:
    """Upload files tab implementation"""
    st.header("Upload Files")
    
    # Documentation and instructions
    create_info_box(
        "📋 Upload Instructions",
        f"""
        **Supported File Types:**
        - 📄 **PDF**: Documents, reports, manuals
        - 📊 **Excel**: .xlsx, .xls spreadsheets  
        - 📋 **CSV**: Comma-separated data files
        - 📝 **Text**: .txt, .docx files
        
        **File Size Limit:** {Config.MAX_FILE_SIZE_MB}MB per file
        
        **Process:**
        1. Choose files using the file uploader below
        2. Files are automatically uploaded to the server
        3. Use other tabs to parse, summarize, and query your documents
        """
    )
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=['pdf', 'docx', 'txt', 'xlsx', 'xls', 'csv'],
        accept_multiple_files=True,
        help=f"Maximum file size: {Config.MAX_FILE_SIZE_MB}MB"
    )
    
    if uploaded_files:
        st.write(f"Selected {len(uploaded_files)} file(s) for upload:")
        
        for file in uploaded_files:
            formatted_size = format_file_size(file.size)
            file_info = get_file_type_info(file.name)
            st.write(f"• {file_info['icon']} {file.name} ({formatted_size})")
            
        if st.button("📤 Upload Files", type="primary"):
            upload_files_to_server(uploaded_files)
    
    # Sample files section
    show_sample_files_section()

def upload_files_to_server(uploaded_files: List) -> None:
    """Upload files to the server"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file in enumerate(uploaded_files):
        status_text.text(f"Uploading {file.name}...")
        
        files = {"file": (file.name, file.getvalue(), file.type)}
        result = make_api_request(Config.ENDPOINTS['upload'], method="post", files=files)
        
        if "error" in result:
            st.error(f"❌ Failed to upload {file.name}: {result['error']}")
        else:
            st.success(f"✅ Successfully uploaded {file.name}")
            
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text("Upload complete!")

def show_sample_files_section() -> None:
    """Show sample files section"""
    if not Config.SAMPLE_FILES_DIR.exists():
        return
        
    st.subheader("📁 Sample Files")
    st.write("Quick upload sample files for testing:")
    
    sample_files = list(Config.SAMPLE_FILES_DIR.glob("*.*"))
    if sample_files:
        selected_samples = st.multiselect(
            "Select sample files to upload",
            [f.name for f in sample_files],
            help="These are sample files from the docs folder"
        )
        
        if selected_samples and st.button("📤 Upload Sample Files"):
            for sample_name in selected_samples:
                sample_path = Config.SAMPLE_FILES_DIR / sample_name
                if sample_path.exists():
                    with open(sample_path, 'rb') as f:
                        files = {"file": (sample_name, f.read(), "application/octet-stream")}
                        result = make_api_request(Config.ENDPOINTS['upload'], method="post", files=files)
                        
                        if "error" in result:
                            st.error(f"❌ Failed to upload {sample_name}")
                        else:
                            st.success(f"✅ Successfully uploaded {sample_name}")

def view_files_tab() -> None:
    """View Files tab implementation"""
    st.header("View Files")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        refresh = st.button("🔄 Refresh", help="Reload the file list from server")
    
    # Get the list of files from the server
    files = fetch_files(Config.ENDPOINTS['list_uploaded'], "Loading file list...")
    
    if files:
        st.success(f"Found {len(files)} files on the server")
        
        # Create a table of files
        file_table = "<table style='width:100%'><tr><th>Index</th><th>Filename</th></tr>"
        for idx, file in enumerate(files):
            file_table += f"<tr><td>{idx+1}</td><td>{file}</td></tr>"
        file_table += "</table>"
        
        st.markdown(file_table, unsafe_allow_html=True)
    else:
        st.info("No files found on the server.")

def parse_files_tab() -> None:
    """Parse Files tab implementation"""
    st.header("Parse Files")
    
    # Get the list of files from the server
    files = fetch_files(Config.ENDPOINTS['list_uploaded'], "Loading files to parse...")
    
    if files:
        selected_file = create_file_selector(files, "Select a file to parse", "Choose a file to convert to structured text")
        # Clear previous parsed file if selection changes
        if "parsed_file" in st.session_state and st.session_state["parsed_file"] != selected_file:
            del st.session_state["parsed_file"]
        if selected_file != "None":
            st.info(f"Selected: {selected_file}")
            # Trigger parse once
            parse_clicked = st.button(
                "Parse File", key=f"parse_{selected_file}", type="primary"
            )
            if parse_clicked:
                st.session_state["parsed_file"] = selected_file
        # Always display parsed content once parsed
        if st.session_state.get("parsed_file") == selected_file:
            display_parsed_file(selected_file)
    else:
        st.info("No files found on the server to parse.")

def display_parsed_file(filename: str) -> None:
    """Parse a file and display its content with editing capabilities"""
    try:
        with st.spinner(f"Parsing file {filename}..."):
            result = make_api_request(f"{Config.ENDPOINTS['parse']}{filename}")
        
        if "error" not in result:
            st.success(f"File parsed successfully!")
            
            # Store original content for comparison
            if "original_content" not in st.session_state:
                st.session_state.original_content = {}
                
            text_content = result.get("text_content", "No content found")
            # Only initialize original content once
            if filename not in st.session_state.original_content:
                st.session_state.original_content[filename] = text_content
            
            # Edit Parsed Content Expander
            with st.expander("Edit Parsed Content", expanded=True):
                text_area_key = f"edited_content_{filename}"
                # Use text_area default for initial value, no manual session state assignment
                edited_content = st.text_area(
                    "You can edit the content below:",
                    text_content,
                    height=500,
                    key=text_area_key
                )
                
                # Save Changes Button inside expander
                col1, col2 = st.columns(2)
                with col1:
                    save_clicked = st.button("💾 Save Changes", key=f"save_{filename}")
                with col2:
                    save_ingest_clicked = st.button("💾📚 Save & Ingest", key=f"save_ingest_{filename}", type="primary")
                
                if save_clicked:
                    with st.spinner("Saving content..."):
                        save_result = make_api_request(
                            f"{Config.ENDPOINTS['save_content']}{filename}", 
                            method="post", 
                            data={"content": edited_content}
                        )
                        
                    if "error" not in save_result:
                        if edited_content != st.session_state.original_content[filename]:
                            st.success(save_result.get("message", "Changes saved successfully!"))
                        else:
                            st.success("Content saved successfully!")
                        # Update original content after save
                        st.session_state.original_content[filename] = edited_content
                    else:
                        st.error(f"Save failed: {save_result['error']}")
                
                if save_ingest_clicked:
                    with st.spinner("Saving content and ingesting to search index..."):
                        save_ingest_result = make_api_request(
                            f"{Config.ENDPOINTS['save_and_ingest']}{filename}", 
                            method="post", 
                            data={"content": edited_content}
                        )
                        
                    if "error" not in save_ingest_result:
                        if edited_content != st.session_state.original_content[filename]:
                            st.success(save_ingest_result.get("message", "Changes saved and document ingested successfully!"))
                        else:
                            st.success("Content saved and document ingested successfully!")
                        # Update original content after save
                        st.session_state.original_content[filename] = edited_content
                    else:
                        st.error(f"Save & Ingest failed: {save_ingest_result['error']}")
            
            # Metadata Expander
            with st.expander("Metadata", expanded=False):
                st.json(result.get("metadata", {}))
    except Exception as e:
        st.error(f"An error occurred while parsing: {str(e)}")

def summarize_files_tab() -> None:
    """Summarize Content tab implementation"""
    st.header("Summarize Content")
    
    with st.expander("About Summarization", expanded=False):
        st.write("""
        This feature uses AI to create concise summaries of parsed documents.
        Supports all file types: PDF, Excel (.xlsx/.xls), CSV, and other documents.
        
        Process:
        1. Select a file from the parsed documents list
        2. Click 'Summarize Content' to generate a summary
        3. The summary will be displayed below
        """)
    
    # Get the list of files from the server
    files = fetch_files(Config.ENDPOINTS['list_parsed'], "Loading files to summarize...")
    
    if files:
        # Get enhanced file list with type information
        enhanced_files = get_enhanced_file_list(files)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if enhanced_files:
                # Create display options
                display_options = ["None"] + [item['display'] for item in enhanced_files]
                selected_display = st.selectbox(
                    "Select a parsed file to summarize", 
                    display_options, 
                    key="summarize_file_select",
                    help="Choose a parsed file to generate a summary. Shows original file type for clarity."
                )
                
                # Get the actual filename
                selected_file = "None"
                if selected_display != "None":
                    for item in enhanced_files:
                        if item['display'] == selected_display:
                            selected_file = item['filename']
                            break
            else:
                selected_file = st.selectbox(
                    "Select a parsed file to summarize", 
                    ["None"] + files, 
                    key="summarize_file_select",
                    help="Choose a parsed file to generate a summary"
                )
        
        if selected_file != "None":
            # Show file type information
            file_info = get_file_type_info(selected_file)
            st.info(f"Ready to summarize: {file_info['icon']} {selected_file.replace('.md', '')} ({file_info['type']} file)")
            
            # Summarize Button
            if st.button("✨ Generate Summary", key=f"summarize_{selected_file}", type="primary"):
                summarize_and_display(selected_file)
                
            # Display summary if it exists in session state
            summary_key = f"summary_{selected_file}"
            if summary_key in st.session_state:
                with st.expander("Summary", expanded=True):
                    st.markdown(st.session_state[summary_key])
    else:
        st.info("No parsed files found on the server. Parse files first using the 'Parse Files' tab.")

def summarize_and_display(filename: str) -> None:
    """Fetch and display the summary for a file with error handling"""
    summary_key = f"summary_{filename}"
    # Display the edited document content if available
    edited_key = f"edited_content_{filename}"
    if edited_key in st.session_state:
        with st.expander("Document Content", expanded=True):
            st.markdown(st.session_state[edited_key])
    
    with st.spinner(f"Summarizing {filename}..."):
        result = make_api_request(
            f"{Config.ENDPOINTS['summarize']}/{filename}",
            handle_error=False
        )
    
    if "error" in result:
        st.error(f"Error summarizing: {result['error']}")
        if summary_key in st.session_state:
            del st.session_state[summary_key]
    else:
        st.success("Summary generated successfully!")
        st.session_state[summary_key] = result.get("summary", "No summary available.")
        
        # Show metadata if available
        if "metadata" in result:
            with st.expander("Summary Metadata", expanded=False):
                st.json(result["metadata"])

def generate_questions_tab() -> None:
    """Generate Questions tab implementation"""
    st.header("Generate Questions")
    
    with st.expander("About Question Generation", expanded=False):
        st.write("""
        This feature uses AI to generate relevant questions based on parsed documents.
        Questions are generated fresh each time for the most relevant results.
        Supports all file types: PDF, Excel (.xlsx/.xls), CSV, and other documents.
        
        Process:
        1. Select a file from the parsed documents list
        2. Choose the number of questions to generate (1-50)
        3. Click 'Generate Questions' to create fresh questions
        4. The questions will be displayed below
        """)
    
    # Get the list of files from the server
    files = fetch_files(Config.ENDPOINTS['list_parsed'], "Loading files to generate questions...")
    
    if files:
        # Get enhanced file list with type information
        enhanced_files = get_enhanced_file_list(files)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if enhanced_files:
                # Create display options
                display_options = ["None"] + [item['display'] for item in enhanced_files]
                selected_display = st.selectbox(
                    "Select a parsed file to generate questions", 
                    display_options, 
                    key="questions_file_select",
                    help="Choose a parsed file to generate questions from. Shows original file type for clarity."
                )
                
                # Get the actual filename
                selected_file = "None"
                if selected_display != "None":
                    for item in enhanced_files:
                        if item['display'] == selected_display:
                            selected_file = item['filename']
                            break
            else:
                selected_file = st.selectbox(
                    "Select a parsed file to generate questions", 
                    ["None"] + files, 
                    key="questions_file_select",
                    help="Choose a parsed file to generate questions from"
                )
        
        with col2:
            num_questions = st.number_input(
                "Number of questions",
                min_value=1,
                max_value=50,
                value=10,
                key="num_questions",
                help="Choose how many questions to generate (1-50)"
            )
        
        if selected_file != "None":
            # Show file type information
            file_info = get_file_type_info(selected_file)
            st.info(f"Ready to generate {num_questions} fresh questions for: {file_info['icon']} {selected_file.replace('.md', '')} ({file_info['type']} file)")
            
            # Generate Questions Button
            if st.button("❓ Generate Fresh Questions", key=f"generate_btn_{selected_file}_{num_questions}", type="primary"):
                generate_questions_and_display(selected_file, num_questions)
                
            # Display questions if they exist in session state
            questions_key = f"questions_data_{selected_file}_{num_questions}"
            if questions_key in st.session_state:
                with st.expander("Generated Questions", expanded=True):
                    try:
                        # Parse questions into table format
                        questions_df = parse_questions_to_table(st.session_state[questions_key])
                        
                        if not questions_df.empty:
                            # Display as table
                            st.dataframe(
                                questions_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Question #": st.column_config.NumberColumn(
                                        "Question #",
                                        width="small"
                                    ),
                                    "Question": st.column_config.TextColumn(
                                        "Question",
                                        width="large"
                                    )
                                }
                            )
                            
                            # Show summary
                            st.info(f"📊 Total questions generated: {len(questions_df)}")
                        else:
                            st.warning("No questions could be parsed from the response.")
                            
                            # Show raw response as fallback
                            with st.expander("Raw Response", expanded=False):
                                st.text(str(st.session_state[questions_key]))
                    except Exception as e:
                        st.error(f"Error displaying questions: {str(e)}")
                        
                        # Show raw response as fallback
                        with st.expander("Raw Response", expanded=False):
                            st.text(str(st.session_state[questions_key]))
    else:
        st.info("No parsed files found on the server. Parse files first using the 'Parse Files' tab.")

def generate_questions_and_display(filename: str, num_questions: int) -> None:
    """Fetch and display the generated questions for a file with error handling"""
    questions_key = f"questions_data_{filename}_{num_questions}"
    
    # Display the edited document content if available
    edited_key = f"edited_content_{filename}"
    if edited_key in st.session_state:
        with st.expander("Document Content", expanded=True):
            st.markdown(st.session_state[edited_key])
    
    with st.spinner(f"Generating {num_questions} fresh questions for {filename}..."):
        result = make_api_request(
            f"{Config.ENDPOINTS['generate_questions']}/{filename}?number_of_questions={num_questions}",
            handle_error=False
        )
    
    if "error" in result:
        st.error(f"Error generating questions: {result['error']}")
        if questions_key in st.session_state:
            del st.session_state[questions_key]
    else:
        st.success("Fresh questions generated successfully!")
        st.session_state[questions_key] = result.get("questions", "No questions available.")
        
        # Show metadata if available
        if "metadata" in result:
            with st.expander("Questions Metadata", expanded=False):
                st.json(result["metadata"])

def generate_faq_and_display(filename: str, num_faqs: int) -> None:
    """Fetch and display the generated FAQ for a file with error handling"""
    faq_key = f"faq_data_{filename}_{num_faqs}"
    
    # Display the edited document content if available
    edited_key = f"edited_content_{filename}"
    if edited_key in st.session_state:
        with st.expander("Document Content", expanded=True):
            st.markdown(st.session_state[edited_key])
    
    with st.spinner(f"Generating {num_faqs} fresh FAQ items for {filename}..."):
        result = make_api_request(
            f"{Config.ENDPOINTS['generate_faq']}/{filename}?number_of_faqs={num_faqs}",
            handle_error=False
        )
    
    if "error" in result:
        st.error(f"Error generating FAQ: {result['error']}")
        if faq_key in st.session_state:
            del st.session_state[faq_key]
    else:
        st.success("Fresh FAQ generated successfully!")
        
        # Format FAQ items for display
        faq_items = result.get("faq_items", [])
        if faq_items:
            formatted_faq = ""
            for i, item in enumerate(faq_items, 1):
                formatted_faq += f"**Q{i}: {item['question']}**\n\n"
                formatted_faq += f"A{i}: {item['answer']}\n\n"
                formatted_faq += "---\n\n"
            st.session_state[faq_key] = formatted_faq
        else:
            st.session_state[faq_key] = "No FAQ items generated."
        
        # Show metadata if available
        if "metadata" in result:
            with st.expander("FAQ Metadata", expanded=False):
                st.json(result["metadata"])

def generate_faq_tab() -> None:
    """Generate FAQ tab implementation"""
    st.header("Generate FAQ")
    
    with st.expander("About FAQ Generation", expanded=False):
        st.write("""
        This feature uses AI to generate Frequently Asked Questions (FAQ) based on parsed documents.
        FAQ items are generated fresh each time with both questions and comprehensive answers.
        Supports all file types: PDF, Excel (.xlsx/.xls), CSV, and other documents.
        
        Process:
        1. Select a file from the parsed documents list
        2. Choose the number of FAQ items to generate (1-20)
        3. Click 'Generate FAQ' to create fresh FAQ items
        4. The FAQ items will be displayed with questions and answers
        """)
    
    # Get the list of files from the server
    files = fetch_files(Config.ENDPOINTS['list_parsed'], "Loading files to generate FAQ...")
    
    if files:
        # Get enhanced file list with type information
        enhanced_files = get_enhanced_file_list(files)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if enhanced_files:
                # Create display options
                display_options = ["None"] + [item['display'] for item in enhanced_files]
                selected_display = st.selectbox(
                    "Select a parsed file to generate FAQ", 
                    display_options, 
                    key="faq_file_select",
                    help="Choose a parsed file to generate FAQ from. Shows original file type for clarity."
                )
                
                # Get the actual filename
                selected_file = "None"
                if selected_display != "None":
                    for item in enhanced_files:
                        if item['display'] == selected_display:
                            selected_file = item['filename']
                            break
            else:
                selected_file = st.selectbox(
                    "Select a parsed file to generate FAQ", 
                    ["None"] + files, 
                    key="faq_file_select",
                    help="Choose a parsed file to generate FAQ from"
                )
        
        with col2:
            num_faqs = st.number_input(
                "Number of FAQ items",
                min_value=1,
                max_value=20,
                value=5,
                key="num_faqs",
                help="Choose how many FAQ items to generate (1-20)"
            )
        
        if selected_file != "None":
            # Show file type information
            file_info = get_file_type_info(selected_file)
            st.info(f"Ready to generate {num_faqs} fresh FAQ items for: {file_info['icon']} {selected_file.replace('.md', '')} ({file_info['type']} file)")
            
            # Generate FAQ Button
            if st.button("❓ Generate Fresh FAQ", key=f"generate_faq_btn_{selected_file}_{num_faqs}", type="primary"):
                generate_faq_and_display(selected_file, num_faqs)
                
            # Display FAQ if it exists in session state
            faq_key = f"faq_data_{selected_file}_{num_faqs}"
            if faq_key in st.session_state:
                with st.expander("Generated FAQ", expanded=True):
                    st.markdown(st.session_state[faq_key])
    else:
        st.info("No parsed files found on the server. Parse files first using the 'Parse Files' tab.")

def hybrid_search_tab() -> None:
    """Hybrid Search tab implementation"""
    st.header("Hybrid Search")
    st.write("Comprehensive search across both document content and Excel/CSV data.")
    
    with st.expander("About Hybrid Search", expanded=False):
        st.write("""
        This hybrid search provides **two complementary search methods**:
        
        **📄 Document Search (Pinecone + BM25):**
        - Searches parsed content from ALL file types (PDF, Excel, CSV, etc.)
        - Combines vector search (semantic similarity) + keyword search (exact matches)
        - **NEW**: Filter by specific source document or search across all documents
        - Best for: Finding specific entities, detailed information, structured data
        
        **📊 Excel/CSV Search (Pandas Agent):**
        - Direct DataFrame queries on Excel/CSV files
        - Uses AI to perform calculations and data analysis
        - Best for: Complex data queries, calculations, statistical analysis
        
        **Document Filtering:**
        - Select a specific document to search within only that document's content
        - Choose "All Documents" to search across all indexed content
        - Useful when you know which document contains the information you need
        
        **Tips for better results:**
        - For specific names: "Mrs Cumings" or "List all details of Mrs Cumings"
        - For concepts: "What happened to passengers in first class?"
        - For calculations: "Average age of survivors"
        
        **Note**: Excel/CSV files must be parsed and ingested to appear in document search.
        """)
    
    # Source document selection
    source_documents = fetch_files(Config.ENDPOINTS['source_documents'], "Loading available documents...")
    
    if source_documents:
        # Get enhanced file list with type information
        enhanced_source_docs = get_enhanced_file_list(source_documents)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if enhanced_source_docs:
                display_options = ["All Documents"] + [item['display'] for item in enhanced_source_docs]
                selected_display = st.selectbox(
                    "Select source document (optional)",
                    display_options,
                    key="source_doc_select",
                    help="Choose a specific document to search within, or 'All Documents' to search across all content"
                )
                
                # Get the actual filename
                selected_source = None
                if selected_display != "All Documents":
                    for item in enhanced_source_docs:
                        if item['display'] == selected_display:
                            selected_source = item['filename']
                            break
            else:
                selected_source = st.selectbox(
                    "Select source document (optional)",
                    ["All Documents"] + source_documents,
                    key="source_doc_select",
                    help="Choose a specific document to search within, or 'All Documents' to search across all content"
                )
                if selected_source == "All Documents":
                    selected_source = None
        
        with col2:
            debug_mode = st.checkbox(
                "Debug Mode", 
                help="Show retrieved documents and search details"
            )
    else:
        st.warning("No indexed documents found. Please upload and ingest documents first.")
        selected_source = None
        debug_mode = st.checkbox("Debug Mode", help="Show retrieved documents and search details")

    # Search input
    col1, col2 = st.columns([4, 1])
    with col1:
        # Initialize query from session state if set by example buttons
        default_query = st.session_state.get("example_query", "")
        query = st.text_input(
            "Enter your search query", 
            value=default_query,
            placeholder="e.g. 'List all details of Miss Sandstrom' or 'What information do we have about the Sandstrom family?'",
            help="Try specific entity names or detailed questions for best results"
        )
        # Clear the example query from session state after using it
        if "example_query" in st.session_state:
            del st.session_state["example_query"]
    
    with col2:
        # Show search scope info
        if selected_source:
            file_info = get_file_type_info(selected_source)
            st.info(f"🎯 Searching in: {file_info['icon']} {selected_source.replace('.md', '')} ({file_info['type']})")
        else:
            st.info("🌐 Searching all documents")
    
    # Example queries
    st.write("**Example queries:**")
    example_queries = [
        "List all details of Miss Sandstrom",
        "What information do we have about the Sandstrom family?", 
        "Show me all passengers with cabin G6",
        "Who survived from first class?",
        "What happened to 4-year-old passengers?"
    ]
    
    cols = st.columns(len(example_queries))
    for i, example in enumerate(example_queries):
        if cols[i].button(f"Try: {example[:20]}...", key=f"example_{i}"):
            st.session_state["example_query"] = example
            st.rerun()
    
    # Search execution
    if st.button("🔍 Search", type="primary", disabled=not query.strip()):
        if query.strip():
            with st.spinner("Performing hybrid search..."):
                search_data = {
                    "query": query.strip(),
                    "debug": debug_mode,
                    "source_document": selected_source
                }
                result = make_api_request(Config.ENDPOINTS['hybrid_search'], method="post", data=search_data)
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    if debug_mode and "debug_info" in result:
                        # Show debug information
                        debug_info = result["debug_info"]
                        doc_debug = debug_info.get("document_debug", {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.success("Search completed successfully!")
                            st.write(f"**Query:** {doc_debug.get('query', query)}")
                            st.write(f"**Documents found:** {doc_debug.get('documents_found', 0)}")
                        
                        # Show document search results
                        doc_search = result.get("document_search", {})
                        if doc_search.get("success") and doc_search.get("result"):
                            st.subheader("📄 Document Search Results:")
                            doc_result = doc_search["result"]
                            if isinstance(doc_result, dict) and "result" in doc_result:
                                st.write(doc_result["result"])
                            else:
                                st.write(doc_result)
                        
                        # Show pandas agent results
                        pandas_search = result.get("pandas_agent_search", {})
                        if pandas_search.get("results"):
                            st.subheader("📊 Excel/CSV Search Results:")
                            for file_result in pandas_search["results"]:
                                st.write(f"**{file_result['filename']} ({file_result['file_type'].upper()}):**")
                                st.write(file_result["answer"])
                                st.divider()
                        
                        # Show retrieved documents
                        if doc_debug.get("documents"):
                            with st.expander("🔍 Retrieved Documents (Debug)", expanded=True):
                                for doc in doc_debug["documents"]:
                                    st.write(f"**Document {doc['index']}:**")
                                    if doc.get("metadata"):
                                        st.json(doc["metadata"])
                                    st.text(doc["preview"])
                                    st.divider()
                    else:
                        # Standard response - show all results
                        st.success("Hybrid search completed successfully!")
                        
                        # Show document search results
                        doc_search = result.get("document_search", {})
                        if doc_search.get("success") and doc_search.get("result"):
                            st.subheader("📄 Document Search Results:")
                            doc_result = doc_search["result"]
                            if isinstance(doc_result, dict) and "result" in doc_result:
                                st.write(doc_result["result"])
                            else:
                                st.write(doc_result)
                        elif doc_search.get("error"):
                            st.error(f"Document search error: {doc_search['error']}")
                        
                        # Show pandas agent results
                        pandas_search = result.get("pandas_agent_search", {})
                        if pandas_search.get("results"):
                            st.subheader("📊 Excel/CSV Search Results:")
                            for file_result in pandas_search["results"]:
                                st.write(f"**{file_result['filename']} ({file_result['file_type'].upper()}):**")
                                st.write(file_result["answer"])
                                st.divider()
                        
                        # Show summary
                        summary = result.get("summary", {})
                        if summary:
                            with st.expander("Search Summary", expanded=False):
                                st.json(summary)
                        
                        # If no results found anywhere
                        if not doc_search.get("success") and not pandas_search.get("results"):
                            st.warning("No results found in document search or Excel/CSV files.")
        else:
            st.info("Please enter a search query.")

def excel_search_tab() -> None:
    """Excel & CSV Search tab implementation"""
    st.header("Excel & CSV Search")
    st.write("Search and analyze Excel/CSV files using natural language queries.")
    
    with st.expander("About Excel Search", expanded=False):
        st.write("""
        This feature allows you to query Excel and CSV files using natural language:
        
        **Capabilities:**
        - **Data Analysis**: "What is the average salary?" or "How many employees in each department?"
        - **Filtering**: "Show me all employees over 30" or "List all Engineering staff"
        - **Statistics**: "Calculate total revenue" or "Find the highest score"
        - **Comparisons**: "Compare sales by region" or "Which department has most employees?"
        
        **Process:**
        1. Upload Excel/CSV files using the Upload tab
        2. Process them using Parse Files and Ingest Documents tabs
        3. Select a file and ask natural language questions
        4. Get intelligent answers based on your data
        
        **Supported Files**: .xlsx, .xls, .csv
        """)
    
    # Get list of uploaded files and filter for Excel/CSV
    files = fetch_files(Config.ENDPOINTS['list_uploaded'], "Loading Excel/CSV files...")
    
    if files:
        # Filter for Excel and CSV files
        excel_csv_files = [f for f in files if f.lower().endswith(('.xlsx', '.xls', '.csv'))]
        
        if excel_csv_files:
            st.success(f"Found {len(excel_csv_files)} Excel/CSV files")
            
            # File selection
            selected_file = create_file_selector(excel_csv_files, "Select an Excel/CSV file to query", "Choose an Excel or CSV file to analyze with natural language")
            
            if selected_file != "None":
                st.info(f"Selected file: {selected_file}")
                
                # Query input
                col1, col2 = st.columns([4, 1])
                with col1:
                    # Initialize query from session state if set by example buttons
                    default_query = st.session_state.get("excel_example_query", "")
                    query = st.text_input(
                        "Ask a question about your data", 
                        value=default_query,
                        placeholder="e.g. 'What is the average age?' or 'How many people in each department?'",
                        help="Ask natural language questions about your Excel/CSV data",
                        key="excel_query_input"
                    )
                    # Clear the example query from session state after using it
                    if "excel_example_query" in st.session_state:
                        del st.session_state["excel_example_query"]
                
                with col2:
                    show_data_info = st.checkbox(
                        "Show Data Info", 
                        help="Display dataset information and structure"
                    )
                
                # Example queries specific to Excel/CSV data
                st.write("**Example queries for spreadsheet data:**")
                excel_example_queries = [
                    "What columns are in this dataset?",
                    "How many rows of data are there?",
                    "What is the average of numeric columns?",
                    "Show me the first 10 rows",
                    "What are the unique values in each column?"
                ]
                
                cols = st.columns(len(excel_example_queries))
                for i, example in enumerate(excel_example_queries):
                    if cols[i].button(f"Try: {example[:15]}...", key=f"excel_example_{i}"):
                        st.session_state["excel_example_query"] = example
                        st.rerun()
                
                # Search execution
                if st.button("📊 Analyze Data", type="primary", disabled=not query.strip()):
                    if query.strip():
                        with st.spinner("Analyzing your Excel/CSV data..."):
                            # Use the dedicated pandas query API for direct Excel/CSV analysis
                            search_data = {
                                "query": query.strip(),
                                "debug": show_data_info
                            }
                            result = make_api_request(Config.ENDPOINTS['pandas_query'], method="post", data=search_data)
                            
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                # Get results from the pandas query endpoint
                                excel_results = result.get("results", [])
                                
                                # Find result for our selected file
                                file_result = next((r for r in excel_results if r['filename'] == selected_file), None)
                                
                                if file_result:
                                    st.success("Analysis completed successfully!")
                                    
                                    # Show the answer
                                    st.subheader("Answer:")
                                    st.write(file_result['answer'])
                                    
                                    # Show data info if requested
                                    if show_data_info and 'data_summary' in file_result:
                                        with st.expander("📊 Dataset Information", expanded=True):
                                            data_summary = file_result['data_summary']
                                            
                                            col1, col2, col3 = st.columns(3)
                                            with col1:
                                                st.metric("File Type", file_result.get('file_type', 'Unknown').upper())
                                            with col2:
                                                st.metric("Rows", data_summary.get('total_rows', 'Unknown'))
                                            with col3:
                                                st.metric("Columns", data_summary.get('total_columns', 'Unknown'))
                                            
                                            if 'column_info' in data_summary:
                                                st.write("**Column Information:**")
                                                st.json(data_summary['column_info'])
                                            
                                            # Show additional debug info if available
                                            debug_info = result.get("debug_info", {})
                                            if debug_info:
                                                st.write("**Query Debug Info:**")
                                                st.json(debug_info)
                                                
                                elif excel_results:
                                    # Show results for all files if the specific file wasn't found
                                    st.success("Analysis completed successfully!")
                                    st.subheader("Results:")
                                    for file_result in excel_results:
                                        st.write(f"**{file_result['filename']} ({file_result.get('file_type', 'unknown').upper()}):**")
                                        st.write(file_result['answer'])
                                        st.divider()
                                else:
                                    # No results found
                                    summary = result.get("summary", {})
                                    if summary.get("files_with_errors", 0) > 0:
                                        errors = result.get("errors", [])
                                        st.error("Errors occurred during analysis:")
                                        for error in errors:
                                            st.error(error)
                                    else:
                                        st.warning("No results found. Make sure you have uploaded Excel/CSV files.")
                    else:
                        st.info("Please enter a question about your data.")
            else:
                st.info("Please select an Excel or CSV file to analyze.")
        else:
            st.warning("No Excel or CSV files found. Please upload .xlsx, .xls, or .csv files using the Upload tab.")
    else:
        st.info("No files found on the server. Please upload files first using the Upload tab.")

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        st.write("👋 Application interrupted by user")
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        st.code(f"Error details: {e}", language="python")
        st.write("Please check the server connection and try again.")

