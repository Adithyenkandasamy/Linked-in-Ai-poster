from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
def generate_post(content):
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=content+" also remove all *symbols in the artcile and in the sub headings plzamek it for linkedin and dont tell heres ur likethat only give the article "
    )
    return response.text

