# Integration Tests for Document Processing API

This directory contains comprehensive integration tests for the Document Processing API endpoints. The tests are designed to validate the functionality of the deployed API at `https://document-processing-service-38231329931.us-central1.run.app`.

## Test Structure

The integration tests are organized into four main categories, each testing a specific group of endpoints:

### 1. File Management Tests (`test_file_management.py`)
Tests the file management endpoints:
- **POST** `/uploadfile/` - Upload files (PDF, Excel, etc.)
- **GET** `/listfiles/{directory}` - List files in directories
- **DELETE** `/deletefile/{directory}/{filename}` - Delete files

### 2. Document Processing Tests (`test_document_processing.py`)
Tests the document processing pipeline:
- **GET** `/parsefile/{filename}` - Parse uploaded files to markdown
- **POST** `/savecontent/{filename}` - Save content to parsed files
- **POST** `/saveandingst/{filename}` - Save content and ingest to search indexes
- **POST** `/ingestdocuments/{filename}` - Ingest documents to search indexes

### 3. Search & Query Tests (`test_search_queries.py`)
Tests the search and query functionality:
- **POST** `/hybridsearch/` - Intelligent hybrid search across documents and data
- **POST** `/querypandas/` - Direct Excel/CSV data analysis with AI
- **GET** `/sourcedocuments/` - Get list of available source documents

### 4. Content Generation Tests (`test_content_generation.py`)
Tests the AI content generation features:
- **GET** `/summarizecontent/{filename}` - Summarize content from parsed files
- **GET** `/generatequestions/{filename}` - Generate questions from parsed files
- **GET** `/generatefaq/{filename}` - Generate FAQ from parsed files

## Test Files

The test suite uses sample documents from the `server/test/docs/` directory:
- `Sample1.pdf` - A sample PDF document for testing
- `train.xlsx` - A sample Excel file for testing

## Running the Tests

### Prerequisites

1. Ensure you have Python 3.7+ installed
2. Install required dependencies:
   ```bash
   pip install requests
   ```

### Running All Tests

To run all integration tests:

```bash
cd server/test/integration_tests
python run_tests.py
```

### Running with Custom API URL

To test against a different API endpoint:

```bash
python run_tests.py --url https://your-custom-api-url.com
```

### Running Individual Test Categories

You can also run the original test runner with specific categories:

```bash
python test_runner.py --endpoint file_management
python test_runner.py --endpoint document_processing
python test_runner.py --endpoint search_queries
python test_runner.py --endpoint content_generation
```

## Test Output

The tests provide detailed output including:

- ✅ **Passed tests** - Tests that completed successfully
- ❌ **Failed tests** - Tests that encountered errors
- ⏭️ **Skipped tests** - Tests that were skipped due to dependencies

Each test includes:
- Test name and status
- Execution time
- Error details (if failed)
- Skip reason (if skipped)

## Test Coverage

### File Management Tests
- Upload PDF and Excel files
- Validate file type detection
- Test file listing functionality
- Test file deletion
- Error handling for invalid operations

### Document Processing Tests
- File parsing with LlamaParse
- Content saving and retrieval
- Document ingestion to search indexes
- Error handling for missing files

### Search & Query Tests
- Hybrid search with various query types
- Source document filtering
- Debug mode functionality
- Pandas agent for Excel/CSV analysis
- Error handling for missing files

### Content Generation Tests
- AI-powered content summarization
- Question generation with custom counts
- FAQ generation with custom counts
- Metadata validation
- Error handling for missing files

## Test Features

### Comprehensive Validation
- **Response Structure**: Validates that API responses contain expected fields
- **Status Codes**: Ensures correct HTTP status codes are returned
- **Content Validation**: Checks that generated content is meaningful
- **Error Handling**: Tests proper error responses for invalid requests

### Real-world Scenarios
- **File Upload Workflow**: Tests complete file processing pipeline
- **Search Functionality**: Tests both document and data search capabilities
- **Content Generation**: Tests AI-powered content creation features
- **Error Conditions**: Tests system behavior under various error conditions

### Test Dependencies
- Tests are designed to handle dependencies between endpoints
- File upload tests prepare data for processing tests
- Processing tests prepare data for search tests
- Proper cleanup and setup methods ensure test isolation

## Troubleshooting

### Common Issues

1. **Network Connectivity**: Ensure you can reach the API endpoint
2. **File Dependencies**: Tests require sample files in `server/test/docs/`
3. **API Rate Limits**: Some tests may be affected by API rate limiting
4. **Test Data**: Tests may fail if sample files are corrupted or missing

### Debug Mode

For detailed debugging, you can modify the test files to include debug output:

```python
# Add debug logging to any test method
print(f"Debug: Response status: {response.status_code}")
print(f"Debug: Response content: {response.text}")
```

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use the `BaseTest` class for common functionality
3. Include both positive and negative test cases
4. Add proper error handling and validation
5. Update this README with new test information

## API Documentation

For detailed API documentation, visit:
- **Swagger UI**: https://document-processing-service-38231329931.us-central1.run.app/docs
- **ReDoc**: https://document-processing-service-38231329931.us-central1.run.app/redoc

## Test Results Example

```
🚀 Starting Integration Tests for Document Processing API
📍 Target URL: https://document-processing-service-38231329931.us-central1.run.app
================================================================================

📁 Testing File Management Endpoints
==================================================
  ✅ Upload PDF file (0.76s)
  ✅ Upload Excel file (0.36s)
  ✅ Upload file with invalid filename (0.17s)
  ✅ List uploaded files (0.16s)
  ✅ List parsed files (0.15s)
  ✅ List non-existent directory (0.11s)
  ✅ Delete uploaded file (0.88s)
  ✅ Delete non-existent file (0.17s)
  ✅ Delete file from invalid directory (0.14s)

📄 Testing Document Processing Endpoints
==================================================
  ✅ Parse PDF file (1.02s)
  ✅ Parse Excel file (0.89s)
  ✅ Parse non-existent file (0.25s)
  ✅ Save content to file (1.19s)
  ✅ Save content to non-existent file (0.32s)
  ✅ Save content and ingest (4.29s)
  ✅ Save and ingest non-existent file (1.55s)
  ✅ Ingest documents (2.35s)
  ✅ Ingest non-existent documents (1.31s)

🔍 Testing Search & Query Endpoints
==================================================
  ✅ Get source documents (0.25s)
  ✅ Hybrid search with general query (5.55s)
  ✅ Hybrid search with source filter (3.72s)
  ✅ Hybrid search with debug mode (9.27s)
  ✅ Hybrid search with empty query (4.44s)
  ✅ Pandas query with Excel file (2.70s)
  ✅ Pandas query with debug mode (7.01s)
  ✅ Pandas query with no Excel files (0.70s)

📝 Testing Content Generation Endpoints
==================================================
  ✅ Summarize content (2.52s)
  ✅ Summarize non-existent content (0.70s)
  ✅ Generate questions (3.50s)
  ✅ Generate questions with custom count (2.17s)
  ✅ Generate questions for non-existent file (2.64s)
  ✅ Generate FAQ (4.84s)
  ✅ Generate FAQ with custom count (4.51s)
  ✅ Generate FAQ for non-existent file (4.69s)

================================================================================
📊 TEST SUMMARY
================================================================================
⏱️  Total Duration: 75.26 seconds
📈 Total Tests: 34
✅ Passed: 34
❌ Failed: 0
⏭️  Skipped: 0
📊 Success Rate: 100.0%

🎉 All tests passed! (34 test(s))
``` 