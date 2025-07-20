"""
Base Test Class for Integration Tests

This module provides a base class with common functionality
for all integration tests.
"""

import time
import requests
from typing import Dict, Any, Optional
from pathlib import Path


class BaseTest:
    """Base class for all integration tests."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
    def log_test(self, test_name: str, status: str, duration: float = 0, 
                 error: str = None, reason: str = None) -> None:
        """Log test result."""
        result = {
            'test_name': test_name,
            'status': status,
            'duration': duration,
            'timestamp': time.time()
        }
        
        if error:
            result['error'] = error
        if reason:
            result['reason'] = reason
            
        self.results.append(result)
        
        # Print status
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌',
            'SKIP': '⏭️'
        }
        
        print(f"  {status_emoji.get(status, '❓')} {test_name} ({duration:.2f}s)")
        if error:
            print(f"    Error: {error}")
        if reason:
            print(f"    Reason: {reason}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"
        return self.session.request(method, url, **kwargs)
    
    def assert_status_code(self, response: requests.Response, expected_status: int, 
                          test_name: str) -> bool:
        """Assert response status code."""
        if response.status_code == expected_status:
            return True
        else:
            error_msg = f"Expected status {expected_status}, got {response.status_code}"
            self.log_test(test_name, 'FAIL', 0, error_msg)
            return False
    
    def assert_response_structure(self, response: requests.Response, 
                                expected_keys: list, test_name: str) -> bool:
        """Assert response has expected structure."""
        try:
            data = response.json()
            missing_keys = [key for key in expected_keys if key not in data]
            
            if not missing_keys:
                return True
            else:
                error_msg = f"Missing keys in response: {missing_keys}"
                self.log_test(test_name, 'FAIL', 0, error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            self.log_test(test_name, 'FAIL', 0, error_msg)
            return False
    
    def get_test_file_path(self, filename: str) -> Path:
        """Get path to test file."""
        test_docs_dir = Path(__file__).parent.parent / "docs"
        return test_docs_dir / filename
    
    def upload_test_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Upload a test file and return the response."""
        file_path = self.get_test_file_path(filename)
        
        if not file_path.exists():
            print(f"⚠️  Test file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'application/octet-stream')}
                response = self.make_request('POST', '/uploadfile/', files=files)
                
                if response.status_code == 201:
                    return response.json()
                else:
                    print(f"⚠️  Failed to upload {filename}: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"⚠️  Error uploading {filename}: {str(e)}")
            return None
    
    def run_test(self, test_name: str, test_func, *args, **kwargs) -> None:
        """Run a test with timing and error handling."""
        start_time = time.time()
        
        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            if result:
                self.log_test(test_name, 'PASS', duration)
            else:
                self.log_test(test_name, 'FAIL', duration, "Test returned False")
                
        except Exception as e:
            duration = time.time() - start_time
            self.log_test(test_name, 'FAIL', duration, str(e))
    
    def skip_test(self, test_name: str, reason: str) -> None:
        """Skip a test with reason."""
        self.log_test(test_name, 'SKIP', 0, reason=reason)
    
    def run_all_tests(self) -> None:
        """Run all tests in the class. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement run_all_tests()") 