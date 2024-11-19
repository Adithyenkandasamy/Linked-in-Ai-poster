import os
from PIL import Image
from linkedin_api import Linkedin  # Hypothetical LinkedIn API interaction library
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
linkedin_username_or_phone = os.getenv("LINKEDIN_USERNAME_OR_PHONE")
linkedin_password = os.getenv("LINKEDIN_PASSWORD")
openai_endpoint = os.getenv("OPENAI_ENDPOINT", "https://models.inference.ai.azure.com")
model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

# Initialize OpenAI client
def initialize_openai_client():
    """Initialize and return OpenAI client."""
    openai.api_key = openai_api_key
    openai.api_base = openai_endpoint
    return openai

# Authenticate LinkedIn API
def authenticate_linkedin():
    """Authenticate and return LinkedIn client."""
    try:
        linkedin = Linkedin(linkedin_username_or_phone, linkedin_password)
        print("LinkedIn login successful.")
        return linkedin
    except Exception as e:
        print(f"Error logging into LinkedIn: {e}")
        exit()

def generate_article(client, topic, target_audience):
    """Generate a LinkedIn article using OpenAI."""
    try:
        prompt = f"""
        Write a professional and engaging LinkedIn article about {topic} aimed at {target_audience}.
        Structure the content with a captivating introduction, informative body, and a clear conclusion.
        Keep the tone professional yet approachable. Provide value to readers in the field.
        Format the output with clear section headings and bullet points where necessary.
        """

        response = client.ChatCompletion.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert LinkedIn content writer. Create an article as described.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )

        article = response.choices[0].message.content.strip()
        return article
    except Exception as e:
        print(f"Error generating article: {e}")
        return None

def validate_image(image_path):
    """Validate the provided image file."""
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

def post_to_linkedin(linkedin, topic, target_audience, image_path):
    """Generate and post an article to LinkedIn."""
    client = initialize_openai_client()

    print("Generating LinkedIn article...")
    article_content = generate_article(client, topic, target_audience)

    if not article_content:
        print("Failed to generate article content.")
        return

    print("\nGenerated Article Content:\n")
    print(article_content)

    confirm = input("\nDo you want to post this article to LinkedIn? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Post cancelled.")
        return

    # Validate image
    validated_image = validate_image(image_path) if image_path else None
    if image_path and not validated_image:
        print("Skipping image due to validation issues.")

    try:
        print("Posting to LinkedIn...")
        post_content = {"title": topic, "content": article_content}
        if validated_image:
            post_content["image"] = validated_image

        linkedin.submit_post(**post_content)
        print("Article posted successfully on LinkedIn!")
    except Exception as e:
        print(f"Error posting to LinkedIn: {e}")

def main():
    try:
        # Authenticate LinkedIn
        linkedin = authenticate_linkedin()

        # Get article details from user
        topic = input("Enter the topic for your LinkedIn article: ").strip()
        target_audience = input("Who is the target audience? (e.g., professionals, developers, marketers): ").strip()
        image_path = input("Enter the full path of the image to include (or press Enter to skip): ").strip()

        post_to_linkedin(linkedin, topic, target_audience, image_path if image_path else None)

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
