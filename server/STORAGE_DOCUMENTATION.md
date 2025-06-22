# Document Processing Server - Storage Documentation

Complete guide for configuring and using storage in the Document Processing Server, covering both local development and cloud deployment scenarios.

## Table of Contents

1. [Storage Modes Overview](#storage-modes-overview)
2. [Quick Start](#quick-start)
3. [Configuration Methods](#configuration-methods)
4. [Environment Detection](#environment-detection)
5. [Local Development](#local-development)
6. [Cloud Storage Integration](#cloud-storage-integration)
7. [BM25 Index Storage](#bm25-index-storage)
8. [Deployment](#deployment)
9. [Testing and Validation](#testing-and-validation)
10. [Troubleshooting](#troubleshooting)
11. [Reference](#reference)

---

## Storage Modes Overview

The server supports three storage modes that can be configured based on your deployment needs:

| Mode | Description | Use Case | Storage Location |
|------|-------------|----------|------------------|
| `local` | Uses local filesystem | Development, testing | Local directories |
| `cloud` | Uses Google Cloud Storage | Production, Cloud Run | GCS buckets |
| `auto` | Auto-detects based on environment | Default (recommended) | Automatic selection |

### Storage Benefits

#### Local Mode (`local`)
- ✅ **Fast access** - No network latency
- ✅ **Simple debugging** - Files visible in filesystem
- ✅ **Offline development** - No cloud authentication needed
- ✅ **Quick iteration** - Immediate file access
- ❌ **Not persistent** - Files lost on container restart (unless using volumes)
- ❌ **Single instance** - No sharing between instances

#### Cloud Mode (`cloud`)
- ✅ **Persistent storage** - Files survive container restarts
- ✅ **Scalable** - Shared storage across multiple instances
- ✅ **Reliable** - Cloud-grade durability and backup
- ✅ **Production ready** - Handles high availability scenarios
- ❌ **Network latency** - Slower than local access
- ❌ **Authentication required** - Needs Google Cloud setup

---

## Quick Start

### For Local Development
```bash
# Start with local storage and auto-reload
python start_server.py --storage local --reload
```

### For Cloud Testing
```bash
# Test cloud storage locally (requires authentication)
GOOGLE_CLOUD_PROJECT=your-project-id python start_server.py --storage cloud
```

### For Production Deployment
```bash
# Deploy to Cloud Run (automatically uses cloud storage)
./deploy.sh your-project-id
```

### Using Docker Compose
```bash
# Local storage (default)
STORAGE_MODE=local docker compose up

# Cloud storage
STORAGE_MODE=cloud GOOGLE_CLOUD_PROJECT=your-project-id docker compose up
```

---

## Configuration Methods

### 1. Startup Script (Recommended)

The `start_server.py` script provides the easiest configuration method:

```bash
# Local development with auto-reload
python start_server.py --storage local --reload

# Cloud storage testing
python start_server.py --storage cloud

# Auto-detection (default)
python start_server.py --storage auto

# Custom port and host
python start_server.py --storage local --host 0.0.0.0 --port 8005 --reload
```

**Options:**
- `--storage {local,cloud,auto}` - Storage mode
- `--host HOST` - Host to bind to (default: 0.0.0.0)
- `--port PORT` - Port to bind to (default: 8004)
- `--reload` - Enable auto-reload for development
- `--log-level {debug,info,warning,error}` - Set log level
- `--workers N` - Number of worker processes

### 2. Environment Variables

```bash
# Set environment variable
export STORAGE_MODE=local
uvicorn app:app --host 0.0.0.0 --port 8004

# Inline usage
STORAGE_MODE=local uvicorn app:app --reload

# Multiple variables
STORAGE_MODE=cloud GOOGLE_CLOUD_PROJECT=my-project uvicorn app:app
```

### 3. Docker Compose

The `docker-compose.yml` supports storage mode configuration:

```yaml
# Default configuration uses local storage
services:
  doc-server:
    environment:
      - STORAGE_MODE=${STORAGE_MODE:-local}
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
```

Usage:
```bash
# Local storage (default)
docker compose up

# Cloud storage
STORAGE_MODE=cloud GOOGLE_CLOUD_PROJECT=your-project docker compose up
```

### 4. Docker Run

```bash
# Local storage
docker run -p 8004:8004 -e STORAGE_MODE=local document-processing-server

# Cloud storage
docker run -p 8004:8004 \
  -e STORAGE_MODE=cloud \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  document-processing-server

# With persistent volumes (local mode)
docker run -p 8004:8004 \
  -e STORAGE_MODE=local \
  -v $(pwd)/uploaded_files:/app/uploaded_files \
  -v $(pwd)/parsed_files:/app/parsed_files \
  -v $(pwd)/edited_files:/app/edited_files \
  -v $(pwd)/summarized_files:/app/summarized_files \
  -v $(pwd)/bm25_indexes:/app/bm25_indexes \
  document-processing-server
```

---

## Environment Detection

The system automatically detects the appropriate storage mode using this priority order:

1. **`STORAGE_MODE`** environment variable (highest priority)
2. **Legacy variables**: `FORCE_LOCAL_STORAGE`, `FORCE_CLOUD_STORAGE`
3. **Cloud Run detection**: `K_SERVICE` environment variable (set by Cloud Run)
4. **Explicit cloud config**: `USE_CLOUD_STORAGE=true`
5. **Google Cloud project**: `GOOGLE_CLOUD_PROJECT` or `GCP_PROJECT` variables
6. **Default**: Local storage

### Environment Variables Reference

| Variable | Values | Description |
|----------|--------|-------------|
| `STORAGE_MODE` | `local`, `cloud`, `auto` | Explicit storage mode control |
| `GOOGLE_CLOUD_PROJECT` | Project ID | Required for cloud storage |
| `K_SERVICE` | Service name | Auto-set by Cloud Run |
| `USE_CLOUD_STORAGE` | `true`, `false` | Legacy: Enable cloud storage |
| `FORCE_LOCAL_STORAGE` | `true`, `false` | Legacy: Force local storage |
| `FORCE_CLOUD_STORAGE` | `true`, `false` | Legacy: Force cloud storage |

### Detection Examples

```bash
# Local storage - no cloud config
python start_server.py
# Output: Using local filesystem for file operations

# Cloud storage - project ID set
GOOGLE_CLOUD_PROJECT=my-project python start_server.py
# Output: Using Cloud Storage for file operations

# Explicit override
STORAGE_MODE=local GOOGLE_CLOUD_PROJECT=my-project python start_server.py
# Output: Using local filesystem for file operations (override wins)
```

---

## Local Development

### Directory Structure

When using local storage, the following directories are created automatically:

```
server/
├── uploaded_files/     # User uploaded files
├── parsed_files/       # LlamaParse processed files (.md)
├── edited_files/       # User edited content (.md)
├── summarized_files/   # AI generated summaries
└── bm25_indexes/       # BM25 search indexes (.json)
```

### Development Commands

```bash
# Standard local development
python start_server.py --storage local --reload

# Debug mode with verbose logging
python start_server.py --storage local --reload --log-level debug

# Custom port for multiple instances
python start_server.py --storage local --port 8005

# Using uvicorn directly
STORAGE_MODE=local uvicorn app:app --reload --host 0.0.0.0 --port 8004
```

### File Operations in Local Mode

All file operations work on the local filesystem:

```python
# Files are saved to ./uploaded_files/document.pdf
file_manager.save_binary_file("uploaded_files", "document.pdf", content)

# Files are loaded from ./parsed_files/document.md
content = file_manager.load_file("parsed_files", "document.md")

# Directory listing from ./uploaded_files/
files = file_manager.list_files("uploaded_files")
```

---

## Cloud Storage Integration

### Bucket Mapping

Local directories automatically map to Google Cloud Storage buckets:

| Local Directory | Cloud Storage Bucket | Purpose |
|----------------|---------------------|---------|
| `uploaded_files/` | `{project-id}-uploaded-files` | User uploaded documents |
| `parsed_files/` | `{project-id}-parsed-files` | LlamaParse processed files |
| `edited_files/` | `{project-id}-edited-files` | User edited content |
| `summarized_files/` | `{project-id}-summarized-files` | AI generated summaries |
| `bm25_indexes/` | `{project-id}-bm25-indexes` | Search indexes |

### Automatic Features

#### Bucket Creation
Buckets are automatically created during deployment:
```bash
# Created automatically by deploy script
gs://your-project-id-uploaded-files
gs://your-project-id-parsed-files
gs://your-project-id-edited-files
gs://your-project-id-summarized-files
gs://your-project-id-bm25-indexes
```

#### Environment Detection
Cloud storage is automatically enabled when:
- Running in Cloud Run (`K_SERVICE` environment variable detected)
- `GOOGLE_CLOUD_PROJECT` environment variable is set
- `STORAGE_MODE=cloud` is explicitly set

#### Seamless API
The same API works for both local and cloud storage:
```python
# This code works in both modes
file_manager = get_file_manager()
file_manager.save_file("uploaded_files", "doc.txt", "content")
content = file_manager.load_file("uploaded_files", "doc.txt")
```

### Authentication for Cloud Storage

#### In Cloud Run (Automatic)
- Cloud Run automatically provides credentials
- No additional setup required

#### Local Development
```bash
# Method 1: gcloud authentication
gcloud auth login
gcloud auth application-default login

# Method 2: Service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Method 3: gcloud config
gcloud config set project your-project-id
```

---

## BM25 Index Storage

The server includes a hybrid search system that uses BM25 indexes for text retrieval. These indexes are automatically managed using the same storage system.

### How BM25 Indexes Work

1. **Document Ingestion**: When you upload and parse documents, BM25 indexes are created
2. **Storage**: Indexes are saved as `.json` files in the `bm25_indexes` directory
3. **Retrieval**: During hybrid search, all indexes are loaded and merged for comprehensive search

### BM25 Index Lifecycle

#### Creation (via `/ingestdocuments/{filename}`)
```python
# Creates BM25 index for processed document
POST /ingestdocuments/Sample1.pdf

# Results in:
# - Pinecone vector embedding created
# - BM25 index saved as: bm25_indexes/Sample1.json
```

#### Storage Location
- **Local Mode**: `./bm25_indexes/Sample1.json`
- **Cloud Mode**: `gs://your-project-id-bm25-indexes/Sample1.json`

#### Loading and Merging
The hybrid search system automatically:
1. Lists all `.json` files in `bm25_indexes/`
2. Loads each BM25 index
3. Merges them into a single encoder for comprehensive search
4. Uses the merged encoder for hybrid search queries

### BM25 Index Benefits

#### Local Mode
- ✅ **Fast Loading** - Direct file system access
- ✅ **Easy Debugging** - Index files visible locally
- ✅ **Development Friendly** - Quick iteration

#### Cloud Mode  
- ✅ **Persistent Indexes** - Survive container restarts
- ✅ **Shared Search** - Multiple instances share same indexes
- ✅ **Scalable** - Supports large-scale document collections
- ✅ **Production Ready** - Cloud-grade storage reliability

### BM25 Index Management

#### Viewing Indexes
```bash
# Local mode
ls bm25_indexes/

# Cloud mode
gsutil ls gs://your-project-id-bm25-indexes/
```

#### Manual Cleanup
```bash
# Local mode
rm bm25_indexes/unwanted_index.json

# Cloud mode
gsutil rm gs://your-project-id-bm25-indexes/unwanted_index.json
```

### Troubleshooting BM25 Issues

#### No Search Results
1. Check if BM25 indexes exist:
   ```bash
   # Via API
   GET /listfiles/bm25_indexes
   
   # Expected: List of .json files
   ```

2. Verify document ingestion:
   ```bash
   # Ingest documents to create indexes
   POST /ingestdocuments/Sample1.pdf
   ```

#### Index Loading Errors
- Check application logs for BM25 encoder messages
- Verify file permissions (local mode)
- Confirm cloud storage authentication (cloud mode)

---

## Deployment

### Cloud Run Deployment (Recommended)

Use the automated deployment script:

```bash
# Basic deployment (uses auto-detection)
./deploy.sh your-project-id

# Deploy to different region
./deploy.sh your-project-id --region us-west1

# Deploy with Secret Manager
./deploy.sh your-project-id --use-secrets
```

**What the deployment script does:**
1. ✅ Validates prerequisites (gcloud, Docker)
2. ✅ Enables required APIs (Cloud Run, Storage, Artifact Registry)
3. ✅ Creates Cloud Storage buckets automatically
4. ✅ Builds and pushes Docker image
5. ✅ Deploys to Cloud Run with correct environment variables
6. ✅ Tests the deployment

### Manual Cloud Run Deployment

```bash
# 1. Enable APIs
gcloud services enable run.googleapis.com storage.googleapis.com

# 2. Create buckets
gsutil mb -l us-central1 gs://your-project-id-uploaded-files
gsutil mb -l us-central1 gs://your-project-id-parsed-files
gsutil mb -l us-central1 gs://your-project-id-edited-files
gsutil mb -l us-central1 gs://your-project-id-summarized-files
gsutil mb -l us-central1 gs://your-project-id-bm25-indexes

# 3. Build and push image
docker build --platform linux/amd64 -t gcr.io/your-project-id/doc-server .
docker push gcr.io/your-project-id/doc-server

# 4. Deploy to Cloud Run
gcloud run deploy document-processing-service \
  --image gcr.io/your-project-id/doc-server \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-project-id \
  --allow-unauthenticated
```

### Kubernetes/GKE Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: document-processing
spec:
  template:
    spec:
      containers:
      - name: doc-server
        image: your-image
        env:
        - name: STORAGE_MODE
          value: "cloud"
        - name: GOOGLE_CLOUD_PROJECT
          value: "your-project-id"
        ports:
        - containerPort: 8004
```

---

## Testing and Validation

### Test Storage Modes

Use the provided test script:
```bash
# Test all storage modes
python test_storage_modes.py

# Output example:
# ✅ LOCAL Mode: FileManager initialized successfully
# ✅ AUTO Mode: FileManager initialized successfully  
# ✅ CLOUD Mode: Authentication may be required for actual use
```

### Test Individual Modes

```bash
# Test local mode
STORAGE_MODE=local python -c "
from file_util_enhanced import get_file_manager
fm = get_file_manager()
print(f'Using cloud storage: {fm.use_cloud_storage}')
"

# Test cloud mode (requires authentication)
STORAGE_MODE=cloud GOOGLE_CLOUD_PROJECT=your-project python -c "
from file_util_enhanced import get_file_manager
fm = get_file_manager()
print(f'Project ID: {fm.storage_manager.project_id}')
"
```

### Test Cloud Storage Integration

Use the comprehensive test script:
```bash
# Test deployed service (includes automatic cleanup)
python test_cloud_storage.py

# Test without cleaning up test files
python test_cloud_storage.py --no-cleanup

# Only run cleanup (useful for manual cleanup)
python test_cloud_storage.py --cleanup-only

# Expected output:
# ✅ File upload to Cloud Storage
# ✅ File listing from Cloud Storage
# ✅ File parsing with Cloud Storage
# ✅ Content saving to Cloud Storage
# 🧹 Cleaning up test files...
# ✅ All tests passed!
```

### Verify Cloud Storage Buckets

```bash
# List all buckets
gsutil ls

# Check specific bucket contents
gsutil ls gs://your-project-id-uploaded-files/
gsutil ls gs://your-project-id-edited-files/

# Download a file for inspection
gsutil cp gs://your-project-id-uploaded-files/document.pdf ./
```

---

## Troubleshooting

### Common Issues

#### 1. Cloud Storage Authentication Failed
**Symptoms:**
- Error: "Your default credentials were not found"
- 403 Forbidden errors

**Solutions:**
```bash
# Check authentication
gcloud auth list

# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Verify project
gcloud config get-value project
```

#### 2. Bucket Creation Failed
**Symptoms:**
- Error: "The bucket you tried to create already exists"
- Permission denied creating buckets

**Solutions:**
```bash
# Check if buckets exist
gsutil ls gs://your-project-id-uploaded-files

# Check permissions
gcloud projects get-iam-policy your-project-id

# Try different project ID or clean up existing buckets
```

#### 3. Files Not Persisting in Cloud Run
**Symptoms:**
- Files disappear after container restart
- Empty directories in local mode

**Solutions:**
- Verify `GOOGLE_CLOUD_PROJECT` is set in deployment
- Check application logs for storage mode confirmation
- Ensure cloud storage is actually being used:
  ```bash
  # Check logs for storage mode
  gcloud run logs read document-processing-service --region=us-central1
  ```

#### 4. Local Directories Not Created
**Symptoms:**
- File not found errors in local mode
- Permission denied creating directories

**Solutions:**
```bash
# Create directories manually
mkdir -p uploaded_files parsed_files edited_files summarized_files bm25_indexes

# Check permissions
ls -la

# Use startup script (handles directory creation)
python start_server.py --storage local
```

#### 5. Docker Volume Issues
**Symptoms:**
- Files not visible between host and container
- Permission errors in Docker

**Solutions:**
```bash
# Ensure correct volume mounts
docker run -v $(pwd)/uploaded_files:/app/uploaded_files ...

# Check container directories
docker exec -it container-name ls -la /app/

# Use absolute paths
docker run -v /full/path/to/uploaded_files:/app/uploaded_files ...
```

#### 6. BM25 Index Issues
**Symptoms:**
- Hybrid search returns no results
- "No BM25 index files found" warnings

**Solutions:**
```bash
# Check if BM25 indexes exist
GET /listfiles/bm25_indexes

# Create indexes by ingesting documents
POST /ingestdocuments/Sample1.pdf

# Verify indexes were created
GET /listfiles/bm25_indexes
# Should show: ["Sample1.json"]
```

### Monitoring Storage Mode

Check application logs to confirm which storage mode is active:

**Local Mode:**
```
🔧 Storage mode explicitly set to LOCAL
✅ Using local filesystem for file operations
Loading BM25 indexes from directory: bm25_indexes
Found 2 BM25 index files: ['Sample1.json', 'document.json']
```

**Cloud Mode:**
```
🔧 Storage mode explicitly set to CLOUD
✅ Using Cloud Storage for file operations
✅ Ensuring buckets exist for project: your-project-id
Loading BM25 indexes from directory: bm25_indexes
Found 2 BM25 index files: ['Sample1.json', 'document.json']
```

**Auto-Detection:**
```
🔧 Storage mode: AUTO-DETECT
Environment detection: K_SERVICE=None, USE_CLOUD_STORAGE=, GCP_PROJECT=your-project
✅ Using Cloud Storage for file operations
BM25 encoder created successfully with merged indexes
```

---

## Reference

### API Endpoints
All endpoints work the same regardless of storage mode:

- `POST /uploadfile/` - Upload a document
- `GET /listfiles/{directory}` - List files in directory
- `DELETE /deletefile/{directory}/{filename}` - Delete a specific file
- `GET /parsefile/{filename}` - Parse uploaded file
- `POST /savecontent/{filename}` - Save edited content
- `GET /summarizecontent/{filename}` - Summarize content
- `POST /ingestdocuments/{filename}` - Create Pinecone and BM25 indexes
- `POST /hybridsearch/` - Perform hybrid search using Pinecone + BM25

### File Operations
The `FileManager` class provides unified file operations:

```python
from file_util_enhanced import get_file_manager

fm = get_file_manager()

# Save text file
fm.save_file("uploaded_files", "doc.txt", "content")

# Save binary file  
fm.save_binary_file("uploaded_files", "doc.pdf", binary_content)

# Load text file
content = fm.load_file("parsed_files", "doc.md")

# Load binary file
binary_data = fm.load_binary_file("uploaded_files", "doc.pdf")

# List files
files = fm.list_files("uploaded_files")

# Check if file exists
exists = fm.file_exists("edited_files", "doc.md")

# Delete file
deleted = fm.delete_file("uploaded_files", "doc.pdf")

# Get local file path (downloads to temp if cloud storage)
path = fm.get_file_path("uploaded_files", "doc.pdf")
```

### Command Reference

| Scenario | Command |
|----------|---------|
| Local development | `python start_server.py --storage local --reload` |
| Cloud testing | `GOOGLE_CLOUD_PROJECT=xxx python start_server.py --storage cloud` |
| Production deployment | `./deploy.sh your-project-id` |
| Docker local | `STORAGE_MODE=local docker compose up` |
| Test all modes | `python test_storage_modes.py` |
| Test cloud integration | `python test_cloud_storage.py` |

### Files Overview

| File | Purpose |
|------|---------|
| `start_server.py` | Smart server startup with storage configuration |
| `file_util_enhanced.py` | Unified file manager with auto-detection |
| `cloud_storage_util.py` | Google Cloud Storage operations |
| `app.py` | Main FastAPI application (uses FileManager) |
| `hybrid_search.py` | Hybrid search with BM25 + Pinecone (uses FileManager) |
| `ingest_docs.py` | Document ingestion and BM25 index creation (uses FileManager) |
| `docker-compose.yml` | Local development with Docker |
| `deploy.sh` | Automated Cloud Run deployment |
| `test_storage_modes.py` | Test storage mode switching |
| `test_cloud_storage.py` | Test cloud storage integration (with cleanup) |
| `test_delete_endpoint.py` | Test file deletion functionality |

---

## Summary

The Document Processing Server provides flexible storage configuration suitable for both development and production environments:

- **🔧 Simple Configuration**: Multiple ways to control storage mode
- **🔍 Smart Detection**: Automatic environment-based selection  
- **📝 Clear Logging**: Always know which storage mode is active
- **🔄 Seamless Switching**: Same code works with local or cloud storage
- **🔍 Hybrid Search**: BM25 indexes work with both storage modes
- **📚 Comprehensive Testing**: Validate all configurations work correctly

**Perfect for development teams** who need local storage for fast development iteration and cloud storage for production reliability, with easy switching between modes. 