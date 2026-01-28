# Telegram Cloud Storage

Personal cloud storage powered by your own Telegram bot. Infinite storage via Telegram's CDN with true byte-streaming downloads.

## ✨ Features

- 🚀 **Unlimited Storage** - Use your Telegram account as cloud storage
- ⚡ **True Streaming** - Direct CDN to browser, no server buffering
- 🎨 **Modern UI** - Antigravity design with glassmorphism and gradients
- 📱 **Mobile-First** - Optimized for all screen sizes
- 🔒 **Private** - Your bot, your channel, your data
- 📦 **Chunked Uploads** - Automatic 20MB chunking for large files

## 🎨 New UI

The app now features a complete **Antigravity design system**:
- Soft neon gradients (cyan/blue/violet)
- Glassmorphism cards with backdrop blur
- Real-time upload progress tracking
- Smooth micro-animations
- Mobile-optimized touch targets

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+ (for Tailwind CSS)
- Telegram account
- Telegram Bot Token
- Private Telegram Channel

### Installation

1. **Clone and setup**:
```bash
cd d:\ULstorage\telegram-cloud
pip install -r requirements.txt
npm install
```

2. **Configure environment** (`.env`):
```env
SECRET_KEY=your-secret-key
ADMIN_PASSWORD=your-password
BOT_TOKEN=your-bot-token
CHANNEL_ID=your-channel-id
UPLOAD_FOLDER=temp_uploads
```

3. **Build CSS**:
```bash
npm run build:css
```

4. **Run the app**:
```bash
python app.py
```

5. **Access**: http://localhost:5000

## 📖 Usage

### Login
- Navigate to http://localhost:5000
- Enter your admin password
- Access the dashboard

### Upload Files
- Click the upload area on the dashboard
- Select a file (any size)
- Watch real-time progress as it chunks and uploads
- Files appear in the list when complete

### Download Files
- Click the download icon next to any file
- Enjoy true streaming direct from Telegram CDN
- Compatible with download managers (IDM, etc.)

### Delete Files
- Click the trash icon next to any file
- Confirm deletion
- File is removed from Telegram and database

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│   Flask     │────▶│  Telegram   │
│   (User)    │◀────│   Server    │◀────│     CDN     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   SQLite    │
                    │  Database   │
                    └─────────────┘
```

### Upload Flow
1. File selected in browser
2. Saved to temp folder
3. Chunked into 20MB pieces
4. Each chunk uploaded to Telegram
5. Metadata stored in database
6. Temp file deleted

### Download Flow
1. File ID requested
2. Metadata fetched from database
3. Telegram message IDs retrieved
4. Chunks streamed directly to browser
5. Zero buffering on server

## 📁 Project Structure

```
telegram-cloud/
├── app.py                 # Flask routes
├── auth.py                # Authentication
├── uploader.py            # Chunked upload logic
├── downloader.py          # Streaming download
├── telegram_client.py     # Telegram API wrapper
├── db.py                  # Database operations
├── templates/             # HTML templates (Tailwind)
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   └── health.html
├── static/
│   ├── css/
│   │   ├── input.css      # Tailwind source
│   │   └── app.css        # Compiled CSS
│   └── js/
│       └── core.js        # Utilities
├── tailwind.config.js     # Design system config
└── FRONTEND_GUIDE.md      # Frontend docs
```

## 🎨 Design System

See `FRONTEND_GUIDE.md` for complete documentation on:
- Color palette
- Typography
- Component library
- Animations
- Mobile-first approach

## 🐛 Troubleshooting

### CSS not loading
```bash
npm run build:css
# Refresh browser with Ctrl+F5
```

### Upload fails
- Check `temp_uploads/` folder exists
- Verify bot token in `.env`
- Check channel ID is correct

### Download slow
- Ensure bot is admin in channel
- Check internet connection
- Verify Telegram API is accessible

## 📝 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret | `dev-secret-key-12345` |
| `ADMIN_PASSWORD` | Login password | `your-secure-password` |
| `BOT_TOKEN` | Telegram bot token | `1234567890:ABC...` |
| `CHANNEL_ID` | Private channel ID | `-100123456789` |
| `UPLOAD_FOLDER` | Temp upload directory | `temp_uploads` |

## 🚧 Development

### Watch Mode
```bash
# Terminal 1: Auto-rebuild CSS
npm run build:css

# Terminal 2: Flask dev server
python app.py
```

### Production Build
```bash
npm run build:css:prod
python run_production.py
```

## 📊 Performance

- **Upload**: Chunked, parallel to Telegram
- **Download**: Direct CDN streaming, no buffering
- **CSS**: 50KB unminified, ~10KB gzipped
- **JavaScript**: < 2KB total
- **First Paint**: < 1 second

## 🔒 Security

- Passwords hashed with bcrypt
- Session-based authentication
- No file storage on server
- Direct Telegram CDN delivery
- Private channel isolation

## 📄 License

MIT License - see LICENSE file

## 🙏 Credits

- **UI/UX**: Antigravity design system
- **Backend**: Flask + Pyrogram
- **Storage**: Telegram Platform
- **Styling**: Tailwind CSS

---

**Built with ❤️ for power users, developers, and creators**
