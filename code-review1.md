# Code Review

**Date**: 2025-09-16
**Scope**: Entire repository (backend, web, mobile)
**Overall Assessment**: Needs Work

## Summary

- Solid foundations (encryption enforced, session management abstractions, broad pytest coverage) but several contract gaps can block clients or expose private UI flashes.
- Addressing the service update schema, router mounting, and auth-guard timing will prevent regressions across backend and frontends.

## Issues Found

### 🔴 Critical (Must Fix)

- None.

### 🟡 Important (Should Fix)

- Service connection updates still require `service_name`, making partial refreshes of tokens impossible without resending immutable metadata. This causes 422s when clients legitimately PATCH only secrets. Relax the field to Optional in the update schema. (`apps/server/app/schemas/service_connection.py:26`)
- The services router is mounted under both `/services` and `/api/v1/services`, but the routes themselves already include `/services`. The public API becomes `/services/services` and `/api/v1/services/services`, which diverges from typical REST expectations and the documented `/api/v1/services` contract. Adjust either the prefixes or the route definitions so clients can rely on `/services` and `/api/v1/services` without duplication. (`apps/server/main.py:59`-`apps/server/main.py:61`)
- `AppShell` renders the full private layout whenever the auth context finishes initializing, even if `auth.token` is null. Users who lose their session briefly see protected UI before the redirect effect runs. Gate on `auth.token` (returning a loader or redirect) to avoid leaking private content. (`apps/web/src/components/app-shell.tsx:41`)

### 🟢 Suggestions (Consider)

- Provide typed param lists for the React Navigation stacks/tabs so that route changes stay type-safe as screens evolve. (`apps/mobile/App.tsx:392`)
- Broaden the web/mobile fetch helpers to expose structured errors (status/message) so downstream callers do not need to pattern match on strings like "unauthorized". (`apps/web/src/lib/api.ts:119`, `apps/mobile/App.tsx:270`)

## What Works Well

- Encryption helpers validate the Fernet key upfront and keep token handling centralized.
- Alembic runner hooks into startup cleanly, and pytest fixtures override DB/session dependencies for fast unit tests.
- Frontend auth provider abstracts storage and exposes clear login/register/logout flows shared across pages.

## Security Review

- Passwords are hashed with bcrypt, JWTs sign with configurable secrets, and ENCRYPTION_KEY is enforced at startup. Frontends store tokens client-side (local/async storage); document hardening options for production builds.

## Performance Considerations

- No major bottlenecks spotted; catalog endpoints are static and cache-friendly. Keep an eye on double router inclusion once paths are normalized to avoid redundant handler registrations.

## Test Coverage

- Current coverage: Not reported.
- Missing tests for: service connection PATCH without `service_name`, frontend auth guard regressions, and mobile unauthorized refresh handling.

## Recommendations

- Make the schema/router fixes above, then add regression tests (backend pytest + frontend E2E/unit) to lock behavior.
- Consider adding lint/test guardrails (e.g., React Navigation param typing, CI smoke tests) to surface future contract drift sooner.
