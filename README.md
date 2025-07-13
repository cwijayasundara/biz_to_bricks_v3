# Biz To Bricks - AI-Powered Document Processing Platform

🚀 **A comprehensive document processing and intelligent search system with FastAPI backend and Streamlit frontend, featuring AI-powered parsing, summarization, question generation, and hybrid search capabilities.**

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT INTERFACE                            │
├─────────────────────────────────────────────────────────────────┤
│  📱 Streamlit Frontend (client.py)                             │
│  • File Upload & Management                                     │
│  • Document Parsing & Editing                                   │
│  • AI Content Generation                                        │
│  • Intelligent Search Interface                                 │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP/REST API
┌─────────────────▼───────────────────────────────────────────────┐
│                 FASTAPI BACKEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  🔧 Core API (app.py) - 10+ REST endpoints                     │
│  • File Management (upload, list, delete)                       │
│  • Document Processing (parse, save, edit)                      │
│  • AI Services (summarize, questions, FAQ)                     │
│  • Search & Query (hybrid search, pandas agent)                │
│  • Index Management (ingest, source documents)                 │
└─────────────────┬───────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│              PROCESSING LAYER                                   │
├─────────────────────────────────────────────────────────────────┤
│  📄 Document Parser     │  🤖 AI Services     │  🔍 Search Engine │
│  • LlamaParse API       │  • OpenAI GPT-4.1   │  • Pinecone Vector │
│  • PDF, DOCX, Excel     │  • Text Summaries   │  • BM25 Keyword    │
│  • CSV Processing       │  • Question Gen     │  • Hybrid Results  │
│  • Markdown Output      │  • FAQ Generation   │  • Smart Ranking   │
│                         │  • Pandas Agent     │                    │
└─────────────────┬───────┴─────────────────────┴────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                STORAGE LAYER                                    │
├─────────────────────────────────────────────────────────────────┤
│  💾 Local Development          │  ☁️ Cloud Production          │
│  • File System Storage         │  • Google Cloud Storage        │
│  • Local Directories           │  • Auto-managed Buckets        │
│  • Direct File Access          │  • Persistent & Scalable       │
│                                 │  • Cross-region Replication    │
└─────────────────────────────────┴─────────────────────────────────┘
```

### 🧩 Core Components

#### **1. Frontend Layer (Streamlit)**
- **Purpose**: User-friendly web interface for document processing
- **Features**: 8 specialized tabs for complete document lifecycle
- **Technology**: Streamlit with custom styling and enhanced UX
- **Responsibilities**:
  - File upload and management
  - Document parsing and content editing
  - AI-powered content generation
  - Intelligent search and querying

#### **2. API Layer (FastAPI)**
- **Purpose**: RESTful backend providing all document processing capabilities
- **Features**: 10+ endpoints with comprehensive OpenAPI documentation
- **Technology**: FastAPI with Pydantic models and async support
- **Responsibilities**:
  - Request handling and validation
  - Business logic orchestration
  - Error handling and logging
  - Response formatting

#### **3. Processing Services**

**📄 Document Processing Engine**
- **LlamaParse Integration**: Advanced document understanding with context preservation
- **Multi-format Support**: PDF, DOCX, TXT, Excel (.xlsx/.xls), CSV files
- **Intelligent Parsing**: Table extraction, image analysis, structure detection
- **Output**: Structured markdown with preserved formatting

**🤖 AI Services Layer**
- **OpenAI GPT-4.1 Integration**: Advanced language model for content generation
- **Services Provided**:
  - Document summarization with key insights
  - Intelligent question generation (1-50 questions)
  - FAQ creation with Q&A pairs
  - Pandas agent for natural language data queries

**🔍 Hybrid Search Engine**
- **Dual Search Strategy**:
  - **Vector Search (Pinecone)**: Semantic similarity matching
  - **Keyword Search (BM25)**: Exact term and phrase matching
- **AI-Powered Ranking**: Intelligent result comparison and selection
- **Multi-source Capability**: Documents + Excel/CSV data analysis

#### **4. Storage Management**

**💾 Intelligent Storage System**
- **Auto-Detection**: Automatically chooses appropriate storage based on environment
- **Local Development**: File system with organized directory structure
- **Cloud Production**: Google Cloud Storage with persistent buckets
- **Smart Upsert**: Prevents duplicates while allowing content updates

### 🔄 Data Flow Architecture

```
📤 UPLOAD → 📝 PARSE → ✏️ EDIT → 📚 INGEST → 🔍 SEARCH
    │         │         │         │          │
    ▼         ▼         ▼         ▼          ▼
