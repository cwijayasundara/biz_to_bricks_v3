"""
Request models for the Document Processing API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ContentUpdate(BaseModel):
    """Model for content update requests - used to save edited parsed content"""
    content: str = Field(
        ..., 
        description="The edited markdown content to save to parsed files directory",
        examples=["# Sample Document\n\nThis is the edited content with **markdown formatting**.\n\n## Key Points\n- Point 1\n- Point 2"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "# Updated Document\n\nThis is the revised content after editing.\n\n## Summary\n- Updated information\n- Corrected data"
            }
        }
    )


class SearchQuery(BaseModel):
    """Model for search queries - supports both document search and Excel/CSV analysis"""
    query: str = Field(
        ..., 
        description="Natural language search query or question about the data",
        examples=["What is the average salary by department?"]
    )
    debug: bool = Field(
        False, 
        description="Include debug information showing search process and retrieved documents",
        examples=[False]
    )
    source_document: Optional[str] = Field(
        None, 
        description="Optional filename to search within specific document (omit for all documents)",
        examples=["sales_data.xlsx"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "General search across all documents",
                    "value": {
                        "query": "What are the main conclusions about market trends?",
                        "debug": False,
                        "source_document": None
                    }
                },
                {
                    "description": "Targeted document search",
                    "value": {
                        "query": "List all passengers in first class",
                        "debug": False,
                        "source_document": "titanic.csv"
                    }
                },
                {
                    "description": "Excel data analysis with debug",
                    "value": {
                        "query": "Calculate average age and survival rate by passenger class",
                        "debug": True,
                        "source_document": "passenger_data.xlsx"
                    }
                }
            ]
        }
    ) 