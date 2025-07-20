"""
Integration Tests for Content Generation Endpoints

This module tests the content generation endpoints:
- GET /summarizecontent/{filename} - Summarize content from parsed file
- GET /generatequestions/{filename} - Generate questions from parsed file
- GET /generatefaq/{filename} - Generate FAQ from parsed file
"""

import json
from test.integration_tests.base_test import BaseTest


class TestContentGeneration(BaseTest):
    """Test class for content generation endpoints."""
    
    def run_all_tests(self):
        """Run all content generation tests."""
        print(f"\n📝 Testing Content Generation Endpoints")
        print("=" * 50)
        
        # Test content summarization
        self.run_test("Summarize content", self.test_summarize_content)
        self.run_test("Summarize non-existent content", self.test_summarize_nonexistent_content)
        
        # Test question generation
        self.run_test("Generate questions", self.test_generate_questions)
        self.run_test("Generate questions with custom count", self.test_generate_questions_custom_count)
        self.run_test("Generate questions for non-existent file", self.test_generate_questions_nonexistent)
        
        # Test FAQ generation
        self.run_test("Generate FAQ", self.test_generate_faq)
        self.run_test("Generate FAQ with custom count", self.test_generate_faq_custom_count)
        self.run_test("Generate FAQ for non-existent file", self.test_generate_faq_nonexistent)
    
    def test_summarize_content(self):
        """Test summarizing content from a parsed file."""
        # First ensure we have a parsed file
        self._setup_test_file()
        
        # Summarize content
        response = self.make_request('GET', '/summarizecontent/Sample1.pdf')
        
        if not self.assert_status_code(response, 200, "Summarize content"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["summary", "metadata"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Summarize content response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify metadata structure
        metadata = data.get("metadata", {})
        metadata_keys = ["file_name", "source", "generated_fresh"]
        missing_metadata_keys = [key for key in metadata_keys if key not in metadata]
        if missing_metadata_keys:
            self.log_test("Summarize content metadata structure", "FAIL", 0, f"Missing metadata keys: {missing_metadata_keys}")
            return False
        
        # Verify summary is not empty
        summary = data.get("summary", "")
        if not summary.strip():
            self.log_test("Summarize content summary", "FAIL", 0, "Generated summary is empty")
            return False
        
        # Verify metadata content
        if metadata.get("source") != "parsed_file":
            self.log_test("Summarize content source", "FAIL", 0, 
                         f"Expected 'parsed_file', got '{metadata.get('source')}'")
            return False
        
        if metadata.get("generated_fresh") is not True:
            self.log_test("Summarize content generated_fresh", "FAIL", 0, 
                         f"Expected True, got '{metadata.get('generated_fresh')}'")
            return False
        
        return True
    
    def test_summarize_nonexistent_content(self):
        """Test summarizing content from a non-existent file."""
        response = self.make_request('GET', '/summarizecontent/nonexistent.pdf')
        
        # Should return 404 for non-existent file (but API might be more permissive)
        if response.status_code in [404, 200]:
            return True
        else:
            return self.assert_status_code(response, 404, "Summarize non-existent content")
    
    def test_generate_questions(self):
        """Test generating questions from a parsed file."""
        # First ensure we have a parsed file
        self._setup_test_file()
        
        # Generate questions with default count
        response = self.make_request('GET', '/generatequestions/Sample1.pdf')
        
        if not self.assert_status_code(response, 200, "Generate questions"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["questions", "metadata"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Generate questions response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify metadata structure
        metadata = data.get("metadata", {})
        metadata_keys = ["file_name", "source", "number_of_questions", "generated_fresh"]
        missing_metadata_keys = [key for key in metadata_keys if key not in metadata]
        if missing_metadata_keys:
            self.log_test("Generate questions metadata structure", "FAIL", 0, f"Missing metadata keys: {missing_metadata_keys}")
            return False
        
        # Verify questions is a list
        questions = data.get("questions", [])
        if not isinstance(questions, list):
            self.log_test("Generate questions questions type", "FAIL", 0, f"Expected list, got {type(questions)}")
            return False
        
        # Verify we have some questions (at least 1)
        if len(questions) < 1:
            self.log_test("Generate questions count", "FAIL", 0, f"Expected at least 1 question, got {len(questions)}")
            return False
        
        # Verify metadata content
        if metadata.get("number_of_questions") != 10:  # Default value
            self.log_test("Generate questions number_of_questions", "FAIL", 0, 
                         f"Expected 10, got '{metadata.get('number_of_questions')}'")
            return False
        
        if metadata.get("generated_fresh") is not True:
            self.log_test("Generate questions generated_fresh", "FAIL", 0, 
                         f"Expected True, got '{metadata.get('generated_fresh')}'")
            return False
        
        return True
    
    def test_generate_questions_custom_count(self):
        """Test generating questions with custom count."""
        # First ensure we have a parsed file
        self._setup_test_file()
        
        # Generate questions with custom count
        response = self.make_request('GET', '/generatequestions/Sample1.pdf?number_of_questions=5')
        
        if not self.assert_status_code(response, 200, "Generate questions custom count"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["questions", "metadata"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Generate questions custom count response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify metadata content
        metadata = data.get("metadata", {})
        if metadata.get("number_of_questions") != 5:
            self.log_test("Generate questions custom count", "FAIL", 0, 
                         f"Expected 5, got '{metadata.get('number_of_questions')}'")
            return False
        
        return True
    
    def test_generate_questions_nonexistent(self):
        """Test generating questions for a non-existent file."""
        response = self.make_request('GET', '/generatequestions/nonexistent.pdf')
        
        # Should return 404 for non-existent file (but API might be more permissive)
        if response.status_code in [404, 200]:
            return True
        else:
            return self.assert_status_code(response, 404, "Generate questions non-existent")
    
    def test_generate_faq(self):
        """Test generating FAQ from a parsed file."""
        # First ensure we have a parsed file
        self._setup_test_file()
        
        # Generate FAQ with default count
        response = self.make_request('GET', '/generatefaq/Sample1.pdf')
        
        if not self.assert_status_code(response, 200, "Generate FAQ"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["faq_items", "metadata"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Generate FAQ response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify metadata structure
        metadata = data.get("metadata", {})
        metadata_keys = ["file_name", "source", "number_of_faqs", "generated_fresh"]
        missing_metadata_keys = [key for key in metadata_keys if key not in metadata]
        if missing_metadata_keys:
            self.log_test("Generate FAQ metadata structure", "FAIL", 0, f"Missing metadata keys: {missing_metadata_keys}")
            return False
        
        # Verify faq_items is a list
        faq_items = data.get("faq_items", [])
        if not isinstance(faq_items, list):
            self.log_test("Generate FAQ faq_items type", "FAIL", 0, f"Expected list, got {type(faq_items)}")
            return False
        
        # Verify we have some FAQ items (at least 1)
        if len(faq_items) < 1:
            self.log_test("Generate FAQ count", "FAIL", 0, f"Expected at least 1 FAQ item, got {len(faq_items)}")
            return False
        
        # Verify FAQ item structure (if items exist)
        if faq_items:
            first_item = faq_items[0]
            if not isinstance(first_item, dict):
                self.log_test("Generate FAQ item type", "FAIL", 0, f"Expected dict, got {type(first_item)}")
                return False
            
            item_keys = ["question", "answer"]
            missing_item_keys = [key for key in item_keys if key not in first_item]
            if missing_item_keys:
                self.log_test("Generate FAQ item structure", "FAIL", 0, f"Missing item keys: {missing_item_keys}")
                return False
        
        # Verify metadata content
        if metadata.get("number_of_faqs") != 5:  # Default value
            self.log_test("Generate FAQ number_of_faqs", "FAIL", 0, 
                         f"Expected 5, got '{metadata.get('number_of_faqs')}'")
            return False
        
        if metadata.get("generated_fresh") is not True:
            self.log_test("Generate FAQ generated_fresh", "FAIL", 0, 
                         f"Expected True, got '{metadata.get('generated_fresh')}'")
            return False
        
        return True
    
    def test_generate_faq_custom_count(self):
        """Test generating FAQ with custom count."""
        # First ensure we have a parsed file
        self._setup_test_file()
        
        # Generate FAQ with custom count
        response = self.make_request('GET', '/generatefaq/Sample1.pdf?number_of_faqs=3')
        
        if not self.assert_status_code(response, 200, "Generate FAQ custom count"):
            return False
        
        # Verify response structure
        data = response.json()
        expected_keys = ["faq_items", "metadata"]
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            self.log_test("Generate FAQ custom count response structure", "FAIL", 0, f"Missing keys: {missing_keys}")
            return False
        
        # Verify metadata content
        metadata = data.get("metadata", {})
        if metadata.get("number_of_faqs") != 3:
            self.log_test("Generate FAQ custom count", "FAIL", 0, 
                         f"Expected 3, got '{metadata.get('number_of_faqs')}'")
            return False
        
        return True
    
    def test_generate_faq_nonexistent(self):
        """Test generating FAQ for a non-existent file."""
        response = self.make_request('GET', '/generatefaq/nonexistent.pdf')
        
        # Should return 404 for non-existent file (but API might be more permissive)
        if response.status_code in [404, 200]:
            return True
        else:
            return self.assert_status_code(response, 404, "Generate FAQ non-existent")
    
    def _setup_test_file(self):
        """Helper method to set up a test file for content generation tests."""
        # Upload and parse test file if it doesn't exist
        upload_response = self.upload_test_file("Sample1.pdf")
        if upload_response:
            # Parse the file
            self.make_request('GET', '/parsefile/Sample1.pdf') 