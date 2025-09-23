# Code Review

**Date**: 2025-09-23
**Scope**: main...1.5 (Backend, Web, Mobile)
**Overall Assessment**: Needs Work

## Summary

- OAuth (Google) added end-to-end: FastAPI routes + `OAuthService`, session middleware, env settings, and UI buttons on Web/Mobile.
- Mobile integrates Expo WebBrowser for OAuth; Web parses access token from URL hash; backend issues JWTs and redirects appropriately.
- Tests for OAuth exist but need refinement; password handling for OAuth users risks runtime errors.

## Issues Found

### 🔴 Critical (Must Fix)

- Blank password hash for OAuth users causes verification errors: `user.hashed_password = ""` leads to bcrypt/verification failures in flows that call `verify_password` (e.g., password change). Use a valid random placeholder hash or branch logic for OAuth users instead of clearing the hash.
  - apps/server/app/integrations/oauth.py:159
  - apps/server/app/services/users.py:287

- Login should not allow enumeration or break for OAuth-only users: current login blocks `google_oauth_sub` (good), but any future password check against an empty hash will raise. Ensure generic error message and keep a valid hash for OAuth users.
  - apps/server/app/api/routes/auth.py:63-74
  - apps/server/app/api/routes/profile.py:115-118 (warning comment acknowledges the issue)

- Mobile OAuth callback scheme mismatch: `.env.example` shows `FRONTEND_REDIRECT_URL_MOBILE=area://oauth/callback` while `app.json` sets `scheme: "areamobile"`. These must match for deep link handling.
  - .env.example:19-21 vs apps/mobile/app.json:8

### 🟡 Important (Should Fix)

- Duplicate provider-account creation logic: similar flows exist in `OAuthService._find_or_create_google_user` and `get_or_create_user_from_oauth` (services). Consolidate to one path to avoid divergence (confirmation, hash strategy, linking).
  - apps/server/app/integrations/oauth.py:135-164
  - apps/server/app/services/users.py:246-292

- Web OAuth initiation uses `window.location.href = ${NEXT_PUBLIC_API_BASE_URL}/oauth/google` but server route is mounted at `/api/v1/oauth/google`. Ensure `NEXT_PUBLIC_API_BASE_URL` already includes `/api/v1` or change the path to `${...}/api/v1/oauth/google` to avoid 404s.
  - apps/web/src/app/page.tsx:109-115

- Session middleware secret source: `SessionMiddleware` uses `settings.secret_key` (JWT secret). Consider a dedicated session secret or document coupling.
  - apps/server/main.py:33

- Tests stub the OAuth client but do not cover redirect URL selection for mobile vs web user agents and rely on default settings without explicit env mocking. Add tests for `generate_redirect_url` mobile branch and for misconfiguration (missing client id/secret).
  - apps/server/tests/api/test_oauth_endpoints.py (suite-wide)

### 🟢 Suggestions (Consider)

- Replace `print` statements with structured logging and include `exc_info=True` in error logs; return 500 for unexpected exceptions in OAuth flows.
  - apps/server/app/integrations/oauth.py:128-133

- In Web `AuthProvider`, when parsing `#access_token=...`, consider supporting multiple hash params (`URLSearchParams`) for extensibility.
  - apps/web/src/components/auth-provider.tsx:54-67

- Mobile: after successful OAuth, navigate users to authenticated screens to complete the flow (currently shows an alert and persists token).
  - apps/mobile/App.tsx:392-401

- Document Google OAuth setup steps in `README.md` or `docs/` with screenshots and the exact redirect URIs used by the app.

## What Works Well

- Clean separation of OAuth concerns into `OAuthService` with testable hooks and cached client creation.
- Clear FastAPI routing (`/api/v1/oauth/{provider}`) and redirect handling that supports web (hash) and mobile (query) token delivery.
- Web and Mobile UX additions are minimal and cohesive; Expo WebBrowser integration is the right direction.

## Security Review

- No plaintext secrets added; `.env.example` updated with placeholders and guidance.
- Enumeration protection maintained with generic login error (keep consistent across all branches).
- Risk: empty password hashes on OAuth accounts can cause exceptions that bubble as 500; fix by storing a valid random hash or branching logic.

## Performance Considerations

- OAuth flow is single round-trip plus DB lookup; no N+1 issues observed.
- Additional middlewares/config are lightweight; no noticeable impact expected.

## Test Coverage

- Current coverage: not measured here.
- Add tests for:
  - Misconfigured OAuth (missing client id/secret) → 500 on initiation/callback.
  - Redirect URL generation for mobile user agents.
  - Happy path for service-backed callback with token issuance and redirect.
  - Password change behavior for OAuth-only users (should be disallowed or supported via set-password flow).

## Recommendations

1. Store a valid placeholder bcrypt hash for OAuth users (e.g., hash of a random 32-byte value) and set `has_password` to false; update password-change route to block OAuth-only users or provide a set-password flow.
2. Align deep link scheme between `.env.example` and `app.json` (e.g., both `areamobile`), and update mobile redirect URL accordingly.
3. Consolidate OAuth user creation/linking into a single function (prefer the service layer) and remove duplicates.
4. Update Web OAuth button URL to match the server route (`/api/v1/oauth/google`) or ensure the env var contains `/api/v1`.
5. Replace `print` with structured logging and tighten exception handling in `OAuthService`.
6. Extend tests to cover misconfiguration, redirect selection, and OAuth happy-path with proper mocks.
