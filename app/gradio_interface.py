import gradio as gr
import base64
import tempfile
import os
import time
from typing import List, Dict, Any

from src.blog_agent import BlogAgent


# Initialize the blog agent with your Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # Set your API key as an environment variable
blog_agent = BlogAgent(api_key=GEMINI_API_KEY)


def process_uploaded_files(files):
    """Process uploaded files and convert them to the format needed by the agent"""
    processed_files = []
    
    if files:
        for file in files:
            with open(file.name, 'rb') as f:
                file_content = f.read()
                encoded_content = base64.b64encode(file_content).decode('utf-8')
                processed_files.append({
                    "name": os.path.basename(file.name),
                    "content": encoded_content
                })
    
    return processed_files

def generate_blog(topic, files, progress=gr.Progress()):
    """Generate a blog post and update the progress"""
    if not topic.strip():
        return "Please enter a topic for your blog post.", None, None, None
    
    # Process uploaded files
    processed_files = process_uploaded_files(files)
    
    # Show progress updates
    progress(0, desc="Processing input...")
    time.sleep(0.5)
    
    progress(0.1, desc="Analyzing context files...")
    time.sleep(0.5)
    
    progress(0.2, desc="Creating blog outline...")
    time.sleep(0.5)
    
    progress(0.4, desc="Generating content...")
    time.sleep(0.5)
    
    progress(0.7, desc="Reviewing and finalizing...")
    time.sleep(0.5)
    
    # Generate the blog post
    result = blog_agent.generate_blog(topic, processed_files)
    
    progress(1.0, desc="Done!")
    
    if not result["success"]:
        return f"Error: {result['error']}", None, None, None
    
    return result["blog_post"], result["recommendations"], result["outline"], result["title"]

# Custom CSS for a clean, Gemini-like interface
# Custom CSS for a clean, Gemini-like interface with better text contrast
custom_css = """
:root {
    --primary-color: #8e24aa;
    --secondary-color: #e1bee7;
    --background-color: #f5f5f5;
    --surface-color: #ffffff;
    --text-color: #333333;
    --border-radius: 8px;
    --shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.gradio-container {
    background-color: var(--background-color);
    font-family: 'Google Sans', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.main-header {
    background: linear-gradient(135deg, #8e24aa, #673ab7);
    color: white !important;
    padding: 20px;
    border-radius: var(--border-radius);
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}

.main-header h1, .main-header p {
    color: white !important;
}

.input-section, .output-section {
    background-color: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 20px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
}

.input-section h2, .output-section h2 {
    color: var(--primary-color) !important;
    margin-top: 0;
    font-size: 20px;
}

.generate-button {
    background-color: var(--primary-color) !important;
    color: white !important;
    border: none !important;
    padding: 10px 20px !important;
    font-size: 16px !important;
    border-radius: var(--border-radius) !important;
    cursor: pointer !important;
    transition: background-color 0.3s !important;
}

.generate-button:hover {
    background-color: #7b1fa2 !important;
}

.tabs {
    border-radius: var(--border-radius);
    overflow: hidden;
}

.tab-nav {
    background-color: var(--secondary-color);
}

.tab-nav button {
    color: var(--text-color) !important;
    font-weight: 500;
}

.tab-nav button.selected {
    background-color: var(--primary-color);
    color: white !important;
}

.footer {
    text-align: center;
    padding: 10px;
    color: #666 !important;
    font-size: 14px;
}

/* Critical fix for markdown content */
.prose {
    color: var(--text-color) !important;
}

.prose * {
    color: var(--text-color) !important;
}

.prose h1, .prose h2, .prose h3 {
    color: var(--primary-color) !important;
}

.prose h1 {
    font-size: 24px;
}

.prose h2 {
    font-size: 20px;
}

.prose h3 {
    font-size: 18px;
}

.prose ul, .prose ol {
    padding-left: 20px;
}

.prose li {
    color: var(--text-color) !important;
}

.prose code {
    background-color: #f0f0f0;
    padding: 2px 4px;
    border-radius: 4px;
    color: #d81b60 !important;
}

.prose pre {
    background-color: #f0f0f0;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
}

/* Fix for all text elements */
.gr-form, .gr-form input, .gr-form textarea {
    color: var(--text-color) !important;
}

/* Force all text to have proper contrast */
p, span, div, li, a, label, button {
    color: var(--text-color) !important;
}

/* Only exceptions are specific UI elements */
.main-header *, button.generate-button, .tab-nav button.selected {
    color: white !important;
}
"""


# Create the Gradio interface
with gr.Blocks(css=custom_css) as demo:
    # Header
    with gr.Column(elem_classes="main-header"):
        gr.Markdown("# AI Blogging Agent")
        gr.Markdown("Generate comprehensive, well-structured blog posts with just a topic and optional context files.")
    
    # Input section
    with gr.Column(elem_classes="input-section"):
        gr.Markdown("## Create Your Blog Post")
        
        topic_input = gr.Textbox(
            label="Blog Topic", 
            placeholder="Enter the topic for your blog post (e.g., 'Python Best Practices for Beginners')",
            lines=2
        )
        
        files_input = gr.File(
            label="Upload Context Files (Optional)", 
            file_count="multiple",
            file_types=["pdf", "py", "js", "java", "cpp", "txt", "html", "css"]
        )
        
        generate_button = gr.Button("Generate Blog Post", elem_classes="generate-button")
    
    # Output section
    with gr.Column(elem_classes="output-section"):
        blog_title = gr.Textbox(label="Blog Title", visible=False)
        
        with gr.Tabs(elem_classes="tabs") as tabs:
            with gr.TabItem("Blog Post", id=1):
                blog_output = gr.Markdown(elem_classes="prose")
            
            with gr.TabItem("Recommendations", id=2):
                recommendations_output = gr.Markdown(elem_classes="prose")
            
            with gr.TabItem("Outline", id=3):
                outline_output = gr.Markdown(elem_classes="prose")
    
    # Footer
    with gr.Column(elem_classes="footer"):
        gr.Markdown("Powered by Gemma 3 and LangGraph | Created with ❤️ by AI Enthusiasts")
    
    # Set up the click event
    generate_button.click(
        generate_blog,
        inputs=[topic_input, files_input],
        outputs=[blog_output, recommendations_output, outline_output, blog_title],
    )
    
    # Update the title when it changes
    blog_title.change(
        lambda x: gr.update(label=f"Blog Post: {x}"),
        inputs=[blog_title],
        outputs=[tabs.children[0]]
    )

# Launch the app
if __name__ == "__main__":
    demo.launch(share=True)
