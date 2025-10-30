# Telegram Mini App Testing Guide

## Overview

This guide explains how to test the Telegram Mini App integration both locally and in production.

## Local Development

### Prerequisites
1. Backend running on `http://127.0.0.1:8000`
2. PostgreSQL database running with migrations applied
3. `.env` file configured with required variables

### Setup

1. **Configure `.env` file** (in project root):
```bash
# Backend configuration
OPENAI_API_KEY=your-key-here
TELEGRAM_BOT_TOKEN=your-token-here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lang_agent_v2
DB_USER=postgres
DB_PASSWORD=postgres

# Frontend configuration
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_USER_ID=1
VITE_USER_USERNAME=testuser
VITE_USER_FIRST_NAME=Test
VITE_USER_LAST_NAME=User
```

2. **Start the backend**:
```bash
# From project root
python -m backend.cli
```

3. **Start the frontend dev server**:
```bash
# From apps/frontend/
npm install
npm run dev
```

4. **Open in browser**: Navigate to `http://localhost:5173`

### Testing User Context

Open the browser console and run:
```javascript
// Check if running in Telegram
console.log("Is Telegram:", Boolean(window.Telegram?.WebApp));

// View current user context (from .env)
console.log("User ID:", document.cookie);
// Or check network requests in DevTools → Network → Headers → X-User-Id
```

Make API requests and verify headers:
1. Open DevTools → Network tab
2. Click "Тренировка" or "Колоды"
3. Inspect API requests (e.g., `/api/decks`)
4. Check Request Headers:
   - `X-User-Id: 1`
   - `X-User-Username: testuser`
   - `X-User-First-Name: Test`
   - `X-User-Last-Name: User`

## Testing in Telegram

### Setup Mini App in BotFather

1. Open [@BotFather](https://t.me/botfather) in Telegram
2. Send `/mybots`
3. Select your bot
4. Click "Bot Settings" → "Menu Button"
5. Click "Configure Menu Button"
6. Enter:
   - **Button text**: `Открыть приложение` (or any text)
   - **URL**: Your deployed frontend URL (e.g., `https://lang-agent.home.osadchii.me`)

### Testing Real User Context

1. Open your bot in Telegram
2. Click the menu button to launch the mini app
3. Open DevTools (if testing on desktop):
   - Right-click → "Inspect"
   - Navigate to Console
4. Run:
```javascript
// Check Telegram WebApp is loaded
console.log("Telegram WebApp:", window.Telegram.WebApp);

// View your Telegram user data
console.log("User:", window.Telegram.WebApp.initDataUnsafe.user);

// Expected output:
// {
//   id: 123456789,
//   first_name: "Your Name",
//   last_name: "...",
//   username: "yourusername",
//   language_code: "ru"
// }
```

5. Check network requests to verify headers:
   - DevTools → Network → `/api/decks` or `/api/training/next`
   - Request Headers should show your real Telegram user ID

### Testing User Isolation

To verify that each user sees their own data:

1. Create a deck and cards with User A's account
2. Open the mini app with User B's Telegram account
3. Verify User B doesn't see User A's decks
4. Create a deck with User B
5. Switch back to User A and verify they still see only their own decks

### Mobile Testing

1. Open Telegram on your phone
2. Navigate to your bot
3. Tap the menu button
4. The mini app should:
   - Fill the entire screen
   - Show navigation at the bottom
   - Allow easy scrolling without nested scroll conflicts
   - Show scoring buttons without needing to scroll

## Debugging Tips

### User not authenticated
**Symptom**: API returns 400 "X-User-Id header is required"

**Fix**:
- Local dev: Check `.env` has `VITE_USER_ID=1` or higher
- Production: Verify `runtime-config.js` is being loaded and populated correctly

### Wrong user ID
**Symptom**: Data from another user appears

**Fix**:
- Check `window.Telegram.WebApp.initDataUnsafe.user.id` matches the request headers
- Clear browser cache and reload
- Verify backend database has correct `user_id` foreign keys

### Theme not applying
**Symptom**: App doesn't match Telegram theme

**Fix** (future enhancement):
```javascript
// Get Telegram theme
const theme = window.Telegram.WebApp.colorScheme; // 'light' or 'dark'
const themeParams = window.Telegram.WebApp.themeParams;
```

## Production Deployment Checklist

- [ ] Backend API is accessible at the configured `API_BASE_URL`
- [ ] Database migrations applied
- [ ] `runtime-config.js` placeholders are replaced during deployment
- [ ] CORS is configured to allow requests from Telegram domains
- [ ] HTTPS is enabled (required for Telegram Mini Apps)
- [ ] Bot menu button URL points to deployed frontend
- [ ] Test with at least 2 different Telegram accounts to verify user isolation

## Troubleshooting

### API requests fail with CORS errors
Configure FastAPI CORS middleware in `apps/backend/src/backend/api/app.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### initData validation (optional security enhancement)
If you need to validate Telegram data cryptographically:
1. Send `window.Telegram.WebApp.initData` to backend
2. Backend validates hash using bot token
3. See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

## References

- [Telegram Mini Apps Documentation](https://core.telegram.org/bots/webapps)
- [BotFather Commands](https://core.telegram.org/bots#botfather)
- ADR-0002: Telegram WebApp User Context Integration
