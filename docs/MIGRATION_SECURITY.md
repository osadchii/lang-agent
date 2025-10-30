# Security Migration Guide

## Overview

This guide explains how to enable secure Telegram authentication in production.

## Before Migration (Insecure)

- ❌ API accepts any `X-User-Id` header without validation
- ❌ Anyone can impersonate any user
- ❌ No cryptographic verification

## After Migration (Secure)

- ✅ API validates Telegram `initData` signature
- ✅ User impersonation is prevented
- ✅ HMAC-SHA256 cryptographic verification

## Migration Steps

### Step 1: Update Environment Variables

**Production `.env` or deployment config:**
```bash
# Enable strict Telegram authentication
REQUIRE_TELEGRAM_AUTH=true

# Ensure bot token is set
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

**Local development `.env`:**
```bash
# Keep development mode for local testing
REQUIRE_TELEGRAM_AUTH=false

# Local development user
VITE_USER_ID=1
VITE_USER_USERNAME=dev_user
```

### Step 2: Deploy Updated Code

1. Pull latest code with security changes
2. Deploy backend with new `telegram_auth.py` module
3. Deploy frontend with updated `client.ts`
4. Restart services

### Step 3: Verify Security

**Test 1: Production rejects header-based auth**
```bash
# Should return 401 Unauthorized
curl https://your-api.com/api/decks \
  -H "X-User-Id: 123456789"

# Expected response:
# {"detail": "Telegram-Init-Data is required in production mode"}
```

**Test 2: Invalid initData is rejected**
```bash
# Should return 401 with validation error
curl https://your-api.com/api/decks \
  -H "Telegram-Init-Data: fake_data&hash=invalid"

# Expected response:
# {"detail": "Invalid Telegram authentication: Invalid hash..."}
```

**Test 3: Valid Telegram users can authenticate**
1. Open mini app in Telegram
2. Check browser DevTools → Network → Request Headers
3. Should see `Telegram-Init-Data: query_id=...&user=...&hash=...`
4. API requests should return 200 OK with user's data

### Step 4: Monitor Logs

After deployment, monitor backend logs for authentication failures:

```bash
# Docker logs
docker compose logs -f backend | grep "Invalid Telegram authentication"

# Look for patterns:
# - Legitimate users having issues → check Telegram WebApp integration
# - Many failed attempts from same IP → potential attack, consider rate limiting
```

## Rollback Plan

If issues occur, you can temporarily disable strict mode:

```bash
# Emergency rollback
REQUIRE_TELEGRAM_AUTH=false
```

Then restart services. This re-enables header-based auth (insecure) until issues are resolved.

## Common Issues

### Issue 1: All requests fail with 401

**Symptom:** Even real Telegram users get 401 errors

**Possible causes:**
- Frontend not sending `Telegram-Init-Data` header
- Telegram WebApp SDK not loaded (`<script src="https://telegram.org/js/telegram-web-app.js">`)
- Bot token mismatch between backend config and BotFather

**Fix:**
1. Check browser console for JavaScript errors
2. Verify `window.Telegram.WebApp.initData` is populated
3. Confirm `TELEGRAM_BOT_TOKEN` in backend matches BotFather token

### Issue 2: Local development stopped working

**Symptom:** Can't test API with curl/Postman

**Fix:**
```bash
# In local .env
REQUIRE_TELEGRAM_AUTH=false
```

### Issue 3: initData expired errors

**Symptom:** Users get 401 after some time in the app

**Cause:** Telegram initData may have limited lifetime

**Fix (optional):** Implement timestamp validation:
```python
# In telegram_auth.py
auth_date = int(params.get("auth_date", 0))
max_age = 3600  # 1 hour
if time.time() - auth_date > max_age:
    raise TelegramAuthError("initData expired")
```

## Security Checklist

Before going live with `REQUIRE_TELEGRAM_AUTH=true`:

- [ ] HTTPS is enabled (required by Telegram)
- [ ] `TELEGRAM_BOT_TOKEN` is correct in production
- [ ] Frontend sends `Telegram-Init-Data` header
- [ ] Tested with multiple real Telegram accounts
- [ ] Verified 401 errors for forged requests
- [ ] Monitoring/alerting is set up for auth failures
- [ ] CORS is configured (not wildcard `*`)
- [ ] Rate limiting is enabled at infrastructure level

## References

- [Telegram WebApp Validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
- `docs/SECURITY.md` - Complete security documentation
- `docs/adr/0002-telegram-webapp-user-context.md` - Architecture decision
