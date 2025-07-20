"""
Integration Tests for File Management Endpoints

This module tests the file management endpoints:
- POST /uploadfile/ - Upload files
- GET /listfiles/{directory} - List files in directory
- DELETE /deletefile/{directory}/{filename} - Delete files
"""

import os
from pathlib import Path
from test.integration_tests.base_test import BaseTest


class TestFileManagement(BaseTest):
    """Test class for file management endpoints."""
    
    def run_all_tests(self):
        """Run all file management tests."""
        print(f"\n📁 Testing File Management Endpoints")
        print("=" * 50)
        
        # Test file upload
        self.run_test("Upload PDF file", self.test_upload_pdf_file)
        self.run_test("Upload Excel file", self.test_upload_excel_file)
        self.run_test("Upload file with invalid filename", self.test_upload_invalid_file)
        
        # Test list files
        self.run_test("List uploaded files", self.test_list_uploaded_files)
        self.run_test("List parsed files", self.test_list_parsed_files)
        self.run_test("List non-existent directory", self.test_list_invalid_directory)
        
        # Test delete files
        self.run_test("Delete uploaded file", self.test_delete_uploaded_file)
        self.run_test("Delete non-existent file", self.test_delete_nonexistent_file)
        self.run_test("Delete file from invalid directory", self.test_delete_invalid_directory)
    
    def test_upload_pdf_file(self):
        """Test uploading a PDF file."""
        # Upload PDF file
        pdf_response = self.upload_test_file("Sample1.pdf")
        if not pdf_response:
            return False
        
        # Verify response structure
        expected_keys = ["filename", "file_path", "file_type", "is_excel_csv", "message"]
        missing_keys = [key for key in expected_keys if key not in pdf_response]
        if missing_keys:
            self.log_test("Upload PDF response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify response content
        if pdf_response.get("filename") != "Sample1.pdf":
            self.log_test("Upload PDF filename", "FAIL", 0, f"Expected 'Sample1.pdf', got '{pdf_response.get('filename')}'")
            return False
        
        if pdf_response.get("file_type") != "document":
            self.log_test("Upload PDF file type", "FAIL", 0, f"Expected 'document', got '{pdf_response.get('file_type')}'")
            return False
        
        if pdf_response.get("is_excel_csv") is not False:
            self.log_test("Upload PDF is_excel_csv", "FAIL", 0, f"Expected False, got '{pdf_response.get('is_excel_csv')}'")
            return False
        
        return True
    
    def test_upload_excel_file(self):
        """Test uploading an Excel file."""
        # Upload Excel file
        excel_response = self.upload_test_file("train.xlsx")
        if not excel_response:
            return False
        
        # Verify response structure
        expected_keys = ["filename", "file_path", "file_type", "is_excel_csv", "message"]
        missing_keys = [key for key in expected_keys if key not in excel_response]
        if missing_keys:
            self.log_test("Upload Excel response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify response content
        if excel_response.get("filename") != "train.xlsx":
            self.log_test("Upload Excel filename", "FAIL", 0, f"Expected 'train.xlsx', got '{excel_response.get('filename')}'")
            return False
        
        if excel_response.get("file_type") not in ["xlsx", "excel"]:
            self.log_test("Upload Excel file type", "FAIL", 0, f"Expected 'xlsx' or 'excel', got '{excel_response.get('file_type')}'")
            return False
        
        if excel_response.get("is_excel_csv") is not True:
            self.log_test("Upload Excel is_excel_csv", "FAIL", 0, f"Expected True, got '{excel_response.get('is_excel_csv')}'")
            return False
        
        return True
    
    def test_upload_invalid_file(self):
        """Test uploading a file with invalid filename."""
        try:
            # Create a temporary file with no extension
            temp_file_path = self.get_test_file_path("temp_file")
            with open(temp_file_path, 'w') as f:
                f.write("test content")
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('', f, 'application/octet-stream')}
                response = self.make_request('POST', '/uploadfile/', files=files)
            
            # Clean up
            os.remove(temp_file_path)
            
            # Should return 400 for invalid filename
            return self.assert_status_code(response, 400, "Upload invalid file")
            
        except Exception as e:
            self.log_test("Upload invalid file", "FAIL", 0, str(e))
            return False
    
    def test_list_uploaded_files(self):
        """Test listing uploaded files."""
        response = self.make_request('GET', '/listfiles/uploaded_files')
        
        if not self.assert_status_code(response, 200, "List uploaded files"):
            return False
        
        # Verify response structure
        data = response.json()
        if "files" not in data:
            self.log_test("List uploaded files structure", "FAIL", 0, "Missing 'files' key in response")
            return False
        
        # Verify that we have at least our test files
        files = data.get("files", [])
        expected_files = ["Sample1.pdf", "train.xlsx"]
        missing_files = [f for f in expected_files if f not in files]
        
        if missing_files:
            self.log_test("List uploaded files content", "FAIL", 0, f"Missing expected files: {missing_files}")
            return False
        
        return True
    
    def test_list_parsed_files(self):
        """Test listing parsed files."""
        response = self.make_request('GET', '/listfiles/parsed_files')
        
        if not self.assert_status_code(response, 200, "List parsed files"):
            return False
        
        # Verify response structure
        data = response.json()
        if "files" not in data:
            self.log_test("List parsed files structure", "FAIL", 0, "Missing 'files' key in response")
            return False
        
        return True
    
    def test_list_invalid_directory(self):
        """Test listing files from invalid directory."""
        response = self.make_request('GET', '/listfiles/invalid_directory')
        
        # Should return 500 for invalid directory
        return self.assert_status_code(response, 500, "List invalid directory")
    
    def test_delete_uploaded_file(self):
        """Test deleting an uploaded file."""
        # First, ensure we have a file to delete by uploading one
        test_file_response = self.upload_test_file("Sample1.pdf")
        if not test_file_response:
            self.skip_test("Delete uploaded file", "No test file available for deletion")
            return True
        
        # Delete the file
        response = self.make_request('DELETE', '/deletefile/uploaded_files/Sample1.pdf')
        
        if not self.assert_status_code(response, 200, "Delete uploaded file"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["status", "message"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Delete file response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify response content
        if data.get("status") != "success":
            self.log_test("Delete file status", "FAIL", 0, f"Expected 'success', got '{data.get('status')}'")
            return False
        
        return True
    
    def test_delete_nonexistent_file(self):
        """Test deleting a non-existent file."""
        response = self.make_request('DELETE', '/deletefile/uploaded_files/nonexistent.pdf')
        
        # Should return 404 for non-existent file
        return self.assert_status_code(response, 404, "Delete non-existent file")
    
    def test_delete_invalid_directory(self):
        """Test deleting file from invalid directory."""
        response = self.make_request('DELETE', '/deletefile/invalid_directory/test.pdf')
        
        # Should return 400 for invalid directory
        return self.assert_status_code(response, 400, "Delete from invalid directory") 