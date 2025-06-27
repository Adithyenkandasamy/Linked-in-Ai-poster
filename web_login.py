from flask import Flask, request, render_template_string, jsonify, Response
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import threading
import logging
import json
import os
import sys
import time
import atexit
import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional, Tuple, List, Union

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())

# Get base URL from environment or use ngrok default
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

# In-memory storage for user sessions and browser instances
user_sessions: Dict[str, Any] = {}
browser_instances: Dict[str, Dict[str, Any]] = {}
# Lock for thread-safe operations
browser_lock = threading.Lock()

# Add CORS headers for all responses
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Cleanup function to close all browser instances
def cleanup_browsers():
    """Close all browser instances on application exit"""
    logger.info("Cleaning up browser instances...")
    with browser_lock:
        for user_id, instance in list(browser_instances.items()):
            try:
                logger.info(f"Closing browser for user {user_id}")
                browser = instance.get('browser')
                playwright = instance.get('playwright')
                if browser:
                    browser.close()
                if playwright:
                    playwright.stop()
            except Exception as e:
                logger.error(f"Error cleaning up browser for user {user_id}: {e}")
            finally:
                if user_id in browser_instances:
                    del browser_instances[user_id]
                if user_id in user_sessions:
                    del user_sessions[user_id]

# Register cleanup function
atexit.register(cleanup_browsers)

def run_web_server() -> None:
    """Run the Flask web server with production settings"""
    # Use Waitress as a production WSGI server
    from waitress import serve
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    logger.info(f"Starting web server on {host}:{port}")
    
    # In production, use Waitress
    serve(app, host=host, port=port, threads=4)

if __name__ == '__main__':
    # Development mode
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