uploaded_  parsed_   edited_   vector_    search_
files/     files/    content   index      results
```

**Detailed Flow:**
1. **Upload**: Files stored in `uploaded_files/` (local) or cloud bucket
2. **Parse**: LlamaParse converts to markdown → `parsed_files/`
3. **Edit**: Optional content editing and saving
4. **Ingest**: Content vectorized → Pinecone + BM25 indexes
5. **Search**: Hybrid queries return intelligent results

### 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit 1.28+ | Interactive web interface |
| **Backend** | FastAPI 0.104+ | High-performance REST API |
| **AI Processing** | OpenAI GPT-4.1 | Content generation & analysis |
| **Document Parsing** | LlamaParse | Advanced document understanding |
| **Vector Search** | Pinecone | Semantic similarity matching |
| **Keyword Search** | BM25 (Rank-BM25) | Exact term matching |
| **Data Analysis** | Pandas + AI Agent | Natural language data queries |
| **Local Storage** | File System | Development environment |
| **Cloud Storage** | Google Cloud Storage | Production persistence |
| **Deployment** | Google Cloud Run | Serverless container platform |
| **Containerization** | Docker | Consistent deployment |

## 📋 Prerequisites

### System Requirements
- **Python 3.8+** (Recommended: 3.10+)
- **pip** or **conda** for package management
- **Docker** (optional, for containerized deployment)
- **Google Cloud SDK** (for GCP deployment)
- **4GB+ RAM** (for local processing)
- **2GB+ disk space** (for documents and indexes)

### Required API Keys

Create a `.env` file in the **project root** with the following credentials:

```env
# OpenAI API (for summarization and embeddings)
OPENAI_API_KEY=sk-your-openai-api-key-here

# LlamaParse API (for document parsing)
LLAMA_CLOUD_API_KEY=llx-your-llama-cloud-api-key-here

# Pinecone API (for vector search)
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment

# Google Cloud (for production deployment - optional for local dev)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Storage Configuration (optional - auto-detects by default)
STORAGE_MODE=auto  # Options: auto, local, cloud
```

### 🔑 API Key Setup Guide

1. **OpenAI API**: 
   - Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
   - Create account → Generate API key
   - Add billing information for usage

2. **LlamaParse**: 
   - Visit [LlamaIndex Cloud](https://cloud.llamaindex.ai/)
   - Sign up → Get API key from dashboard
   - Free tier available for testing

3. **Pinecone**: 
   - Visit [Pinecone Console](https://app.pinecone.io/)
   - Create account → Create index → Get API key
   - Free tier: 1 index, 100K vectors

4. **Google Cloud**: 
   - Visit [GCP Console](https://console.cloud.google.com/)
   - Create project → Enable billing → Service account key

## 🖥️ Local Development Setup

### Quick Start (Recommended)

**1. Clone and Setup Environment:**
```bash
git clone <repository-url>
cd biz_to_bricks_v3

