# Biz To Bricks - Document Processing Platform

A comprehensive document processing and querying system with FastAPI backend and Streamlit frontend, featuring AI-powered parsing, summarization, question generation, and hybrid search capabilities.

## 🚀 Features

- **📄 Document Upload & Storage** - Support for PDF, DOCX, and other file formats
- **🔍 Advanced PDF Parsing** - LlamaParse integration for high-quality text extraction
- **✏️ Document Editing** - Edit parsed content with real-time saving and auto-ingestion
- **📝 AI Summarization** - Generate concise summaries using OpenAI GPT
- **❓ Question Generation** - Create relevant questions from document content (1-50 questions)
- **🔎 Hybrid Search** - Combine vector search (Pinecone) with BM25 keyword search
- **🔄 Smart Upsert** - Prevent document duplicates with intelligent update functionality
- **☁️ Cloud Storage** - Seamless local/cloud storage with automatic environment detection
- **📊 Interactive Dashboard** - User-friendly Streamlit interface with 7 specialized tabs

## 🏗️ Architecture

```
biz_to_bricks_v3/
├── server/                     # FastAPI Backend
│   ├── app.py                 # Main API application (10 endpoints)
│   ├── file_parser.py         # Document parsing with LlamaParse
│   ├── doc_summarizer.py      # AI text summarization
│   ├── question_gen.py        # AI question generation
│   ├── faq_gen.py             # AI FAQ generation
│   ├── hybrid_search.py       # Vector + BM25 search
│   ├── ingest_docs.py         # Document ingestion with upsert
│   ├── pinecone_util.py       # Pinecone vector operations
│   ├── cloud_storage_util.py  # GCS integration
│   ├── file_util_enhanced.py  # Unified file management
│   ├── start_server.py        # Server startup script
│   ├── deploy_to_cloudrun.py  # Automated GCP deployment
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Docker configuration
├── client/                    # Streamlit Frontend
│   ├── client.py             # Streamlit application (7 tabs)
│   └── requirements.txt      # Client dependencies
├── docs/                     # Sample documents for testing
├── API_DOCUMENTATION.md      # Complete API reference
└── README.md                # This file
```

## 📋 Prerequisites

- **Python 3.8+** (Recommended: 3.10+)
- **pip** or **conda** for package management
- **Docker** (optional, for containerized deployment)
- **Google Cloud SDK** (for GCP deployment)

## 🔑 Environment Setup

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

### Where to Get API Keys

