#!/usr/bin/env python3
"""
Simple Integration Test Runner

This script runs all integration tests for the Document Processing API.
It can be run directly from the integration_tests directory.

Usage:
    python run_tests.py
    python run_tests.py --url <custom_url>
"""

import sys
import os
import time
from pathlib import Path

# Add the server directory to the path for imports
current_dir = Path(__file__).parent
server_dir = current_dir.parent.parent
sys.path.insert(0, str(server_dir))

# Import test classes
from test.integration_tests.test_file_management import TestFileManagement
from test.integration_tests.test_document_processing import TestDocumentProcessing
from test.integration_tests.test_search_queries import TestSearchQueries
from test.integration_tests.test_content_generation import TestContentGeneration


def main():
    """Main function to run all integration tests."""
    # Default API URL
    base_url = "https://document-processing-service-38231329931.us-central1.run.app"
    
    # Check for custom URL argument
    if len(sys.argv) > 1 and sys.argv[1] == "--url" and len(sys.argv) > 2:
        base_url = sys.argv[2]
    
    print("🚀 Starting Integration Tests for Document Processing API")
    print(f"📍 Target URL: {base_url}")
    print("=" * 80)
    
    start_time = time.time()
    
    # Initialize test classes
    test_classes = [
        TestFileManagement(base_url),
        TestDocumentProcessing(base_url),
        TestSearchQueries(base_url),
        TestContentGeneration(base_url)
    ]
    
    all_results = []
    
    # Run all tests
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__class__.__name__}...")
        test_class.run_all_tests()
        all_results.extend(test_class.results)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Generate summary
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results if result.get('status') == 'PASS')
    failed_tests = sum(1 for result in all_results if result.get('status') == 'FAIL')
    skipped_tests = sum(1 for result in all_results if result.get('status') == 'SKIP')
    
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
        for result in all_results:
            if result.get('status') == 'FAIL':
                print(f"  - {result.get('test_name', 'Unknown')}: {result.get('error', 'Unknown error')}")
    
    # Print skipped tests
    if skipped_tests > 0:
        print("\n⏭️  SKIPPED TESTS:")
        for result in all_results:
            if result.get('status') == 'SKIP':
                print(f"  - {result.get('test_name', 'Unknown')}: {result.get('reason', 'No reason provided')}")
    
    # Exit with appropriate code
    if failed_tests > 0:
        print(f"\n💥 {failed_tests} test(s) failed!")
        sys.exit(1)
    else:
        print(f"\n🎉 All tests passed! ({passed_tests} test(s))")
        sys.exit(0)


if __name__ == "__main__":
    main() 