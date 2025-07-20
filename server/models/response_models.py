"""
Response models for the Document Processing API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List


class ErrorResponse(BaseModel):
    """Model for standardized error responses"""
    error: str = Field(
        ..., 
        description="Detailed error message explaining what went wrong",
        examples=["File not found: sample.pdf does not exist in uploaded_files directory"]
    )


class SuccessResponse(BaseModel):
    """Model for standardized success responses"""
    status: str = Field(
        "success", 
        description="Status of the operation (always 'success' for this model)",
        examples=["success"]
    )
    message: str = Field(
        ..., 
        description="Detailed success message with operation results",
        examples=["Content for sample_document saved and ingested successfully. Document is now searchable in the hybrid search system."]
    )


class FileResponse(BaseModel):
    """Model for file upload responses with file type detection"""
    filename: str = Field(
        ..., 
        description="Original name of the uploaded file",
        examples=["financial_report.xlsx"]
    )
    file_path: str = Field(
        ..., 
        description="Server path where the file is stored",
        examples=["uploaded_files/financial_report.xlsx"]
    )
    file_type: str = Field(
        default="document", 
        description="Detected file type: 'excel', 'csv', or 'document'",
        examples=["excel"]
    )
    is_excel_csv: bool = Field(
        default=False, 
        description="True if file is Excel (.xlsx/.xls) or CSV, False for other documents",
        examples=[True]
    )
    message: str = Field(
        default="File uploaded successfully", 
        description="Upload status message with next steps guidance",
        examples=["EXCEL file uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch for comprehensive search or /querypandas for DataFrame queries."]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "sales_data.xlsx",
                "file_path": "uploaded_files/sales_data.xlsx",
                "file_type": "excel",
                "is_excel_csv": True,
                "message": "EXCEL file uploaded successfully. Use /parsefile and /ingestdocuments to process, then /hybridsearch for comprehensive search or /querypandas for DataFrame queries."
            }
        }
    )


class FilesListResponse(BaseModel):
    """Model for file listing responses from various directories"""
    files: List[str] = Field(
        ..., 
        description="List of file names in the requested directory",
        examples=[["document1.pdf", "spreadsheet.xlsx", "data.csv", "report.docx"]]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "files": ["financial_report.pdf", "sales_data.xlsx", "customer_list.csv"]
            }
        }
    ) 