from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
import pathlib

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4.1-mini", 
                 api_key=OPENAI_API_KEY)

QUESTION_GEN_PROMPT = """
You are a helpful assistant that generates questions based on the given text.

You are given a text and you need to generate {number_of_questions} questions based on the text.

Read the text carefully and generate questions that are relevant and contextually correct to the text.

Return ONLY a JSON array of questions, e.g. [\"Question 1\", \"Question 2\", ...]. Do not include any other text, explanation, or formatting.

{text}

"""

def generate_questions(text, number_of_questions=10):
    prompt = QUESTION_GEN_PROMPT.format(text=text, 
                                        number_of_questions=number_of_questions)
    response = llm.invoke(prompt)
    return response.content

# Test block commented out
# if __name__ == "__main__":
#     from file_util_enhanced import load_markdown_file
#     base_dir = pathlib.Path(__file__).parent
#     # Assuming a test file exists for manual testing if needed
#     test_file_path = base_dir / "parsed_files" / "Sample1.md"
#     text_content, metadata = load_markdown_file(test_file_path)
#     questions = generate_questions(text_content)
#     print(questions)