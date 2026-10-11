# Marginalia — an editorial blog

A complete, server-rendered blog with a protected publishing studio. Built with
Django 5.2 LTS, SQLite (or PostgreSQL), and a small hand-written design system.

- **Readers:** home page with a featured story, paginated archive, article pages
  (author, date, reading time, topic, tags, cover image), topics, tags, author
  pages, full-text search, related articles, RSS/Atom feeds, sitemap, social and
  search-engine metadata, moderated comments and a double-opt-in newsletter.
- **Editors:** sign-in with brute-force lockout, a dashboard of real publishing
  data, a Markdown editor with live preview in the public layout, drafts,
  scheduled and published states, image library with validated uploads, topic,
  tag and author management, comment moderation, and a subscriber list with CSV
  export.

> The site name "Marginalia" is a placeholder. Change it with `SITE_NAME`.

---

## Quick start (local development)

Requirements: **Python 3.12+**. Nothing else needs to be installed: no Node.js,
database server or Redis.

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Configure
cp .env.example .env            # Windows: copy .env.example .env
# Set DJANGO_SECRET_KEY to a long random value, e.g.:
python -c "import secrets; print(secrets.token_urlsafe(50))"

# 3. Create the database
python manage.py migrate

# 4. Create an editor account (prompts for a password)
python manage.py create_editor yourname --name "Your Name"

# 5. Optional: add clearly marked demo content
python manage.py seed_demo

# 6. Run
python manage.py runserver
```

Open <http://127.0.0.1:8000/> for the site and <http://127.0.0.1:8000/studio/>
for the studio.

### Demo content

`seed_demo` creates 12 published articles, 1 scheduled and 1 draft, plus a
sample author, 4 topics, generated abstract cover images and 2 comments. Every
demo record is flagged:

- it shows a **Demo** badge in the studio;
- demo articles end with a note saying they are sample content.

Remove all of it (and nothing else) with:

```bash
python manage.py seed_demo --clear
```

### Accounts

| Command | Purpose |
| --- | --- |
| `python manage.py create_editor <username> [--name "Display Name"] [--email …]` | Creates or updates a studio editor and a linked author profile. Reads the password from `EDITOR_PASSWORD` or prompts for it. |
| `python manage.py createsuperuser` | Full access to the studio and to the built-in Django admin at `DJANGO_ADMIN_PATH` (default `/django-admin/`). |

Studio access is controlled by the `blog.manage_publication` permission, which
belongs to the **Editors** group. Superusers have it automatically.

---

## Running the checks

```bash
pytest                         # 147 unit + integration tests (browser tests are opt-in)
ruff check . && ruff format --check .
python manage.py makemigrations --check --dry-run
```

The suite covers:

- **Authentication:** sign-in and sign-out, lockout after 5 failures, and safe redirects.
- **Authorization:** every studio URL is tested as an anonymous visitor, a signed-in non-editor and an editor. Refused write requests are confirmed to change nothing in the database.
- **Post management:** creating, validating, slug handling and redirects, scheduling, preview, publish/unpublish and delete.
- **Search:** ranking, visibility, and hostile input.
- **Security:** Markdown XSS sanitization, and upload validation (fake extensions, SVG, oversized files, decompression bombs, EXIF stripping).
- **Comments:** spam defences and moderation.
- **Newsletter:** consent, duplicates, confirm and unsubscribe tokens, and honest delivery reporting.
- **Infrastructure:** rate limiting, feeds, sitemap and the management commands.

### Browser tests (opt-in)

`tests/e2e/` drives a real browser through Playwright. It covers:

- **Reader journey:** home → article → search.
- **Mobile menu.**
- **Editor journey:** auto-slug, Markdown toolbar, preview in a new tab, publish, view publicly, delete.
- **Accessible validation errors.**
- **Every public and studio page at 1440×900 and 390×844:** checked for horizontal overflow and axe-core accessibility violations.

```bash
python -m playwright install chromium        # one-time browser download
pytest -m e2e
# or reuse an installed browser instead of downloading one:
pytest -m e2e --browser-channel msedge       # or: chrome
```

---

## Configuration

All configuration is through environment variables, optionally loaded from
`.env`. See [.env.example](.env.example) for the full list.

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | — | **Required** when `DJANGO_DEBUG=false`. |
| `DJANGO_DEBUG` | `false` | Use `true` only locally. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` in debug | Comma-separated. Required in production. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | — | e.g. `https://blog.example.com` |
| `SITE_NAME`, `SITE_TAGLINE` | Marginalia | Publication identity. |
| `SITE_URL` | `http://127.0.0.1:8000` | Absolute URL used in feeds, sitemap, structured data and emails. |
| `DJANGO_TIME_ZONE` | `UTC` | Used for scheduling and display. |
| `DATABASE_URL` | SQLite at `data/db.sqlite3` | e.g. `postgres://user:pass@host:5432/blog` (install `psycopg[binary]`). |
| `MEDIA_ROOT` | `data/media` | Uploaded images. Must be on persistent storage. |
| `DJANGO_SERVE_MEDIA` | `false` | Let Django serve uploads when `DEBUG=false` (fine for one small server). |
| `S3_BUCKET_NAME` and `S3_*` | — | S3-compatible storage for uploads (install `django-storages[s3]`). |
| `EMAIL_HOST` and `EMAIL_*` | — | SMTP for newsletter confirmation emails. See below. |
| `COMMENTS_ENABLED` | `true` | Close comments site-wide. |
| `DJANGO_ADMIN_PATH` | `django-admin/` | Built-in admin for superusers. Blank disables it. |
| `DJANGO_BEHIND_PROXY` | `false` | Trust `X-Forwarded-Proto` from your load balancer. |
| `DJANGO_TRUST_X_FORWARDED_FOR` | `false` | Use the client IP from `X-Forwarded-For` for rate limits and lockouts. Enable only behind a trusted proxy. |
| `DJANGO_HSTS_SECONDS` | 30 days | Set `DJANGO_HSTS_INCLUDE_SUBDOMAINS=true` only if every subdomain is HTTPS. |

