# LineUp: notes for agents

Consumer haircut app: Flask JSON API (`lineup_backend/`, entry `app.py`) and a
static single-page frontend (`index.html`, `config.js`, `src/js/` ES modules,
Tailwind CLI build to `styles.css`). Users sign in (Firebase ID tokens, or dev
JWTs from `POST /auth/dev-login` when Firebase is not configured), are clients
from their first request (no onboarding step) and spend credits on metered
routes. The barber side (shop management, bookings, portfolios/packages,
community feed, Barber Pro) still exists in the API behind
`LINEUP_BARBER_SIDE=true` but is off for the launch and has no frontend on
this branch; the last two-sided frontend is on branch
`finish-lineup-fullstack-polish-ui`. README.md has the architecture, env vars,
API table with auth and credit columns, production setup and deployment.

## Run

```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
npm ci && npm run build            # src/input.css -> styles.css (minified)
scripts/dev.sh                     # API :5000 (FLASK_ENV=development) + frontend :8000
```

No API keys are needed: without them the API returns mock analysis, sample
barbers and a preview try-on, and the sign-in page shows the developer
sign-in. Any dev-login email creates a client with 3 credits; the seeded
`client@lineup.dev` is uid `client_1` (`barber@lineup.dev` / `barber_1` is
still seeded for the barber-side tests). Copy `.env.example` to `.env` to add
keys; set `LINEUP_DEV_SECRET` so dev tokens survive restarts. **Restart the
API on :5000 after any backend change**; a stale server answers with the old
routes and auth rules.

## Test and verify

- Backend: `.venv/bin/python -m pytest -q` (184 tests, no network; fakes are
  injected via `create_app(**overrides)`, see `tests/conftest.py`). The
  fixtures build the full two-sided app (`barber_side=True`) so the barber
  routes stay covered; `tests/test_consumer_mode.py` builds the shipped
  consumer-only configuration and the production persistence guard. Add tests
  next to the blueprint you touch.
- Signed-in requests in tests: use the fixtures `as_client`, `as_barber`,
  `as_pro_barber` (seeded barber upgraded via `svc.ledger.set_plan`) and
  `other_client`; each is an `AuthedClient` whose `get/post/put/delete` add the
  bearer header, with `.uid`, `.user` and `.refresh()`. For another identity
  call `login(client, email, role=..., shop_name=...)` from `conftest.py`
  (dev-login, then onboarding when a role is given). The bare `client` fixture
  is anonymous. Stripe: `configure_fake_stripe(svc, prices=...)`,
  `stripe_event(...)` and `post_webhook(client, event)` in `tests/helpers.py`.
- Registered routes: `.venv/bin/python -c "from lineup_backend import create_app; app=create_app(); [print(r.rule, sorted(r.methods - {'HEAD','OPTIONS'})) for r in app.url_map.iter_rules()]"`
- Frontend: there is no JS test suite. Verify in a headless browser (Playwright
  is not a dependency; `npm i --no-save playwright` then a script) at 375, 768
  and 1440 px, signed out and as `client@lineup.dev`, with zero console errors.
- `render.yaml` must parse: `uv run --no-project --with pyyaml python -c "import yaml; yaml.safe_load(open('render.yaml'))"`.

## Where things live

- `lineup_backend/config.py`: the only place env vars are read. Add new
  settings there and to `.env.example`, `ENVIRONMENT_SETUP.md`, the README
  table and (secrets as `sync: false`) `render.yaml`.
- `lineup_backend/pricing.py`: credit costs, signup credits, packs, Barber Pro,
  Pro feature list, provider cost estimates. Change prices here and in Stripe.
- `lineup_backend/routes/*.py`: one blueprint per domain, registered in
  `routes/__init__.py` (`CONSUMER_BLUEPRINTS` always; `BARBER_SIDE_BLUEPRINTS`
  only with `config.barber_side`). `barbers.py` is discovery (search, photo
  proxy, public reviews); `barber_shop.py` is shop management. `storage/`
  refuses the memory store in production (`PersistentStoreRequired`) unless
  `allow_memory_store`. `services/`: integrations with mock fallbacks, plus
  `auth.py` (token verification), `users.py` (entitlements), `billing.py`
  (`Ledger`, `metered`), `stripe_gateway.py`, `stripe_events.py`. `storage/`:
  `Store`/`Collection` interface with memory and Firestore implementations;
  `seed.py` holds demo data and the dev accounts.
