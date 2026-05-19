# Compare Your Website

A website trust & conversion audit tool. Paste a URL, and the app:

1. **Crawls** the home page plus a handful of trust-bearing pages (about, contact, shipping, FAQ, privacy) with a headless Chromium browser.
2. **Module A — Hard Trust Scan**: checks SSL, registered legal entity, physical address, contact channels (email / phone / WhatsApp), industry certifications, privacy/terms page, customer reviews.
3. **Module B — Consistency Check**: compares the same fact (cut-off time, free-delivery rule, service area, business hours) across pages and flags conflicts with quoted snippets and source URLs.
4. **Module C — Form Friction Audit**: locates inquiry / contact forms, counts required vs unnecessary fields, and estimates monthly revenue lost to over-asking.
5. Computes a **0–100 score** and an action list. A teaser preview is shown for free; the real score, every conflict, every required-field finding and the full action plan are unlocked after a $29 USD Stripe Checkout payment (test mode by default).

The UI ships in **English + Chinese** with a top-right language switch, and includes a fully interactive order-form preview (Section 03 in the report) that demonstrates the recommended layout.

---

## Stack

- **Backend** — Python 3.11 · FastAPI · Playwright (Chromium) · BeautifulSoup
- **Frontend** — Next.js 14 (App Router, React 18) · TypeScript
- **Payments** — Stripe Checkout (test mode, swap to live keys when you're ready)
- **No database** — reports are generated in real time and held in memory only

---

## Quick start

```bash
# 1) First-time install (creates venv, installs Python + npm deps, downloads Chromium)
./setup.sh

# 2) Launch both services
./start.sh
```

Then open **http://localhost:3000** in your browser. The backend listens on **http://localhost:8000** (Swagger UI at `/docs`).

Stop everything with **Ctrl-C**.

### Manual setup (if you don't want to use the scripts)

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Enabling Stripe (when you go live)

Right now the project runs in **test mode** by default. The teaser is fully working without Stripe; the “Unlock” button shows a friendly "Stripe not configured" notice until you fill in your keys.

1. Sign in at <https://dashboard.stripe.com>.
2. Grab your **test** keys at <https://dashboard.stripe.com/test/apikeys>.
3. Fill in `backend/.env`:

   ```env
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   UNLOCK_PRICE_CENTS=2900
   FRONTEND_URL=http://localhost:3000
   ALLOWED_ORIGINS=http://localhost:3000
   ```

4. Restart the backend.
5. Test the flow with Stripe's test card: **`4242 4242 4242 4242`**, any future expiry, any CVC.

Apple Pay / Google Pay show up automatically in Stripe Checkout based on the buyer's device & region — you don't need to configure anything else.

### Going live (real charges)

1. Activate your Stripe account (business details, payouts).
2. Replace the test keys with **live** keys (`sk_live_...`, `pk_live_...`) in `backend/.env`.
3. Set `FRONTEND_URL` to your production domain.
4. Restart. That's the whole switch.

---

## Configuration knobs

`backend/.env`:

| Variable | Default | What it does |
| --- | --- | --- |
| `STRIPE_SECRET_KEY` | _empty_ | Enables the paywall when set. Leave empty to keep payment off. |
| `STRIPE_PUBLISHABLE_KEY` | _empty_ | Public key (frontend can read via `/config` if you wire it in later). |
| `UNLOCK_PRICE_CENTS` | `2900` | Price of the full-report unlock in USD cents. |
| `FRONTEND_URL` | `http://localhost:3000` | Where Stripe redirects after success/cancel. |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed CORS origins. |
| `MAX_PAGES_PER_SITE` | `8` | Hard cap on pages crawled per audit. |
| `PAGE_TIMEOUT_MS` | `20000` | Per-page navigation timeout. |

`frontend/.env.local`:

| Variable | Default | What it does |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Where the frontend calls the API. Set this to your backend's public URL in production. |

---

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/healthz` | Liveness ping. |
| `GET` | `/config` | Returns `{stripe_enabled, unlock_price_cents, unlock_price_display}` for the frontend. |
| `POST` | `/analyze` | Body: `{url, monthly_visitors?, avg_order_value?}`. Returns the teaser audit. Optional query `?unlock=<report_id>` reveals the full payload once payment has been recorded for that report id. |
| `POST` | `/checkout` | Body: `{report_id, url}`. Creates a Stripe Checkout session and returns its URL. Marks the report as paid on success-return (test-mode convenience). |

Run `uvicorn` and visit `http://localhost:8000/docs` for the full schema.

---

## Project layout

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry — routes + paywall gate
│   │   ├── crawler.py           Playwright crawler (home + curated internal links)
│   │   ├── modules/
│   │   │   ├── trust.py         Module A — trust scan
│   │   │   ├── consistency.py   Module B — cross-page conflict detection
│   │   │   └── forms.py         Module C — form friction + loss model
│   │   ├── scoring.py           0-100 score + teaser score
│   │   ├── payments.py          Stripe Checkout session creator
│   │   ├── schemas.py           Pydantic request / response models
│   │   └── config.py            Env-driven settings
│   ├── tests/test_modules.py    Offline smoke tests (no network)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 Next.js App Router (page.tsx, layout.tsx)
│   │   ├── components/          Gauge, InteractiveForm
│   │   ├── lib/                 api.ts, i18n.ts (EN/中文)
│   │   └── styles/globals.css   Editorial design lifted from the brand reference
│   ├── package.json
│   └── .env.example
├── setup.sh                     First-time install
├── start.sh                     One-shot launcher
└── README.md
```

---

## How the paywall works

- A free `POST /analyze` returns a **teaser**:
  - A deliberately understated score (the real one is hidden).
  - The headline monthly-loss estimate.
  - All trust-check items (these aren't worth gating; they're the hook).
  - The *count* of conflicts found, but not their content.
  - One teaser action; the rest are locked.
- The teaser response carries a `report_id` (in `forms_summary.report_id`).
- `POST /checkout` with that `report_id` creates a Stripe Checkout session.
- On success Stripe redirects to `?paid=1&rid=<report_id>` — the frontend re-calls `/analyze?unlock=<report_id>` and the full payload comes back.
- Reports live in memory and expire after 1 hour. (Move to Redis / Postgres when you scale.)

---

## Testing the analysis modules without network

```bash
cd backend
source .venv/bin/activate
python tests/test_modules.py
```

This runs every module against synthetic HTML fixtures and asserts that the conflict, trust and form-friction logic all behave correctly. It does **not** hit the network or launch Playwright, so it's the fastest sanity check.

---

## Troubleshooting

**“Could not launch browser: Executable doesn't exist …”**  Run `playwright install chromium` inside the backend's virtualenv.

**“CORS error from the frontend”**  Add your frontend origin to `ALLOWED_ORIGINS` in `backend/.env` and restart.

**“Stripe redirects to `localhost` after payment in production”**  Set `FRONTEND_URL` in `backend/.env` to your real domain.

**“The audit can't see my form”**  Forms behind a login wall, JavaScript click-to-open modals, or third-party widgets (Typeform, HubSpot iframes) are not visible to the crawler — that's expected.

---

## License

Proprietary. © Compare Your Website. All rights reserved.
