import streamlit as st
import requests
import os
import json
from pathlib import Path
import sys
# Configuration
# BASE_URL = "http://localhost:8004"
BASE_URL = "https://document-processing-service-yawfj7f47q-uc.a.run.app"
UPLOAD_API_URL = f"{BASE_URL}/uploadfile/"
LIST_FILES_API_URL = f"{BASE_URL}/listfiles/uploaded_files"
PARSE_FILE_API_URL = f"{BASE_URL}/parsefile/"
SAVE_CONTENT_API_URL = f"{BASE_URL}/savecontent/"
LIST_FILE_FOR_SUMMARIZE = f"{BASE_URL}/listfiles/parsed_files"
SUMMARIZE_CONTENT_API_URL_BASE = f"{BASE_URL}/summarizecontent"
GENERATE_QUESTIONS_API_URL_BASE = f"{BASE_URL}/generatequestions"
INGEST_DOCUMENTS_API_URL = f"{BASE_URL}/ingestdocuments/"
SAVE_AND_INGEST_API_URL = f"{BASE_URL}/saveandingst/"
HYBRID_SEARCH_API_URL = f"{BASE_URL}/hybridsearch/"
SAMPLE_FILES_DIR = Path("../docs")  # Path to docs folder with sample files

# Set page config for better UI
st.set_page_config(
    page_title="Document Processor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API utility functions
def make_api_request(url, method="get", data=None, files=None, handle_error=True):
    """General purpose API request handler with error handling"""
    try:
        if method.lower() == "get":
            response = requests.get(url)
        elif method.lower() == "post":
            if files:
                response = requests.post(url, files=files)
            else:
                response = requests.post(url, json=data)
        else:
            return {"error": f"Unsupported method: {method}"}
            
        if response.status_code in (200, 201):
            return response.json()
        else:
            error_msg = f"API Error: {response.status_code}"
            try:
                error_detail = response.json().get("error", response.text)
                error_msg = f"{error_msg} - {error_detail}"
            except:
                error_msg = f"{error_msg} - {response.text}"
                
            if handle_error:
                st.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        error_msg = f"Connection error: {str(e)}"
        if handle_error:
            st.error(error_msg)
        return {"error": error_msg}

def fetch_files(url, message="Fetching files..."):
    """Fetch files from the specified API endpoint"""
    with st.spinner(message):
        result = make_api_request(url)
        
    if "error" in result:
        return []
    return result.get("files", [])

def main():
    # Apply custom styling
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 1rem;
        }
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Document Processor 📄")
    st.write("Upload, view, parse, and summarize documents using FastAPI backend.")
    
    # Create tabs for different functionality
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📤 Upload", "📋 View Files", "📝 Parse Files", "📊 Summarize", "❓ Generate Questions", "📚 Ingest Documents", "💾📚 Save & Ingest", "🔍 Hybrid Search"])
    
    with tab1:
        upload_files()
    
    with tab2:
        view_files()
        
    with tab3:
        parse_files()
        
    with tab4:
        summarize_files_tab()
    
    with tab5:
        generate_questions_tab()

    with tab6:
        ingest_documents_tab()

    with tab7:
        save_and_ingest_tab()

    with tab8:
        hybrid_search_tab()

