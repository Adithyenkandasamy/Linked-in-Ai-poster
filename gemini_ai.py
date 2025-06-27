# gemini_ai.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def generate_post(topic: str) -> str:
    prompt = f"Write a professional LinkedIn post on the topic: {topic}"
    response = model.generate_content(prompt)
    return response.text.strip()