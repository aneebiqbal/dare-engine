# 07 — Auth and security

## Password hashing

`argon2-cffi` `PasswordHasher()` (Argon2id) in `api/app/auth.py`. Hashing and
verification are in `_hash()` / `_verify()`. Passwords must be at least 10
characters (`SignUp`, `ChangePassword`, `ResetPassword`). The password is never
logged, printed or returned.

## Sign-up

`POST /auth/sign-up` (`api/app/auth.py`):

1. Normalise email to lower case, validate the shape.
2. If `INVITE_REQUIRED` (default `true`) or a code was supplied, look up the
   invite by code. It must exist, be unused, unrevoked and unexpired; if it has
   an email, it must match.
3. Reject an existing email with 409.
4. Insert the user with `role='creator'`, mark the invite used, create a session.
5. Set the session cookie and a fresh CSRF cookie.

The first admin is not created through sign-up: `make create-admin` runs
`api/app/create_admin.py`, which prompts for an email and password (never an
argument, never logged) and inserts an `admin`.

## Sign-in

`POST /auth/sign-in`:

1. Count `login_attempts` for that email in the last 15 minutes; at 20 → 429.
2. Look up the user. If missing, record a failed attempt and return a generic
   401.
3. If `locked_until > now`, record a failed attempt and return 423.
4. Verify the password. On failure increment `failed_logins`; at 10 set
   `locked_until = now + 15 min`; record the attempt; return 401.
5. On success reset `failed_logins`/`locked_until`, set `last_login_at`, create
   a session, set cookies.

The updates are committed before the error is raised (raising inside the DB
context manager would roll them back — fixed in this build).

## Sessions and cookies

- Token: `secrets.token_urlsafe(32)`, stored in `sessions.token` (primary key).
- Cookie `clipdesk_session`: `HttpOnly`, `SameSite=Lax`, `Path=/`,
  `Max-Age=30 days`, `Secure` when `APP_ENV=production` (or `COOKIE_SECURE=true`).
- Row `expires_at = now() + 30 days`; `current_user` rejects expired rows.
- `current_user` (`api/app/users.py`) joins `sessions` → `users` and returns
  `id,email,display_name,role`.

## CSRF

`api/app/users.py:csrf_protect`, applied to every router except the relay hooks
in `api/app/main.py`:

- `GET /auth/csrf` issues a non-HttpOnly `clipdesk_csrf` cookie and returns the
  same token.
- Every `POST/PUT/PATCH/DELETE` (except `/hooks/*`) must send
  `X-CSRF-Token` equal to the cookie, compared with `hmac.compare_digest`.
- Sign-in, sign-up and change-password rotate the CSRF cookie; the browser
  reads the new cookie value and sends it as the header.

## Roles

- `users.role` is `admin` or `creator`.
- `require_admin` (`api/app/users.py`) returns 403 for non-admins.
- The whole `admin` router has `dependencies=[Depends(require_admin)]`
  (`api/app/admin.py`); the mission-admin routes in `api/app/missions.py` add
  `Depends(require_admin)` per route.
- All non-admin queries are scoped by `user_id` (`current_user`).
- `PATCH /missions/{id}` is available to any signed-in user (creators edit
  missions); this is broader than "admin-only".

## Invites

`invites` table: `code` (`secrets.token_urlsafe(12)`), optional email,
`created_by`, 7-day expiry, `used_by`/`used_at`, `revoked_at`. Admin creates
(`POST /admin/invites`) and revokes (`POST /admin/invites/{id}/revoke`).
Sign-up consumes the code.

## Lockout

See sign-in. `MAX_FAILURES=10`, `LOCK_MINUTES=15`, `RATE_LIMIT=20`,
`RATE_WINDOW_MINUTES=15` (`api/app/auth.py`). A locked account stays locked
even with the correct password (423), proven by
`tests/acceptance/test_r1_auth.py::test_locked_account_stays_locked`.

## Password reset

`POST /admin/users/{id}/reset-link` (`api/app/admin.py`) creates a random token,
stores `sha256(token)` in `password_resets` with a 60-minute expiry, and returns
`{url}` to the admin (there is no email service). `POST /auth/reset-password`
validates the token, updates the hash, clears lockout, marks the token used and
deletes all sessions. One-time; proven by
`test_password_reset_link_works_once`.

## Sign out

`POST /auth/sign-out` deletes the current session. `POST /auth/sign-out-all`
deletes every session for the user (audit-logged).

## What is stored about a person

`users`: `email`, `display_name`, `password_hash`, `role`, `failed_logins`,
`locked_until`, `last_login_at`, `created_by_invite`, plus the legacy nullable
`google_subject`. No payment details, no address, no phone. `login_attempts`
stores the email and a boolean, not the password. See `04-data-model.md`.

## Known weaknesses

- **`SESSION_SECRET` is declared but unused.** Session tokens are random and
  stored in plaintext in `sessions.token`; a database dump exposes live
  sessions. No signing or hashing of the stored token.
- **Rate limiting is per email only.** `login_attempts.ip` exists but is never
  written; there is no per-IP limit.
- **Role changes do not invalidate sessions.** A demoted admin keeps access
  until the session expires.
- **The relay shared secret is optional.** `RELAY_HOOK_SECRET` defaults to empty
  (check disabled). The relay config sends it only for the segment hook; the
  auth hook relies on the stream key alone.
- **The admin reset URL is returned in the API and shown in the UI.** Anyone
  with the admin's screen or API access can use it.
- **`DEV_AUTH_ENABLED` is only refused when `APP_ENV=production`.** In another
  environment it would be active if set.
- **Upload chunk endpoints are unauthenticated.** `POST /uploads/start`,
  `GET /uploads/{id}` and `PUT /uploads/{id}/chunks/{index}` do not check a
  session; the random `upload_id` is the only capability. Anyone who learns one
  can write chunks into that upload.
- **Cookies are not `Secure` in development** (HTTP localhost).
- **No database-level `NOT NULL` on `email`** (legacy users may have null
  email); uniqueness is a partial unique index on `lower(email)`.
- **`POST /auth/dev/sign-in` upserts a user** and is only hidden by the flag.