# Create .env file with your API keys (see above)
cp .env.example .env  # Edit with your keys
```

**2. Start the Backend Server:**
```bash
cd server
pip install -r requirements.txt
python start_server.py --storage local --reload
```

**3. Start the Frontend Client (New Terminal):**
```bash
cd client
pip install -r requirements.txt
streamlit run client.py
```

### 🎯 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **📊 Streamlit Dashboard** | http://localhost:8501 | Main user interface |
| **🔗 FastAPI Backend** | http://localhost:8004 | API server |
| **📖 Swagger UI** | http://localhost:8004/docs | Interactive API docs |
| **📚 ReDoc** | http://localhost:8004/redoc | Alternative API docs |

### 📁 Local Directory Structure

The server automatically creates these directories:

```text
server/
├── uploaded_files/       # Original uploaded documents
├── parsed_files/         # Markdown versions (editable)
├── generated_questions/  # AI-generated questions and FAQs
└── bm25_indexes/        # Search index files (auto-generated)
```

### 🔧 Advanced Local Setup

**Install Dependencies Separately:**
```bash
# Backend dependencies
cd server
pip install -r requirements.txt

# Frontend dependencies  
cd ../client
pip install -r requirements.txt
```

**Start Services with Custom Configuration:**
```bash
# Backend with custom port and debug mode
cd server
uvicorn app:app --host 0.0.0.0 --port 8005 --reload --log-level debug

# Frontend with custom port
cd client
streamlit run client.py --server.port 8502
```

**Environment Variables for Local Development:**
```bash
export STORAGE_MODE=local
export LOG_LEVEL=INFO
export MAX_FILE_SIZE_MB=200
```

## ☁️ Google Cloud Platform Deployment

### 🚀 Prerequisites for GCP Deployment

**1. Install Google Cloud SDK:**
```bash
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows: Download from https://cloud.google.com/sdk/docs/install
```

**2. Authenticate with Google Cloud:**
```bash
# Login to your Google account
gcloud auth login

# Set up application default credentials
gcloud auth application-default login
```

**3. Create and Configure GCP Project:**
```bash
# Create new project (optional)
gcloud projects create your-unique-project-id --name="Document Processing Platform"

# Set as active project
gcloud config set project your-unique-project-id

# Enable billing for the project
# Visit: https://console.cloud.google.com/billing
```

### 🤖 Automated Deployment (Recommended)

The fastest way to deploy to Google Cloud Run:

**Single Command Deployment:**
```bash
cd server
python deploy_to_cloudrun.py --project-id your-project-id --region us-central1
```

**Advanced Deployment Options:**
```bash
# Custom service name and region
python deploy_to_cloudrun.py \
  --project-id your-project-id \
  --service-name my-doc-processor \
  --region europe-west1 \
  --memory 4Gi \
  --cpu 2

# Use Google Secret Manager for enhanced security
python deploy_to_cloudrun.py \
  --project-id your-project-id \
  --use-secrets \
  --enable-monitoring

# Enable custom domain and SSL
python deploy_to_cloudrun.py \
  --project-id your-project-id \
  --custom-domain your-domain.com

# View all deployment options
python deploy_to_cloudrun.py --help
```

### 🔄 What the Automated Deployment Does

The `deploy_to_cloudrun.py` script performs comprehensive deployment:

**Phase 1: Prerequisites & Validation**
- ✅ Verifies Google Cloud SDK installation
- ✅ Checks Docker availability
- ✅ Validates environment variables and API keys
- ✅ Confirms project permissions and billing

**Phase 2: Google Cloud Setup**
- 🔧 Enables required Google Cloud APIs:
  - Cloud Run API
  - Artifact Registry API
  - Cloud Build API
  - Cloud Storage API
  - Secret Manager API (if using secrets)
- 🏗️ Creates Artifact Registry repository for Docker images
- 🪣 Creates persistent Cloud Storage buckets

**Phase 3: Container Build & Deploy**
- 📦 Builds optimized Docker image for Cloud Run
- 🚀 Pushes image to Google Artifact Registry
- ⚙️ Configures Cloud Run service with:
  - Environment variables
  - Memory and CPU allocation
  - Auto-scaling settings
  - Health checks

**Phase 4: Storage & Persistence**
- 📁 Creates organized Cloud Storage buckets:
  - `{project-id}-uploaded-files` - Original documents
  - `{project-id}-parsed-files` - Processed markdown
  - `{project-id}-generated-questions` - AI content
  - `{project-id}-bm25-indexes` - Search indexes

**Phase 5: Validation & Output**
- 🧪 Tests deployed service health
- 📊 Provides service URLs and monitoring links
- 📋 Outputs configuration details

### 🏗️ Manual GCP Deployment

For advanced users who prefer step-by-step control:

**1. Enable Required APIs:**
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com
```

