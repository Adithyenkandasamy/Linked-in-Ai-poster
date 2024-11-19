import os
import re
from PIL import Image
from linkedin_api import Linkedin  # A hypothetical library for LinkedIn API interaction
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("github")
linkedin_username = os.getenv("linkedin_username")
linkedin_password = os.getenv("linkedin_password")

# Initialize OpenAI
openai.api_key = openai_api_key
 Load environment variables
load_dotenv()
token = os.getenv("github_key")
endpoint = "https://models.inference.ai.azure.com"
model_name = "gpt-4o"

def initialize_openai_client():
    """Initialize and return OpenAI client"""
    openai.api_key = token
    openai.api_base = endpoint
    return openai

# Authenticate LinkedIn API
linkedin = Linkedin(linkedin_username, linkedin_password)

def initialize_openai_client():
    """Initialize and return OpenAI client."""
    return openai

def generate_article_prompt(client, topic, target_audience):
    """Generate a LinkedIn article prompt using OpenAI."""
    try:
        prompt = f"""
        Write a professional and engaging LinkedIn article about {topic} aimed at {target_audience}.
        Structure the content with a captivating introduction, informative body, and a clear conclusion.
        Keep the tone professional yet approachable. Provide value to readers in the field. Format the output with clear section headings and bullet points where necessary.
        """
        
        response = client.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert LinkedIn content writer. Create an article as described.",
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        )

        article = response.choices[0].message.content.strip()
        return article
    except Exception as e:
        print(f"Error generating article prompt: {e}")
        return None

def attach_image(image_path):
    """Validate and prepare an image for LinkedIn post."""
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return None
    
    try:
        with Image.open(image_path) as img:
            img.verify()  # Check if the file is a valid image
            return image_path
    except Exception as e:
        print(f"Error validating image: {e}")
        return None

def post_to_linkedin(topic, target_audience, image_path):
    """Create and post an article on LinkedIn."""
    client = initialize_openai_client()

    print("Generating LinkedIn article...")
    article_content = generate_article_prompt(client, topic, target_audience)

    if not article_content:
        print("Failed to generate article content.")
        return

    print("Article content generated successfully!")
    print(article_content)

    confirm = input("\nDo you want to post this article to LinkedIn? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Post cancelled.")
        return

    # Validate and prepare image
    if image_path:
        validated_image = attach_image(image_path)
        if not validated_image:
            print("Skipping image due to validation issues.")
            validated_image = None
    else:
        validated_image = None

    try:
        print("Posting to LinkedIn...")
        post_content = {
            "title": topic,
            "content": article_content,
        }
        
        # Add image if available
        if validated_image:
            post_content["image"] = validated_image

        linkedin.submit_post(**post_content)
        print("Article posted successfully on LinkedIn!")
    except Exception as e:
        print(f"Error posting to LinkedIn: {e}")

def main():
    try:
        # Get article details from user
        topic = input("Enter the topic for your LinkedIn article: ").strip()
        target_audience = input("Who is the target audience? (e.g., professionals, developers, marketers): ").strip()
        image_path = input("Enter the full path of the image to include (or press Enter to skip): ").strip()

        if not image_path:
            image_path = None

        post_to_linkedin(topic, target_audience, image_path)

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