def upload_files():
    st.header("Upload Files")
    
    # Add documentation and instructions
    with st.expander("Instructions", expanded=False):
        st.write("""
        1. Select a sample file from the docs directory
        2. Click 'Upload File' to send it to the server
        3. The server will store the file and return its details
        """)
    
    # Check if docs directory exists and list sample files
    if os.path.exists(SAMPLE_FILES_DIR):
        sample_files = list(SAMPLE_FILES_DIR.glob("*.*"))
        if sample_files:
            sample_file_names = [file.name for file in sample_files]
            selected_sample = st.selectbox(
                "Select a sample file", 
                ["None"] + sample_file_names, 
                key="upload_sample",
                help="Choose a file from the docs directory to upload"
            )
            
            # Display file info if selected
            if selected_sample != "None":
                sample_path = SAMPLE_FILES_DIR / selected_sample
                file_size = os.path.getsize(sample_path)
                st.info(f"Selected: {selected_sample} ({file_size/1024:.1f} KB)")
        else:
            st.warning("No sample files found in docs directory.")
            selected_sample = "None"
    else:
        st.error("Docs directory not found.")
        selected_sample = "None"
    
    # Upload button
    if st.button("Upload File", type="primary", disabled=(selected_sample == "None")):
        if selected_sample != "None":
            # Handle selected sample file from docs directory
            sample_file_path = SAMPLE_FILES_DIR / selected_sample
            with open(sample_file_path, "rb") as file:
                with st.spinner("Uploading file..."):
                    file_content = file.read()
                    files = {"file": (selected_sample, file_content)}
                    result = make_api_request(UPLOAD_API_URL, method="post", files=files)
                
                if "error" not in result:
                    st.success(f"File uploaded successfully!")
                    st.json(result)

def view_files():
    st.header("View Files")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        refresh = st.button("🔄 Refresh", help="Reload the file list from server")
    
    # Get the list of files from the server
    files = fetch_files(LIST_FILES_API_URL, "Loading file list...")
    
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

def parse_files():
    st.header("Parse Files")
    
    # Get the list of files from the server
    files = fetch_files(LIST_FILES_API_URL, "Loading files to parse...")
    
    if files:
        selected_file = st.selectbox(
            "Select a file to parse",
            ["None"] + files,
            key="parse_file_select",
            help="Choose a file to convert to structured text"
        )
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

def display_parsed_file(filename):
    """Parse a file and display its content with editing capabilities"""
    try:
        with st.spinner(f"Parsing file {filename}..."):
            result = make_api_request(f"{PARSE_FILE_API_URL}{filename}")
        
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
                    if edited_content != st.session_state.original_content[filename]:
                        with st.spinner("Saving changes..."):
                            save_result = make_api_request(
                                f"{SAVE_CONTENT_API_URL}{filename}", 
                                method="post", 
                                data={"content": edited_content}
                            )
                            
                        if "error" not in save_result:
                            st.success(save_result.get("message", "Changes saved successfully!"))
                            # Update original content after save
                            st.session_state.original_content[filename] = edited_content
                    else:
                        st.info("No changes detected.")
                
                if save_ingest_clicked:
                    if edited_content != st.session_state.original_content[filename]:
                        with st.spinner("Saving changes and ingesting to search index..."):
                            save_ingest_result = make_api_request(
                                f"{SAVE_AND_INGEST_API_URL}{filename}", 
                                method="post", 
                                data={"content": edited_content}
                            )
                            
                        if "error" not in save_ingest_result:
                            st.success(save_ingest_result.get("message", "Changes saved and document ingested successfully!"))
                            # Update original content after save
                            st.session_state.original_content[filename] = edited_content
                        else:
                            st.error(f"Save & Ingest failed: {save_ingest_result['error']}")
                    else:
                        st.info("No changes detected.")
            
            # Metadata Expander
            with st.expander("Metadata", expanded=False):
                st.json(result.get("metadata", {}))
    except Exception as e:
        st.error(f"An error occurred while parsing: {str(e)}")

def summarize_files_tab():
    st.header("Summarize Content")
    
    with st.expander("About Summarization", expanded=False):
        st.write("""
        This feature uses AI to create concise summaries of parsed documents.
        
        Process:
        1. Select a file from the parsed documents list
        2. Click 'Summarize Content' to generate a summary
        3. The summary will be displayed below
        """)
    
    # Get the list of files from the server
    files = fetch_files(LIST_FILE_FOR_SUMMARIZE, "Loading files to summarize...")
    
    if files:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_file = st.selectbox(
                "Select a parsed file to summarize", 
                ["None"] + files, 
                key="summarize_file_select",
                help="Choose a parsed file to generate a summary"
            )
        
        if selected_file != "None":
            st.info(f"Ready to summarize: {selected_file}")
            
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

