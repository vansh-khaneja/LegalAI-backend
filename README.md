# Legal AI Backend

This repository contains the backend API for the Legal AI application, a powerful tool designed to process, analyze, and retrieve information from legal documents.

## 📋 Table of Contents

- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Core Services](#core-services)
- [Data Flow](#data-flow)

## Project Structure

```
vansh-khaneja-legalai-backend/
├── app.py                  # Main application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Dependencies
├── api/                    # API-related modules
│   ├── __init__.py
│   ├── responses.py        # Response formatters
│   └── routes.py           # API endpoints
├── database/               # Database operations
│   ├── __init__.py
│   ├── db_utils.py         # Database utility functions
│   └── models.py           # Data models
├── logs/                   # Application logs
├── services/               # Core business logic
│   ├── __init__.py
│   ├── cloudinary_service.py  # File storage service
│   ├── document_service.py    # Document processing
│   ├── llm_service.py         # Language model interactions
│   ├── summary_service.py     # Document summarization
│   └── vector_service.py      # Vector embeddings & search
├── uploads/                # Temporary file storage
└── utils/                  # Utility functions
    ├── __init__.py
    ├── file_utils.py       # File handling utilities
    └── logging_utils.py    # Logging configuration
```

## Setup & Installation

### 1. Create a Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Vector Store Configuration
QDRANT_URL = "your-qdrant-cloud-url"
API_KEY = "your-qdrant-api-key"
COLLECTION_NAME = "your-collection-name"

# Database Configuration
DB_URL = "your-postgres-connection-string"

# Cloudinary Configuration
CLOUD_NAME = "your-cloud-name"
CLOUD_KEY = "your-cloud-key"
CLOUD_SECRET = "your-cloud-secret"

# LLM Configuration
GROQ_API = "your-groq-api-key"
```

## Running the Application

```bash
python app.py
```

The application will start on port 5000 by default (http://localhost:5000).

## API Endpoints

### 1. Document Upload

**Endpoint:** `/upload`
**Method:** `POST`
**Content-Type:** `multipart/form-data`

**Request Parameters:**
- `file`: The document file (PDF or DOCX)
- `caseType`: Type of legal case (e.g., "criminal", "civil", etc.)

**Response:**
```json
{
  "success": true,
  "message": "File processed and uploaded as [case_type] case",
  "data": {
    "file_id": 12345
  }
}
```

### 2. Query Retrieval

**Endpoint:** `/retrieve`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "question": "What are the legal implications of copyright infringement?"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "answer": "Detailed response to the question...",
    "metadata": [
      {
        "file_id": 12345,
        "file_url": "https://cloudinary.com/path/to/document.pdf",
        "file_summary": "Summary of the document",
        "case_type": "intellectual_property",
        "score": 0.92,
        "text": "Relevant text snippet from the document"
      }
    ]
  }
}
```

## Core Services

### Document Service
Handles document loading, parsing, and text extraction from various file formats (PDF, DOCX).

### Vector Service
Manages document embeddings and semantic search functionality using Qdrant as the vector database.

### LLM Service
Routes queries and generates responses using the Groq API (Llama 3 model).

### Summarization Service
Generates concise summaries of legal documents.

### Cloudinary Service
Handles file storage operations for uploaded documents.

## Data Flow

1. **Document Upload Flow:**
   - User uploads a document with a case type
   - File is validated and temporarily saved
   - Document is uploaded to Cloudinary for permanent storage
   - Text is extracted and split into chunks
   - Vector embeddings are generated and stored in Qdrant
   - Document metadata is stored in PostgreSQL
   - File ID is returned to the user

2. **Query Flow:**
   - User submits a question
   - LLM service routes the query (general vs. case-based)
   - For case-based queries:
     - Query is converted to vector embedding
     - Similar document chunks are retrieved from Qdrant
     - Relevant context is assembled from these chunks
     - LLM generates a response using the context
   - For general queries:
     - LLM generates a response without document context
   - Response with metadata is returned to the user

---

## Contributing

Please feel free to submit issues, fork the repository and send pull requests!

## License

This project is licensed under the terms of the MIT license.
