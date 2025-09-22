# Code Review

**Date**: 2025-09-21
**Scope**: main...1.5
**Overall Assessment**: Needs Work

## Summary
- Significant OAuth plumbing added across FastAPI, web, and mobile; dedicated service layer introduced alongside new env settings and session middleware.
- Frontend screens now surface a Google sign-in CTA and client-side handling for tokens delivered via URL fragments.
- New pytest module attempts to cover the OAuth flow but currently ships failing expectations and mocks.

## Issues Found

### 🔴 Critical (Must Fix)

- Sanitising the password hash to an empty string after Google sign-up leaves the account with an invalid bcrypt hash; any flow that calls `verify_password` (e.g. password change) now raises `UnknownHashError` and returns 500. Keep a valid hash (e.g. random placeholder) or branch the password checks for OAuth users instead of blanking the field. (`apps/server/app/integrations/oauth.py:159`, `apps/server/app/api/routes/auth.py:234`)
- The new password failure branch returns `"Invalid password."`, while the missing-user branch still returns `"Invalid email or password."`, revealing which emails are registered and regressing account enumeration protections. Please revert to a single generic message. (`apps/server/app/api/routes/auth.py:73`)
- React Native does not expose `window.open`; tapping the new Google button will throw `window` is undefined. Use `Linking.openURL` (or WebBrowser) for Expo instead. (`apps/mobile/App.tsx:373`)

### 🟡 Important (Should Fix)

- We now have two parallel implementations of the Google OAuth flow: the legacy handlers remain in `auth.py`, bypass the new `OAuthService`, and still send confirmation emails plus blank the password. Consolidate on the service-backed router to avoid divergence and misconfiguration. (`apps/server/app/api/routes/auth.py:137`)

### 🟢 Suggestions (Consider)

- Replace the `print` statements with structured logger calls (and return 500 for unexpected exceptions) so OAuth errors land in observability tooling. (`apps/server/app/integrations/oauth.py:128`)
- When parsing the OAuth hash, consider supporting multiple query params (e.g. `#access_token=...&provider=google`) so future metadata survives the redirect. (`apps/web/src/components/auth-provider.tsx:66`)

## What Works Well

- Good extraction of OAuth logic into `OAuthService`, complete with caching hooks and helper methods.
- Adding `SessionMiddleware` and environment documentation makes it easier to configure Google OAuth locally.
- The frontend UX clearly separates password and Google flows with consistent CTA styling.

## Security Review

- Critical: Login error messaging now leaks whether an email exists, undoing prior enumeration mitigation.
- Critical: Blank password hashes on OAuth accounts create 500s during password verification.
- No additional plain-text secrets surfaced; new env vars remain documented placeholders.

## Performance Considerations

- No blocking performance regressions observed; new DB touches remain bounded to single queries per OAuth flow.

## Test Coverage

- Current coverage: not measured in this review.
- Missing tests for: happy-path execution once the mocks are corrected (the current suite fails before asserting behaviour).

## Recommendations

1. Restore a valid password hash strategy for OAuth users and harden password-dependent code paths.
2. Revert to generic auth error messaging to maintain enumeration protection.
3. Repair the pytest suite (`AsyncMock`, settings patch) so CI can exercise the new flow.
4. Fix the Expo Google button by using the platform `Linking` API.
5. Delete or refactor the redundant OAuth handlers in `auth.py` to ensure a single, tested code path.