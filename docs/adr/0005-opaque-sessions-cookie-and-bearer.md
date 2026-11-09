# ADR-0005 — Authentication: opaque sessions in the database, cookie for web, Bearer for mobile

Status: accepted · Date: 2026-10-26

## Context
Separate student and admin accounts, permissions checked server-side, secure sessions. Two clients: browser (cookies are natural) and native app (token storage).

## Options
1. **Opaque sessions**: random 32-byte token, stored hashed in `sessions(token_hash, user_id, expires_at)`, carried in a `HttpOnly; Secure; SameSite=Lax` cookie (web) or `Authorization: Bearer` (mobile).
2. **Stateless JWT**: no table, but revocation is impossible without a denylist (so some state anyway), key rotation, classic implementation errors.
3. **OAuth / external provider**: nothing to gain for fictional accounts.

## Decision
Option 1. One mechanism, two transports. Logout = deleting the row. Sliding 7-day expiry. Passwords in argon2id. Rate limiting on `/auth/login`.

## Same origin
A `SameSite=Lax` cookie is not sent to an API hosted on a different domain from the SPA. Rather than `SameSite=None` (which reintroduces CSRF and a mandatory `Origin` check), **the API serves the built SPA** (`/` → static files, `/api/*` → routes): same origin, no CORS in production, a single deployment, a single URL in the README. In development, the Vite server proxies `/api` to the local API. If the team insists on hosting the SPA separately (Vercel, Netlify), this choice becomes: `SameSite=None; Secure` + `Origin` checked on every state-changing request + allowlisted CORS.

## Consequences
- `+` Immediate revocation; no signing secret to manage; short code.
- `+` CSRF covered by `SameSite=Lax` and the same origin; the API does not accept HTML forms.
- `−` One database read per authenticated request (index on `token_hash`, negligible at this scale).
