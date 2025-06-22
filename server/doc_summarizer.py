from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv
import pathlib

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

llm = init_chat_model("gpt-4.1-mini", 
                      model_provider="openai",
                      api_key=api_key)

prompt = ChatPromptTemplate.from_messages(
    [("system", """Write a concise summary of the following document without losing any important information:
      {context}. 
      Return a fully formatted markdown document.""")]
)

chain = create_stuff_documents_chain(llm, 
                                     prompt)

def summarize_docs(text_content: str):
    """
    Summarize the provided text content.
    """
    # Wrap the raw text into a Document object
    docs = [Document(page_content=text_content, metadata={})]
    # Use chain.invoke with the correct input structure
    result = chain.invoke({"context": docs})
    return result

# Renamed function to reflect it takes text, not a file path
def summarize_text_content(text_content: str):
    """
    Summarize the provided text content.
    """
    return summarize_docs(text_content)

# Test block commented out
# if __name__ == "__main__":
#     from file_util_enhanced import load_markdown_file
#     base_dir = pathlib.Path(__file__).parent
#     # Assuming a test file exists for manual testing if needed
#     test_file_path = base_dir / "parsed_files" / "Sample1.md"
#     text_content, metadata = load_markdown_file(test_file_path)
#     summary = summarize_text_content(text_content)
#     print(summary)

