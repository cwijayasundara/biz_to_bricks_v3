# Document Processing Server

A FastAPI server for uploading, parsing, editing, summarizing, and querying documents using LlamaParse, OpenAI, and Pinecone.

## Features

- Document upload and storage
- PDF parsing with LlamaParse
- Document editing and summarization
- Vector search with Pinecone
- Hybrid search combining dense vectors and sparse BM25 encoding

## Environment Setup

Before running the server, you need to create a `.env` file with the following credentials:

```bash
OPENAI_API_KEY=your_openai_api_key
LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
```

## Quick Start with Docker Compose

1. **Create environment file:**
```bash
cp env-template.txt .env
# Edit .env with your actual API keys
```

2. **Run with Docker Compose:**
```bash
docker compose up -d --build
```

The server will be accessible at: http://localhost:8004

## API Endpoints

- `POST /uploadfile/` - Upload a document
- `GET /listfiles/{directory}` - List files in a directory
- `GET /parsefile/{filename}` - Parse an uploaded file to markdown
- `POST /savecontent/{filename}` - Save edited content
- `GET /summarizecontent/{filename}` - Generate a summary for a file
- `POST /ingestdocuments/{filename}` - Ingest a document into Pinecone and BM25 indexes
- `POST /hybridsearch/` - Perform hybrid search query

## Document Processing Flow

1. Upload a document using `/uploadfile/`
2. Parse the document to markdown with `/parsefile/{filename}`
3. Edit the content if needed with `/savecontent/{filename}`
4. Summarize the document with `/summarizecontent/{filename}`
5. Ingest the document with `/ingestdocuments/{filename}`
6. Query the document with `/hybridsearch/`

## Google Cloud Run Deployment

**⚠️ Important: File Storage in Cloud Run**

Cloud Run containers have ephemeral storage, meaning files are lost when containers restart. This application automatically uses **Google Cloud Storage** for persistent file storage when deployed to Cloud Run.

The following directories are automatically mapped to Cloud Storage buckets:
- `uploaded_files` → `{project-id}-uploaded-files`
- `parsed_files` → `{project-id}-parsed-files` 
- `edited_files` → `{project-id}-edited-files`
- `summarized_files` → `{project-id}-summarized-files`
- `bm25_indexes` → `{project-id}-bm25-indexes`

### Quick Deployment (Automated)

Use the automated deployment script (creates buckets automatically):

```bash
# Basic deployment
python deploy_to_cloudrun.py --project-id YOUR_PROJECT_ID --region us-central1

# With Secret Manager (production)
python deploy_to_cloudrun.py --project-id YOUR_PROJECT_ID --region us-central1 --use-secrets

# View all options
python deploy_to_cloudrun.py --help
```

### Manual Deployment

Follow these steps to manually deploy to Google Cloud Run:

#### 1. Prerequisites
```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### 2. Enable Required APIs
```bash
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

#### 3. Create Artifact Registry Repository
```bash
gcloud artifacts repositories create document-processing \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for document processing service"
```

#### 4. Build and Push Docker Image
```bash
# Build for Cloud Run (linux/amd64)
docker build --platform linux/amd64 \
    -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/document-processing/document-processing-server:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/document-processing/document-processing-server:latest
```

#### 5. Deploy to Cloud Run
```bash
# Source environment variables
source .env

# Deploy service
gcloud run deploy document-processing-service \
    --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/document-processing/document-processing-server:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY,LLAMA_CLOUD_API_KEY=$LLAMA_CLOUD_API_KEY,PINECONE_API_KEY=$PINECONE_API_KEY,PINECONE_ENVIRONMENT=$PINECONE_ENVIRONMENT \
    --port 8004 \
    --memory 2Gi \
    --cpu 1
```

#### 6. Get Service URL
```bash
gcloud run services describe document-processing-service --region=us-central1 --format='value(status.url)'
```

### Environment Variables

For production deployments, consider using Google Secret Manager:

```bash
# Create secrets
echo -n "your_openai_key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your_llama_key" | gcloud secrets create llama-cloud-api-key --data-file=-
echo -n "your_pinecone_key" | gcloud secrets create pinecone-api-key --data-file=-
echo -n "your_pinecone_env" | gcloud secrets create pinecone-environment --data-file=-

# Deploy with secrets
gcloud run deploy document-processing-service \
    --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/document-processing/document-processing-server:latest \
    --region us-central1 \
    --set-secrets OPENAI_API_KEY=openai-api-key:latest,LLAMA_CLOUD_API_KEY=llama-cloud-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest,PINECONE_ENVIRONMENT=pinecone-environment:latest
```

## Storage Configuration

The server supports multiple storage modes that can be configured based on your deployment needs:

- **`local`** - Uses local filesystem (development, testing)
- **`cloud`** - Uses Google Cloud Storage (production, Cloud Run)  
- **`auto`** - Auto-detects based on environment (default)

For detailed configuration options, see [STORAGE_CONFIGURATION.md](STORAGE_CONFIGURATION.md).

## Local Development

### Option 1: Using the Startup Script (Recommended)
```bash
# Local storage with auto-reload
python start_server.py --storage local --reload

# Cloud storage for testing
GOOGLE_CLOUD_PROJECT=your-project-id python start_server.py --storage cloud
```

### Option 2: Using Environment Variables
```bash
# Local storage
STORAGE_MODE=local uvicorn app:app --reload --host 0.0.0.0 --port 8004

# Cloud storage
STORAGE_MODE=cloud GOOGLE_CLOUD_PROJECT=your-project-id uvicorn app:app --host 0.0.0.0 --port 8004
```

### Option 3: Using Docker Compose
```bash
# Local storage (default)
STORAGE_MODE=local docker compose up

# Cloud storage
STORAGE_MODE=cloud GOOGLE_CLOUD_PROJECT=your-project-id docker compose up
```

### Option 4: Direct Docker Build
```bash
cd server
docker build -t document-processing-server .
docker run -d -p 8004:8004 --name doc-server --env-file .env \
    -e STORAGE_MODE=local \
    -v $(pwd)/uploaded_files:/app/uploaded_files \
    -v $(pwd)/parsed_files:/app/parsed_files \
    -v $(pwd)/edited_files:/app/edited_files \
    -v $(pwd)/summarized_files:/app/summarized_files \
    -v $(pwd)/bm25_indexes:/app/bm25_indexes \
    document-processing-server
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Ensure you're authenticated: `gcloud auth login`
   - Check project access: `gcloud projects get-iam-policy YOUR_PROJECT_ID`

2. **Image Architecture Issues**
   - Always build with `--platform linux/amd64` for Cloud Run

3. **Port Configuration**
   - Cloud Run expects apps to listen on the PORT environment variable
   - Our Dockerfile handles this automatically

4. **Environment Variables**
   - Ensure .env file exists and contains all required keys
   - Use Secret Manager for production deployments

### Monitoring and Logs
```bash
# View service logs
gcloud run services logs read document-processing-service --region=us-central1

# Monitor service
gcloud run services describe document-processing-service --region=us-central1
```

## API Documentation

Once deployed, access the interactive API documentation at:
- Local: http://localhost:8004/docs
- Cloud Run: https://YOUR_SERVICE_URL/docs 