@app.route('/login')
def login() -> Response:
    """Handle LinkedIn login request"""
    try:
        user_id = request.args.get("user")
        if not user_id:
            logger.error("Login attempt without user ID")
            return jsonify({"status": "error", "message": "Missing user ID"}), 400
        
        logger.info(f"Login request from user {user_id}")
        
        # Store user session
        with browser_lock:
            user_sessions[user_id] = {
                'status': 'waiting_login',
                'last_active': time.time()
            }
        
        # Simple mobile-friendly login page with direct LinkedIn login
        login_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login with LinkedIn</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background-color: #f3f6f8;
                    text-align: center;
                }
                .container {
                    padding: 20px;
                    max-width: 400px;
                    width: 100%;
                }
                .card {
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                }
                .logo {
                    width: 100px;
                    height: auto;
                    margin-bottom: 20px;
                }
                .btn {
                    display: block;
                    background-color: #0a66c2;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 24px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                    transition: background-color 0.2s;
                }
                .btn:hover {
                    background-color: #004182;
                }
                .status {
                    margin: 20px 0;
                    padding: 15px;
                    border-radius: 5px;
                    background-color: #e8f0fe;
                    color: #0a66c2;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <img src="https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Logo.png.original.png" 
                         alt="LinkedIn" class="logo">
                    <h2>Welcome to LinkedIn Poster</h2>
                    <p>Click the button below to log in with your LinkedIn account.</p>
                    
                    <a href="https://www.linkedin.com/checkpoint/lg/login-submit" class="btn">
                        Continue with LinkedIn
                    </a>
                    
                    <div class="status">
                        You will be redirected to LinkedIn to log in.
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">
                        By continuing, you agree to our Terms of Service and Privacy Policy.
                    </p>
                </div>
            </div>
            
            <script>
                // Auto-redirect after a short delay
                setTimeout(function() {
                    window.location.href = "https://www.linkedin.com/checkpoint/lg/login-submit";
                }, 2000);
            </script>
        </body>
        </html>
        """
        
        return login_html
        
    except Exception as e:
        logger.error(f"Unexpected error in login endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": "An unexpected error occurred"
        }), 500

@app.route('/status')
def status() -> Response:
    """Check login status for a user"""
    try:
        user_id = request.args.get("user")
        if not user_id:
            logger.warning("Status check without user ID")
            return jsonify({"status": "error", "message": "Missing user ID"}), 400
        
        logger.debug(f"Status check for user {user_id}")
        
        with browser_lock:
            if user_id in user_sessions and user_sessions[user_id].get('logged_in'):
                # Verify the session is still valid by checking the browser
                if user_id in browser_instances:
                    try:
                        # Check if browser is still responsive
                        page = browser_instances[user_id].get('page')
                        if page and not page.is_closed():
                            # Update last activity time
                            user_sessions[user_id]['last_activity'] = datetime.datetime.now().isoformat()
                            
                            return jsonify({
                                "status": "success", 
                                "logged_in": True,
                                "last_activity": user_sessions[user_id].get('last_activity'),
                                "session_active": True
                            })
                    except Exception as e:
                        logger.warning(f"Browser check failed for user {user_id}: {e}")
                        # Clean up invalid session
                        cleanup_user_session(user_id)
                
                # If we get here, the browser check failed
                cleanup_user_session(user_id)
                return jsonify({"status": "success", "logged_in": False, "session_expired": True})
            
            return jsonify({"status": "success", "logged_in": False})
            
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

def launch_browser_login(user_id: str) -> bool:
    """
    Launch browser and handle LinkedIn login process
    
    Args:
        user_id: Unique identifier for the user session
        
    Returns:
        bool: True if login was successful, False otherwise
    """
    playwright = None
    browser = None
    
    try:
        logger.info(f"Starting browser for user {user_id}")
        
        # Update user session status
        with browser_lock:
            if user_id in user_sessions:
                user_sessions[user_id].update({
                    'status': 'browser_starting',
                    'last_activity': datetime.datetime.utcnow()
                })
        
        # Initialize Playwright
        playwright = sync_playwright().start()
        
        # Launch browser with additional options for better stability and automation detection evasion
        browser = playwright.chromium.launch(
            headless=False,  # Need to be visible for login
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-blink-features=AutomationControlled',
                '--disable-blink-features=AutomationControlled',
                f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                '--window-size=1280,800'
            ],
            handle_sigint=False,
            handle_sigterm=False,
            handle_sighup=False,
            timeout=60000  # 60 seconds timeout
        )
        
        # Create a new browser context with viewport settings
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
            timezone_id='America/New_York',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            permissions=['geolocation', 'notifications'],
            bypass_csp=True,
            ignore_https_errors=True,
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
            device_scale_factor=1.0,
            screen={'width': 1280, 'height': 800},
            color_scheme='light',
            reduced_motion='no-preference',
            forced_colors='none',
            accept_downloads=True
        )
        
        # Add init script to prevent detection
        context.add_init_script("""
        // Overwrite the `languages` property to use a custom getter.
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Overwrite the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Overwrite the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        """)
        
        # Create a new page
        page = context.new_page()
        
        # Store browser instance with lock
        with browser_lock:
            if user_id not in user_sessions:
                user_sessions[user_id] = {}
                
            user_sessions[user_id].update({
                'browser': browser,
                'context': context,
                'page': page,
                'playwright': playwright,
                'status': 'navigating_to_login',
                'last_activity': datetime.datetime.utcnow()
            })
            
            # Only store the browser instance if we have a valid user session
            browser_instances[user_id] = {
                'browser': browser,
                'context': context,
                'page': page,
                'playwright': playwright,
                'start_time': datetime.datetime.utcnow().isoformat()
            }
        
        logger.info(f"Navigating to LinkedIn login for user {user_id}")
        
        # Update status
        with browser_lock:
            if user_id in user_sessions:
                user_sessions[user_id].update({
                    'status': 'navigating_to_login',
                    'last_activity': datetime.datetime.utcnow()
                })
        
        # Navigate to LinkedIn login with retry logic and timeout
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                # Set a timeout for the page load
                page.set_default_timeout(60000)  # 60 seconds
                
                # Add a navigation event listener to handle redirects
                def handle_navigation(request):
                    logger.debug(f"Navigating to: {request.url}")
                    
                page.on("request", handle_navigation)
                
                # Navigate to LinkedIn login page
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Loading LinkedIn login page")
                
                # First, go to the main LinkedIn page to get cookies
                page.goto('https://www.linkedin.com', wait_until='domcontentloaded')
                
                # Then navigate to login page
                login_url = 'https://www.linkedin.com/login'
                logger.info(f"Navigating to login page: {login_url}")
                
                response = page.goto(
                    login_url,
                    wait_until='domcontentloaded',
                    timeout=60000  # 60 seconds timeout
                )
                
                # Check if navigation was successful
                if not response or not response.ok:
                    raise Exception(f"Failed to load login page. Status: {response.status if response else 'No response'}")
                
                logger.info("Successfully loaded LinkedIn login page")
                break
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    raise
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                # Wait for the login form to be visible
                logger.info("Waiting for login form...")
                try:
                    # Wait for either the email field or the "Use password" button (in case LinkedIn shows email first)
                    email_selector = 'input[autocomplete="username"], input[type="text"][id*="username"], input[type="email"]'
                    password_selector = 'input[type="password"]'
                    
                    # Wait for either the email field or the password field
                    try:
                        page.wait_for_selector(f"{email_selector}, {password_selector}", timeout=10000)
                    except Exception as e:
                        logger.warning(f"Login form not found with standard selectors: {e}")
                        
                        # Try to find any input field that might be the email/username field
                        input_fields = page.query_selector_all('input')
                        if input_fields:
                            logger.info(f"Found {len(input_fields)} input fields, trying to identify login fields")
                            
                            # Try to find email/username field by common attributes
                            for field in input_fields:
                                field_type = field.get_attribute('type') or ''
                                field_id = (field.get_attribute('id') or '').lower()
                                field_name = (field.get_attribute('name') or '').lower()
                                field_placeholder = (field.get_attribute('placeholder') or '').lower()
                                
                                if ('email' in field_id or 'user' in field_id or 'login' in field_id or 
                                    'email' in field_name or 'user' in field_name or 'login' in field_name or
                                    'email' in field_placeholder or 'phone' in field_placeholder):
                                    logger.info(f"Found potential email/username field: id={field_id}, name={field_name}, type={field_type}")
                                    email_selector = f'#{field_id}' if field_id else f'[name="{field_name}"]' if field_name else ''
                                    if email_selector:
                                        break
                    
                    # Check if we're already logged in by looking for the feed
                    if page.url.startswith('https://www.linkedin.com/feed/'):
                        logger.info("Already logged in to LinkedIn")
                        with browser_lock:
                            if user_id in user_sessions:
                                user_sessions[user_id].update({
                                    'status': 'logged_in',
                                    'logged_in': True,
                                    'last_activity': datetime.datetime.utcnow()
                                })
                        return True
                    
                    # Take a screenshot for debugging
                    screenshot_path = f"login_page_{user_id}.png"
                    page.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved to {screenshot_path}")
                    
                    # Wait for user to complete login (check every 5 seconds for 10 minutes max)
                    max_wait_time = 600  # 10 minutes
                    check_interval = 5  # seconds
                    start_time = time.time()
                    
                    logger.info("Waiting for user to complete login...")
                    
                    while time.time() - start_time < max_wait_time:
                        # Check if we've been redirected to the feed
                        if 'linkedin.com/feed/' in page.url or 'linkedin.com/in/' in page.url:
                            logger.info("Detected successful login via URL change")
                            with browser_lock:
                                if user_id in user_sessions:
                                    user_sessions[user_id].update({
                                        'status': 'logged_in',
                                        'logged_in': True,
                                        'last_activity': datetime.datetime.utcnow()
                                    })
                            return True
                            
                        # Check for login success indicators
                        try:
                            # Look for the main feed or profile icon
                            feed_visible = page.is_visible('div.feed-identity-module')
                            profile_icon_visible = page.is_visible('li.global-nav__me')
                            
                            if feed_visible or profile_icon_visible:
                                logger.info("Detected successful login via UI elements")
                                with browser_lock:
                                    if user_id in user_sessions:
                                        user_sessions[user_id].update({
                                            'status': 'logged_in',
                                            'logged_in': True,
                                            'last_activity': datetime.datetime.utcnow()
                                        })
                                return True
                        except Exception as e:
                            logger.debug(f"Error checking login status: {e}")
                        
                        # Wait before checking again
                        time.sleep(check_interval)
                        
                        # Update last activity
                        with browser_lock:
                            if user_id in user_sessions:
                                user_sessions[user_id]['last_activity'] = datetime.datetime.utcnow()
                    
                    # If we get here, login timeout was reached
                    raise TimeoutError("Login timeout: User did not complete login within the allowed time")
                    
                except Exception as e:
                    logger.error(f"Error during login process: {e}")
                    with browser_lock:
                        if user_id in user_sessions:
                            user_sessions[user_id].update({
                                'status': 'error',
                                'error': f"Navigation failed: {str(e)}",
                                'last_activity': datetime.datetime.utcnow()
                            })
                    raise RuntimeError(f"Failed to navigate to LinkedIn: {e}")
                
                logger.warning(f"Navigation attempt {attempt + 1} failed, retrying...")
                time.sleep(5)  # Wait before retry
        
        # This point should never be reached due to the raise statements above
        return False
        
    except Exception as e:
        logger.error(f"Critical error in launch_browser_login for user {user_id}: {e}", exc_info=True)
        with browser_lock:
            if user_id in user_sessions:
                user_sessions[user_id].update({
                    'status': 'error',
                    'error': f"Critical error: {str(e)}",
                    'last_activity': datetime.datetime.utcnow()
                })
        raise
        
    finally:
        # Clean up if login was not successful
        with browser_lock:
            if user_id in browser_instances and not (user_id in user_sessions and user_sessions[user_id].get('logged_in')):
                try:
                    logger.info(f"Cleaning up browser instance for user {user_id}")
                    instance = browser_instances.get(user_id, {})
                    
                    # Try to close the page and context gracefully
                    page = instance.get('page')
                    if page and not page.is_closed():
                        try:
                            page.close()
                        except Exception as e:
                            logger.warning(f"Error closing page: {e}")
                    
                    context = instance.get('context')
                    if context:
                        try:
                            context.close()
                        except Exception as e:
                            logger.warning(f"Error closing context: {e}")
                    
                    # Close the browser
                    browser = instance.get('browser')
                    if browser:
                        try:
                            browser.close()
                        except Exception as e:
                            logger.warning(f"Error closing browser: {e}")
                    
                    # Stop Playwright
                    pw = instance.get('playwright')
                    if pw:
                        try:
                            pw.stop()
                        except Exception as e:
                            logger.warning(f"Error stopping Playwright: {e}")
                    
                    # Remove from instances
                    if user_id in browser_instances:
                        del browser_instances[user_id]
                    
                    logger.info(f"Successfully cleaned up browser instance for user {user_id}")
                    
                except Exception as e:
                    logger.error(f"Error during browser cleanup for user {user_id}: {e}", exc_info=True)
            
            # Clean up user session if not logged in
            if user_id in user_sessions and not user_sessions[user_id].get('logged_in'):
                try:
                    logger.info(f"Cleaning up failed login session for user {user_id}")
                    if user_id in user_sessions:
                        del user_sessions[user_id]
                except Exception as e:
                    logger.error(f"Error cleaning up user session for {user_id}: {e}", exc_info=True)
                    
        # If we get here, the login process has completed or failed
        # The actual login handling is done in the earlier part of the function
        return False

def cleanup_user_session(user_id: str) -> None:
    """Clean up user session and browser instance"""
    with browser_lock:
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        if user_id in browser_instances:
            instance = browser_instances[user_id]
            browser = instance.get('browser')
            context = instance.get('context')
            page = instance.get('page')
            playwright = instance.get('playwright')
            
            try:
                if page and hasattr(page, 'close') and not page.is_closed():
                    page.close()
                if context and hasattr(context, 'close'):
                    context.close()
                if browser and hasattr(browser, 'close'):
                    browser.close()
                if playwright and hasattr(playwright, 'stop'):
                    playwright.stop()
            except Exception as e:
                logger.error(f"Error cleaning up browser for user {user_id}: {e}", exc_info=True)
            finally:
                if user_id in browser_instances:
                    del browser_instances[user_id]
