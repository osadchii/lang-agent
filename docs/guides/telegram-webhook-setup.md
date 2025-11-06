# Telegram Webhook Setup

## Overview

Telegram бот теперь работает на webhook'ах вместо polling. Webhook интегрирован в основное API приложение и работает на том же домене.

## Configuration

### 1. Set Webhook URL

Add the following to your `.env` file:

```env
TELEGRAM_WEBHOOK_URL=https://lang-agent-api.home.osadchii.me/api/telegram/webhook
```

Replace `lang-agent-api.home.osadchii.me` with your actual API domain.

### 2. Start the API Server

The API server will automatically:
- Set up the webhook on startup
- Clean up the webhook on shutdown

```bash
docker-compose up -d backend
```

## How It Works

1. **Webhook Endpoint**: `/api/telegram/webhook` - receives updates from Telegram
2. **Automatic Setup**: Webhook is configured when the API starts
3. **Integrated Processing**: All bot handlers work through the same service layer

## Development

For local development without webhook:
- Leave `TELEGRAM_WEBHOOK_URL` empty in `.env`
- The bot will not register a webhook
- You can use `ngrok` or similar tools to expose your local server for testing

### Using ngrok for local testing

```bash
# Start ngrok
ngrok http 8000

# Copy the HTTPS URL and add to .env
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok.io/api/telegram/webhook

# Start the API
uvicorn backend.api.app:create_api --factory --reload
```

## Troubleshooting

### Check webhook status

You can check the webhook status using Telegram Bot API:

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

### Remove webhook manually

If needed, you can remove the webhook manually:

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook
```

## Migration from Polling

The old `python -m backend run` command is no longer needed. The bot now runs as part of the API server.

**Before:**
- Separate bot process with polling
- `python -m backend run`

**After:**
- Integrated with API server
- Webhook-based updates
- Single docker container for both API and bot
