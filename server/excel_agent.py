#!/usr/bin/env python3
"""
Excel/CSV Agent using LangChain Pandas Agent
Processes Excel/CSV files directly with pandas without saving to database
"""
import pandas as pd
import os
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
from dotenv import load_dotenv
from pathlib import Path
from config import LLM_MODEL_NAME

# Load environment variables
load_dotenv()

class ExcelAgent:
    """
    An Excel/CSV agent using LangChain's pandas agent
    """
    
    def __init__(self, file_path: str, model: str = LLM_MODEL_NAME):
        """
        Initialize the Excel Agent
        
        Args:
            file_path: Path to the Excel or CSV file
            model: OpenAI model to use (default: from config)
        """
        self.file_path = file_path
        self.model = model
        
        # Load data into pandas DataFrame
        self.df = self._load_data()
        
        # Initialize LangChain OpenAI LLM
        self.llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create pandas agent with enhanced instructions
        self.agent = create_pandas_dataframe_agent(
            self.llm,
            self.df,
            verbose=True,
            agent_type="tool-calling",
            allow_dangerous_code=True,
            max_iterations=10,
            return_intermediate_steps=False,
            prefix="""
You are working with a pandas DataFrame called `df`. 
You have access to a Python REPL environment where you can execute code.

IMPORTANT INSTRUCTIONS:
1. ALWAYS execute Python code to answer questions - never just provide code suggestions
2. Use the python_repl_ast tool to run code and get actual results
3. The DataFrame is already loaded as `df` - you can use it directly
4. Always provide the actual computed result, not just code examples
5. When asked for counts, sums, or specific data, execute the code and return the real numbers

Available DataFrame info:
- Shape: {shape}
- Columns: {columns}

Always execute code to get real answers!
""".format(shape=self.df.shape, columns=list(self.df.columns))
        )
    
    def _detect_file_format(self) -> str:
        """Detect the actual file format by examining file content"""
        try:
            # Try to read first few lines to detect format
            with open(self.file_path, 'rb') as f:
                first_bytes = f.read(512)
            
            # Check for Excel signatures
            if first_bytes.startswith(b'PK\x03\x04'):  # ZIP signature (xlsx)
                return 'xlsx'
            elif first_bytes.startswith(b'\xd0\xcf\x11\xe0'):  # OLE signature (xls)
                return 'xls'
            else:
                # Try to decode as text and check for CSV patterns
                try:
                    text_content = first_bytes.decode('utf-8', errors='ignore')
                    # Look for CSV-like patterns (commas, quotes, newlines)
                    if ',' in text_content and '\n' in text_content:
                        return 'csv'
                except:
                    pass
                
                # Default based on extension if detection fails
                if self.file_path.endswith('.csv'):
                    return 'csv'
                elif self.file_path.endswith('.xlsx'):
                    return 'xlsx'
                elif self.file_path.endswith('.xls'):
                    return 'xls'
                else:
                    return 'unknown'
        except Exception as e:
            print(f"Warning: Could not detect file format, using extension: {e}")
            # Fallback to extension-based detection
            if self.file_path.endswith('.csv'):
                return 'csv'
            elif self.file_path.endswith('.xlsx'):
                return 'xlsx'
            elif self.file_path.endswith('.xls'):
                return 'xls'
            else:
                return 'unknown'

    def _load_data(self) -> pd.DataFrame:
        """Load data from CSV or Excel file"""
        try:
            # Detect actual file format
            actual_format = self._detect_file_format()
            print(f"📋 File extension: {Path(self.file_path).suffix}")
            print(f"🔍 Detected format: {actual_format}")
            
            # Load data based on detected format
            if actual_format == 'csv':
                df = pd.read_csv(self.file_path)
            elif actual_format in ['xlsx', 'xls']:
                # Try different engines for Excel files to handle various formats
                df = None
                engines_to_try = ['openpyxl', 'xlrd']
                
                for engine in engines_to_try:
                    try:
                        if actual_format == 'xlsx':
                            # For .xlsx files, prefer openpyxl
                            df = pd.read_excel(self.file_path, engine='openpyxl')
                        else:
                            # For .xls files, try xlrd first, then openpyxl
                            if engine == 'xlrd':
                                df = pd.read_excel(self.file_path, engine='xlrd')
                            else:
                                df = pd.read_excel(self.file_path, engine='openpyxl')
                        print(f"✅ Successfully read with {engine} engine")
                        break  # If successful, break out of the loop
                    except Exception as engine_error:
                        print(f"Failed to read with {engine} engine: {engine_error}")
                        continue
                
                # If all Excel engines failed, try reading as CSV (common misnamed files)
                if df is None:
                    print("⚠️ Excel engines failed, trying to read as CSV...")
                    try:
                        df = pd.read_csv(self.file_path)
                        print("✅ Successfully read as CSV despite Excel extension")
                    except Exception as csv_error:
                        raise Exception(f"Could not read file as Excel or CSV. Excel error: Failed with all engines. CSV error: {csv_error}")
            else:
                raise ValueError(f"Unsupported file type: {self.file_path} (detected format: {actual_format})")
            
            print(f"✅ Loaded data: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"📊 Columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            raise Exception(f"Error loading file {self.file_path}: {str(e)}")
    
    def query(self, question: str) -> str:
        """
        Query the data using natural language
        
        Args:
            question: Natural language question about the data
            
        Returns:
            Answer from the pandas agent
        """
        try:
            print(f"🤔 Question: {question}")
            
            # Enhance the question to ensure code execution
            enhanced_question = f"""
{question}

IMPORTANT: You must execute Python code using the available tools to answer this question. 
Do not just provide code examples - run the code and give me the actual results.
The DataFrame is available as 'df'. Execute the necessary pandas operations to get the real answer.
"""
            
            result = self.agent.invoke({"input": enhanced_question})
            
            # Extract the output from the agent response
            if isinstance(result, dict):
                answer = result.get("output", str(result))
            else:
                answer = str(result)
            
            # Check if the answer seems to be just code suggestions instead of results
            if ("import pandas" in answer or 
                "df = pd.read" in answer or 
                "you can run" in answer.lower() or
                "in your own python environment" in answer.lower()):
                print("⚠️ Detected code suggestion instead of execution, retrying with more explicit instructions...")
                
                # Try again with even more explicit instructions
                retry_question = f"""
Execute this Python code now and give me the result: {question}
Use the DataFrame 'df' that is already loaded. Run the code and return the actual computed value.
"""
                result = self.agent.invoke({"input": retry_question})
                if isinstance(result, dict):
                    answer = result.get("output", str(result))
                else:
                    answer = str(result)
            
            print(f"🤖 Answer: {answer}")
            return answer
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get a summary of the loaded data"""
        try:
            # Get column information
            column_info = {}
            for col in self.df.columns:
                dtype = str(self.df[col].dtype)
                column_info[col] = {
                    "type": dtype,
                    "is_numeric": self.df[col].dtype.kind in 'biufc'  # boolean, int, uint, float, complex
                }
            
            # Convert all numpy/pandas types to native Python types for JSON serialization
            return {
                "file_path": self.file_path,
                "total_rows": int(len(self.df)),  # Convert to native int
                "total_columns": int(len(self.df.columns)),  # Convert to native int
                "shape": [int(self.df.shape[0]), int(self.df.shape[1])],  # Convert tuple to list of ints
                "columns": list(self.df.columns),
                "dtypes": {col: str(dtype) for col, dtype in self.df.dtypes.items()},
                "column_info": column_info,
                "memory_usage": int(self.df.memory_usage(deep=True).sum()),  # Convert to native int
                "has_null_values": bool(self.df.isnull().any().any())  # Convert to native bool
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_basic_info(self) -> str:
        """Get basic information about the dataset"""
        try:
            info_question = "Provide basic information about this dataset including shape, columns, data types, and a few sample rows"
            return self.query(info_question)
        except Exception as e:
            return f"Error getting basic info: {str(e)}"
    
    def close(self):
        """Close any resources (no-op for pandas agent)"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_excel_agent(file_path: str, model: str = LLM_MODEL_NAME) -> ExcelAgent:
    """
    Factory function to create an Excel Agent
    
    Args:
        file_path: Path to the Excel or CSV file
        model: OpenAI model to use
        
    Returns:
        Configured ExcelAgent instance
    """
    return ExcelAgent(file_path, model)


# Example usage
if __name__ == "__main__":
    # Example with a CSV file
    try:
        # Create a sample CSV for testing
        sample_data = {
            'Name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'Age': [25, 30, 35, 28, 32],
            'City': ['New York', 'London', 'Paris', 'Tokyo', 'Sydney'],
            'Salary': [50000, 60000, 70000, 55000, 65000],
            'Department': ['Engineering', 'Sales', 'Engineering', 'Marketing', 'Sales']
        }
        df = pd.DataFrame(sample_data)
        df.to_csv('sample_data.csv', index=False)
        
        # Create and use the agent
        with create_excel_agent('sample_data.csv') as agent:
            # Example queries
            print("=== Excel Agent with LangChain Pandas Agent Demo ===")
            print(f"Data Summary: {agent.get_data_summary()}")
            
            queries = [
                "What is the average salary?",
                "Who are the people in the Engineering department?",
                "What is the highest salary and who has it?",
                "Show me the first 3 rows of data",
                "What are the basic statistics for all numeric columns?",
                "How many people work in each department?"
            ]
            
            for query in queries:
                print(f"\n🤔 Question: {query}")
                print(f"🤖 Answer: {agent.query(query)}")
        
        # Clean up the test file
        import os
        if os.path.exists('sample_data.csv'):
            os.remove('sample_data.csv')
            print("\n🧹 Cleaned up test file: sample_data.csv")
                
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have set your OPENAI_API_KEY in your environment or .env file") 