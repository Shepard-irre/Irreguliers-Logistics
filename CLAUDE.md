# Les Irréguliers — Hub Logistique

Application Streamlit de gestion logistique pour l'organisation Star Citizen "Les Irréguliers".
Stack : Python 3.11 · Streamlit · SQLite · API UEX Corp 2.0 · API sc-craft.tools

## Lancer l'app

```bash
C:\Users\YannMANCHON\AppData\Local\Programs\Python\Python312\python.exe -m streamlit run app.py
```
ou via Codespaces : ouvrir le repo → "Open in Codespaces" (lance automatiquement).

Créer un `.env` à la racine :
```
UEX_BEARER_TOKEN=<ton token UEX>
UEX_SECRET_KEY=<ta clé secrète UEX>
```

Comptes par défaut (si DB vierge) : `Shepard40 / sc1234`, `Darkias / sc1234`, `Camus / sc1234`

---

## Backend API (FastAPI) + Frontend React

Les 8 pages Streamlit (`app.py`) ont été portées avec parité fonctionnelle vers un backend FastAPI + frontend React (thème console fédérale sci-fi, voir mémoire Claude Code `decision_frontend_react_rewrite`). `app.py` reste intact et déployé sur Streamlit Cloud — le React/FastAPI est une réécriture qui tourne en parallèle, pas encore la version "officielle".

**IMPORTANT — jamais `--reload` sur Windows** : laisse des process `python.exe` (multiprocessing.spawn) orphelins qui continuent à servir de l'ancien code silencieusement. Toujours relancer manuellement après une modif backend, puis vérifier via `GET /openapi.json`.

```bash
cd backend
python -m uvicorn main:app --port 8000
```
(lancer depuis `backend/` — `import auth`, `from routers import ...` sont relatifs à ce dossier ; `uex_library.py`/`wp_auth.py`/`config.py` à la racine du repo sont trouvés via `sys.path.insert` dans `main.py`)

```bash
cd frontend
npm run dev
```

- `backend/main.py` — app FastAPI, CORS (`FRONTEND_ORIGIN` env, défaut `http://localhost:5173`), montage des routers
- `backend/security.py` — JWT API (`APP_JWT_SECRET` ou fallback `IRR_JWT_SECRET`), 12h d'expiration
- `backend/auth.py` — `POST /auth/login`, `POST /auth/sso` (reprend `WPAuth` tel quel), `get_current_user`/`require_permission` (dépendances FastAPI)
- `backend/deps.py` — singleton `UEXManager` partagé + `records_without_nan()` (pandas NaN → JSON)
- `backend/routers/` — un router par page Streamlit (`raffineries`, `sessions`, `commerce`, `gestion_stock`, `stock_federation`, `commerce_federation`, `transport`, `crafting`)
- `backend/tests/` — pytest, TDD (tdd-guard actif sur ce projet), 74 tests, tout mocké (aucun appel réseau/DB réel)
- `frontend/` — React 19 + Vite + Tailwind, `VITE_API_BASE` (défaut `http://localhost:8000`) pointe vers l'API

### Déploiement (test en ligne)

**Frontend** : `render.yaml` décrit un service Render static site `irreguliers-logistics-app` (`cd frontend && npm ci && npm run build`, publie `frontend/dist`). Fonctionne bien, reste sur Render.

**Backend** : d'abord tenté sur Render (`irreguliers-logistics-api` dans `render.yaml`), abandonné — l'IP de sortie de Render se fait bloquer par le challenge JS Cloudflare d'`api.uexcorp.space` (HTTP 403 "Just a moment..." sur `commodities`/`terminals`/`refineries_methods`, testé avec et sans `User-Agent` navigateur, sans succès). Bascule sur **Railway** (`railway.json` à la racine : Nixpacks, `pip install -r requirements.txt`, start `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`). Si Railway est un jour flagué à son tour, c'est un problème d'IP de sortie de l'hébergeur, pas de code — changer d'hébergeur backend est la seule vraie option (avec potentiellement `render.yaml` à réactiver un jour si Render change de plage IP).

**Piège résolu** : `uex_library.py.headers` lisait `UEX_BEARER_TOKEN`/`UEX_SECRET_KEY` via `dotenv_values(<racine>/.env)` — un parsing direct du fichier disque, ignorant `os.environ`. Sans fichier `.env` réel sur l'hébergeur (gitignored), les env vars classiques du dashboard ne suffisaient pas. Remplacé par `os.getenv(...)` (commit `1875841`+ suivant) — fonctionne avec de simples Environment Variables sur n'importe quel hébergeur (Render, Railway, Streamlit Cloud qui expose aussi ses secrets en env vars). `APP_JWT_SECRET`, `WP_URL`, etc. utilisaient déjà `os.getenv`, seul ce endroit était concerné.

**Limite connue** : `irr_inventory.db` (SQLite) n'est pas versionné (`.gitignore`) et le disque des hébergeurs free n'est pas persistant entre déploiements — la base repart à vide à chaque redeploy du service API. Suffisant pour un test fonctionnel, pas pour de la donnée durable (même limite déjà existante sur Streamlit Cloud).

---

## Architecture

```
app.py              # UI Streamlit — 8 pages, navigation sidebar, login
uex_library.py      # Tout le métier : UEXManager (API + SQLite)
irr_inventory.db    # Base SQLite locale (gitignorée)
.env                # Tokens API (gitignorée)
```

### Flux auth
1. Login page → `uex.authenticate_user(username, password)` → SHA256 hash
2. Rôles récupérés → permissions agrégées dans `st.session_state.permissions`
3. Navigation sidebar construite dynamiquement selon les permissions

