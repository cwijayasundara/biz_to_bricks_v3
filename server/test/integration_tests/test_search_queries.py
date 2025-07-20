"""
Integration Tests for Search & Query Endpoints

This module tests the search and query endpoints:
- POST /hybridsearch/ - Intelligent hybrid search across documents and data
- POST /querypandas/ - Direct Excel/CSV data analysis with AI
- GET /sourcedocuments/ - Get list of available source documents
"""

import json
from test.integration_tests.base_test import BaseTest


class TestSearchQueries(BaseTest):
    """Test class for search and query endpoints."""
    
    def run_all_tests(self):
        """Run all search and query tests."""
        print(f"\n🔍 Testing Search & Query Endpoints")
        print("=" * 50)
        
        # Test source documents
        self.run_test("Get source documents", self.test_get_source_documents)
        
        # Test hybrid search
        self.run_test("Hybrid search with general query", self.test_hybrid_search_general)
        self.run_test("Hybrid search with source filter", self.test_hybrid_search_with_source)
        self.run_test("Hybrid search with debug mode", self.test_hybrid_search_debug)
        self.run_test("Hybrid search with empty query", self.test_hybrid_search_empty)
        
        # Test pandas query
        self.run_test("Pandas query with Excel file", self.test_pandas_query_excel)
        self.run_test("Pandas query with debug mode", self.test_pandas_query_debug)
        self.run_test("Pandas query with no Excel files", self.test_pandas_query_no_files)
    
    def test_get_source_documents(self):
        """Test getting source documents."""
        response = self.make_request('GET', '/sourcedocuments/')
        
        if not self.assert_status_code(response, 200, "Get source documents"):
            return False
        
        # Verify response structure
        data = response.json()
        if "files" not in data:
            self.log_test("Source documents structure", "FAIL", 0, "Missing 'files' key in response")
            return False
        
        # Verify files is a list
        files = data.get("files", [])
        if not isinstance(files, list):
            self.log_test("Source documents files type", "FAIL", 0, f"Expected list, got {type(files)}")
            return False
        
        return True
    
    def test_hybrid_search_general(self):
        """Test hybrid search with a general query."""
        # First ensure we have some processed files
        self._setup_test_files()
        
        # Perform hybrid search
        search_data = {
            "query": "What is the main topic of this document?",
            "source_document": None,
            "debug": False
        }
        
        response = self.make_request('POST', '/hybridsearch/', json=search_data)
        
        if not self.assert_status_code(response, 200, "Hybrid search general"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["query", "source_filter", "document_search", "pandas_agent_search", "summary"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Hybrid search response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify query is preserved
        if data.get("query") != search_data["query"]:
            self.log_test("Hybrid search query preservation", "FAIL", 0, 
                         f"Expected '{search_data['query']}', got '{data.get('query')}'")
            return False
        
        # Verify summary structure
        summary = data.get("summary", {})
        summary_keys = ["total_sources", "search_strategy", "search_successful", 
                       "has_document_results", "has_pandas_results"]
        missing_summary_keys = [key for key in summary_keys if key not in summary]
        if missing_summary_keys:
            self.log_test("Hybrid search summary structure", "FAIL", 0, f"Missing summary keys: {missing_summary_keys}")
            return False
        
        return True
    
    def test_hybrid_search_with_source(self):
        """Test hybrid search with source document filter."""
        # First ensure we have some processed files
        self._setup_test_files()
        
        # Perform hybrid search with source filter
        search_data = {
            "query": "What information is available in this file?",
            "source_document": "Sample1.pdf",
            "debug": False
        }
        
        response = self.make_request('POST', '/hybridsearch/', json=search_data)
        
        if not self.assert_status_code(response, 200, "Hybrid search with source"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["query", "source_filter", "document_search", "pandas_agent_search", "summary"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Hybrid search with source response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify source filter is preserved
        if data.get("source_filter") != search_data["source_document"]:
            self.log_test("Hybrid search source filter", "FAIL", 0, 
                         f"Expected '{search_data['source_document']}', got '{data.get('source_filter')}'")
            return False
        
        return True
    
    def test_hybrid_search_debug(self):
        """Test hybrid search with debug mode enabled."""
        # First ensure we have some processed files
        self._setup_test_files()
        
        # Perform hybrid search with debug
        search_data = {
            "query": "Test query for debug mode",
            "source_document": None,
            "debug": True
        }
        
        response = self.make_request('POST', '/hybridsearch/', json=search_data)
        
        if not self.assert_status_code(response, 200, "Hybrid search debug"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["query", "source_filter", "document_search", "pandas_agent_search", "summary", "debug_info"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Hybrid search debug response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify debug info is present
        debug_info = data.get("debug_info", {})
        if not debug_info:
            self.log_test("Hybrid search debug info", "FAIL", 0, "Debug info should be present when debug=True")
            return False
        
        return True
    
    def test_hybrid_search_empty(self):
        """Test hybrid search with empty query."""
        search_data = {
            "query": "",
            "source_document": None,
            "debug": False
        }
        
        response = self.make_request('POST', '/hybridsearch/', json=search_data)
        
        if not self.assert_status_code(response, 200, "Hybrid search empty"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["query", "source_filter", "document_search", "pandas_agent_search", "summary"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Hybrid search empty response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        return True
    
    def test_pandas_query_excel(self):
        """Test pandas query with Excel file."""
        # First ensure we have an Excel file uploaded
        upload_response = self.upload_test_file("train.xlsx")
        if not upload_response:
            self.skip_test("Pandas query Excel", "Could not upload Excel file")
            return True
        
        # Perform pandas query
        query_data = {
            "query": "What are the column names in this dataset?",
            "source_document": None,
            "debug": False
        }
        
        response = self.make_request('POST', '/querypandas/', json=query_data)
        
        if not self.assert_status_code(response, 200, "Pandas query Excel"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["query", "files_queried", "successful_queries", "results", "errors", "summary"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Pandas query response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify summary structure
        summary = data.get("summary", {})
        summary_keys = ["query_successful", "files_with_results", "files_with_errors"]
        missing_summary_keys = [key for key in summary_keys if key not in summary]
        if missing_summary_keys:
            self.log_test("Pandas query summary structure", "FAIL", 0, f"Missing summary keys: {missing_summary_keys}")
            return False
        
        return True
    
    def test_pandas_query_debug(self):
        """Test pandas query with debug mode enabled."""
        # First ensure we have an Excel file uploaded
        upload_response = self.upload_test_file("train.xlsx")
        if not upload_response:
            self.skip_test("Pandas query debug", "Could not upload Excel file")
            return True
        
        # Perform pandas query with debug
        query_data = {
            "query": "Show me the first few rows of data",
            "source_document": None,
            "debug": True
        }
        
        response = self.make_request('POST', '/querypandas/', json=query_data)
        
        if not self.assert_status_code(response, 200, "Pandas query debug"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["query", "files_queried", "successful_queries", "results", "errors", "summary", "debug_info"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Pandas query debug response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify debug info is present
        debug_info = data.get("debug_info", {})
        if not debug_info:
            self.log_test("Pandas query debug info", "FAIL", 0, "Debug info should be present when debug=True")
            return False
        
        return True
    
    def test_pandas_query_no_files(self):
        """Test pandas query when no Excel files are available."""
        # Delete any existing Excel files first
        list_response = self.make_request('GET', '/listfiles/uploaded_files')
        if list_response.status_code == 200:
            data = list_response.json()
            files = data.get("files", [])
            for file in files:
                if file.endswith(('.xlsx', '.xls', '.csv')):
                    self.make_request('DELETE', f'/deletefile/uploaded_files/{file}')
        
        # Perform pandas query
        query_data = {
            "query": "What are the column names?",
            "source_document": None,
            "debug": False
        }
        
        response = self.make_request('POST', '/querypandas/', json=query_data)
        
        # Should return 404 when no Excel files are available
        return self.assert_status_code(response, 404, "Pandas query no files")
    
    def _setup_test_files(self):
        """Helper method to set up test files for search tests."""
        # Upload and parse test files if they don't exist
        upload_response = self.upload_test_file("Sample1.pdf")
        if upload_response:
            # Parse the file
            self.make_request('GET', '/parsefile/Sample1.pdf')
        
        upload_response = self.upload_test_file("train.xlsx")
        if upload_response:
            # Parse the file
            self.make_request('GET', '/parsefile/train.xlsx') 