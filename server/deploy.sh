#!/bin/bash

# Simple deployment script for Document Processing Server to Google Cloud Run
# Usage: ./deploy.sh [project-id] [region]

set -e  # Exit on any error

# Default values
PROJECT_ID=${1:-"ibm-keras"}
REGION=${2:-"us-central1"}

echo "🚀 Starting deployment to Google Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if we're in the right directory
if [ ! -f "Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found. Please run this script from the server directory."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please create it with your API keys."
    echo "Required keys: OPENAI_API_KEY, LLAMA_CLOUD_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT"
    exit 1
fi

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install it first."
    exit 1
fi

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not authenticated with gcloud. Please run 'gcloud auth login'"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Set project
echo "🔧 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Configure Docker auth
echo "🔧 Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Create Artifact Registry repository
echo "🔧 Creating Artifact Registry repository..."
gcloud artifacts repositories create document-processing \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for document processing service" \
    --quiet || echo "Repository already exists"

# Create Cloud Storage buckets
echo "🔧 Creating Cloud Storage buckets..."
for bucket in uploaded-files parsed-files summarized-files bm25-indexes; do
    gsutil mb -l $REGION gs://${PROJECT_ID}-${bucket} 2>/dev/null || echo "Bucket ${PROJECT_ID}-${bucket} already exists"
done

# Build and push Docker image
echo "🔧 Building Docker image..."
docker build --platform linux/amd64 \
    -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/document-processing/document-processing-server:latest .

echo "🔧 Pushing image to Artifact Registry..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/document-processing/document-processing-server:latest

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."

# Load environment variables
source .env

# Deploy with environment variables
gcloud run deploy document-processing-service \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/document-processing/document-processing-server:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8004 \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY},LLAMA_CLOUD_API_KEY=${LLAMA_CLOUD_API_KEY},PINECONE_API_KEY=${PINECONE_API_KEY},PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT},GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

# Get service URL
echo "🔍 Getting service URL..."
SERVICE_URL=$(gcloud run services describe document-processing-service \
    --region $REGION \
    --format="value(status.url)")

echo ""
echo "🎉 Deployment completed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📖 API Docs: $SERVICE_URL/docs"
echo ""
echo "You can now use the service at: $SERVICE_URL" 