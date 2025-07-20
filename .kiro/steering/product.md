# Product Overview

**Biz To Bricks** is an AI-powered document processing platform that provides comprehensive document workflow automation through intelligent parsing, summarization, question generation, and hybrid search capabilities.

## Core Functionality

- **Document Processing**: Multi-format support (PDF, DOCX, Excel, CSV, TXT) with LlamaParse integration for advanced document understanding
- **AI Content Generation**: OpenAI GPT-4.1 powered summarization, question generation, and FAQ creation
- **Intelligent Search**: Hybrid search combining Pinecone vector search (semantic) with BM25 keyword search
- **Data Analysis**: Natural language querying of Excel/CSV files using pandas agent
- **Cloud-Native**: Supports both local development and Google Cloud Run deployment with persistent storage

## Architecture

The system follows a client-server architecture:
- **Frontend**: Streamlit web interface with 8 specialized tabs for complete document lifecycle
- **Backend**: FastAPI REST API with 10+ endpoints providing comprehensive document processing
- **Storage**: Intelligent storage system that auto-detects environment (local filesystem vs Google Cloud Storage)
- **AI Services**: Integration with OpenAI, LlamaParse, and Pinecone for advanced document understanding

## Target Use Cases

- Document digitization and content extraction
- Knowledge base creation and management  
- Automated content summarization and Q&A generation
- Intelligent document search and retrieval
- Data analysis and natural language querying of spreadsheets