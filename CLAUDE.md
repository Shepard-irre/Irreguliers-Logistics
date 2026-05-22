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
