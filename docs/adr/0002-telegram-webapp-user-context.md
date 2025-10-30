# 2. Telegram WebApp User Context Integration

- Status: Accepted
- Date: 2025-10-30

## Context

The frontend mini app needs to identify individual Telegram users to provide personalized experiences (decks, flashcards, progress tracking). Previously, the app used static configuration values for user identification during local development, which meant all users shared the same data in production when accessed via Telegram.

## Decision

- Integrate the official [Telegram WebApp SDK](https://core.telegram.org/bots/webapps) to extract authenticated user data directly from the Telegram client.
- Create a typed `telegram.ts` utility module that safely accesses `window.Telegram.WebApp` and provides:
  - User data extraction (`getTelegramUser()`)
  - WebApp initialization (`initTelegramWebApp()`)
  - Environment detection (`isTelegramWebApp()`)
- Update the API client authentication layer to prioritize Telegram user data over fallback configuration:
  1. **Telegram WebApp user** (when running inside Telegram) → highest priority
  2. **Runtime config** (placeholder-replaced values in production)
  3. **Vite env variables** (`.env` file for local development)
  4. **Default values** (last resort)
- Add the Telegram WebApp SDK script to `index.html` before application initialization.

## Implementation Details

### Frontend Structure

**New files:**
- `apps/frontend/src/utils/telegram.ts` - TypeScript definitions and utilities for Telegram WebApp API

**Modified files:**
- `apps/frontend/index.html` - Added Telegram SDK script tag
- `apps/frontend/src/api/client.ts` - Updated to extract user from Telegram first
- `apps/frontend/src/main.tsx` - Initialize Telegram WebApp on startup
- `apps/frontend/tsconfig.base.json` - Added `@utils/*` path alias
- `apps/frontend/vite.config.ts` - Added `@utils` resolver alias

### User Data Priority

```typescript
const telegramUser = getTelegramUser();

const USER_ID = telegramUser
  ? telegramUser.id
  : // fallback to runtime config or env variables
```

This ensures:
- **Production (Telegram)**: Each user sees their own decks and progress
- **Local development**: Uses `VITE_USER_ID` from `.env` file
- **Standalone web**: Uses runtime-config placeholders or defaults

### API Communication

The backend expects HTTP headers for authentication:
- `X-User-Id` (required, integer) - Telegram user ID
- `X-User-Username` (optional)
- `X-User-First-Name` (optional)
- `X-User-Last-Name` (optional)

The frontend API client automatically sets these headers using data extracted from Telegram WebApp.

## Consequences

### Positive

- **Personalized user experience**: Each Telegram user has isolated decks, cards, and learning progress.
- **Zero authentication overhead**: Telegram handles user authentication; the mini app trusts the data provided by the Telegram client.
- **Seamless development workflow**: Local development continues to work with `.env` variables; production automatically uses real Telegram user data.
- **Type safety**: Full TypeScript definitions for Telegram WebApp API reduce runtime errors.

### Negative

- **Development mode allows impersonation**: When `REQUIRE_TELEGRAM_AUTH=false`, anyone can forge user IDs via HTTP headers. This is acceptable for local development but **must be disabled in production**.
- **No offline support**: User data is only available when the app runs inside Telegram; standalone web access falls back to generic/demo user.

## Security Implementation (Updated 2025-10-30)

After initial implementation, we added cryptographic validation of Telegram initData to prevent user impersonation attacks.

### Backend Security Module

**File:** `apps/backend/src/backend/services/telegram_auth.py`

Implements HMAC-SHA256 validation of Telegram initData:
1. Parse `initData` query string
2. Extract and validate `hash` parameter
3. Compute `secret_key = HMAC-SHA256(bot_token, "WebAppData")`
4. Compute `expected_hash = HMAC-SHA256(secret_key, sorted_params)`
5. Compare hashes using constant-time comparison to prevent timing attacks

### Frontend Integration

**File:** `apps/frontend/src/api/client.ts`

The API client now:
1. Checks if `window.Telegram.WebApp.initData` exists
2. If available, sends it in `Telegram-Init-Data` HTTP header
3. Falls back to `X-User-*` headers for local development

### Deployment Modes

**Production (`REQUIRE_TELEGRAM_AUTH=true`):**
- ✅ Only accepts `Telegram-Init-Data` header
- ✅ Validates cryptographic signature
- ✅ Prevents user impersonation attacks
- ❌ Rejects requests with only `X-User-Id` headers

**Development (`REQUIRE_TELEGRAM_AUTH=false`):**
- ✅ Accepts `Telegram-Init-Data` (validated if present)
- ✅ Falls back to `X-User-Id` headers for testing
- ❌ No protection against header forgery

### Configuration

```bash
# Production
REQUIRE_TELEGRAM_AUTH=true

# Local Development
REQUIRE_TELEGRAM_AUTH=false
```

See `docs/SECURITY.md` for complete security documentation.

## References

- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Telegram WebApp API Reference](https://core.telegram.org/bots/webapps#initializing-mini-apps)
- ADR-0001: Telegram Runtime (backend user persistence)
