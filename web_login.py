from flask import Flask, request, render_template_string
from playwright.sync_api import sync_playwright
import threading

app = Flask(__name__)
user_sessions = {}

@app.route('/login')
def login():
    user_id = request.args.get("user")
    if not user_id:
        return "Missing user ID", 400
    threading.Thread(target=launch_browser_login, args=(user_id,), daemon=True).start()
    return render_template_string("<h3>Login opening in browser...</h3>")

def launch_browser_login(user_id):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.linkedin.com/login")
        try:
            page.wait_for_selector("div.feed-identity-module", timeout=120000)
            user_sessions[user_id] = context
            print(f"[{user_id}] ✅ Logged in.")
        except Exception as e:
            print(f"[{user_id}] ❌ Login failed: {e}")