**2. Create Artifact Registry Repository:**
```bash
gcloud artifacts repositories create document-processing \
  --repository-format=docker \
  --location=us-central1 \
  --description="Document processing service images"
```

**3. Configure Docker Authentication:**
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**4. Create Cloud Storage Buckets:**
```bash
PROJECT_ID=$(gcloud config get-value project)

# Create buckets with proper configuration
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$PROJECT_ID-uploaded-files
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$PROJECT_ID-parsed-files
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$PROJECT_ID-generated-questions
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$PROJECT_ID-bm25-indexes

# Set bucket permissions
gsutil iam ch serviceAccount:$(gcloud config get-value project | xargs -I {} gcloud projects describe {} --format="value(projectNumber)")-compute@developer.gserviceaccount.com:objectAdmin gs://$PROJECT_ID-*
```

**5. Build and Push Docker Image:**
```bash
cd server

# Build for Cloud Run (linux/amd64)
docker build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/$PROJECT_ID/document-processing/server:latest .

# Push to registry
docker push us-central1-docker.pkg.dev/$PROJECT_ID/document-processing/server:latest
```

**6. Deploy to Cloud Run:**
```bash
gcloud run deploy document-processing-service \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/document-processing/server:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8004 \
  --memory 4Gi \
  --cpu 2 \
  --max-instances 10 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,STORAGE_MODE=cloud" \
  --set-env-vars "OPENAI_API_KEY=$OPENAI_API_KEY" \
  --set-env-vars "LLAMA_CLOUD_API_KEY=$LLAMA_CLOUD_API_KEY" \
  --set-env-vars "PINECONE_API_KEY=$PINECONE_API_KEY" \
  --set-env-vars "PINECONE_ENVIRONMENT=$PINECONE_ENVIRONMENT"
```

### 🌐 Post-Deployment Configuration

**1. Get Service URL:**
```bash
SERVICE_URL=$(gcloud run services describe document-processing-service \
  --region us-central1 \
  --format 'value(status.url)')
echo "Service deployed at: $SERVICE_URL"
```

**2. Update Client Configuration:**
```python
# In client/client.py, update the BASE_URL:
BASE_URL = "https://your-cloud-run-service-url"
# Example: "https://document-processing-service-xxxxx-uc.a.run.app"
```

**3. Test Deployment:**
```bash
# Health check
curl $SERVICE_URL/

# API documentation
curl $SERVICE_URL/docs
```

**4. Run Client Locally (pointing to cloud backend):**
```bash
cd client
streamlit run client.py
```

### 🔒 Security Best Practices for Production

**1. Use Google Secret Manager (Recommended):**
```bash
# Store API keys securely
echo -n "$OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
echo -n "$LLAMA_CLOUD_API_KEY" | gcloud secrets create llama-cloud-api-key --data-file=-
echo -n "$PINECONE_API_KEY" | gcloud secrets create pinecone-api-key --data-file=-

# Deploy with secret references
gcloud run deploy document-processing-service \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/document-processing/server:latest \
  --region us-central1 \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
  --set-secrets="LLAMA_CLOUD_API_KEY=llama-cloud-api-key:latest" \
  --set-secrets="PINECONE_API_KEY=pinecone-api-key:latest"
```

**2. Enable Authentication (Optional):**
```bash
# Remove public access
gcloud run services remove-iam-policy-binding document-processing-service \
  --region us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"

# Add authenticated users
gcloud run services add-iam-policy-binding document-processing-service \
  --region us-central1 \
  --member="user:your-email@domain.com" \
  --role="roles/run.invoker"
```

### 📊 Monitoring and Logging

