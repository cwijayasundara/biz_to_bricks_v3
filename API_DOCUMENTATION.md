# Document Processing API Documentation

## Overview

The Document Processing API provides comprehensive functionality for uploading, parsing, editing, summarizing, and searching documents. Built with FastAPI, it offers a robust solution for document workflow automation.

**Base URL (Local Development):** `http://localhost:8004`
**Base URL (Production):** `https://document-processing-service-yawfj7f47q-uc.a.run.app`

## Authentication

Currently, no authentication is required for API endpoints.

---

## API Endpoints

### 1. File Upload

#### `POST /uploadfile/`

Upload a file to the server for processing.

**Parameters:**
- `file` (form-data, required): The file to upload

**Response:**
```json
{
  "filename": "example.pdf",
  "file_path": "uploaded_files/example.pdf"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8004/uploadfile/" \
  -F "file=@example.pdf"
```

---

### 2. File Listing

#### `GET /listfiles/{directory}`

List all files in a specified directory.

**Path Parameters:**
- `directory` (string, required): Directory to list files from
  - Valid values: `uploaded_files`, `parsed_files`, `bm25_indexes`, `generated_questions`

**Response:**
```json
{
  "files": ["file1.pdf", "file2.docx", "file3.txt"]
}
```

**Example:**
```bash
curl "http://localhost:8004/listfiles/uploaded_files"
```

---

### 3. File Parsing

#### `GET /parsefile/{filename}`

Parse an uploaded file into markdown format using LlamaIndex.

**Path Parameters:**
- `filename` (string, required): Name of the file to parse

**Response:**
```json
{
  "text_content": "# Document Title\n\nContent of the document...",
  "metadata": {
    "file_name": "example",
    "file_path": "parsed_files/example"
  }
}
```

**Example:**
```bash
curl "http://localhost:8004/parsefile/example.pdf"
```

---

### 4. Content Saving

#### `POST /savecontent/{filename}`

Save edited content to the parsed files directory.

**Path Parameters:**
- `filename` (string, required): Name of the file to save content for

**Request Body:**
```json
{
  "content": "# Updated Document\n\nEdited content here..."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content for example saved successfully"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8004/savecontent/example" \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated content"}'
```

---

### 5. Save Content & Ingest Documents

#### `POST /saveandingst/{filename}`

Save edited content to the parsed files directory and immediately ingest the document to Pinecone vector database and BM25 index in a single operation.

**Path Parameters:**
- `filename` (string, required): Name of the file to save content for and ingest

**Request Body:**
```json
{
  "content": "# Updated Document\n\nEdited content that will be saved and indexed..."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content for example saved and ingested successfully. Document is now searchable in the hybrid search system."
}
```

**Example:**
```bash
curl -X POST "http://localhost:8004/saveandingst/example" \
  -H "Content-Type: application/json" \
  -d '{"content": "Updated content that will be indexed"}'
```

**Features:**
- Combines content saving and document ingestion in one atomic operation
- Automatically creates vector embeddings for semantic search
- Updates BM25 index for keyword search
- Makes the document immediately available for hybrid search
- Provides detailed error handling for both save and ingest operations

---

### 6. Content Summarization

#### `GET /summarizecontent/{filename}`

Generate an AI-powered summary of a parsed document.

**Path Parameters:**
- `filename` (string, required): Name of the file to summarize (with or without extension)

**Response:**
```json
{
  "summary": "This document discusses...",
  "metadata": {
    "file_name": "example",
    "source": "parsed_file",
    "generated_fresh": true
  }
}
```

**Example:**
```bash
curl "http://localhost:8004/summarizecontent/example"
```

---

### 7. Question Generation

#### `GET /generatequestions/{filename}`

Generate relevant questions based on a parsed document using AI.
Questions are generated fresh each time without saving to disk.

**Path Parameters:**
- `filename` (string, required): Name of the file to generate questions for

**Query Parameters:**
- `number_of_questions` (integer, optional): Number of questions to generate
  - Default: 10
  - Range: 1-50

