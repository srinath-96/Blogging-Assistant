import google.generativeai as genai

class GemmaClient:
    def __init__(self, model_name="gemini-2.0-flash", api_key=None):
        """Initialize the Gemini client with model name and API key"""
        self.model_name = model_name
        self.api_key = api_key
        
        if api_key:
            genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel(model_name)
    
    def generate(self, prompt, max_tokens=1000, temperature=0.7):
        """Generate text using Gemini model"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            return response.text
        except Exception as e:
            return f"Error generating content: {str(e)}"
    
    def create_prompt(self, system_prompt, messages):
        """Create a formatted prompt for Gemini"""
        prompt = f"{system_prompt}\n\n"
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
            elif role == "system":
                prompt += f"System: {content}\n\n"
        
        prompt += "Assistant: "
        return prompt
