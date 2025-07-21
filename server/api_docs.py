"""
API documentation strings and examples for the Document Processing API.
"""

# Main API description
API_DESCRIPTION = """
🚀 **Comprehensive Document Processing & AI-Powered Search API**

This API provides a complete document processing pipeline with AI-powered search capabilities:

## 📋 **Quick Start Workflow**

1. **📤 Upload Files**: Upload PDFs, Excel files (.xlsx/.xls), CSV files, or text documents
2. **📝 Parse Files**: Convert documents to structured markdown format using LlamaParse
3. **📚 Ingest Documents**: Index parsed content for hybrid search (Pinecone + BM25) with automatic duplicate prevention
4. **🔍 Search & Query**: Use hybrid search for documents or pandas agent for Excel/CSV analysis

## 🎯 **Key Features**

- **Multi-format Support**: PDF, Excel, CSV, DOCX, TXT files
- **Hybrid Search**: Combines vector search (Pinecone) + keyword search (BM25)
- **Excel/CSV Analysis**: Natural language queries on spreadsheet data
- **AI Content Generation**: Summaries, questions, and FAQ generation
- **Intelligent Search**: AI-powered result ranking and comparison
- **Duplicate Prevention**: Automatic cleanup of duplicate documents in vector database
- **Smart Content Processing**: Enhanced parsing with comprehensive content extraction

## 📊 **Search Capabilities**

- **Document Search**: Semantic + keyword search across PDF, DOCX, TXT files
- **Targeted Search**: Search within specific documents
- **Excel/CSV Queries**: Natural language data analysis via Pandas agent
- **Intelligent Ranking**: AI compares and ranks results from multiple sources

**Note**: Excel/CSV files are parsed and saved but NOT indexed to search databases since they use the Pandas agent for direct data queries.

## 🛠️ **Supported File Types**

| Type | Extensions | Processing | Search Method |
|------|------------|------------|---------------|
| Documents | `.pdf`, `.docx`, `.txt` | LlamaParse → Markdown | Pinecone + BM25 |
| Spreadsheets | `.xlsx`, `.xls` | Pandas → Markdown | Pandas Agent Queries |
| Data Files | `.csv` | Pandas → Markdown | Pandas Agent Queries |

## 🔗 **API Workflow Examples**

### Basic Document Processing:
```
POST /uploadfile/ → GET /parsefile/{filename} → POST /ingestdocuments/{filename} → POST /hybridsearch/
```

### Excel/CSV Analysis:
```
POST /uploadfile/ → GET /parsefile/{filename} → POST /querypandas/ (direct analysis)
```

### Content Generation:
```
POST /uploadfile/ → GET /parsefile/{filename} → GET /summarizecontent/{filename}
```

### Re-processing with Duplicate Prevention:
```
POST /ingestdocuments/{filename} (automatic cleanup + re-index)
```
"""

# Hybrid Search description
HYBRID_SEARCH_DESCRIPTION = """
🔍 **Advanced AI-powered search with intelligent strategy selection**

This endpoint provides smart search across your documents with three distinct modes:

## 🎯 **Search Modes**

### 1. **Sequential Smart Search** (no source_document or "all")
- **Step 1**: Searches document index (Pinecone + BM25) first
- **Step 2**: If no meaningful document results found, searches Excel/CSV files as fallback
- **Step 3**: Returns results from successful method or "no results" message
- **Intelligence**: Evaluates result quality to determine fallback necessity
- Best for: General questions when you're unsure of the source

### 2. **Document-Targeted Search** (PDF/DOCX source)
- Searches only within the specified document using hybrid search
- Combines semantic similarity (Pinecone) + keyword matching (BM25)
- Best for: Specific questions about a particular document

### 3. **Data-Targeted Search** (Excel/CSV source)
- Queries only the specified Excel/CSV file using pandas agent
- Performs calculations, filtering, and data analysis
- Best for: Statistical questions and data calculations

## 🧠 **AI Intelligence Features**

**Smart Search Strategy:**
- Automatically selects the best search method based on file type
- Sequential fallback ensures maximum coverage
- Prioritizes document search for text-based queries
- Falls back to data analysis when documents don't contain answers

**Query Understanding:**
- Semantic search for concept-based queries
- Keyword search for exact matches and names
- Data analysis for numerical and statistical questions

## 🔧 **Debug Mode**

Enable `debug: true` to see:
- Retrieved document chunks and scores
- Search execution logs
- Performance metrics
- Raw results from each search method

## 📊 **Performance**
- Document search: ~2-5 seconds
- Excel/CSV analysis: ~3-8 seconds  
- Sequential search: ~2-8 seconds (efficient fallback execution)
"""

