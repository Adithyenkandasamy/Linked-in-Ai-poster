from flask import Flask, render_template, request, redirect, url_for, session
from linkedin_helper import LinkedInHelper
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'

linkedin_helper = LinkedInHelper(LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, REDIRECT_URI)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/auth/linkedin')
def linkedin_auth():
    auth_url = linkedin_helper.get_auth_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: No authorization code provided", 400
    
    try:
        access_token = linkedin_helper.get_access_token(code)
        session['access_token'] = access_token
        return "Successfully authenticated with LinkedIn! You can now close this window and return to the bot."
    except Exception as e:
        return f"Authentication failed: {str(e)}", 400

if __name__ == '__main__':
    app.run(debug=True)
