# gemini_ai.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def generate_post(prompt: str) -> str:
    """
    Get a response from GitHub's AI model
    
    Args:
        prompt (str): The user's input prompt
        
    Returns:
        str: The AI's response
    """
    try:
        # Initialize the GitHub AI client
        github_ai = GitHubAI(
            token=os.getenv("GITHUB_TOKEN"),
            model="gpt-4"  # or any other supported model
        )
        
        # Get the response
        response = github_ai.complete(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error getting AI response: {str(e)}"

