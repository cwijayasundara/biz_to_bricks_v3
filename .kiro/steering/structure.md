# Project Structure & Organization

## Root Directory Layout

```
biz_to_bricks_v3/
├── .env                    # Environment variables (API keys)
├── .gitignore             # Git ignore patterns
├── README.md              # Main project documentation
├── API_DOCUMENTATION.md   # Complete API reference
├── requirements.txt       # Root-level dependencies
├── client/                # Streamlit frontend application
├── server/                # FastAPI backend application
└── docs/                  # Sample documents for testing
```

## Client Directory (`client/`)

**Purpose**: Streamlit web interface for document processing

```
client/
├── client.py              # Main Streamlit application
└── __pycache__/          # Python bytecode cache
```

**Key Features**:
- 8 specialized tabs for complete document lifecycle
- File upload and management interface
- Real-time document editing with markdown preview
- AI content generation controls
- Hybrid search interface

## Server Directory (`server/`)

**Purpose**: FastAPI backend with comprehensive document processing capabilities

```
server/
├── app.py                     # Main FastAPI application
├── requirements.txt           # Server-specific dependencies
├── start_server.py           # Server startup script with options
├── Dockerfile                # Container configuration
├── docker-compose.yml        # Multi-service orchestration
├── deploy.sh                 # Deployment automation script
├── deploy_to_cloudrun.py     # GCP Cloud Run deployment
├── .env                      # Server environment variables
├── README.md                 # Server-specific documentation
├── STORAGE_DOCUMENTATION.md  # Storage configuration guide
├── .dockerignore             # Docker build exclusions
│
├── Core Processing Modules:
├── file_parser.py            # LlamaParse document parsing
├── file_util_enhanced.py     # Enhanced file operations & storage
├── cloud_storage_util.py     # Google Cloud Storage integration
├── doc_summarizer.py         # AI-powered summarization
├── question_gen.py           # Question generation service
├── faq_gen.py               # FAQ generation service
├── excel_agent.py           # Pandas agent for data analysis
├── hybrid_search.py         # Vector + keyword search
├── pinecone_util.py         # Vector database operations
├── ingest_docs.py           # Document indexing pipeline
│
└── Runtime Directories:
    ├── uploaded_files/       # Original uploaded documents
    ├── parsed_files/         # Markdown versions (editable)
    ├── generated_questions/  # AI-generated Q&A content
    ├── bm25_indexes/        # Keyword search indexes
    └── __pycache__/         # Python bytecode cache
```

## Data Flow & Directory Usage

### Document Processing Pipeline
1. **Upload** → `uploaded_files/` - Original documents stored
2. **Parse** → `parsed_files/` - LlamaParse converts to markdown
3. **Edit** → `parsed_files/` - User edits saved in-place
4. **Generate** → `generated_questions/` - AI content creation
5. **Index** → `bm25_indexes/` - Search indexes created
6. **Search** → Hybrid queries across all indexed content

### Storage Modes
- **Local Development**: Uses filesystem directories under `server/`
- **Cloud Production**: Maps to Google Cloud Storage buckets:
  - `uploaded_files/` → `{project-id}-uploaded-files`
  - `parsed_files/` → `{project-id}-parsed-files`
  - `generated_questions/` → `{project-id}-generated-questions`
  - `bm25_indexes/` → `{project-id}-bm25-indexes`

## Key Architecture Patterns

### File Management
- **Intelligent Storage**: Auto-detection between local/cloud storage
- **Smart Upsert**: Prevents duplicates while allowing content updates
- **Organized Structure**: Separate directories for each processing stage

### API Design
- **RESTful Endpoints**: 10+ endpoints following REST conventions
- **Pydantic Models**: Type-safe request/response validation
- **Error Handling**: Comprehensive error responses with proper HTTP codes
- **Documentation**: Auto-generated OpenAPI/Swagger documentation

### Configuration Management
- **Environment Variables**: Centralized configuration via `.env` files
- **Storage Modes**: Configurable storage backend (local/cloud/auto)
- **Deployment Options**: Multiple deployment strategies supported

### Code Organization
- **Separation of Concerns**: Each module handles specific functionality
- **Async Support**: FastAPI with async/await patterns where beneficial
- **Error Resilience**: Graceful handling of API failures and timeouts

## Development Conventions

### File Naming
- Snake_case for Python modules and directories
- Descriptive names indicating functionality
- Consistent suffixes (`_util.py`, `_agent.py`, `_gen.py`)

### Directory Structure
- Runtime directories created automatically
- Clear separation between source code and data
- Consistent organization across local and cloud environments

### Configuration
- Environment-specific settings in `.env` files
- Sensible defaults with override capabilities
- Clear documentation of required vs optional settings