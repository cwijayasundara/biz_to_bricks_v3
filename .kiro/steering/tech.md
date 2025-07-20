# Technology Stack & Build System

## Core Technologies

### Backend Stack
- **FastAPI 0.115.12**: High-performance REST API framework with automatic OpenAPI documentation
- **Python 3.8+**: Recommended 3.10+ for optimal performance
- **Uvicorn**: ASGI server for production deployment
- **Pydantic**: Data validation and serialization

### AI & ML Services
- **OpenAI GPT-4.1**: Content generation, summarization, and analysis
- **LlamaParse**: Advanced document parsing with context preservation
- **Pinecone**: Vector database for semantic search
- **LangChain**: AI application framework and orchestration
- **BM25 (Rank-BM25)**: Keyword-based search indexing

### Frontend & Client
- **Streamlit**: Interactive web interface with custom styling
- **Pandas**: Data manipulation and analysis
- **Requests**: HTTP client for API communication

### Storage & Deployment
- **Google Cloud Storage**: Persistent file storage for production
- **Google Cloud Run**: Serverless container deployment
- **Docker**: Containerization with multi-stage builds
- **Local Filesystem**: Development environment storage

## Environment Setup

### Required API Keys
Create `.env` file in project root:
```bash
OPENAI_API_KEY=sk-your-openai-api-key
LLAMA_CLOUD_API_KEY=llx-your-llama-cloud-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
GOOGLE_CLOUD_PROJECT=your-gcp-project-id  # For cloud deployment
STORAGE_MODE=auto  # Options: auto, local, cloud
```

## Common Commands

### Local Development
```bash
# Backend server (recommended)
cd server
python start_server.py --storage local --reload

# Alternative backend startup
cd server
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8004

# Frontend client
cd client
pip install -r requirements.txt
streamlit run client.py
```

### Docker Development
```bash
# Using Docker Compose (recommended)
docker compose up -d --build

# Manual Docker build
cd server
docker build -t document-processing-server .
docker run -d -p 8004:8004 --env-file .env document-processing-server
```

### Cloud Deployment
```bash
# Automated deployment (recommended)
cd server
python deploy_to_cloudrun.py --project-id YOUR_PROJECT_ID --region us-central1

# Manual deployment
gcloud run deploy document-processing-service \
  --image us-central1-docker.pkg.dev/PROJECT_ID/document-processing/server:latest \
  --region us-central1 --memory 4Gi --cpu 2
```

### Testing & Debugging
```bash
# Run tests
pytest

# Check API health
curl http://localhost:8004/

# View API documentation
open http://localhost:8004/docs
```

## Build Configuration

### Python Dependencies
- Separate requirements.txt files for server and client
- Pinned versions for stability
- Optional testing dependencies

### Docker Configuration
- Multi-stage builds for optimization
- Python 3.12-slim base image
- Automatic directory creation
- Environment variable support

### Storage Modes
- **local**: File system storage (development)
- **cloud**: Google Cloud Storage (production)
- **auto**: Environment-based detection (default)