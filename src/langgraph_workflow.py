from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
import json
import re
from langgraph.graph import StateGraph
from .file_processing import process_file
from .gemma_client import GemmaClient

# Define the state structure for the blogging agent
class BlogAgentState(TypedDict):
    messages: Annotated[List[Dict[str, str]], operator.add]
    blog_outline: Dict[str, Any]
    draft_sections: List[Dict[str, str]]
    final_content: str
    context_data: Dict[str, Any]
    recommendations: List[str]
    error: Optional[str]

class BlogAgentWorkflow:
    def __init__(self, gemma_client):
        self.gemma_client = gemma_client
        self.graph = self._build_graph()
    
    def _build_graph(self):
        # Create the graph for the blogging agent
        graph_builder = StateGraph(BlogAgentState)
        
        # Add nodes to the graph
        graph_builder.add_node("process_input", self.process_input_node)
        graph_builder.add_node("analyze_context", self.analyze_context_node)
        graph_builder.add_node("create_outline", self.create_outline_node)
        graph_builder.add_node("generate_sections", self.generate_sections_node)
        graph_builder.add_node("review_content", self.review_content_node)
        graph_builder.add_node("finalize_blog", self.finalize_blog_node)
        
        # Define the workflow
        graph_builder.add_edge("process_input", "analyze_context")
        graph_builder.add_edge("analyze_context", "create_outline")
        graph_builder.add_edge("create_outline", "generate_sections")
        graph_builder.add_edge("generate_sections", "review_content")
        graph_builder.add_edge("review_content", "finalize_blog")
        
        # Set the entry and exit points
        graph_builder.set_entry_point("process_input")
        graph_builder.set_finish_point("finalize_blog")
        
        # Compile the graph
        return graph_builder.compile()
    
    def process_input_node(self, state: BlogAgentState) -> BlogAgentState:
        """Process the initial input and extract the topic"""
        try:
            # Extract the user's message
            user_message = next((msg for msg in state["messages"] if msg["role"] == "user"), None)
            
            if not user_message:
                state["error"] = "No user message found in the input."
                return state
            
            # Extract topic and file information
            content = user_message["content"]
            
            # Initialize context_data if not present
            if "context_data" not in state or not state["context_data"]:
                state["context_data"] = {
                    "topic": content,
                    "files": []
                }
            else:
                state["context_data"]["topic"] = content
            
            # Add a confirmation message
            new_message = {
                "role": "assistant", 
                "content": f"I'll create a blog post about '{content}'. Processing any attached files..."
            }
            
            return {
                **state,
                "messages": state["messages"] + [new_message]
            }
        except Exception as e:
            state["error"] = f"Error in process_input_node: {str(e)}"
            return state
    
    def analyze_context_node(self, state: BlogAgentState) -> BlogAgentState:
        """Analyze context files if provided"""
        try:
            # Check if there are any files to process
            if "files" in state["context_data"] and state["context_data"]["files"]:
                file_analyses = []
                
                for file_info in state["context_data"]["files"]:
                    file_name = file_info["name"]
                    file_content = base64.b64decode(file_info["content"])
                    
                    analysis = process_file(file_content, file_name)
                    file_analyses.append({
                        "file_name": file_name,
                        "analysis": analysis
                    })
                
                state["context_data"]["file_analyses"] = file_analyses
                
                # Add a message about processed files
                new_message = {
                    "role": "assistant", 
                    "content": f"I've analyzed {len(file_analyses)} file(s) and will incorporate relevant information into the blog post."
                }
                
                return {
                    **state,
                    "messages": state["messages"] + [new_message]
                }
            else:
                # No files to process
                new_message = {
                    "role": "assistant", 
                    "content": "No context files provided. I'll create the blog post based on the topic alone."
                }
                
                return {
                    **state,
                    "messages": state["messages"] + [new_message]
                }
        except Exception as e:
            state["error"] = f"Error in analyze_context_node: {str(e)}"
            return state
    
    def create_outline_node(self, state: BlogAgentState) -> BlogAgentState:
        """Create an outline for the blog post"""
        try:
            topic = state["context_data"]["topic"]
            
            # Prepare context information from files if available
            context_info = ""
            if "file_analyses" in state["context_data"]:
                context_info = "Based on the following file analyses:\n\n"
                for file_analysis in state["context_data"]["file_analyses"]:
                    # Truncate very long analyses to avoid token limits
                    analysis = file_analysis["analysis"]
                    if len(analysis) > 2000:
                        analysis = analysis[:2000] + "... [truncated]"
                    context_info += f"File: {file_analysis['file_name']}\n{analysis}\n\n"
            
            # Create the prompt for outline generation
            system_prompt = """You are an expert blog post writer. 
            Create a detailed outline for a blog post on the given topic.
            The outline should include:
            1. An engaging title
            2. A brief introduction
            3. 4-6 main sections with descriptive headings
            4. A conclusion section
            
            Format the outline as a JSON object with the following structure:
            {
                "title": "Blog Post Title",
                "introduction": "Brief description of the introduction",
                "sections": [
                    {"heading": "Section 1 Heading", "content_plan": "What this section will cover"},
                    {"heading": "Section 2 Heading", "content_plan": "What this section will cover"}
                ],
                "conclusion": "Brief description of the conclusion"
            }
            
            Ensure the outline is comprehensive and well-structured."""
            
            messages = [
                {"role": "user", "content": f"Create a blog post outline about: {topic}\n\n{context_info}"}
            ]
            
            prompt = self.gemma_client.create_prompt(system_prompt, messages)
            outline_response = self.gemma_client.generate(prompt, max_tokens=1500)
            
            # Extract JSON from the response
            try:
                # Find JSON object in the response
                json_match = re.search(r'({.*})', outline_response, re.DOTALL)
                if json_match:
                    outline_json = json.loads(json_match.group(1))
                else:
                    # If no JSON found, try to parse the entire response
                    outline_json = json.loads(outline_response)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a structured outline manually
                outline_parts = outline_response.split('\n')
                title = next((line for line in outline_parts if line.strip()), "Blog Post")
                
                outline_json = {
                    "title": title,
                    "introduction": "Introduction to the topic",
                    "sections": [{"heading": f"Section {i}", "content_plan": "Content for this section"} 
                                for i in range(1, 4)],
                    "conclusion": "Conclusion and summary"
                }
            
            # Add a message with the outline
            outline_message = {
                "role": "assistant",
                "content": f"I've created an outline for the blog post titled: **{outline_json['title']}**\n\n"
                          f"The post will have {len(outline_json['sections'])} main sections."
            }
            
            return {
                **state,
                "blog_outline": outline_json,
                "messages": state["messages"] + [outline_message]
            }
        except Exception as e:
            state["error"] = f"Error in create_outline_node: {str(e)}"
            return state
    
    def generate_sections_node(self, state: BlogAgentState) -> BlogAgentState:
        try:
            outline = state["blog_outline"]
            topic = state["context_data"]["topic"]
            
            # Prepare context information
            context_info = ""
            if "file_analyses" in state["context_data"]:
                for file_analysis in state["context_data"]["file_analyses"]:
                    # Use a shorter version for section generation to save tokens
                    analysis = file_analysis["analysis"]
                    if len(analysis) > 1000:
                        analysis = analysis[:1000] + "... [truncated]"
                    context_info += f"File: {file_analysis['file_name']}\n{analysis}\n\n"
            
            # Generate introduction
            system_prompt = """You are an expert blog writer. Write an engaging introduction for a blog post.
            The introduction should:
            1. Hook the reader with an interesting opening
            2. Introduce the topic clearly
            3. Provide a brief overview of what the blog post will cover
            4. Be approximately 150-200 words
            
            Write in a conversational, informative style. Use markdown formatting where appropriate."""
            
            messages = [
                {"role": "user", "content": f"Write an introduction for a blog post titled '{outline['title']}' about {topic}.\n\nIntroduction plan: {outline['introduction']}\n\n{context_info if context_info else ''}"}
            ]
            
            prompt = self.gemma_client.create_prompt(system_prompt, messages)
            introduction = self.gemma_client.generate(prompt, max_tokens=500)
            
            # Store the introduction
            draft_sections = [
                {"type": "introduction", "content": introduction}
            ]
            
            # Generate each main section
            for i, section in enumerate(outline["sections"]):
                system_prompt = """You are an expert blog writer. Write a detailed section for a blog post.
                The section should:
                1. Start with a clear heading (use markdown ## for the heading)
                2. Provide valuable, accurate information on the topic
                3. Include examples, data, or anecdotes where relevant
                4. Be well-structured with paragraphs and subheadings if needed
                5. Be approximately 300-400 words
                
                Write in a conversational, informative style. Use markdown formatting where appropriate."""
                
                messages = [
                    {"role": "user", "content": f"Write section {i+1} for a blog post titled '{outline['title']}' about {topic}.\n\nSection heading: {section['heading']}\nContent plan: {section['content_plan']}\n\n{context_info if context_info else ''}"}
                ]
                
                prompt = self.gemma_client.create_prompt(system_prompt, messages)
                section_content = self.gemma_client.generate(prompt, max_tokens=1000)
                
                # Store the section
                draft_sections.append(
                    {"type": "section", "heading": section['heading'], "content": section_content}
                )
            
            # Generate conclusion
            system_prompt = """You are an expert blog writer. Write a compelling conclusion for a blog post.
            The conclusion should:
            1. Summarize the key points covered in the blog post
            2. Provide final thoughts or recommendations
            3. End with a call to action or thought-provoking statement
            4. Be approximately 150-200 words
            
            Write in a conversational, informative style. Use markdown formatting where appropriate."""
            
            messages = [
                {"role": "user", "content": f"Write a conclusion for a blog post titled '{outline['title']}' about {topic}.\n\nConclusion plan: {outline['conclusion']}\n\n{context_info if context_info else ''}"}
            ]
            
            prompt = self.gemma_client.create_prompt(system_prompt, messages)
            conclusion = self.gemma_client.generate(prompt, max_tokens=500)
            
            # Store the conclusion
            draft_sections.append(
                {"type": "conclusion", "content": conclusion}
            )
            
            # Add a message about the generated sections
            sections_message = {
                "role": "assistant",
                "content": f"I've written all sections for the blog post '{outline['title']}', including an introduction, {len(outline['sections'])} main sections, and a conclusion."
            }
            
            return {
                **state,
                "draft_sections": draft_sections,
                "messages": state["messages"] + [sections_message]
            }
        except Exception as e:
            state["error"] = f"Error in generate_sections_node: {str(e)}"
            return state
    
    def review_content_node(self, state: BlogAgentState) -> BlogAgentState:
        """Review the generated content and provide recommendations"""
        try:
            outline = state["blog_outline"]
            draft_sections = state["draft_sections"]
            
            # Combine sections for review with clear formatting
            combined_content = f"# {outline['title']}\n\n"
            
            for section in draft_sections:
                if section["type"] == "introduction":
                    combined_content += section["content"] + "\n\n"
                elif section["type"] == "section":
                    # Ensure section headings are properly formatted
                    if not section["content"].startswith("##"):
                        combined_content += f"## {section['heading']}\n\n"
                    combined_content += f"{section['content']}\n\n"
                elif section["type"] == "conclusion":
                    combined_content += "## Conclusion\n\n" + section["content"] + "\n\n"
            
            # Generate recommendations
            system_prompt = """You are an expert blog editor. Review the blog post and provide specific recommendations for improvement.
            Focus on:
            1. Content quality and accuracy
            2. Structure and flow
            3. Engagement and readability
            4. SEO optimization
            
            Provide 3-5 specific, actionable recommendations. Format each recommendation as a bullet point."""
            
            messages = [
                {"role": "user", "content": f"Review this blog post and provide recommendations for improvement:\n\n{combined_content}"}
            ]
            
            prompt = self.gemma_client.create_prompt(system_prompt, messages)
            recommendations_text = self.gemma_client.generate(prompt, max_tokens=800)
            
            # Extract recommendations as a list
            recommendations = [line.strip() for line in recommendations_text.split('\n') if line.strip().startswith('-') or line.strip().startswith('*')]
            
            if not recommendations:
                # If no bullet points found, try to split by numbers
                recommendations = re.findall(r'\d+\.\s+(.*?)(?=\d+\.|$)', recommendations_text, re.DOTALL)
                recommendations = [rec.strip() for rec in recommendations if rec.strip()]
            
            if not recommendations:
                # If still no recommendations found, use the whole text
                recommendations = [recommendations_text]
            
            # Format recommendations with clear bullet points
            formatted_recommendations = "# Content Recommendations\n\n"
            for rec in recommendations:
                formatted_recommendations += f"- {rec}\n"
            
            # Add a message with the recommendations
            review_message = {
                "role": "assistant",
                "content": f"I've reviewed the blog post and have the following recommendations:\n\n" + "\n".join([f"- {rec}" for rec in recommendations])
            }
            
            return {
                **state,
                "recommendations": recommendations,
                "messages": state["messages"] + [review_message],
                "final_content": combined_content  # Store the combined content for finalization
            }
        except Exception as e:
            state["error"] = f"Error in review_content_node: {str(e)}"
            return state

    
    def finalize_blog_node(self, state: BlogAgentState) -> BlogAgentState:
        """Finalize the blog post with improvements based on recommendations"""
        try:
            # The final content is already stored in the state from the review step
            # We could implement additional improvements here based on recommendations
            
            final_message = {
                "role": "assistant",
                "content": f"Here's your completed blog post about '{state['context_data']['topic']}'."
            }
            
            return {
                **state,
                "messages": state["messages"] + [final_message]
            }
        except Exception as e:
            state["error"] = f"Error in finalize_blog_node: {str(e)}"
            return state
