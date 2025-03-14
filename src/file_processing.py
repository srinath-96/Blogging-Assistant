import PyPDF2
import base64
from io import BytesIO
import re
import os
def extract_text_from_pdf(pdf_content):
    """Extract text from a PDF file"""
    try:
        pdf_file = BytesIO(pdf_content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def process_code_file(code_content, file_extension):
    """Process a code file based on its extension"""
    try:
        code_text = code_content.decode('utf-8')
        
        # Extract docstrings, function definitions, and class definitions
        docstrings = re.findall(r'"""(.*?)"""', code_text, re.DOTALL)
        functions = re.findall(r'def\s+(\w+)\s*\((.*?)\):', code_text)
        classes = re.findall(r'class\s+(\w+)(?:\((.*?)\))?:', code_text)
        
        summary = f"# Code Analysis\n\n"
        summary += f"## File Type: {file_extension}\n\n"
        
        if docstrings:
            summary += "## Docstrings:\n"
            for doc in docstrings:
                summary += f"- {doc.strip()}\n"
            summary += "\n"
        
        if functions:
            summary += "## Functions:\n"
            for func_name, params in functions:
                summary += f"- `{func_name}({params})`\n"
            summary += "\n"
        
        if classes:
            summary += "## Classes:\n"
            for class_name, inherit in classes:
                summary += f"- `{class_name}`"
                if inherit:
                    summary += f" (inherits from: {inherit})"
                summary += "\n"
            summary += "\n"
        
        summary += "## Full Code:\n``````"
        
        return summary
    except Exception as e:
        return f"Error processing code file: {str(e)}"

def process_file(file_content, file_name):
    """Process different types of files"""
    file_extension = file_name.split('.')[-1].lower()
    
    if file_extension == 'pdf':
        return extract_text_from_pdf(file_content)
    elif file_extension in ['py', 'js', 'java', 'cpp', 'c', 'go', 'rs', 'ts', 'html', 'css']:
        return process_code_file(file_content, file_extension)
    else:
        # For text files or other formats
        try:
            return file_content.decode('utf-8')
        except:
            return "Binary file format not supported for detailed analysis."

def encode_file(file_path):
    """Encode a file to base64"""
    with open(file_path, 'rb') as file:
        file_content = file.read()
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        return {
            "name": os.path.basename(file_path),
            "content": encoded_content
        }
