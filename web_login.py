from flask import Flask, request, render_template_string, jsonify
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import threading
import logging
import json
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session

# Store user sessions and browser instances
user_sessions = {}
browser_instances = {}

@app.route('/login')
def login():
    user_id = request.args.get("user")
    if not user_id:
        return jsonify({"status": "error", "message": "Missing user ID"}), 400
    
    # Check if already logged in
    if user_id in user_sessions:
        return jsonify({"status": "success", "message": "Already logged in to LinkedIn"})
    
    # Start login in a separate thread
    try:
        thread = threading.Thread(target=launch_browser_login, args=(user_id,), daemon=True)
        thread.start()
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>LinkedIn Login</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        display: flex; 
                        justify-content: center; 
                        align-items: center; 
                        height: 100vh; 
                        margin: 0; 
                        background: #f3f2ef;
                    }
                    .container { 
                        text-align: center; 
                        padding: 2rem; 
                        background: white; 
                        border-radius: 10px; 
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        max-width: 500px;
                        width: 90%;
                    }
                    .logo { 
                        color: #0a66c2; 
                        font-size: 2rem; 
                        font-weight: bold; 
                        margin-bottom: 1rem;
                    }
                    .spinner {
                        border: 4px solid #f3f3f3;
                        border-top: 4px solid #0a66c2;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 1rem;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="logo">LinkedIn</div>
                    <div class="spinner"></div>
                    <h2>Opening LinkedIn Login...</h2>
                    <p>Please complete the login in the browser window that just opened.</p>
                    <p>If the browser didn't open, <a href="#" onclick="window.open('https://www.linkedin.com/login', '_blank')">click here</a> to open LinkedIn login page.</p>
                    <p>You can close this window once you've logged in.</p>
                </div>
                <script>
                    // Try to open LinkedIn in a new tab
                    window.onload = function() {
                        window.open('https://www.linkedin.com/login', '_blank');
                    };
                </script>
            </body>
            </html>
        """)
    except Exception as e:
        logger.error(f"Error starting login process: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def launch_browser_login(user_id):
    try:
        logger.info(f"Starting LinkedIn login for user {user_id}")
        
        # Launch browser
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=False,  # Set to True for production
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # Create a new browser context
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            permissions=['geolocation'],
            ignore_https_errors=True,
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False
        )
        
        # Add custom headers to avoid bot detection
        context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Create a new page
        page = context.new_page()
        
        # Navigate to LinkedIn login
        logger.info(f"Navigating to LinkedIn login for user {user_id}")
        page.goto(
            "https://www.linkedin.com/login",
            wait_until="domcontentloaded",
            timeout=60000
        )
        
        # Wait for login to complete
        logger.info(f"Waiting for user {user_id} to complete login...")
        try:
            # Wait for either the feed (successful login) or stay on login page
            page.wait_for_selector(
                "div.feed-identity-module, #error-for-username, #error-for-password",
                timeout=300000  # 5 minutes timeout
            )
            
            # Check if login was successful
            if "feed" in page.url:
                user_sessions[user_id] = context
                browser_instances[user_id] = {
                    'browser': browser,
                    'playwright': playwright
                }
                logger.info(f"✅ User {user_id} successfully logged in to LinkedIn")
            else:
                logger.error(f"❌ Login failed for user {user_id}")
                # Try to get error message
                error_msg = "Unknown error"
                try:
                    error_element = page.query_selector("div[role=alert]")
                    if error_element:
                        error_msg = error_element.inner_text()
                except:
                    pass
                logger.error(f"Login error: {error_msg}")
                
                # Close browser if login failed
                context.close()
                browser.close()
                playwright.stop()
                
        except PlaywrightTimeoutError:
            logger.error(f"❌ Login timeout for user {user_id}")
            try:
                context.close()
                browser.close()
            except:
                pass
            playwright.stop()
            
    except Exception as e:
        logger.error(f"❌ Error during login process for user {user_id}: {str(e)}")
        try:
            if 'context' in locals():
                context.close()
            if 'browser' in locals():
                browser.close()
            if 'playwright' in locals():
                playwright.stop()
        except:
            pass