- `lineup_backend/middleware/auth.py`: `require_auth`, `require_role(...)`,
  `optional_auth`, `assert_owner(uid)`, `require_pro(feature)`, `current_user()`;
  the resolved user is `g.user`.
- `src/js/main.js` boots every module; `router.js` (views and auth gate),
  `session.js` (token + user in localStorage, `HOME_HASH`), `auth.js`
  (Firebase or dev sign-in, account menu), `billing.js` (pricing, credits
  pill, Checkout/portal, usage, 402 modal), `api.js` (the only fetch wrapper),
  `state.js` (prefs, last analysis), `nav.js` (Home / Explore tabs plus an
  Account link), `ui/` (toast, modal, skeleton, dropzone), `features/`
  (`analysis`, `tryon`, `barbers`, `landing`).
- `src/input.css`: design tokens (CSS custom properties) and component classes
  in `@layer components`. `tailwind.config.js` mirrors the tokens.

## Auth and billing conventions

- Barber-side routes live in `BARBER_SIDE_BLUEPRINTS`; anything in `billing.py`
  that only makes sense with barbers is wrapped in `@barber_side_only` (404).
- Protect a route with `@require_auth` (any account) or `@require_role("barber")`;
  use `@optional_auth` for public reads that personalise. Inside a view,
  `assert_owner(barber_id)` for barber-owned resources: the owner always comes
  from the token, never from the URL or body. Client ids in bodies (`clientId`,
  `user_id`, `follower_id`, `username`) are ignored.
- Pro gates: call `require_pro("feature")` (402 `{"error": "pro_required",
  "feature": ...}`) or check `is_pro(user)` for soft limits like the free
  portfolio cap. Add the feature name to `PRO_FEATURES` in `pricing.py` and to
  `entitlements()` in `services/users.py` so the frontend can lock the panel
  (`[data-pro-panel="..."]` + `.locked`). Locked panels stay visible with an
  upgrade CTA; never hide them.
- Metered route: add the action and cost to `CREDIT_COSTS` (and
  `ESTIMATED_PROVIDER_COST_USD`) in `pricing.py`, a `MAX_<ACTION>_PER_DAY_PER_USER`
  setting in `config.py` (`daily_caps`), then decorate the view
  `@require_auth` (or `@optional_auth`) followed by
  `@metered("action", free_when=callable)`. `free_when` returns True when
  nothing should be charged (cache hit, provider unconfigured in production).
  Refunds are automatic when the view raises, returns >= 400, or returns a body
  with `cached`, a `reason` ending in `_error`, `reason == "daily_quota_reached"`,
  or `mock` while `charge_for_mock` is off. Do not charge the ledger by hand.
- Error codes the frontend handles globally: 401 (`unauthorized`,
  `invalid_token`, `token_expired`) clears the session; 402
  `insufficient_credits` opens the credits modal; 429 `daily_cap_reached`;
  503 `stripe_not_configured` / `auth_not_configured`. (`onboarding_required`
  and `pro_required` still exist for the barber side.) Keep these codes stable.
- Dev-only routes (`/auth/dev-login`, `/billing/dev-grant`,
  `/billing/dev-activate-pro`) must 404 whenever `config.dev_login_enabled` is
  false; add a test for the production case when adding one.
- Stripe: go through `svc.stripe` (the gateway) and `services/stripe_events.py`;
  never import `stripe` in a route. Webhook handling must stay idempotent
  (`stripe_events` collection).

## Conventions

- Keep every route path and response key the frontend reads (see the README
  API table); add fields rather than renaming them.
- Errors are JSON (`{"error", "message"}` plus `code` where the frontend
  branches on it); validation failures are 400.
- Frontend markup goes through the `html` tagged template in `src/js/dom.js`
  (auto-escaped); use `data-action` attributes with delegated listeners, never
  inline `onclick`. No `alert`/`prompt`/`confirm`: use `ui/toast.js`,
  `ui/modal.js`, `ui/confirm.js`. Show exactly one `.view` at a time through
  `router.js`; do not toggle views from feature modules.
- No emoji in UI text or code output; plain, specific copy in sentence case.
- After adding a component class to `src/input.css`, run
  `node src/tools/gen-safelist.js && npm run build` and commit `styles.css`.
- Python 3.12 is the tested version; the dependencies also install on 3.14.
- Do not commit `.env`, `node_modules/`, `.venv/`. `styles.css` and
  `images/screens/*.png` are committed.