### Email and the newsletter: what is and isn't sent

- **No `EMAIL_HOST` (the default):** nothing is emailed. Confirmation messages are written to the server log (console), and the sign-up page says so: *"Request recorded — no email was sent."* Subscribers stay *Awaiting confirmation* until they open the logged link.
- **With SMTP configured:** confirmation emails are sent through your provider.
- **If sending fails:** the page reports the failure, and the error is logged.

The subscriber list always lives in this site's database, and you can export it
as CSV from the studio. To sync with a newsletter platform (Buttondown,
Mailchimp, …), implement the two methods in
[apps/newsletter/providers.py](apps/newsletter/providers.py) and set
`NEWSLETTER_PROVIDER` to your class. No third-party integration ships
pre-configured, and the site never claims to send newsletters itself.

---

## How it works

### Project layout

```
config/            settings (env-driven), URLs, WSGI
apps/core          rate limiter, client-IP hashing, robots.txt, error pages, deploy checks
apps/accounts      custom User model, sign-in/out, password change
apps/blog          Author, Category (topic), Tag, Post, SlugRedirect; public views, feeds, sitemap, Markdown
apps/images        Image model, upload validation and re-encoding
apps/search        search backends (SQLite FTS5, PostgreSQL, portable fallback) + index signals
apps/comments      moderated comments
apps/newsletter    subscribers, double opt-in, provider adapter
apps/studio        the protected publishing UI (views/forms only; logic lives in each app's services)
templates/         all HTML; static/ holds CSS, a little JS, and self-hosted OFL fonts
tests/             pytest suite
```

### Publishing states

A post is **Draft** or **Published**:

