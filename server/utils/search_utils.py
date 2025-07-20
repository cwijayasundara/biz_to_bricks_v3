"""
Search utility functions for the Document Processing API.
"""

import logging
import os
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from config import LLM_MODEL_NAME

logger = logging.getLogger(__name__)

# Initialize LLM for result comparison
llm_openai = ChatOpenAI(model=LLM_MODEL_NAME, api_key=os.getenv("OPENAI_API_KEY"))


def compare_and_rerank_results(query: str, document_result: str, pandas_results: List[Dict]) -> Dict[str, Any]:
    """
    Compare results from document search and pandas agent, then return the most suitable result.
    
    Args:
        query: The original search query
        document_result: Result from Pinecone/BM25 document search
        pandas_results: List of results from pandas agent search
        
    Returns:
        Dictionary with the best result and explanation
    """
    try:
        logger.info(f"🤖 Comparing and reranking results for query: {query}")
        
        # Handle case where we have no results
        if not document_result and not pandas_results:
            logger.info("❌ No results from either search method")
            return {
                "best_result": "No results found for your query.",
                "source": "none",
                "explanation": "Neither document search nor data analysis found relevant information.",
                "comparison_performed": True
            }
        
        # Handle case where we only have document results
        if document_result and not pandas_results:
            logger.info("📄 Only document search results available")
            return {
                "best_result": document_result,
                "source": "document_search",
                "explanation": "Only document search found relevant information.",
                "comparison_performed": False
            }
        
        # Handle case where we only have pandas results
        if not document_result and pandas_results:
            logger.info("📊 Only pandas agent results available")
            # If multiple pandas results, combine them
            combined_pandas = "\n\n".join([
                f"**{result['filename']} ({result['file_type'].upper()}):**\n{result['answer']}"
                for result in pandas_results
            ])
            return {
                "best_result": combined_pandas,
                "source": "pandas_agent",
                "explanation": "Only data analysis found relevant information.",
                "comparison_performed": False
            }
        
        # We have both types of results - perform intelligent comparison
        logger.info("🤖 Both search methods found results - performing AI comparison")
        
        # Prepare pandas results for comparison
        pandas_summary = "\n\n".join([
            f"**{result['filename']} ({result['file_type'].upper()}):**\n{result['answer']}"
            for result in pandas_results
        ])
        
        # Create comparison prompt
        comparison_prompt = f"""
You are an AI assistant that evaluates search results to determine which is most relevant and useful for answering a user's query.

**User Query:** {query}

**Document Search Result (from text documents):**
{document_result}

**Data Analysis Result (from Excel/CSV files):**
{pandas_summary}

**Task:** Analyze both results and determine which one better answers the user's query. Consider:
1. Relevance to the specific question asked
2. Accuracy and specificity of the answer
3. Completeness of the information provided
4. Whether the query is better suited for text analysis or data analysis

**Instructions:**
- If the query is asking for specific data, calculations, or statistical information, prefer the data analysis result
- If the query is asking for conceptual information, explanations, or general knowledge, prefer the document search result
- If both are equally relevant, choose the one that provides more specific and actionable information
- If one result is clearly irrelevant or doesn't answer the query, choose the other

**Response Format:**
Choose one of: "document_search", "pandas_agent", or "combined"

If "combined", merge the best parts of both results.
If "document_search" or "pandas_agent", return the chosen result.

**Your Choice:** [document_search/pandas_agent/combined]

**Best Answer:** [Provide the best answer based on your choice]

**Explanation:** [Brief explanation of why you chose this result]
"""
        
        # Get LLM comparison
        response = llm_openai.invoke(comparison_prompt)
        response_text = response.content
        
        # Parse the response
        lines = response_text.strip().split('\n')
        choice = "document_search"  # default
        best_answer = document_result  # default
        explanation = "Default selection"
        
        for i, line in enumerate(lines):
            if "**Your Choice:**" in line:
                choice_line = line.split("**Your Choice:**")[1].strip()
                if "pandas_agent" in choice_line.lower():
                    choice = "pandas_agent"
                elif "combined" in choice_line.lower():
                    choice = "combined"
                elif "document_search" in choice_line.lower():
                    choice = "document_search"
            
            elif "**Best Answer:**" in line:
                # Get everything after this line until "**Explanation:**"
                answer_parts = []
                for j in range(i + 1, len(lines)):
                    if "**Explanation:**" in lines[j]:
                        break
                    answer_parts.append(lines[j])
                if answer_parts:
                    best_answer = "\n".join(answer_parts).strip()
            
            elif "**Explanation:**" in line:
                explanation = line.split("**Explanation:**")[1].strip()
        
        # Apply the choice
        if choice == "pandas_agent":
            final_result = pandas_summary
            source = "pandas_agent"
        elif choice == "combined":
            final_result = best_answer if best_answer != document_result else f"{document_result}\n\n**Data Analysis:**\n{pandas_summary}"
            source = "combined"
        else:  # document_search
            final_result = document_result
            source = "document_search"
        
        logger.info(f"🎯 AI chose: {choice} | Source: {source}")
        
        return {
            "best_result": final_result,
            "source": source,
            "explanation": explanation,
            "comparison_performed": True,
            "ai_choice": choice
        }
        
    except Exception as e:
        logger.error(f"❌ Error in result comparison: {str(e)}")
        # Fallback to document result or pandas result
        if document_result:
            return {
                "best_result": document_result,
                "source": "document_search",
                "explanation": "Comparison failed, defaulting to document search result.",
                "comparison_performed": False,
                "error": str(e)
            }
        elif pandas_results:
            combined_pandas = "\n\n".join([
                f"**{result['filename']} ({result['file_type'].upper()}):**\n{result['answer']}"
                for result in pandas_results
            ])
            return {
                "best_result": combined_pandas,
                "source": "pandas_agent", 
                "explanation": "Comparison failed, defaulting to data analysis result.",
                "comparison_performed": False,
                "error": str(e)
            }
        else:
            return {
                "best_result": "No results found for your query.",
                "source": "none",
                "explanation": "Comparison failed and no results available.",
                "comparison_performed": False,
                "error": str(e)
            } 