---

## Système de permissions

| Permission | Page |
|---|---|
| `page_raffineries` | Raffineries |
| `page_commerce` | Commerce marché public |
| `page_gestion_stock` | Gestion de stock (écriture) |
| `page_stock_federation` | Stock Fédération (lecture) |
| `page_commerce_federation` | Commerce Fédération |
| `page_transport` | Bons de transport |
| `page_crafting` | Crafting / blueprints |
| `admin_panel` | Gestion utilisateurs & rôles |

### Rôles système (définis dans `ROLE_DEFAULTS`)
- **Administrateurs** : tout
- **Amiraux** : tout sauf admin_panel
- **Lieutenants** : commerce + stock lecture + commerce fédération
- **Membres** : stock lecture + commerce
- **Mineurs** : raffineries + gestion stock + stock + commerce
- **Crafteurs** : gestion stock + commerce + crafting
- **Commerciaux** : commerce + commerce fédération
- **Gestion des stocks federation** : gestion stock + stock + commerce
- **Marine Marchande** : transport + stock + commerce

---

## Base de données SQLite (`irr_inventory.db`)

### Tables métier
| Table | Contenu |
|---|---|
| `refinery_jobs` | Jobs de raffinage (pending → confirmed/cancelled) |
| `commodity_lots` | Lots de minerais raffinés en stock |
| `commodity_stock` | Agrégat stock minerais par type |
| `transport_orders` | Bons de transport (pending → in_progress → delivered) |
| `inventory` | Composants vaisseaux en stock |
| `fed_prices` | Tarifs internes fédération |
| `logs` | Historique des actions |

### Tables auth
| Table | Contenu |
|---|---|
| `users` | Utilisateurs (username, password_hash SHA256, is_active) |
| `roles` | Rôles (is_system=1 pour les rôles par défaut) |
| `user_roles` | Association user ↔ role (N:N) |
| `role_permissions` | Association role ↔ permission (N:N) |

### Cycle de vie d'un lot de minerai
```
Mineur → create_refinery_job() [pending]
       → confirm_refinery_job() [confirmed] → add_commodity_lot()
       → create_transport_order() [pending]
       → update_transport_status('in_progress')
       → update_transport_status('delivered') → update_commodity_stock()
```

---

## UEXManager — méthodes clés

### API UEX Corp 2.0 (`https://api.uexcorp.space/2.0`)
- `get_commodities()` — liste toutes les ressources
- `get_refinable_commodities()` — ressources raffinables
- `get_refinery_terminals()` — stations de raffinage
- `get_refinery_methods()` — méthodes (Cormack, Dinyx, etc.)
- `calculate_refinery_estimate(commodity_id, terminal_id, method_code, qty)` — estimation auto-apprenante (données locales > UEX > fallback)
- `get_prices_for_item(commodity_id)` — prix marché
- `get_wallet()` — solde compte UEX

### API sc-craft.tools (`https://sc-craft.tools/api/blueprints`)
- `get_blueprints_from_api(search, page, limit)` — 1040 blueprints, no auth
- `get_lots_for_ingredient(name)` — lots en stock matchant un ingrédient

### Gestion utilisateurs
- `authenticate_user(username, password)` → dict `{id, username, roles[]}`
- `create_user / update_user / delete_user / toggle_user_active / change_password`
- `add_user_role / remove_user_role`
- `create_role / update_role / delete_role / set_role_permissions`

---

## Pages (app.py)

| Page | Permission | Description |
|---|---|---|
| 🏗️ Raffineries | `page_raffineries` | Estimation rendement + confirmation jobs + stock minerais |
| 💰 Commerce | `page_commerce` | Prix marché public UEX |
| 📦 Gestion de stock Fédération | `page_gestion_stock` | Ajout composants vaisseaux + inventaire |
| 📦 Stock Fédération | `page_stock_federation` | Vue consolidée stocks composants + minerais |
| 🤝 Commerce Fédération | `page_commerce_federation` | Tarifs internes fédération |
| 🚚 Transport | `page_transport` | Bons de transport (prise en charge + livraison) |
| 🔧 Crafting | `page_crafting` | Recherche blueprints + blocage lots |
| 👤 Gestion Utilisateurs | `admin_panel` | CRUD users & rôles |

---

## Conventions

- Toute la logique métier va dans `uex_library.py` (classe `UEXManager`)
- `app.py` ne fait que de l'UI Streamlit — pas de SQL, pas d'appels API directs
- Les noms de minerais sont stockés sans suffixe `(Raw)` — migration auto au démarrage via `_migrate_schema()`
- La qualité des lots est sur une échelle 1–1000 (🟢 ≥700, 🟡 ≥400, 🔴 <400)
- `@st.cache_resource` sur UEXManager, `@st.cache_data(ttl=300)` sur les appels API lourds

---

## Migration future (WP)

Le site principal `lesirreguliers.fr` tourne sur WordPress + Ultimate Member.
L'auth SQLite est **temporaire** — elle sera remplacée par l'API WP REST :
- Endpoint cible : `POST /wp-json/jwt-auth/v1/token`
- Rôles UM (`um_amiral`, `um_lieutenant`, etc.) → mapping vers permissions app
- Tables `wp_scm_*` déjà présentes en base WP (vides) — migration des données prévue

Ne pas over-engineer l'auth actuelle, elle est vouée à être swappée.

---

## Contacts
- **Shepard40** (Yann) — Lead dev, admin
- **Darkias** — Co-dev
- **Camus68** — Marine Marchande (transport assigné par défaut)
