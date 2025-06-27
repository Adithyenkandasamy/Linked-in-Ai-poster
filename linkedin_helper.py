from playwright.sync_api import sync_playwright
import requests
from urllib.parse import urlencode
import json

class LinkedInHelper:
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = ['r_liteprofile', 'w_member_social', 'r_emailaddress']
    
    def get_auth_url(self):
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scope),
            'state': 'random_state_string'
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def get_access_token(self, code):
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json().get('access_token')
    
    @staticmethod
    def post_to_linkedin(access_token, content, visibility="PUBLIC"):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json',
        }
        
        post_data = {
            "author": "urn:li:person/YOUR_MEMBER_ID",  # This needs to be fetched from the user's profile
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        response = requests.post(
            f"{self.API_BASE_URL}/ugcPosts",
            headers=headers,
            data=json.dumps(post_data)
        )
        
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def post_with_selenium(linkedin_email, linkedin_password, content):
        """Alternative method using Selenium for posting"""
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        driver = webdriver.Chrome()
        try:
            driver.get("https://www.linkedin.com/")
            
            # Login
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "session_key"))
            )
            email_field.send_keys(linkedin_email)
            
            password_field = driver.find_element(By.ID, "session_password")
            password_field.send_keys(linkedin_password)
            
            sign_in_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            sign_in_button.click()
            
            # Wait for home page to load and click on 'Start a post'
            post_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[text()='Start a post']"))
            )
            post_button.click()
            
            # Enter post content
            post_modal = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "share-box-feed-entry__container"))
            )
            
            post_content = post_modal.find_element(By.CLASS_NAME, "ql-editor")
            post_content.send_keys(content)
            
            # Click post button
            post_button = driver.find_element(By.XPATH, "//button[contains(@class, 'share-actions__primary-action')]")
            post_button.click()
            
            time.sleep(5)  # Wait for post to complete
            
        finally:
            driver.quit()