# Pandas Query description
PANDAS_QUERY_DESCRIPTION = """
📊 **Natural language queries on Excel and CSV files using AI-powered pandas agent**

This endpoint provides direct access to spreadsheet data analysis without requiring document indexing.
Perfect for immediate data exploration, calculations, and statistical analysis.

## 🎯 **Key Features**

**Natural Language Processing:**
- Ask questions in plain English about your data
- Automatic code generation and execution
- Smart interpretation of column names and data types

**Advanced Data Analysis:**
- Statistical calculations (mean, median, sum, count, etc.)
- Data filtering and grouping operations
- Cross-tabulation and pivot table operations
- Data visualization insights

**Multi-file Support:**
- Automatically processes ALL Excel/CSV files in uploaded_files
- Returns results from each file separately
- Compares data across multiple files when relevant

## 📋 **Supported Operations**

### Statistical Analysis:
- `"What is the average salary by department?"`
- `"Calculate the total revenue for each quarter"`
- `"Show the distribution of customer ages"`

### Data Exploration:
- `"What columns are in this dataset?"`
- `"How many rows of data do we have?"`
- `"Show me the first 10 records"`
- `"What are the unique values in the category column?"`

### Filtering & Grouping:
- `"Show all employees with salary > 50000"`
- `"List customers from California"`
- `"Group sales by region and month"`

### Comparisons:
- `"Which department has the highest average salary?"`
- `"Compare Q1 vs Q4 performance"`
- `"Find the top 5 customers by revenue"`

## 🔧 **Debug Mode**

Enable `debug: true` to see:
- Dataset summary (rows, columns, data types)
- Generated pandas code
- Execution steps and intermediate results
- Performance metrics

## ⚡ **Performance**
- Small files (<1MB): 1-3 seconds
- Medium files (1-10MB): 3-8 seconds
- Large files (10-50MB): 8-15 seconds
- Processes multiple files in parallel

## 📤 **No Upload Required**
Works directly with uploaded Excel/CSV files - no parsing or ingestion needed!
"""

# Ingest Documents description
INGEST_DOCUMENTS_DESCRIPTION = """
📚 **Advanced document indexing with duplicate prevention and intelligent processing**

This endpoint processes parsed documents and creates searchable indexes for hybrid search capabilities.
Automatically handles different file types and prevents duplicate entries in the vector database.

## 🎯 **Key Features**

**Intelligent Processing:**
- **Document Files** (PDF, DOCX, TXT): Creates both Pinecone vector index and BM25 keyword index
- **Excel/CSV Files**: Parses and saves content but skips indexing (uses Pandas agent instead)
- **Automatic Detection**: Identifies file type and applies appropriate processing strategy

**Duplicate Prevention:**
- Automatically removes existing entries before adding new ones
- Supports all filename variations and extensions
- Ensures only one occurrence per source file in vector database
- Comprehensive cleanup of both source-based and ID-based duplicates

**Enhanced Content Processing:**
- Intelligent document chunking to avoid metadata size limits
- Preserves document structure and relationships
- Optimized for searchability and retrieval accuracy

## 🔧 **Processing Details**

### Document Files Processing:
1. **Chunk Creation**: Splits large documents into searchable chunks (4000 characters max)
2. **Metadata Enhancement**: Adds source tracking, chunk information, and document relationships  
3. **Vector Indexing**: Creates embeddings using OpenAI models for semantic search
4. **Keyword Indexing**: Builds BM25 index for exact keyword matching
5. **Duplicate Cleanup**: Removes any existing entries with the same source name

### Excel/CSV Files Processing:
1. **Content Parsing**: Converts tabular data to structured markdown format
2. **Metadata Creation**: Captures file statistics, column information, and data types
3. **Storage Only**: Saves parsed content without indexing (optimized for Pandas agent queries)
4. **Ready for Analysis**: Immediately available for natural language data queries

## ⚡ **Performance & Reliability**

**Processing Speed:**
- Small files (<1MB): 5-15 seconds
- Medium files (1-10MB): 15-45 seconds  
- Large files (10-50MB): 45-120 seconds

**Reliability Features:**
- Automatic retry mechanisms for parsing failures
- Comprehensive error handling and reporting
- Metadata size validation and truncation
- Graceful handling of malformed documents

**Resource Optimization:**
- Efficient chunking strategies
- Memory-conscious processing
- Parallel operations where possible

## 🛡️ **Data Integrity**

**Duplicate Prevention:**
- Scans for existing entries by source name, filename variations, and ID patterns
- Comprehensive cleanup before new ingestion
- Maintains data consistency across re-ingestion cycles
- Prevents vector database bloat and search result duplication

**Content Preservation:**
- Maintains document structure and formatting
- Preserves metadata and relationships
- Ensures searchability of all content elements
- Handles special characters and multilingual content

## 📋 **Supported Input Files**

Must be previously parsed files from the `/parsefile/` endpoint:
- PDF documents → parsed to markdown
- Excel/CSV files → converted to structured format
- DOCX files → extracted to markdown
- Text files → processed and enhanced

## 🎯 **Integration Notes**

**For Document Search:** Files are automatically indexed and ready for hybrid search queries
**For Data Analysis:** Excel/CSV files are ready for immediate Pandas agent queries
**For Content Generation:** All processed files support AI content generation endpoints
"""

