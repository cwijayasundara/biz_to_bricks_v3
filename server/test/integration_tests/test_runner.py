#!/usr/bin/env python3
"""
Integration Test Runner for Document Processing API

This module provides a comprehensive test suite for all API endpoints
defined in the Document Processing API.

Usage:
    python test_runner.py
    python test_runner.py --endpoint upload
    python test_runner.py --endpoint all
"""

import sys
import os
import time
import argparse
from typing import List, Dict, Any
import requests
from pathlib import Path

# Add the server directory to the path for imports
current_dir = Path(__file__).parent
server_dir = current_dir.parent.parent
sys.path.insert(0, str(server_dir))

# Import all test modules
from test.integration_tests.test_file_management import TestFileManagement
from test.integration_tests.test_document_processing import TestDocumentProcessing
from test.integration_tests.test_search_queries import TestSearchQueries
from test.integration_tests.test_content_generation import TestContentGeneration


class IntegrationTestRunner:
    """Main test runner for all integration tests."""
    
    def __init__(self, base_url: str = "https://document-processing-service-38231329931.us-central1.run.app"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.start_time = None
        self.end_time = None
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("🚀 Starting Integration Tests for Document Processing API")
        print(f"📍 Target URL: {self.base_url}")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # Initialize test classes
        test_classes = [
            TestFileManagement(self.base_url),
            TestDocumentProcessing(self.base_url),
            TestSearchQueries(self.base_url),
            TestContentGeneration(self.base_url)
        ]
        
        # Run all tests
        for test_class in test_classes:
            print(f"\n📋 Running {test_class.__class__.__name__}...")
            test_class.run_all_tests()
            self.test_results.extend(test_class.results)
        
        self.end_time = time.time()
        
        # Generate summary
        return self.generate_summary()
    
    def run_specific_tests(self, endpoint: str) -> Dict[str, Any]:
        """Run tests for a specific endpoint category."""
        print(f"🎯 Running tests for endpoint: {endpoint}")
        print(f"📍 Target URL: {self.base_url}")
        print("=" * 80)
        
        self.start_time = time.time()
        
        if endpoint == "file_management":
            test_class = TestFileManagement(self.base_url)
        elif endpoint == "document_processing":
            test_class = TestDocumentProcessing(self.base_url)
        elif endpoint == "search_queries":
            test_class = TestSearchQueries(self.base_url)
        elif endpoint == "content_generation":
            test_class = TestContentGeneration(self.base_url)
        else:
            print(f"❌ Unknown endpoint: {endpoint}")
            return {"error": f"Unknown endpoint: {endpoint}"}
        
        print(f"\n📋 Running {test_class.__class__.__name__}...")
        test_class.run_all_tests()
        self.test_results.extend(test_class.results)
        
        self.end_time = time.time()
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get('status') == 'PASS')
        failed_tests = sum(1 for result in self.test_results if result.get('status') == 'FAIL')
        skipped_tests = sum(1 for result in self.test_results if result.get('status') == 'SKIP')
        
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏭️  Skipped: {skipped_tests}")
        print(f"📊 Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "📊 Success Rate: 0%")
        
        # Print failed tests
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result.get('status') == 'FAIL':
                    print(f"  - {result.get('test_name', 'Unknown')}: {result.get('error', 'Unknown error')}")
        
        # Print skipped tests
        if skipped_tests > 0:
            print("\n⏭️  SKIPPED TESTS:")
            for result in self.test_results:
                if result.get('status') == 'SKIP':
                    print(f"  - {result.get('test_name', 'Unknown')}: {result.get('reason', 'No reason provided')}")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "duration": duration,
            "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0,
            "results": self.test_results
        }


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Integration Test Runner for Document Processing API")
    parser.add_argument(
        "--endpoint", 
        choices=["all", "file_management", "document_processing", "search_queries", "content_generation"],
        default="all",
        help="Specific endpoint category to test (default: all)"
    )
    parser.add_argument(
        "--url",
        default="https://document-processing-service-38231329931.us-central1.run.app",
        help="Base URL for the API (default: production URL)"
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = IntegrationTestRunner(args.url)
    
    try:
        if args.endpoint == "all":
            summary = runner.run_all_tests()
        else:
            summary = runner.run_specific_tests(args.endpoint)
        
        # Exit with appropriate code
        if summary.get('failed', 0) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 