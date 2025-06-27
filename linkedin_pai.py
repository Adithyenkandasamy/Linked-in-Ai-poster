import os
import time
import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LinkedInAPI:
    """A class to handle LinkedIn API interactions with proper error handling and retries."""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """Initialize the LinkedIn API client.
        
        Args:
            api_key: API key for authentication (optional, can be set via environment variable)
            base_url: Base URL for the API (optional, can be set via environment variable)
        """
        self.api_key = api_key or os.getenv('LINKEDIN_API_KEY')
        self.base_url = base_url or os.getenv('LINKEDIN_API_BASE_URL', 'https://api.linkedin.com/v2')
        
        if not self.api_key:
            logger.warning("No LinkedIn API key provided. Some features may not work.")
        
        # Configure session with retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        # Mount the retry adapter
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set default headers
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        })
        
        return session
    
    def post_content(
        self, 
        text: str, 
        image_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Post content to LinkedIn.
        
        Args:
            text: The text content to post
            image_path: Path to an image file to include (optional)
            **kwargs: Additional parameters for the API request
            
        Returns:
            Dict containing the API response
        """
        if not self.api_key:
            raise ValueError("LinkedIn API key is required for posting content")
        
        # Prepare the request data
        data = {
            "author": f"urn:li:person:{os.getenv('LINKEDIN_PERSON_URN')}",
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            **kwargs
        }
        
        # Handle image upload if provided
        files = {}
        if image_path and os.path.exists(image_path):
            # First, register the image upload
            register_upload_response = self._register_upload()
            upload_url = register_upload_response['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset = register_upload_response['value']['asset']
            
            # Upload the image
            self._upload_image(upload_url, image_path)
            
            # Add the image to the post data
            data['content'] = {
                "media": {
                    "id": asset
                },
                "title": {
                    "text": os.path.basename(image_path)
                }
            }
        
        # Make the API request
        response = self.session.post(
            f"{self.base_url}/ugcPosts",
            json=data
        )
        
        # Handle the response
        response.raise_for_status()
        return response.json()
    
    def _register_upload(self) -> Dict[str, Any]:
        """Register an image upload with LinkedIn."""
        register_upload_data = {
            "registerUploadRequest": {
                "recipes": [
                    "urn:li:digitalmediaRecipe:feedshare-image"
                ],
                "owner": f"urn:li:person:{os.getenv('LINKEDIN_PERSON_URN')}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/assets?action=registerUpload",
            json=register_upload_data
        )
        response.raise_for_status()
        return response.json()
    
    def _upload_image(self, upload_url: str, image_path: str) -> None:
        """Upload an image to the provided URL."""
        with open(image_path, 'rb') as image_file:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            response = requests.put(upload_url, data=image_file, headers=headers)
            response.raise_for_status()

# Example usage
if __name__ == "__main__":
    # Initialize the LinkedIn API client
    linkedin = LinkedInAPI()
    
    try:
        # Post a simple text update
        response = linkedin.post_content("Hello from LinkedIn API!")
        print("Post successful!")
        print(response)
        
        # Post with an image
        # response = linkedin.post_content(
        #     "Check out this image!",
        #     image_path="path/to/your/image.jpg"
        # )
        # print("Image post successful!")
        # print(response)
        
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {e}")