**View Logs:**
```bash
# Recent logs
gcloud logs read --project $PROJECT_ID --service document-processing-service --limit 50

# Real-time logs
gcloud logs tail --project $PROJECT_ID --service document-processing-service
```

**Monitor Performance:**
```bash
# Service metrics
gcloud run services describe document-processing-service \
  --region us-central1 \
  --format="table(status.conditions[].type:label=CONDITION,status.conditions[].status:label=STATUS)"
```

**Set up Monitoring (Optional):**
- Visit [Google Cloud Monitoring](https://console.cloud.google.com/monitoring)
- Create custom dashboards for your service
- Set up alerting for errors or high latency

## 🐳 Docker Deployment (Local Production)

For running a production-like environment locally:

### Build and Run Server Container

```bash
cd server

# Build the optimized image
docker build -t document-processing-server:latest .

# Create persistent local directories
mkdir -p uploaded_files parsed_files generated_questions bm25_indexes

# Run with proper configuration
docker run -d -p 8004:8004 --name doc-server \
  --env-file ../.env \
  --restart unless-stopped \
  -v $(pwd)/uploaded_files:/app/uploaded_files \
  -v $(pwd)/parsed_files:/app/parsed_files \
  -v $(pwd)/generated_questions:/app/generated_questions \
  -v $(pwd)/bm25_indexes:/app/bm25_indexes \
  document-processing-server:latest
```

### Advanced Docker Configuration

**Docker Compose Setup (docker-compose.yml):**
```yaml
version: '3.8'
services:
  document-processor:
    build: ./server
    ports:
      - "8004:8004"
    env_file:
      - .env
    volumes:
      - ./data/uploaded_files:/app/uploaded_files
      - ./data/parsed_files:/app/parsed_files
      - ./data/generated_questions:/app/generated_questions
      - ./data/bm25_indexes:/app/bm25_indexes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Run with Docker Compose:**
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🚀 Features Overview

### 📄 Document Processing
- **Multi-format Support**: PDF, DOCX, TXT, Excel (.xlsx/.xls), CSV
- **Advanced Parsing**: LlamaParse with context preservation
- **Intelligent Editing**: Real-time markdown editing with auto-save
- **Smart Upsert**: Duplicate prevention with content updates

### 🤖 AI-Powered Content Generation
- **Summarization**: Concise summaries with key insights extraction
- **Question Generation**: 1-50 intelligent questions per document
- **FAQ Creation**: Question-answer pairs with context
- **Natural Language Data Queries**: Pandas agent for Excel/CSV analysis

### 🔍 Intelligent Search System
- **Hybrid Search**: Vector (Pinecone) + Keyword (BM25) combination
- **AI Result Ranking**: Intelligent comparison and selection
- **Multi-source Queries**: Documents + data files simultaneously
- **Targeted Search**: Specific document or file filtering

### 💾 Smart Storage Management
- **Auto-Detection**: Environment-based storage selection
- **Local Development**: Organized file system structure
- **Cloud Production**: Google Cloud Storage with persistence
- **Cross-platform**: Seamless local ↔ cloud transitions

## 📖 Complete User Workflow

### 1. **📤 Upload Documents**
- Navigate to "Upload" tab in Streamlit interface
- Select files from local system or use sample files from `docs/`
- Supports drag-and-drop for multiple files
- Automatic file type detection and guidance

### 2. **📝 Parse Documents**
- Go to "Parse Files" tab
- Select uploaded file from dropdown
- Click "Parse File" - automatically processes and saves as markdown
- Edit content if needed using built-in editor
- Save changes with auto-ingestion option

### 3. **🤖 Generate AI Content**

**Summarization:**
- Navigate to "Summarize" tab
- Select parsed file
- Generate concise summaries with key insights

**Question Generation:**
- Go to "Generate Questions" tab
- Choose number of questions (1-50)
- AI creates relevant questions based on content

**FAQ Creation:**
- Use "Generate FAQ" tab
- Specify number of FAQ items
- Get question-answer pairs for common topics

### 4. **📚 Index for Search**
- **Automatic**: Use "Save & Ingest" in Parse Files tab
- **Manual**: Use "Ingest Documents" tab for batch processing
- Documents are vectorized and added to search indexes
- Smart upsert prevents duplicates

### 5. **🔍 Search and Query**

**Hybrid Search:**
- Use "Hybrid Search" tab
- Enter natural language queries
- Choose specific documents or search all
- Get AI-ranked results from multiple sources

**Data Analysis:**
- Use "Excel Search" tab for spreadsheet data
- Ask questions about numerical data
- Get calculations, summaries, and insights

## 📊 API Documentation

### Complete API Reference
- **📋 Detailed Documentation**: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)
- **🔗 Interactive Swagger UI**: `http://localhost:8004/docs`
- **📚 ReDoc Interface**: `http://localhost:8004/redoc`

### API Endpoints Overview

| Endpoint | Method | Purpose | Features |
|----------|--------|---------|----------|
| `/uploadfile/` | POST | Upload documents | Auto file type detection |
| `/listfiles/{directory}` | GET | List files | Multiple directory support |
| `/parsefile/{filename}` | GET | Parse documents | LlamaParse integration |
| `/savecontent/{filename}` | POST | Save edited content | Real-time updates |
| `/saveandingst/{filename}` | POST | Save + auto-ingest | ✨ One-step processing |
| `/summarizecontent/{filename}` | GET | Generate summaries | AI-powered insights |
| `/generatequestions/{filename}` | GET | Create questions | Configurable quantity |
| `/generatefaq/{filename}` | GET | Generate FAQ | Q&A pairs |
| `/ingestdocuments/{filename}` | POST | Add to search index | 🔄 Smart upsert |
| `/hybridsearch/` | POST | Intelligent search | Multi-source ranking |
| `/querypandas/` | POST | Excel/CSV analysis | Natural language queries |
| `/sourcedocuments/` | GET | Available documents | Search filtering |

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

**🔴 API Key Configuration Issues**
```bash
# Check if .env file exists and is properly formatted
cat .env

# Verify environment variables are loaded
cd server
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
required_keys = ['OPENAI_API_KEY', 'LLAMA_CLOUD_API_KEY', 'PINECONE_API_KEY']
for key in required_keys:
    status = '✅' if os.getenv(key) else '❌'
    print(f'{status} {key}: {bool(os.getenv(key))}')
"
```

**🔴 Port Conflicts**
```bash
# Check what's using the default ports
lsof -i :8004  # Backend
lsof -i :8501  # Frontend

# Use alternative ports
cd server
python start_server.py --port 8005

cd client
streamlit run client.py --server.port 8502
```

**🔴 Permission and Directory Issues**
```bash
# Fix directory permissions
chmod -R 755 server/uploaded_files server/parsed_files server/generated_questions

# Recreate directories if needed
cd server
rm -rf uploaded_files parsed_files generated_questions bm25_indexes
python -c "
from app import ensure_directories_exist
ensure_directories_exist()
print('Directories recreated successfully')
"
```

**🔴 Memory and Performance Issues**
```bash
# Check system resources
df -h  # Disk space
free -h  # Memory usage
top  # CPU usage

# Clear cache and temporary files
cd server
rm -rf __pycache__/ .cache/
find . -name "*.pyc" -delete

# Restart with memory optimization
python start_server.py --workers 1 --max-requests 100
```

**🔴 Docker Issues**
```bash
# Check Docker status
docker ps -a

# View container logs
docker logs doc-server -f

# Restart container
docker restart doc-server

# Clean rebuild
docker stop doc-server && docker rm doc-server
docker rmi document-processing-server
docker build -t document-processing-server:latest .
```

**🔴 Google Cloud Deployment Issues**
```bash
# Check authentication
gcloud auth list
gcloud config get-value project

# Verify service status
gcloud run services list --region us-central1

# Check Cloud Run logs
gcloud logs read --service document-processing-service --limit 50

# Redeploy service
cd server
python deploy_to_cloudrun.py --project-id $(gcloud config get-value project) --force-redeploy
```

### Performance Optimization

**Local Development:**
```bash
# Enable debug mode for detailed logging
export LOG_LEVEL=DEBUG

# Optimize Python performance
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Use faster JSON library
pip install orjson
```

**Production Deployment:**
```bash
# Cloud Run optimization
gcloud run services update document-processing-service \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --concurrency 100 \
  --max-instances 10
```

### Log Monitoring and Debugging

**Local Development:**
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG

# Monitor real-time logs
tail -f server/app.log  # If file logging enabled

# Python debugging
cd server
python -m pdb start_server.py
```

**Docker Deployment:**
```bash
# Container logs
docker logs doc-server -f --tail 100

# Execute commands inside container
docker exec -it doc-server bash

# Check container health
docker inspect doc-server | grep -A 10 Health
```

**Google Cloud Run:**
```bash
# Real-time log streaming
gcloud logs tail --service document-processing-service

# Error log filtering
gcloud logs read --service document-processing-service \
  --filter 'severity>=ERROR' --limit 20

# Performance monitoring
gcloud run services describe document-processing-service \
  --region us-central1 --format json | jq '.status'
```

## 📊 Deployment Comparison Matrix

| Feature | Local Development | Docker Local | Google Cloud Run |
|---------|-------------------|--------------|------------------|
| **⚡ Setup Speed** | ⭐⭐⭐⭐⭐ Very Fast | ⭐⭐⭐⭐ Fast | ⭐⭐⭐ Moderate |
| **💾 File Persistence** | ✅ Local filesystem | ✅ Docker volumes | ✅ Cloud Storage buckets |
| **📈 Scalability** | ❌ Single instance | ❌ Single instance | ✅ Auto-scaling (0-1000) |
| **🌐 Global Access** | ❌ Local network only | ❌ Local network only | ✅ HTTPS worldwide |
| **💰 Cost** | Free | Free | Pay-per-use (~$0.50-5/day) |
| **🔒 Security** | Basic file permissions | Container isolation | Enterprise-grade |
| **📊 Monitoring** | Console logs | Docker logs | Cloud Monitoring + Logging |
| **🔄 Auto-restart** | Manual | Docker restart policies | Cloud Run health checks |
| **🚀 Performance** | Direct Python | Container overhead | Optimized serverless |
| **🛠️ Debugging** | Full IDE support | Container debugging | Cloud debugging tools |
| **📦 Dependencies** | Local Python env | Containerized | Fully managed |
| **🎯 Best For** | Development & testing | Local production | Production & sharing |
| **🔧 Maintenance** | Manual updates | Image rebuilds | Automatic platform updates |

## 🎯 Best Practices and Recommendations

### Development Workflow
1. **Start Local**: Begin with local development for rapid iteration
2. **Test with Docker**: Validate with Docker before cloud deployment
3. **Deploy to Cloud**: Use Cloud Run for production and sharing
4. **Monitor Performance**: Use Cloud Monitoring for production insights

### Security Recommendations
- Use Google Secret Manager for production API keys
- Enable Cloud Run authentication for sensitive documents
- Regular backup of processed content
- Monitor API usage and set billing alerts

### Performance Optimization
- Use appropriate Cloud Run memory allocation (2-4GB recommended)
- Enable Cloud CDN for static content delivery
- Implement request caching for frequently accessed documents
- Monitor and optimize vector index performance

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
- 📚 Check the [API Documentation](./API_DOCUMENTATION.md)
- 🐛 Open an issue on GitHub
- 📧 Contact support team

---

## 🎉 Getting Started Checklist

- [ ] ✅ Clone repository
- [ ] 🔑 Set up API keys in `.env` file
- [ ] 🖥️ Test local development setup
- [ ] 📄 Upload and parse test documents
- [ ] 🔍 Try hybrid search functionality
- [ ] ☁️ (Optional) Deploy to Google Cloud Run
- [ ] 📚 Explore API documentation
- [ ] 🎯 Customize for your use case

**Ready to transform your document processing workflow? Let's get started!** 🚀