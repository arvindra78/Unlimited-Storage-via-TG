# Telegram Cloud Storage

A personal cloud storage solution using a private Telegram channel as the backend.

## Features
- Unlimited storage (via Telegram)
- 20MB chunking for reliability
- Secure single-user authentication
- Resume-capable design (backend state machine)
- IDM-compatible downloads

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**
   Copy `.env.example` to `.env` and fill in your details:
   - `BOT_TOKEN`: From @BotFather
   - `CHANNEL_ID`: ID of your private channel (add bot as admin first)
   - `ADMIN_PASSWORD`: Your login password

3. **Run**
   ```bash
   python app.py
   ```

4. **Access**
   Open `http://localhost:5000` in your browser.

## Architecture
- **Database**: SQLite (`cloud.db`) maps files to Telegram message IDs.
- **Uploads**: Split into 20MB chunks -> Hashed -> Sent to Telegram -> IDs saved.
- **Downloads**: Message IDs fetched -> Chunks downloaded -> Verified -> Streamed to user.