def summarize_and_display(filename):
    """Fetch and display the summary for a file with error handling"""
    summary_key = f"summary_{filename}"
    # Display the edited document content if available
    edited_key = f"edited_content_{filename}"
    if edited_key in st.session_state:
        with st.expander("Document Content", expanded=True):
            st.markdown(st.session_state[edited_key])
    
    with st.spinner(f"Summarizing {filename}..."):
        result = make_api_request(
            f"{SUMMARIZE_CONTENT_API_URL_BASE}/{filename}",
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

def generate_questions_tab():
    st.header("Generate Questions")
    
    with st.expander("About Question Generation", expanded=False):
        st.write("""
        This feature uses AI to generate relevant questions based on parsed documents.
        Questions are generated fresh each time for the most relevant results.
        
        Process:
        1. Select a file from the parsed documents list
        2. Choose the number of questions to generate (1-50)
        3. Click 'Generate Questions' to create fresh questions
        4. The questions will be displayed below
        """)
    
    # Get the list of files from the server
    files = fetch_files(LIST_FILE_FOR_SUMMARIZE, "Loading files to generate questions...")
    
    if files:
        col1, col2 = st.columns([3, 1])
        with col1:
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
            st.info(f"Ready to generate {num_questions} fresh questions for: {selected_file}")
            
            # Generate Questions Button
            if st.button("❓ Generate Fresh Questions", key=f"generate_btn_{selected_file}_{num_questions}", type="primary"):
                generate_questions_and_display(selected_file, num_questions)
                
            # Display questions if they exist in session state
            questions_key = f"questions_data_{selected_file}_{num_questions}"
            if questions_key in st.session_state:
                with st.expander("Generated Questions", expanded=True):
                    st.markdown(st.session_state[questions_key])
    else:
        st.info("No parsed files found on the server. Parse files first using the 'Parse Files' tab.")

def generate_questions_and_display(filename, num_questions):
    """Fetch and display the generated questions for a file with error handling"""
    questions_key = f"questions_data_{filename}_{num_questions}"
    
    # Display the edited document content if available
    edited_key = f"edited_content_{filename}"
    if edited_key in st.session_state:
        with st.expander("Document Content", expanded=True):
            st.markdown(st.session_state[edited_key])
    
    with st.spinner(f"Generating {num_questions} fresh questions for {filename}..."):
        result = make_api_request(
            f"{GENERATE_QUESTIONS_API_URL_BASE}/{filename}?number_of_questions={num_questions}",
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

# ingest the documents to pinecone and bm25 index
def ingest_documents_tab():
    st.header("Ingest Documents")
    st.write("Ingest documents to Pinecone and BM25 index.")
    # Fetch .md files from parsed_files
    parsed_files = fetch_files(f"{BASE_URL}/listfiles/parsed_files", "Loading parsed files...")
    # Filter for .md files only
    md_files = sorted([f for f in parsed_files if f.endswith('.md')])
    selected_file = st.selectbox(
        "Select a .md file to ingest",
        ["None"] + md_files,
        key="ingest_file_select",
        help="Choose a markdown file to ingest to Pinecone and BM25 index"
    )
    if selected_file != "None":
        if st.button("Ingest Document", type="primary"):
            st.write(f"Ingesting {selected_file} to Pinecone and BM25 index...")
            result = make_api_request(f"{INGEST_DOCUMENTS_API_URL}{selected_file}", method="post", handle_error=False)
            if "error" in result and "not found" in result["error"].lower():
                st.error(f"❗ {result['error']}\n\nPlease make sure you have parsed the file first using the 'Parse Files' tab.")
            elif "error" in result:
                st.error(result["error"])
            else:
                st.success(result.get("message", "Ingestion successful!"))
    else:
        st.info("Please select a .md file to ingest.")

def save_and_ingest_tab():
    st.header("Save & Ingest Documents")
    
    with st.expander("About Save & Ingest", expanded=False):
        st.write("""
        This feature combines content saving and document ingestion in one operation.
        
        Process:
        1. Select a file from the parsed documents list
        2. Edit the content in the text area
        3. Click 'Save & Ingest' to save changes and add to search index
        4. The document will be saved and immediately available for hybrid search
        """)
    
    # Get the list of files from the server
    files = fetch_files(LIST_FILE_FOR_SUMMARIZE, "Loading parsed files...")
    
    if files:
        selected_file = st.selectbox(
            "Select a parsed file to edit and ingest", 
            ["None"] + files, 
            key="save_ingest_file_select",
            help="Choose a parsed file to edit and ingest to the search index"
        )
        
        if selected_file != "None":
            # Load existing content
            try:
                with st.spinner(f"Loading content for {selected_file}..."):
                    # Try to load the parsed file content
                    parsed_result = make_api_request(f"{PARSE_FILE_API_URL}{selected_file}")
                
                if "error" not in parsed_result:
                    text_content = parsed_result.get("text_content", "")
                    
                    st.info(f"Editing: {selected_file}")
                    
                    # Content editor
                    edited_content = st.text_area(
                        "Edit the document content:",
                        text_content,
                        height=400,
                        key=f"save_ingest_content_{selected_file}",
                        help="Make your changes to the document content before saving and ingesting"
                    )
                    
                    # Show content length info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"Characters: {len(edited_content):,}")
                    with col2:
                        st.caption(f"Words: {len(edited_content.split()):,}")
                    
                    # Save & Ingest Button
                    if st.button("💾📚 Save & Ingest", key=f"save_ingest_btn_{selected_file}", type="primary"):
                        save_and_ingest_content(selected_file, edited_content)
                        
                    # Display previous operation status if it exists in session state
                    status_key = f"save_ingest_status_{selected_file}"
                    if status_key in st.session_state:
                        if st.session_state[status_key]["success"]:
                            st.success(st.session_state[status_key]["message"])
                        else:
                            st.error(st.session_state[status_key]["message"])
                else:
                    st.error(f"Failed to load content: {parsed_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"Error loading file content: {str(e)}")
    else:
        st.info("No parsed files found on the server. Parse files first using the 'Parse Files' tab.")

def save_and_ingest_content(filename, content):
    """Save content and ingest document in a single operation"""
    status_key = f"save_ingest_status_{filename}"
    
    with st.spinner(f"Saving and ingesting {filename}..."):
        result = make_api_request(
            f"{SAVE_AND_INGEST_API_URL}{filename}",
            method="post",
            data={"content": content},
            handle_error=False
        )
    
    if "error" in result:
        st.session_state[status_key] = {
            "success": False,
            "message": f"Error: {result['error']}"
        }
        st.error(f"Save & Ingest failed: {result['error']}")
    else:
        st.session_state[status_key] = {
            "success": True,
            "message": result.get("message", "Content saved and document ingested successfully!")
        }
        st.success("✅ Content saved and document ingested successfully! The document is now searchable.")

def hybrid_search_tab():
    st.header("Hybrid Search")
    st.write("Perform a hybrid search using Pinecone and BM25.")
    query = st.text_input("Enter your search query", placeholder="e.g. 'What is the main idea of the document?'")
    if st.button("Search", type="primary"):
        if query:
            with st.spinner("Performing hybrid search..."):
                result = make_api_request(HYBRID_SEARCH_API_URL, method="post", data={"query": query})
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("Hybrid search completed successfully!")
                    st.write(result.get("result", "No results found."))
        else:
            st.info("Please enter a search query.")

if __name__ == "__main__":
    main()