# Parse Files description
PARSE_FILES_DESCRIPTION = """
📝 **Enhanced document parsing with comprehensive content extraction**

This endpoint converts uploaded files into structured, searchable markdown format using advanced AI-powered parsing.
Optimized for maximum content preservation and accurate form field extraction.

## 🎯 **Parsing Capabilities**

**Multi-Modal AI Processing:**
- **LlamaParse Integration**: Uses Gemini 2.0 Flash for advanced document understanding
- **Form Field Extraction**: Captures all form fields including "Prepared by:", "Date:", "Lot #:", etc.
- **Table Recognition**: Converts complex tables to markdown format with proper structure
- **Layout Preservation**: Maintains document structure, headers, footers, and annotations

**File Type Optimization:**
- **PDF Documents**: Advanced OCR and layout analysis for complex documents
- **Excel/CSV Files**: Direct pandas processing for accurate data extraction
- **DOCX Files**: Native content extraction with formatting preservation
- **Text Files**: Enhanced processing with structure detection

## 🛠️ **Advanced Features**

**Comprehensive Content Extraction:**
- Captures ALL text including margins, headers, footers, and sidebars
- Preserves handwritten and filled-in information
- Extracts text from images and complex layouts
- Maintains document metadata and annotations

**Content Cleaning & Optimization:**
- Removes parsing artifacts and NaN values
- Converts HTML tables to clean markdown format
- Handles special characters and multilingual content
- Optimizes for search indexing and AI processing

**Enhanced System Prompts:**
- Specialized prompts for maximum content preservation
- Form field detection and extraction
- Critical requirement: "Every word, number, symbol must appear in output"

## ⚡ **Performance & Reliability**

**Processing Speed:**
- Small files (<1MB): 10-30 seconds
- Medium files (1-10MB): 30-90 seconds
- Large files (10-50MB): 90-300 seconds
- Excel/CSV: 5-15 seconds (pandas processing)

**Quality Assurance:**
- Multi-attempt parsing with retry logic
- Comprehensive error handling and recovery
- Content validation and completeness checks
- Automatic fallback strategies for parsing failures

**Resource Management:**
- Efficient memory usage for large documents
- Async processing for better server performance
- Caching for repeated operations
- Optimal API usage and rate limiting

## 🎯 **Use Cases**

**Form Processing:**
- Quality control records and batch sheets
- Regulatory compliance documents
- Survey forms and questionnaires
- Application forms and certificates

**Document Analysis:**
- Research papers and technical documents
- Financial reports and statements
- Legal documents and contracts
- Standard operating procedures

**Data Extraction:**
- Financial data from spreadsheets
- Inventory and product catalogs
- Customer databases and CRM exports
- Performance metrics and KPIs

## 📋 **Output Format**

**Document Files:** Clean markdown with preserved structure and all content
**Excel/CSV Files:** Structured markdown tables with metadata and data summaries
**All Files:** Include file information, processing details, and data statistics

## 🔗 **Integration Notes**

Parsed files are automatically saved and ready for:
- Immediate ingestion via `/ingestdocuments/{filename}`
- Direct analysis via `/querypandas/` (Excel/CSV)
- Content generation via summary and FAQ endpoints
""" 