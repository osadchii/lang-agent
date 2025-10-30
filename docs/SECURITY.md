# Security Model

## Overview

This document describes the authentication and authorization security model for the Lang Agent platform.

## Threat Model

### Threats We Protect Against

1. **User Impersonation**: Attackers sending forged `X-User-Id` headers to access other users' data
2. **Data Theft**: Unauthorized access to flashcards, decks, and learning progress
3. **Replay Attacks**: Reusing captured authentication tokens (mitigated by Telegram's signature scheme)

### Out of Scope

- **DDoS attacks**: Rate limiting should be handled at infrastructure level (Traefik, Cloudflare, etc.)
- **Database injection**: Mitigated by using SQLAlchemy ORM with parameterized queries
- **XSS**: Frontend uses React which escapes content by default

## Authentication Mechanisms

### Production Mode (REQUIRE_TELEGRAM_AUTH=true)

**How it works:**
1. User opens mini app in Telegram
2. Telegram provides cryptographically signed `initData` via `window.Telegram.WebApp.initData`
3. Frontend sends `initData` in `Telegram-Init-Data` HTTP header
4. Backend validates signature using HMAC-SHA256 and bot token
5. Backend extracts user ID and profile from validated data

**Security guarantees:**
- ✅ User cannot forge their identity
- ✅ Data integrity: initData cannot be modified without detection
- ✅ Authenticity: Only Telegram can generate valid signatures
- ✅ Per-request validation: No session tokens to steal

**Cryptographic verification:**
```python
# Backend validates using this algorithm:
secret_key = HMAC-SHA256(bot_token, "WebAppData")
expected_hash = HMAC-SHA256(secret_key, data_check_string)
assert expected_hash == received_hash  # Prevents tampering
```

See [Telegram's validation docs](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app) for details.

### Development Mode (REQUIRE_TELEGRAM_AUTH=false)

**How it works:**
1. Frontend sends `X-User-Id` and other headers from `.env` configuration
2. Backend accepts these headers without validation
3. Allows testing with curl, Postman, or browser DevTools

**Security guarantees:**
- ❌ **NO PROTECTION** - Anyone can impersonate any user
- ⚠️ **ONLY USE FOR LOCAL DEVELOPMENT**

## Configuration

### Environment Variables

```bash
# Production deployment
REQUIRE_TELEGRAM_AUTH=true

# Local development
REQUIRE_TELEGRAM_AUTH=false
```

### Docker Compose (Production)

```yaml
services:
  backend:
    environment:
      - REQUIRE_TELEGRAM_AUTH=true
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
```

### Local Development

```bash
# .env file
REQUIRE_TELEGRAM_AUTH=false
VITE_USER_ID=1
VITE_USER_USERNAME=testuser
```

## Attack Scenarios & Mitigations

### Scenario 1: Header Injection Attack (Dev Mode)

**Attack:**
```bash
curl http://api.example.com/api/decks \
  -H "X-User-Id: 999999999"
```

**Impact:** Attacker accesses victim's decks

**Mitigation:** Set `REQUIRE_TELEGRAM_AUTH=true` in production

### Scenario 2: Replay Attack (Production Mode)

**Attack:**
1. Attacker captures valid `Telegram-Init-Data` from network traffic
2. Attacker replays the same header in new requests

**Impact:** Limited - `initData` includes `auth_date` timestamp
- Telegram clients typically generate fresh initData
- Old initData may be rejected by Telegram's own TTL checks
- Backend should implement additional timestamp validation if needed

**Mitigation (optional):**
```python
# In telegram_auth.py, add timestamp check:
auth_date = int(params.get("auth_date", 0))
if time.time() - auth_date > 3600:  # 1 hour TTL
    raise TelegramAuthError("initData expired")
```

### Scenario 3: Man-in-the-Middle (MITM)

**Attack:** Attacker intercepts HTTP traffic and steals initData

**Mitigation:**
- ✅ **Always use HTTPS in production** (required by Telegram Mini Apps)
- Telegram will refuse to load mini apps over HTTP

## Deployment Checklist

### Before Going to Production

- [ ] Set `REQUIRE_TELEGRAM_AUTH=true` in production environment
- [ ] Verify HTTPS is enabled (certificate valid)
- [ ] Confirm `TELEGRAM_BOT_TOKEN` is set correctly
- [ ] Test with real Telegram accounts
- [ ] Verify 401 errors when sending requests without `Telegram-Init-Data`
- [ ] Check CORS allows only your domain (not wildcard `*`)
- [ ] Review backend logs for authentication failures

### Testing Authentication

**Test 1: Verify production mode rejects header-based auth**
```bash
# Should return 401 Unauthorized
curl https://your-api.com/api/decks \
  -H "X-User-Id: 1"
```

**Test 2: Verify invalid initData is rejected**
```bash
# Should return 401 with "Invalid hash" message
curl https://your-api.com/api/decks \
  -H "Telegram-Init-Data: query_id=fake&hash=invalid"
```

**Test 3: Verify valid Telegram users can access**
1. Open mini app in Telegram
2. Check browser DevTools → Network → Request Headers
3. Should see `Telegram-Init-Data: query_id=...&user=...&hash=...`
4. API requests should return 200 OK

## Code References

- **Backend validation**: `apps/backend/src/backend/services/telegram_auth.py`
- **Backend dependencies**: `apps/backend/src/backend/api/dependencies.py`
  - `get_authenticated_user()` - strict Telegram-only auth
  - `get_user_profile()` - flexible auth with dev fallback
- **Frontend client**: `apps/frontend/src/api/client.ts`
  - Automatically sends `Telegram-Init-Data` when available

## References

- [Telegram Mini Apps Security](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- ADR-0002: Telegram WebApp User Context Integration
