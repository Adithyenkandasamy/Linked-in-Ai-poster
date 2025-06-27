import openai
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class AIContentGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI content generator with OpenAI API key.
        
        Args:
            api_key: OpenAI API key. If not provided, will try to get from OPENAI_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please set OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.api_key
    
    def generate_linkedin_post(self, topic: str, tone: str = "professional", length: int = 3) -> str:
        """Generate a LinkedIn post about the given topic.
        
        Args:
            topic: The topic or idea for the LinkedIn post
            tone: The tone of the post (e.g., professional, casual, enthusiastic)
            length: Approximate number of paragraphs (1-5)
            
        Returns:
            str: Generated LinkedIn post content
        """
        # Validate length
        length = max(1, min(5, length))
        
        prompt = f"""Write a {tone} LinkedIn post about "{topic}". 
        The post should be approximately {length} paragraphs long. 
        Include relevant hashtags (3-5) at the end. 
        Make it engaging and professional, suitable for a business audience.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional content creator who writes engaging LinkedIn posts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            
            content = response.choices[0].message.content.strip()
            return content
            
        except Exception as e:
            raise Exception(f"Failed to generate content: {str(e)}")
    
    def optimize_post(self, post: str, improvements: list = None) -> str:
        """Optimize an existing LinkedIn post.
        
        Args:
            post: The original post content
            improvements: List of improvements to make (e.g., ['more engaging', 'add statistics'])
            
        Returns:
            str: Optimized post content
        """
        if improvements is None:
            improvements = ["more engaging", "better structure", "stronger call-to-action"]
            
        improvements_str = ", ".join(improvements)
        
        prompt = f"""Optimize the following LinkedIn post to make it {improvements_str}.
        Keep the core message but improve the language, structure, and engagement.
        Here's the original post:
        
        {post}
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional content editor who optimizes LinkedIn posts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.5,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"Failed to optimize post: {str(e)}")
