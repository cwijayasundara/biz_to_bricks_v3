#!/bin/bash

# Script to clean up obsolete cloud storage buckets
# This removes the edited_files and summarized_files buckets that are no longer needed

set -e

# Get project ID
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT environment variable or gcloud default project must be set"
    exit 1
fi

echo "🧹 Cleaning up obsolete cloud storage buckets for project: $PROJECT_ID"
echo "========================================================================="

# Define bucket names to remove
BUCKETS_TO_REMOVE=(
    "${PROJECT_ID}-edited-files"
    "${PROJECT_ID}-summarized-files"
)

# Function to safely delete a bucket
delete_bucket() {
    local bucket_name=$1
    
    echo "🔍 Checking bucket: $bucket_name"
    
    # Check if bucket exists
    if gsutil ls -b gs://$bucket_name >/dev/null 2>&1; then
        echo "📦 Found bucket: $bucket_name"
        
        # List objects in bucket
        object_count=$(gsutil ls gs://$bucket_name/** 2>/dev/null | wc -l || echo "0")
        
        if [ "$object_count" -gt 0 ]; then
            echo "⚠️  Bucket contains $object_count objects. Removing all objects..."
            gsutil -m rm -r gs://$bucket_name/**
        else
            echo "✅ Bucket is already empty"
        fi
        
        echo "🗑️  Deleting bucket: $bucket_name"
        gsutil rb gs://$bucket_name
        echo "✅ Successfully deleted bucket: $bucket_name"
    else
        echo "ℹ️  Bucket $bucket_name does not exist (already cleaned up)"
    fi
    
    echo ""
}

# Delete each bucket
for bucket in "${BUCKETS_TO_REMOVE[@]}"; do
    delete_bucket "$bucket"
done

echo "🎉 Cleanup completed!"
echo ""
echo "Summary of changes:"
echo "- Removed edited_files bucket (files are no longer stored to disk)"
echo "- Removed summarized_files bucket (summaries are generated fresh each time)"
echo "- Updated application code to not use these directories"
echo ""
echo "Active buckets remaining:"
echo "- ${PROJECT_ID}-uploaded-files"
echo "- ${PROJECT_ID}-parsed-files"
echo "- ${PROJECT_ID}-bm25-indexes"
echo "- ${PROJECT_ID}-generated-questions"
