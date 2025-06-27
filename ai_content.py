# gemini_content.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_linkedin_post(topic: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")  # or use gemini-1.5-pro
        prompt = f"Write a short, professional LinkedIn post (max 100 words) about: '{topic}', with a call to action."

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return "⚠️ AI failed to generate content. Please try again."
