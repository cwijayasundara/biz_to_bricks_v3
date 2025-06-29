"""
Google Cloud Storage utility for persistent file storage in Cloud Run.
This replaces local filesystem storage with cloud storage buckets.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional
from google.cloud import storage
from google.cloud.exceptions import NotFound
import logging

logger = logging.getLogger(__name__)


class CloudStorageManager:
    """Manages file operations using Google Cloud Storage buckets."""
    
    def __init__(self, project_id: str, bucket_prefix: str = None):
        """
        Initialize Cloud Storage manager.
        
        Args:
            project_id: Google Cloud Project ID
            bucket_prefix: Prefix for bucket names (defaults to project_id)
        """
        self.project_id = project_id
        self.bucket_prefix = bucket_prefix or project_id
        self.client = storage.Client(project=project_id)
        
        # Define bucket names for each directory
        self.buckets = {
            'uploaded_files': f"{self.bucket_prefix}-uploaded-files",
            'parsed_files': f"{self.bucket_prefix}-parsed-files", 
            'bm25_indexes': f"{self.bucket_prefix}-bm25-indexes",
            'generated_questions': f"{self.bucket_prefix}-generated-questions"
        }
        
        # Initialize buckets
        self._ensure_buckets_exist()
    
    def _ensure_buckets_exist(self):
        """Create buckets if they don't exist."""
        logger.info(f"Ensuring buckets exist for project: {self.project_id}")
        for bucket_type, bucket_name in self.buckets.items():
            try:
                bucket = self.client.get_bucket(bucket_name)
                logger.info(f"Bucket {bucket_name} already exists")
            except NotFound:
                logger.info(f"Creating bucket {bucket_name}")
                try:
                    bucket = self.client.create_bucket(bucket_name, location="US")
                    logger.info(f"Bucket {bucket_name} created successfully")
                except Exception as e:
                    logger.error(f"Failed to create bucket {bucket_name}: {e}")
                    raise
            except Exception as e:
                logger.error(f"Error checking bucket {bucket_name}: {e}")
                raise
    
    def upload_file(self, directory: str, filename: str, file_content: bytes) -> str:
        """
        Upload file content to the appropriate bucket.
        
        Args:
            directory: Directory type (uploaded_files, parsed_files, etc.)
            filename: Name of the file
            file_content: File content as bytes
            
        Returns:
            Cloud Storage URI of the uploaded file
        """
        if directory not in self.buckets:
            raise ValueError(f"Invalid directory: {directory}")
        
        bucket_name = self.buckets[directory]
        logger.info(f"Uploading {filename} to bucket {bucket_name} (size: {len(file_content)} bytes)")
        
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        blob.upload_from_string(file_content)
        
        uri = f"gs://{bucket_name}/{filename}"
        logger.info(f"File uploaded successfully to {uri}")
        return uri
    
    def download_file(self, directory: str, filename: str) -> bytes:
        """
        Download file content from the appropriate bucket.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            File content as bytes
        """
        if directory not in self.buckets:
            raise ValueError(f"Invalid directory: {directory}")
        
        bucket_name = self.buckets[directory]
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        if not blob.exists():
            raise FileNotFoundError(f"File {filename} not found in {directory}")
        
        return blob.download_as_bytes()
    
    def download_file_to_temp(self, directory: str, filename: str) -> str:
        """
        Download file to a temporary local file and return the path.
        Useful for libraries that need file paths.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            Path to the temporary file
        """
        content = self.download_file(directory, filename)
        
        # Create temporary file with same extension
        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.close()
        
        return temp_file.name
    
    def save_file(self, directory: str, filename: str, content: str) -> str:
        """
        Save text content to a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            content: Text content to save
            
        Returns:
            Cloud Storage URI of the saved file
        """
        return self.upload_file(directory, filename, content.encode('utf-8'))
    
    def load_file(self, directory: str, filename: str) -> str:
        """
        Load text content from a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            Text content of the file
        """
        content = self.download_file(directory, filename)
        return content.decode('utf-8')
    
    def list_files(self, directory: str) -> List[str]:
        """
        List all files in a directory.
        
        Args:
            directory: Directory type
            
        Returns:
            List of filenames
        """
        if directory not in self.buckets:
            raise ValueError(f"Invalid directory: {directory}")
        
        bucket_name = self.buckets[directory]
        bucket = self.client.bucket(bucket_name)
        
        blobs = bucket.list_blobs()
        return [blob.name for blob in blobs]
    
    def file_exists(self, directory: str, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            True if file exists, False otherwise
        """
        if directory not in self.buckets:
            return False
        
        bucket_name = self.buckets[directory]
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        return blob.exists()
    
    def delete_file(self, directory: str, filename: str) -> bool:
        """
        Delete a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            True if file was deleted, False if it didn't exist
        """
        if directory not in self.buckets:
            return False
        
        bucket_name = self.buckets[directory]
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        if blob.exists():
            blob.delete()
            logger.info(f"File {filename} deleted from {directory}")
            return True
        return False
    
    def get_file_url(self, directory: str, filename: str, expiration_minutes: int = 60) -> str:
        """
        Generate a signed URL for file access.
        
        Args:
            directory: Directory type
            filename: Name of the file
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Signed URL for file access
        """
        if directory not in self.buckets:
            raise ValueError(f"Invalid directory: {directory}")
        
        bucket_name = self.buckets[directory]
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        from datetime import timedelta
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET"
        )
        
        return url


# Environment-based factory function
def get_storage_manager() -> CloudStorageManager:
    """
    Get storage manager instance based on environment.
    """
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT or GCP_PROJECT environment variable must be set")
    
    return CloudStorageManager(project_id) 