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
3. **📚 Ingest Documents**: Index parsed content for hybrid search (Pinecone + BM25)
4. **🔍 Search & Query**: Use hybrid search for documents or pandas agent for Excel/CSV analysis

## 🎯 **Key Features**

- **Multi-format Support**: PDF, Excel, CSV, DOCX, TXT files
- **Hybrid Search**: Combines vector search (Pinecone) + keyword search (BM25)
- **Excel/CSV Analysis**: Natural language queries on spreadsheet data
- **AI Content Generation**: Summaries, questions, and FAQ generation
- **Intelligent Search**: AI-powered result ranking and comparison

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
"""

# Hybrid Search description
HYBRID_SEARCH_DESCRIPTION = """
🔍 **Advanced AI-powered search with intelligent strategy selection**

This endpoint provides smart search across your documents with three distinct modes:

## 🎯 **Search Modes**

### 1. **Sequential Smart Search** (no source_document)
- **Step 1**: Searches document index (Pinecone + BM25) first
- **Step 2**: If no document results found, searches Excel/CSV files as fallback
- **Step 3**: Returns results from successful method or "no results" message
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