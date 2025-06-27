import time
import logging
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def post_to_linkedin(context, text: str, image_path: Optional[str] = None, max_retries: int = 3) -> Tuple[bool, str]:
    """
    Post content to LinkedIn with retry mechanism and error handling.
    
    Args:
        context: Playwright browser context
        text: The text content to post
        image_path: Optional path to an image to include in the post
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (success: bool, message: str)
        On success: (True, post_url)
        On failure: (False, error_message)
    """
    page = None
    
    try:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_retries}: Creating new LinkedIn post")
                
                # Create a new page for the post
                page = context.new_page()
                page.set_default_timeout(30000)  # 30 seconds timeout for operations
                
                # Navigate to LinkedIn feed
                logger.info("Navigating to LinkedIn feed")
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
                
                # Wait for the share box to be ready
                logger.info("Waiting for share box to be ready")
                try:
                    share_button = page.wait_for_selector(
                        "button.share-box-feed-entry__trigger:not([disabled])",
                        timeout=10000
                    )
                    share_button.click()
                except Exception as e:
                    logger.warning(f"Could not find share button, trying alternative selector: {e}")
                    # Try alternative selectors
                    share_selectors = [
                        "button[aria-label='Start a post']",
                        "button[data-control-name='share.trigger']",
                        "button.share-box-feed-entry__trigger"
                    ]
                    
                    for selector in share_selectors:
                        try:
                            share_button = page.wait_for_selector(selector, timeout=5000)
                            share_button.click()
                            break
                        except:
                            continue
                
                # Wait for the post editor and enter text
                logger.info("Entering post text")
                editor = page.wait_for_selector("div.ql-editor, .editor-content", timeout=10000)
                editor.click()  # Focus the editor
                page.keyboard.press("Control+KeyA")  # Select all (in case there's default text)
                page.keyboard.press("Backspace")  # Clear the editor
                page.keyboard.type(text, delay=50)  # Type with small delay to mimic human
                
                # Handle image upload if provided
                if image_path:
                    logger.info(f"Uploading image: {image_path}")
                    try:
                        # Wait for the image upload button
                        image_button = page.wait_for_selector(
                            "button[aria-label*='photo' i], button[aria-label*='image' i], button[data-test-file-upload-btn]",
                            timeout=10000
                        )
                        image_button.click()
                        
                        # Handle file upload
                        file_input = page.wait_for_selector("input[type='file']", timeout=10000)
                        file_input.set_input_files(image_path)
                        
                        # Wait for upload to complete
                        page.wait_for_selector(
                            "button[aria-label*='Done']:not([disabled]), "
                            "button[data-test-modal-close-btn]:not([disabled])",
                            timeout=30000
                        )
                        
                        # Click done if the button exists
                        done_buttons = page.query_selector_all("button[aria-label*='Done'], button[data-test-modal-close-btn]")
                        for btn in done_buttons:
                            if btn.is_visible():
                                btn.click()
                                break
                                
                    except Exception as e:
                        logger.error(f"Error uploading image: {e}")
                        if attempt == max_retries:
                            return False, f"Failed to upload image after {max_retries} attempts: {e}"
                        continue
                
                # Post the content
                logger.info("Posting content")
                post_button = page.wait_for_selector(
                    "button[data-control-name='share.post'], "
                    "button[aria-label='Post']",
                    timeout=10000
                )
                
                # Scroll the button into view and click
                post_button.scroll_into_view_if_needed()
                post_button.click()
                
                # Wait for success notification or post to appear in feed
                logger.info("Waiting for post to complete")
                try:
                    # Look for success message
                    success_selectors = [
                        "div.artdeco-toast-item__message",  # Success toast
                        "div.feed-shared-update-v2",  # Post in feed
                        "div.share-box-feed-entry__top-card"  # Back to share box
                    ]
                    
                    for selector in success_selectors:
                        try:
                            page.wait_for_selector(selector, timeout=10000)
                            break
                        except:
                            continue
                    
                    # Get the post URL if possible
                    try:
                        post_links = page.query_selector_all("a[href*='/feed/update/'], a[href*='/posts/']")
                        for link in post_links:
                            href = link.get_attribute("href")
                            if href and ('/feed/update/' in href or '/posts/' in href):
                                post_url = href if href.startswith('http') else f"https://www.linkedin.com{href}"
                                logger.info(f"Successfully posted: {post_url}")
                                return True, post_url
                    except Exception as e:
                        logger.warning(f"Could not extract post URL: {e}")
                    
                    # If we can't get the URL but the post seems successful
                    return True, "Post created successfully (could not retrieve URL)"
                    
                except PlaywrightTimeoutError:
                    if attempt == max_retries:
                        return False, "Timed out waiting for post to complete"
                    continue
                
            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    return False, f"Failed after {max_retries} attempts: {str(e)}"
                
                # Wait before retry with exponential backoff
                wait_time = 5 * attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
        
    finally:
        # Clean up the page
        try:
            if page and not page.is_closed():
                page.close()
        except Exception as e:
            logger.error(f"Error cleaning up page: {e}")
    
    return False, "Unexpected error: Reached end of function"
