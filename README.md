# LinkedIn AI Poster Bot

A Telegram bot that helps you create and post engaging content to LinkedIn using AI.

## Features

- 🤖 Generate professional LinkedIn posts using AI (Gemini)
- 🔒 Secure LinkedIn login via browser
- 📱 Easy-to-use Telegram interface
- 🖼️ Support for image posts
- 🚀 One-click posting to LinkedIn

## Prerequisites

- Python 3.8+
- Telegram account
- Google Gemini API key (free tier available)
- LinkedIn account

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Linked-in-Ai-poster
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file and add your API keys:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   GEMINI_API_KEY=your_gemini_api_key_here
   FLASK_SECRET_KEY=generate_a_random_secret_key_here
   ```

## Getting API Keys

### Telegram Bot Token
1. Open Telegram and search for @BotFather
2. Send `/newbot` and follow the instructions
3. Copy the token provided by BotFather

### Google Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Create an API key if you don't have one
3. Copy the API key

## Running the Bot

1. **Start the bot**
   ```bash
   python main.py
   ```

2. **In Telegram**
   - Find your bot by searching for `@YourBotUsername`
   - Send `/start` to begin
   - Use the buttons to login to LinkedIn and create posts

## Usage

1. **Login to LinkedIn**
   - Click the "🔐 Login" button
   - Complete the login in the browser window that opens
   - Return to Telegram after successful login

2. **Create a Post**
   - Click "📝 Post"
   - Enter a topic for your post
   - Optionally, send an image or type 'skip'
   - The bot will generate a post using AI and post it to LinkedIn

## File Structure

```
linkedin_ai_bot/
├── bot.py               # Telegram bot logic
├── web_login.py         # Flask login endpoint with Playwright
├── linkedin_helper.py   # LinkedIn posting logic
├── ai_content.py        # AI content generator (Gemini)
├── main.py             # Application entry point
├── requirements.txt     # Python dependencies
└── .env.example        # Example environment variables
```

## Troubleshooting

- **Login issues**: Make sure your LinkedIn credentials are correct and 2FA is disabled or you've set up an app password
- **API errors**: Verify your API keys are correct and have sufficient quota
- **Browser issues**: Try running with `headless=False` in `web_login.py` for debugging

## License

MIT
