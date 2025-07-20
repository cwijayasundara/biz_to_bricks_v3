"""
Enhanced file utility that supports both local filesystem and Cloud Storage.
This provides a seamless transition between local development and cloud deployment.
"""

import os
import logging
import tempfile
from pathlib import Path as FilePath
from typing import Optional, List, Tuple
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document

# Try to import cloud storage, fallback to None if not available
try:
    from cloud_storage_util import get_storage_manager, CloudStorageManager
    CLOUD_STORAGE_AVAILABLE = True
except ImportError:
    CLOUD_STORAGE_AVAILABLE = False
    get_storage_manager = None
    CloudStorageManager = None

logger = logging.getLogger(__name__)

# Directory constants
UPLOADED_FILES_DIR = "uploaded_files"
PARSED_FILES_DIR = "parsed_files"
BM25_INDEXES_DIR = "bm25_indexes"


class FileManager:
    """
    Unified file manager that works with both local filesystem and Cloud Storage.
    Automatically detects the environment and uses the appropriate storage backend.
    """
    
    def __init__(self, use_cloud_storage: Optional[bool] = None, storage_mode: Optional[str] = None):
        """
        Initialize file manager.
        
        Args:
            use_cloud_storage: Force cloud storage usage. If None, auto-detect based on environment.
            storage_mode: Explicit storage mode ('local', 'cloud', 'auto'). Overrides use_cloud_storage.
        """
        # Handle explicit storage mode setting
        if storage_mode:
            storage_mode = storage_mode.lower()
            if storage_mode == 'local':
                self.use_cloud_storage = False
                logger.info("🔧 Storage mode explicitly set to LOCAL")
            elif storage_mode == 'cloud':
                self.use_cloud_storage = True
                logger.info("🔧 Storage mode explicitly set to CLOUD")
            elif storage_mode == 'auto':
                self.use_cloud_storage = self._should_use_cloud_storage()
                logger.info("🔧 Storage mode set to AUTO-DETECT")
            else:
                raise ValueError(f"Invalid storage_mode: {storage_mode}. Must be 'local', 'cloud', or 'auto'")
        elif use_cloud_storage is not None:
            # Legacy parameter for backward compatibility
            self.use_cloud_storage = use_cloud_storage
            mode_str = "CLOUD" if use_cloud_storage else "LOCAL"
            logger.info(f"🔧 Storage mode set via legacy parameter: {mode_str}")
        else:
            # Auto-detect based on environment
            self.use_cloud_storage = self._should_use_cloud_storage()
            logger.info("🔧 Storage mode: AUTO-DETECT")
        
        self.storage_manager = None
        if self.use_cloud_storage:
            if not CLOUD_STORAGE_AVAILABLE:
                raise ImportError("Cloud storage dependencies not available")
            self.storage_manager = get_storage_manager()
            logger.info("✅ Using Cloud Storage for file operations")
        else:
            self._ensure_local_directories()
            logger.info("✅ Using local filesystem for file operations")
    
    def _should_use_cloud_storage(self) -> bool:
        """Determine if cloud storage should be used based on environment."""
        k_service = os.getenv('K_SERVICE')
        use_cloud_storage = os.getenv('USE_CLOUD_STORAGE', '').lower()
        gcp_project = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
        
        logger.info(f"Environment detection: K_SERVICE={k_service}, USE_CLOUD_STORAGE={use_cloud_storage}, GCP_PROJECT={gcp_project}, CLOUD_STORAGE_AVAILABLE={CLOUD_STORAGE_AVAILABLE}")
        
        # Check for Cloud Run environment
        if k_service:  # Cloud Run sets this environment variable
            logger.info("Cloud Run environment detected, using cloud storage")
            return True
        
        # Check for explicit cloud storage configuration
        if use_cloud_storage in ('true', '1', 'yes'):
            logger.info("Explicit cloud storage configuration detected")
            return True
        
        # Check if Google Cloud project is configured
        if gcp_project:
            logger.info(f"Google Cloud project configured: {gcp_project}, cloud storage available: {CLOUD_STORAGE_AVAILABLE}")
            return CLOUD_STORAGE_AVAILABLE
        
        logger.info("Using local filesystem storage")
        return False
    
    def _ensure_local_directories(self):
        """Create local directories if they don't exist."""
        directories = [
            UPLOADED_FILES_DIR,
            PARSED_FILES_DIR,
            BM25_INDEXES_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created local directory: {directory}")
    
    def save_file(self, directory: str, filename: str, content: str) -> str:
        """
        Save text content to a file.
        
        Args:
            directory: Directory type (uploaded_files, parsed_files, etc.)
            filename: Name of the file
            content: Text content to save
            
        Returns:
            File path or Cloud Storage URI
        """
        if self.use_cloud_storage:
            return self.storage_manager.save_file(directory, filename, content)
        else:
            file_path = os.path.join(directory, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"File saved locally: {file_path}")
            return file_path
    
    def save_binary_file(self, directory: str, filename: str, content: bytes) -> str:
        """
        Save binary content to a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            content: Binary content to save
            
        Returns:
            File path or Cloud Storage URI
        """
        if self.use_cloud_storage:
            return self.storage_manager.upload_file(directory, filename, content)
        else:
            file_path = os.path.join(directory, filename)
            with open(file_path, 'wb') as f:
                f.write(content)
            logger.info(f"Binary file saved locally: {file_path}")
            return file_path
    
    def load_file(self, directory: str, filename: str) -> str:
        """
        Load text content from a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            Text content of the file
        """
        if self.use_cloud_storage:
            return self.storage_manager.load_file(directory, filename)
        else:
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    def load_binary_file(self, directory: str, filename: str) -> bytes:
        """
        Load binary content from a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            Binary content of the file
        """
        if self.use_cloud_storage:
            return self.storage_manager.download_file(directory, filename)
        else:
            file_path = os.path.join(directory, filename)
            with open(file_path, 'rb') as f:
                return f.read()
    
    def get_file_path(self, directory: str, filename: str) -> str:
        """
        Get a file path for reading. For cloud storage, downloads to temp file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            Local file path (may be temporary for cloud storage)
        """
        if self.use_cloud_storage:
            return self.storage_manager.download_file_to_temp(directory, filename)
        else:
            return os.path.join(directory, filename)
    
    def list_files(self, directory: str) -> List[str]:
        """
        List all files in a directory.
        
        Args:
            directory: Directory type
            
        Returns:
            List of filenames
        """
        if self.use_cloud_storage:
            return self.storage_manager.list_files(directory)
        else:
            try:
                if os.path.exists(directory):
                    return os.listdir(directory)
                return []
            except Exception as e:
                logger.error(f"Failed to list files in {directory}: {e}")
                return []
    
    def file_exists(self, directory: str, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            True if file exists, False otherwise
        """
        if self.use_cloud_storage:
            return self.storage_manager.file_exists(directory, filename)
        else:
            file_path = os.path.join(directory, filename)
            return os.path.exists(file_path)
    
    def delete_file(self, directory: str, filename: str) -> bool:
        """
        Delete a file.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            True if file was deleted, False if it didn't exist
        """
        if self.use_cloud_storage:
            return self.storage_manager.delete_file(directory, filename)
        else:
            file_path = os.path.join(directory, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                return True
            return False
    
    def load_markdown_file(self, directory: str, filename: str) -> Tuple[str, dict]:
        """
        Load a markdown file and return content and metadata.
        
        Args:
            directory: Directory type
            filename: Name of the file
            
        Returns:
            Tuple of (content, metadata)
        """
        file_path = self.get_file_path(directory, filename)
        
        try:
            loader = UnstructuredMarkdownLoader(file_path)
            documents = loader.load()
            
            if not documents:
                raise ValueError(f"No content found in {filename}")
            
            metadata = documents[0].metadata
            
            # Combine all document content
            text = ""
            for document in documents:
                text += document.page_content
            
            # Clean up temporary file if using cloud storage
            if self.use_cloud_storage and file_path.startswith('/tmp'):
                try:
                    os.unlink(file_path)
                except Exception:
                    pass
            
            return text, metadata
            
        except Exception as e:
            # Clean up temporary file if using cloud storage
            if self.use_cloud_storage and file_path.startswith('/tmp'):
                try:
                    os.unlink(file_path)
                except Exception:
                    pass
            raise e
    
    def load_edited_file_or_parsed_file(self, filename: str) -> Tuple[str, dict]:
        """
        Load the parsed file (edited content is now stored in parsed_files directory).
        
        Args:
            filename: Base filename (without extension)
            
        Returns:
            Tuple of (content, metadata)
            
        Raises:
            FileNotFoundError: If parsed file doesn't exist
        """
        # Ensure filename has .md extension
        base_name = filename.split(".")[0] if "." in filename else filename
        md_filename = f"{base_name}.md"
        
        # Load from parsed files (where edited content is now stored)
        if self.file_exists(PARSED_FILES_DIR, md_filename):
            logger.info(f"Loading parsed file: {md_filename}")
            return self.load_markdown_file(PARSED_FILES_DIR, md_filename)
        
        # File doesn't exist
        raise FileNotFoundError(
            f"Parsed file does not exist for: {base_name}"
        )


# Global instance
_file_manager = None


def get_storage_mode() -> str:
    """
    Get the storage mode from environment variables or command line.
    
    Returns:
        Storage mode: 'local', 'cloud', or 'auto'
    """
    # Check environment variable first
    storage_mode = os.getenv('STORAGE_MODE', '').lower()
    if storage_mode in ['local', 'cloud', 'auto']:
        return storage_mode
    
    # Check for legacy environment variables
    if os.getenv('FORCE_LOCAL_STORAGE', '').lower() in ('true', '1', 'yes'):
        return 'local'
    if os.getenv('FORCE_CLOUD_STORAGE', '').lower() in ('true', '1', 'yes'):
        return 'cloud'
    
    # Default to auto-detect
    return 'auto'


def get_file_manager() -> FileManager:
    """Get the global file manager instance."""
    global _file_manager
    if _file_manager is None:
        storage_mode = get_storage_mode()
        _file_manager = FileManager(storage_mode=storage_mode)
    return _file_manager


def reset_file_manager():
    """Reset the global file manager instance (useful for testing)."""
    global _file_manager
    _file_manager = None


# Convenience functions for backward compatibility
def create_directory(directory: str) -> str:
    """Create a directory if it doesn't exist (local only)."""
    file_manager = get_file_manager()
    if not file_manager.use_cloud_storage:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Directory '{directory}' created")
        else:
            logger.info(f"Directory '{directory}' already exists")
    return directory


def list_files(directory: str) -> List[str]:
    """List all files in the given directory."""
    return get_file_manager().list_files(directory)


def read_file(file_path: str) -> str:
    """Read a file and return the content as a string (local only)."""
    with open(file_path, "r", encoding='utf-8') as f:
        return f.read()


def load_markdown_file(file_path: str) -> Tuple[str, dict]:
    """Load a markdown file and return content and metadata (local path only)."""
    loader = UnstructuredMarkdownLoader(file_path)
    documents = loader.load()
    
    if not documents:
        raise ValueError(f"No content found in {file_path}")
    
    metadata = documents[0].metadata
    text = ""
    for document in documents:
        text += document.page_content
    
    return text, metadata


def get_file_path(directory: str, filename: str, extension: Optional[str] = None) -> str:
    """Construct file path with proper handling."""
    base_name = filename.split(".")[0] if "." in filename else filename
    if extension:
        return str(FilePath(directory) / f"{base_name}{extension}")
    return str(FilePath(directory) / filename)


def load_edited_file_or_parsed_file(filename: str) -> Tuple[str, dict]:
    """Load the parsed file (edited content is now stored in parsed_files directory)."""
    return get_file_manager().load_edited_file_or_parsed_file(filename) 