- A published post whose `published_at` is in the future is **Scheduled**.
- Public pages, feeds, search and the sitemap only show posts that are published *and* whose time has passed.
- Scheduled posts therefore go live on time without any background worker or cron job.

If you change the slug of a post that has been published, the old URL redirects
permanently (301) to the new one.

### Security

- **Studio access:** every studio view checks for login *and* the editor permission on the server. Every change is a CSRF-protected POST. Destructive actions need a separate confirmation step.
- **Passwords and lockout:** passwords are hashed with Argon2. django-axes locks sign-in for 15 minutes after 5 failures per username and IP.
- **Post bodies:** Markdown has raw HTML disabled, and the output is sanitized again with `nh3` using an allow-list.
- **Comments:** comments are shown as escaped plain text, and nothing appears until an editor approves it.
- **Uploads:** each file is decoded with Pillow (JPEG, PNG and WebP only) and limited to 5 MB and 40 megapixels. It is re-encoded, which strips EXIF/GPS data, and stored under a random filename. SVG is refused.
- **Headers:** a strict Content Security Policy applies (no inline scripts or styles, `frame-ancestors 'none'`), along with HSTS, secure cookies and `nosniff` in production.
- **Rate limits:** comments and newsletter sign-ups are rate-limited with database-backed counters, which hold across processes and restarts. IP addresses are stored only as keyed hashes.
- **Spam defences:** both public forms use a honeypot field. Comment forms also carry a signed timestamp that rejects instant or stale submissions.
- **Newsletter links:** confirm and unsubscribe links are signed tokens. Unsubscribing requires clicking a button, so email link scanners can't unsubscribe people.

### Search

- **SQLite:** an FTS5 virtual table with porter stemming, prefix matching and bm25 ranking (title weighted highest, then tags, topic, excerpt and body). Signals keep it updated when posts, tags or topics change. Rebuild it with `python manage.py rebuild_search_index`.
- **PostgreSQL:** built-in full-text search with weighted vectors.
- **Other databases:** portable term matching.

User input is reduced to plain word tokens, so search syntax can't be injected.

---

## Deployment

The app is a standard WSGI application. A minimal production setup:

```bash
pip install -r requirements.txt gunicorn
export DJANGO_DEBUG=false DJANGO_SECRET_KEY=… DJANGO_ALLOWED_HOSTS=blog.example.com \
       DJANGO_CSRF_TRUSTED_ORIGINS=https://blog.example.com SITE_URL=https://blog.example.com
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3
```

Assumptions and requirements:

- **TLS** is terminated by your host or a reverse proxy. Set `DJANGO_BEHIND_PROXY=true` when the proxy sets `X-Forwarded-Proto`.
- **Static files** (CSS, JS, fonts) are served by WhiteNoise from `staticfiles/` after `collectstatic`.
- **Durable data:** keep the `data/` directory (SQLite database and uploaded media) on a persistent volume and back it up. Alternatively, use `DATABASE_URL` for PostgreSQL and S3-compatible storage for media. Never put uploads on an ephemeral container filesystem.
- **Media serving:** on a single small server, set `DJANGO_SERVE_MEDIA=true` or serve `MEDIA_ROOT` from your web server. With S3, files are served from the bucket or CDN.
- **Email:** configure SMTP before announcing the newsletter (`check --deploy` warns if you haven't).
- **SQLite** runs in WAL mode with immediate transactions. That's fine for a single server with typical blog traffic. Use PostgreSQL if you run several app servers.

**Not verified in this environment:** the PostgreSQL search backend, S3
storage and SMTP delivery. They use standard Django and django-storages
configuration, but no Postgres server, bucket or SMTP account was available to
test against.

---

## Extending

- **Newsletter platform:** implement `apps/newsletter/providers.py`.
- **Comment spam service** (e.g. Akismet): call it in `apps/comments/views.py` before saving, and mark matches as `spam`.
- **Shared cache:** the rate limiter already works without Redis. Add a shared cache only if you introduce caching elsewhere.