**Response:**
```json
{
  "questions": "1. What is the main topic of this document?\n2. Who are the key stakeholders mentioned?\n...",
  "metadata": {
    "file_name": "example",
    "source": "parsed_file",
    "number_of_questions": 10,
    "generated_fresh": true
  }
}
```

**Example:**
```bash
curl "http://localhost:8004/generatequestions/example?number_of_questions=15"
```

**Features:**
- Generates questions fresh each time for most relevant results
- No caching or disk storage of generated questions
- Configurable number of questions (1-50)
- Uses the latest parsed document content

---

### 8. Document Ingestion

#### `POST /ingestdocuments/{filename}`

Ingest documents into Pinecone vector database and BM25 index for search functionality.

**Path Parameters:**
- `filename` (string, required): Name of the file to ingest

**Response:**
```json
{
  "message": "Documents ingested to Pinecone and BM25 index for example"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8004/ingestdocuments/example.md"
```

---

### 9. Hybrid Search

#### `POST /hybridsearch/`

Perform hybrid search using both Pinecone vector search and BM25 keyword search.

**Request Body:**
```json
{
  "query": "What is the main idea of the document?"
}
```

**Response:**
```json
{
  "result": "Based on the documents, the main idea is..."
}
```

**Example:**
```bash
curl -X POST "http://localhost:8004/hybridsearch/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}'
```

---

### 10. File Deletion

#### `DELETE /deletefile/{directory}/{filename}`

Delete a file from a specified directory.

**Path Parameters:**
- `directory` (string, required): Directory containing the file
  - Valid values: `uploaded_files`, `parsed_files`, `bm25_indexes`, `generated_questions`
- `filename` (string, required): Name of the file to delete

**Response:**
```json
{
  "status": "success",
  "message": "File example.pdf deleted successfully from uploaded_files"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8004/deletefile/uploaded_files/example.pdf"
```

---

## Data Models

### ContentUpdate
```json
{
  "content": "string (required)"
}
```

### SearchQuery
```json
{
  "query": "string (required)"
}
```

### ErrorResponse
```json
{
  "error": "string"
}
```

### SuccessResponse
```json
{
  "status": "success",
  "message": "string"
}
```

---

## Error Handling

### HTTP Status Codes

- **200**: Success
- **201**: Created (successful upload)
- **400**: Bad Request (invalid parameters)
- **404**: Not Found (file or endpoint)
- **500**: Internal Server Error

### Error Response Format
```json
{
  "error": "Error description message"
}
```

---

## Workflow Examples

### Complete Document Processing Workflow

1. **Upload a document:**
   ```bash
   curl -X POST "http://localhost:8004/uploadfile/" -F "file=@document.pdf"
   ```

2. **Parse the document:**
   ```bash
   curl "http://localhost:8004/parsefile/document.pdf"
   ```

3. **Edit content (optional):**
   ```bash
   curl -X POST "http://localhost:8004/savecontent/document" \
     -H "Content-Type: application/json" \
     -d '{"content": "Updated content"}'
   ```

4. **Generate summary:**
   ```bash
   curl "http://localhost:8004/summarizecontent/document"
   ```

5. **Generate questions:**
   ```bash
   curl "http://localhost:8004/generatequestions/document?number_of_questions=10"
   ```

6. **Ingest for search:**
   ```bash
   curl -X POST "http://localhost:8004/ingestdocuments/document.md"
   ```

7. **Search the content:**
   ```bash
   curl -X POST "http://localhost:8004/hybridsearch/" \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the key points?"}'
   ```

---

## Directory Structure

The API manages files across several directories:

- `uploaded_files/`: Original uploaded documents
- `parsed_files/`: Markdown versions of parsed documents  
- `generated_questions/`: AI-generated questions (not saved to disk)
- `bm25_indexes/`: BM25 search indexes

Note: Summaries and questions are generated fresh each time and not stored on disk.

---

## Interactive API Documentation

When running the server, you can access interactive API documentation at:
- **Swagger UI**: `http://localhost:8004/docs`
- **ReDoc**: `http://localhost:8004/redoc`

---

## Rate Limits

Currently, no rate limits are implemented. For production use, consider implementing appropriate rate limiting.

---

## Support

For issues or questions, please refer to the project repository or contact the development team.