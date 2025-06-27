import time

def post_to_linkedin(context, text, image_path=None):
    page = context.new_page()
    page.goto("https://www.linkedin.com/feed/")
    page.click("button.share-box-feed-entry__trigger")
    page.wait_for_selector("div.ql-editor", timeout=10000)
    page.fill("div.ql-editor", text)
    if image_path:
        page.click("button[aria-label='Add a photo']")
        page.wait_for_selector("input[type='file']").set_input_files(image_path)
        time.sleep(5)
    page.click("button[data-control-name='share_post']")
    time.sleep(5)
    page.goto("https://www.linkedin.com/feed/")
    page.wait_for_selector("div.feed-shared-update-v2", timeout=10000)
    post_link = page.locator("div.feed-shared-update-v2 a").first.get_attribute("href")
    return f"https://www.linkedin.com{post_link}" if post_link else None
