from typing import List, Dict, Any, Optional
import json

from .gemma_client import GemmaClient
from .langgraph_workflow import BlogAgentWorkflow


class BlogAgent:
    """Main blog agent class that orchestrates the workflow"""
    
    def __init__(self, model_name="gemini-2.0-flash", api_key=None):  # Updated default model name
        """Initialize the blog agent with a model and API key"""
        self.Gemma_client = GemmaClient(model_name=model_name, api_key=api_key)  # Changed to GemmaClient
        self.workflow = BlogAgentWorkflow(self.Gemma_client)  # Pass the Gemma_client to workflow
    
    def generate_blog(self, topic: str, files: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate a blog post based on a topic and optional context files
        
        Args:
            topic (str): The blog post topic
            files (list): Optional list of file dictionaries with 'name' and 'content' (base64 encoded)
            
        Returns:
            Dict containing the blog post, recommendations, and other metadata
        """
        # Initialize the state
        initial_state = {
            "messages": [{"role": "user", "content": topic}],
            "blog_outline": {},
            "draft_sections": [],
            "final_content": "",
            "context_data": {"topic": topic, "files": files or []},
            "recommendations": [],
            "error": None
        }
        
        # Run the workflow
        try:
            result = self.workflow.graph.invoke(initial_state)
            
            # Check for errors
            if result["error"]:
                return {
                    "success": False,
                    "error": result["error"],
                    "blog_post": None,
                    "recommendations": [],
                    "outline": {}
                }
            
            # Format the outline for display
            outline_text = ""
            if result["blog_outline"]:
                outline = result["blog_outline"]
                outline_text = f"# Blog Outline: {outline['title']}\n\n"
                outline_text += f"## Introduction\n{outline['introduction']}\n\n"
                
                for i, section in enumerate(outline['sections']):
                    outline_text += f"## Section {i+1}: {section['heading']}\n{section['content_plan']}\n\n"
                
                outline_text += f"## Conclusion\n{outline['conclusion']}"
            
            # Format recommendations
            recommendations_text = "\n".join([f"- {rec}" for rec in result["recommendations"]])
            
            return {
                "success": True,
                "blog_post": result["final_content"],
                "recommendations": recommendations_text,
                "outline": outline_text,
                "title": result["blog_outline"].get("title", "Blog Post"),
                "messages": result["messages"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating blog: {str(e)}",
                "blog_post": None,
                "recommendations": [],
                "outline": {}
            }