1. **OpenAI**: Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. **LlamaParse**: Visit [LlamaIndex Cloud](https://cloud.llamaindex.ai/)
3. **Pinecone**: Visit [Pinecone Console](https://app.pinecone.io/)
4. **Google Cloud**: Visit [GCP Console](https://console.cloud.google.com/)

---

## 🖥️ Local Development (Recommended)

### Method 1: Quick Start Script

**1. Start the Server:**
```bash
cd server
python start_server.py --storage local --reload
```
Or

```bash
cd server
uvicorn app:app --host 0.0.0.0 --port 8004 --loop asyncio --reload
```

**2. Start the Client (New Terminal):**
```bash
cd client
pip install -r requirements.txt
streamlit run client.py
```

### Method 2: Manual Setup

**1. Install Dependencies:**
```bash
# Server dependencies
cd server
pip install -r requirements.txt

# Client dependencies
cd ../client
pip install -r requirements.txt
```

**2. Start the FastAPI Server:**
```bash
cd server
# Option A: Using the startup script (recommended)
python start_server.py --storage local --reload

# Option B: Direct uvicorn command
uvicorn app:app --host 0.0.0.0 --port 8004 --reload
```

**3. Start the Streamlit Client:**
```bash
cd client
streamlit run client.py
```

### 🎯 Access Points

- **📊 Streamlit Dashboard**: http://localhost:8501
- **🔗 FastAPI Backend**: http://localhost:8004
- **📖 API Documentation**: http://localhost:8004/docs (Swagger UI)
- **📚 Alternative Docs**: http://localhost:8004/redoc (ReDoc)

### 📁 Local Directory Structure

The server automatically creates these directories:

```text
server/
├── uploaded_files/       # Original uploaded documents
├── parsed_files/         # Markdown versions (editable)
├── generated_questions/  # AI-generated questions
└── bm25_indexes/        # Search index files
```

### 💡 Smart Storage System

The application features intelligent storage management:

- **🏠 Local Development**: Uses local filesystem directories
- **☁️ Cloud Deployment**: Automatically switches to Google Cloud Storage buckets
- **🔄 Auto-Detection**: Detects environment and chooses appropriate storage
- **🔄 Upsert Capability**: Prevents document duplicates when re-uploading

---

## ☁️ Google Cloud Platform Deployment

### Prerequisites

1. **Install Google Cloud SDK:**
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Linux/Windows: Visit https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Create/Select GCP Project:**
   ```bash
   # Create new project
   gcloud projects create your-project-id --name="Document Processing"
   
   # Set as active project
   gcloud config set project your-project-id
   
   # Enable billing (required for Cloud Run)
   # Visit: https://console.cloud.google.com/billing
   ```

### 🚀 Automated Deployment (Recommended)

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
  --region europe-west1

# Use Google Secret Manager for API keys (more secure)
python deploy_to_cloudrun.py \
  --project-id your-project-id \
  --use-secrets

# View all options
python deploy_to_cloudrun.py --help
```

### 🔄 What the Deployment Script Does

The automated deployment script performs these steps:

1. ✅ **Prerequisites Check** - Verifies gcloud, Docker, and environment
2. ✅ **API Enablement** - Enables required Google Cloud APIs
3. ✅ **Artifact Registry** - Creates Docker repository
4. ✅ **Cloud Storage** - Creates persistent storage buckets
5. ✅ **Docker Build** - Builds and pushes container image
6. ✅ **Cloud Run Deploy** - Deploys service with proper configuration
7. ✅ **Testing** - Validates deployment and provides service URL

### 🪣 Cloud Storage Buckets

The deployment creates these buckets for persistent storage:

| Bucket Name | Purpose | Local Equivalent |
|-------------|---------|------------------|
| `{project-id}-uploaded-files` | Original documents | `uploaded_files/` |
| `{project-id}-parsed-files` | Parsed markdown | `parsed_files/` |
| `{project-id}-generated-questions` | AI questions | `generated_questions/` |
| `{project-id}-bm25-indexes` | Search indexes | `bm25_indexes/` |

### 🔧 Manual GCP Deployment

If you prefer manual control:

```bash
# 1. Enable required APIs
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com

# 2. Create Artifact Registry repository
gcloud artifacts repositories create document-processing \
  --repository-format=docker \
  --location=us-central1

# 3. Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# 4. Build and push Docker image
cd server
docker build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/your-project-id/document-processing/server:latest .
docker push us-central1-docker.pkg.dev/your-project-id/document-processing/server:latest

# 5. Deploy to Cloud Run
gcloud run deploy document-processing-service \
  --image us-central1-docker.pkg.dev/your-project-id/document-processing/server:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8004 \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-project-id,OPENAI_API_KEY=your-key,LLAMA_CLOUD_API_KEY=your-key,PINECONE_API_KEY=your-key,PINECONE_ENVIRONMENT=your-env
```

### 🌐 Accessing Deployed Service

After successful deployment, you'll receive a Cloud Run URL like:
```
https://document-processing-service-xxxxx-uc.a.run.app
```

**Update Client Configuration:**
```python
# In client/client.py, change:
BASE_URL = "https://your-cloud-run-url-here"
```

**Run Client Locally:**
```bash
cd client
streamlit run client.py
```

---

## 🐳 Docker Deployment (Local Production)

### Build and Run Server Container

```bash
cd server

# Build the image
docker build -t document-processing-server .

# Create local directories
mkdir -p uploaded_files parsed_files generated_questions bm25_indexes

# Run the container
docker run -d -p 8004:8004 --name doc-server \
  --env-file ../.env \
  -v $(pwd)/uploaded_files:/app/uploaded_files \
  -v $(pwd)/parsed_files:/app/parsed_files \
  -v $(pwd)/generated_questions:/app/generated_questions \
  -v $(pwd)/bm25_indexes:/app/bm25_indexes \
  document-processing-server
```

### Run Client

```bash
cd client
pip install -r requirements.txt
streamlit run client.py
```

---

## 📖 Complete User Workflow

### 1. **📤 Upload Documents**

- Go to "Upload" tab
- Select files from `docs/` directory or your own files
- Click "Upload File"

### 2. **📝 Parse Documents**

- Go to "Parse Files" tab
- Select uploaded file
- Click "Parse File" (automatically saves as .md)
- Edit content if needed and save

### 3. **📊 Generate Summary**

- Go to "Summarize" tab
- Select parsed file
- Click "Generate Summary"

### 4. **❓ Generate Questions**

- Go to "Generate Questions" tab
- Select parsed file
- Choose number of questions (1-50)
- Click "Generate Questions"

### 5. **📚 Save & Ingest Documents**

- **Option A**: Go to "Save & Ingest" tab → Select file → Save + Auto-ingest
- **Option B**: Go to "Ingest Documents" tab → Select .md file → Manual ingest
- Documents are automatically upserted (no duplicates created)

### 6. **🔍 Search Documents**

- Go to "Hybrid Search" tab
- Enter search query
- Get AI-powered results combining vector and keyword search

---

## 📊 API Documentation

Comprehensive API documentation is available:

- **📋 Complete Reference**: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)
- **🔗 Interactive Swagger UI**: `http://localhost:8004/docs`
- **📚 ReDoc Interface**: `http://localhost:8004/redoc`

### Quick API Overview

| Endpoint | Method | Purpose | New Features |
|----------|--------|---------|--------------|
| `/uploadfile/` | POST | Upload documents | - |
| `/listfiles/{directory}` | GET | List files | - |
| `/parsefile/{filename}` | GET | Parse documents | - |
| `/savecontent/{filename}` | POST | Save edited content | - |
| `/saveandingst/{filename}` | POST | Save + auto-ingest | ✨ NEW |
| `/summarizecontent/{filename}` | GET | Generate summaries | - |
| `/generatequestions/{filename}` | GET | Generate questions | - |
| `/ingestdocuments/{filename}` | POST | Add to search index | 🔄 Upsert support |
| `/hybridsearch/` | POST | Search documents | - |
| `/deletefile/{directory}/{filename}` | DELETE | Delete files | - |

---

## 🔧 Troubleshooting

### Common Issues

**🔴 API Key Errors**
```bash
# Ensure .env file exists in project root
ls -la .env

# Check environment variables are loaded
cd server
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OPENAI_API_KEY:', bool(os.getenv('OPENAI_API_KEY')))"
```

**🔴 Port Conflicts**
```bash
# Check what's using port 8004
lsof -i :8004

# Use different port
cd server
python start_server.py --port 8005
```

**🔴 Permission Issues**
```bash
# Fix directory permissions
chmod -R 755 server/uploaded_files server/parsed_files
```

**🔴 Connection Timeout**
```bash
# Check if server is running
curl http://localhost:8004/

# Restart server
cd server
python start_server.py --storage local --reload
```

### Log Monitoring

**Local Development:**
```bash
# Server logs appear in terminal where you started the server
# Client logs appear in terminal where you started Streamlit
```

**Docker:**
```bash
docker logs doc-server -f
```

**Google Cloud Run:**
```bash
gcloud logs read --project your-project-id --service document-processing-service --limit 50
```

### Clean Restart

**Local/Docker:**
```bash
# Stop services
pkill -f uvicorn
docker stop doc-server 2>/dev/null || true
docker rm doc-server 2>/dev/null || true

# Clear processed files (optional)
rm -rf server/uploaded_files/* server/parsed_files/* server/generated_questions/* server/bm25_indexes/*

# Restart
cd server && python start_server.py --storage local --reload
```

**Cloud Run:**
```bash
# Delete and redeploy service
gcloud run services delete document-processing-service --region your-region --quiet
cd server && python deploy_to_cloudrun.py --project-id your-project-id
```

---

## 📊 Deployment Comparison

| Feature | Local Dev | Docker Local | Cloud Run |
|---------|-----------|--------------|-----------|
| **⚡ Setup Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **💾 File Persistence** | ✅ Local files | ✅ Docker volumes | ✅ Cloud Storage |
| **📈 Scalability** | ❌ Single instance | ❌ Single instance | ✅ Auto-scaling |
| **🌐 Global Access** | ❌ Local only | ❌ Local network | ✅ HTTPS worldwide |
| **💰 Cost** | Free | Free | Pay-per-use |
| **🔒 Security** | Basic | Containerized | Production-grade |
| **📊 Monitoring** | Manual | Docker logs | Cloud Monitoring |
| **🔄 Upsert Support** | ✅ Full support | ✅ Full support | ✅ Full support |
| **☁️ Storage Mode** | Local filesystem | Local filesystem | Auto cloud storage |
| **🎯 Best For** | Development | Local production | Production/sharing |

---

## 🆘 Getting Help

1. **📖 Check Documentation**: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)
2. **🔍 Review Logs**: Check terminal output or Docker/Cloud Run logs
3. **🧪 Test API**: Use Swagger UI at `/docs` endpoint
4. **🔄 Clean Restart**: Follow troubleshooting steps above
5. **🐛 Report Issues**: Create detailed issue reports with logs

---

## 🎉 Quick Start Summary

**For Development:**

```bash
# Terminal 1: Start server
cd server && python start_server.py --storage local --reload

# Terminal 2: Start client
cd client && streamlit run client.py

# Access: http://localhost:8501
```

**For Production:**

```bash
# One-command deployment to Google Cloud
cd server && python deploy_to_cloudrun.py --project-id your-project-id
```

Happy document processing! 🚀📄