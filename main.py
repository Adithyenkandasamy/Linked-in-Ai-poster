import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment Variables
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
ACCESS_TOKEN = None  # Leave as None, will be fetched dynamically

# Step 1: Get Authorization URL
def get_authorization_url():
    url = "https://www.linkedin.com/oauth/v2/authorization"
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "r_liteprofile w_member_social",
    }
    auth_url = requests.Request("GET", url, params=params).prepare().url
    print(f"Authorize the app by visiting this URL: {auth_url}")

# Step 2: Get Access Token
def get_access_token(authorization_code):
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        global ACCESS_TOKEN
        ACCESS_TOKEN = response.json().get("access_token")
        print("Access token retrieved successfully!")
    else:
        print(f"Error fetching access token: {response.json()}")

# Step 3: Post to LinkedIn
def post_to_linkedin(article_text, article_image_url=None):
    if not ACCESS_TOKEN:
        print("Access token not set. Please authenticate first.")
        return

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # Fetch the user URN to identify the author
    profile_url = "https://api.linkedin.com/v2/me"
    profile_response = requests.get(profile_url, headers=headers)
    if profile_response.status_code != 200:
        print(f"Error fetching user profile: {profile_response.json()}")
        return

    person_urn = profile_response.json().get("id")
    author_urn = f"urn:li:person:{person_urn}"

    post_data = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": article_text},
                "shareMediaCategory": "NONE" if not article_image_url else "IMAGE",
                "media": [] if not article_image_url else [
                    {
                        "status": "READY",
                        "originalUrl": article_image_url
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
    if response.status_code == 201:
        print("Post published successfully!")
    else:
        print(f"Error publishing post: {response.json()}")

# Main Function
def main():
    print("=== LinkedIn API Posting Tool ===")

    # Step 1: Authorize
    print("\nStep 1: Get Authorization URL")
    get_authorization_url()
    authorization_code = input("Enter the authorization code: ").strip()

    # Step 2: Get Access Token
    print("\nStep 2: Fetch Access Token")
    get_access_token(authorization_code)

    # Step 3: Post Content
    print("\nStep 3: Post Content to LinkedIn")
    article_text = input("Enter the text for your LinkedIn post: ").strip()
    article_image_url = input("Enter the image URL (optional, press Enter to skip): ").strip() or None
    post_to_linkedin(article_text, article_image_url)

if __name__ == "__main__":
    main()
