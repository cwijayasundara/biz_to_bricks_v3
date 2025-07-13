from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
import pathlib

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4.1-mini", 
                 api_key=OPENAI_API_KEY)

FAQ_GEN_PROMPT = """
You are a helpful assistant that generates FAQ (Frequently Asked Questions) based on the given text.

You are given a text and you need to generate {number_of_faqs} FAQ items based on the text.

Read the text carefully and generate FAQ items that are relevant and contextually correct to the text.
Each FAQ should consist of a question and a comprehensive answer based on the document content.

The FAQ should be in the following format:

**Q1: What is the main topic discussed in this document?**
A1: [Comprehensive answer based on the document content]

**Q2: Who are the key stakeholders mentioned?**
A2: [Comprehensive answer based on the document content]

**Q3: What are the main findings or conclusions?**
A3: [Comprehensive answer based on the document content]

Instructions:
- Generate practical questions that someone would commonly ask about this document
- Provide comprehensive answers based solely on the document content
- Use a conversational tone that's easy to understand
- Include specific details and examples from the document when relevant
- Format each FAQ with **Q[number]:** for questions and A[number]: for answers

Return the FAQ items in a well-formatted structure.

{text}

"""

def generate_faq(text, number_of_faqs=5):
    """
    Generate FAQ items based on the given text.
    
    Args:
        text (str): The text content to generate FAQ from
        number_of_faqs (int): Number of FAQ items to generate (default: 5)
    
    Returns:
        str: Generated FAQ content
    """
    prompt = FAQ_GEN_PROMPT.format(text=text, 
                                   number_of_faqs=number_of_faqs)
    response = llm.invoke(prompt)
    return response.content

# Test block commented out
# if __name__ == "__main__":
#     from file_util_enhanced import load_markdown_file
#     base_dir = pathlib.Path(__file__).parent
#     # Assuming a test file exists for manual testing if needed
#     test_file_path = base_dir / "parsed_files" / "Sample1.md"
#     text_content, metadata = load_markdown_file(test_file_path)
#     faqs = generate_faq(text_content)
#     print(faqs) 