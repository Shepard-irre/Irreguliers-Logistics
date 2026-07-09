import streamlit as st
import os
import pandas as pd

# Streamlit Cloud : inject secrets into env vars before importing uex_library
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ[_k] = _v
except Exception:
    pass

from uex_library import UEXManager

st.set_page_config(page_title="Irréguliers Logistics", page_icon="🚀", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Alfa+Slab+One&family=Roboto:wght@400;500;700&family=Roboto+Slab:wght@600&display=swap');

html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }

h1 { font-family: 'Alfa Slab One', serif !important; letter-spacing: 2px; color: #6EC1E4 !important; }
h2 { font-family: 'Roboto Slab', serif !important; font-weight: 600 !important; letter-spacing: 0.5px; }
h3 { font-family: 'Roboto Slab', serif !important; font-weight: 600 !important; letter-spacing: 0.3px; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #183c51 100%) !important;
    border-right: 1px solid #1b79ff33;
}

[data-testid="stSidebar"] * { font-family: 'Roboto', sans-serif !important; }

[data-testid="metric-container"] {
    background: #183c51;
    border: 1px solid #1b79ff44;
    border-radius: 8px;
    padding: 8px 12px;
}

.stButton > button {
    background: linear-gradient(135deg, #0061c5, #1b79ff) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Roboto', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #1b79ff, #6EC1E4) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px #1b79ff55;
}

[data-testid="stDataFrame"] { border: 1px solid #1b79ff33; border-radius: 8px; }

.stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #1b79ff44; }
.stTabs [aria-selected="true"] { color: #1b79ff !important; border-bottom: 2px solid #1b79ff !important; }

div[data-testid="stInfo"] { border-left: 4px solid #1b79ff; background: #183c5188; }
div[data-testid="stSuccess"] { border-left: 4px solid #61CE70; background: #2a813622; }
div[data-testid="stWarning"] { border-left: 4px solid #ffd512; background: #d68d1922; }
div[data-testid="stError"] { border-left: 4px solid #db1010; background: #db101022; }
</style>
""", unsafe_allow_html=True)

# Cache les appels API pour éviter les requêtes répétées
@st.cache_resource
def get_uex_manager(_lib_mtime=None):
    return UEXManager()

@st.cache_data(ttl=300)  # Cache 5 minutes
def fetch_commodities():
    return uex.get_commodities()

import os as _os
_lib_mtime = _os.path.getmtime(_os.path.join(_os.path.dirname(__file__), "uex_library.py"))
uex = get_uex_manager(_lib_mtime=_lib_mtime)

# --- SESSION STATE INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Raffineries"
if "permissions" not in st.session_state:
    st.session_state.permissions = []

# --- SSO — auto-login via token passé en URL par WP ---
if not st.session_state.authenticated:
    _sso_token = st.query_params.get("token")
    if _sso_token:
        _sso_user = uex.authenticate_with_token(_sso_token)
        if _sso_user:
            st.session_state.authenticated = True
            st.session_state.user = _sso_user
            st.session_state.permissions = _sso_user['permissions']
            st.query_params.clear()
            st.rerun()

# --- LOGIN PAGE ---
if not st.session_state.authenticated:
    st.title("🛸 Les Irréguliers - Hub Logistique")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Connexion")
        username = st.text_input("Nom d'utilisateur", placeholder="Shepard40")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••")

        if st.button("Se connecter", type="primary", use_container_width=True):
            user = uex.authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.session_state.permissions = user['permissions']
                st.rerun()
            else:
                st.error("❌ Identifiants incorrects")
    st.stop()

# --- HELPER FUNCTIONS ---
def has_permission(permission):
    """Check if user has specific permission"""
    return permission in st.session_state.permissions


# --- LOGGED IN - MAIN APP STARTS HERE ---

# --- CONFIGURATION ---
STAR_SYSTEMS = ["Stanton", "Pyro", "Nyx"]

def fetch_mining_ships():
    return [v['name'] for v in uex.get_vehicles(is_mining=True)]

def fetch_all_ships():
    return [v['name'] for v in uex.get_vehicles()]

CAT_MAP = {
    "🌌 Moteurs Quantum (QT Drive)": [22, 86],
    "🛡️ Boucliers (Shields)": [23],
    "⚡ Générateurs (Power Plants)": [21, 83],
    "⚔️ Armement Vaisseaux": [32, 70, 79, 90],
    "⛏️ Minage (Lasers & Modules)": [29, 30, 74],
    "🛰️ Avionique & Radar": [82, 65]
}

# --- SIDEBAR NAVIGATION ---
user = st.session_state.user
st.sidebar.divider()

# Build navigation menu based on permissions
nav_options = []
if has_permission("page_raffineries"):
    nav_options.append("🏗️ Raffineries")
if has_permission("page_commerce"):
    nav_options.append("💰 Commerce")
if has_permission("page_gestion_stock"):
    nav_options.append("📦 Gestion de stock Fédération")
if has_permission("page_stock_federation"):
    nav_options.append("📦 Stock Fédération")
if has_permission("page_commerce_federation"):
    nav_options.append("🤝 Commerce Fédération")
if has_permission("page_transport") or has_permission("admin_panel"):
    nav_options.append("🚚 Transport")
if has_permission("page_crafting"):
    nav_options.append("🔧 Crafting")
if has_permission("admin_panel"):
    nav_options.append("👤 Gestion Utilisateurs")

# Navigation menu
st.sidebar.subheader("📍 Navigation")
selected_page = st.sidebar.radio("Aller à :", nav_options, label_visibility="collapsed")
st.session_state.current_page = selected_page

st.sidebar.divider()
st.sidebar.success(f"Citoyen : {user['username']}")

# Display roles
roles_str = ", ".join([r['name'] for r in user['roles']])
st.sidebar.info(f"Rôles : {roles_str}")

_wp_url = os.getenv("WP_URL", "https://lesirreguliers.fr")
st.sidebar.link_button("🌐 Retour au site", _wp_url, use_container_width=True)

# --- MAIN CONTENT ---
st.title("🛸 Les Irréguliers - Hub Logistique")

# --- PAGE 1 : RAFFINERIES ---
if selected_page == "🏗️ Raffineries":
    st.header("🏗️ Raffineries")

    _all_terminals = uex.get_all_terminals()
    # Une entrée par lieu unique (certaines stations ont plusieurs terminaux)
    _terminal_labels = sorted(set(
        f"{t['name']} ({t.get('star_system_name', '?')})"
        for t in _all_terminals if t.get('name')
    ))

    tab_sessions, tab_estim, tab_confirm = st.tabs(["📋 Sessions de minage", "🔬 Nouvelle estimation", "⏳ Jobs en attente"])

    # --- ONGLET SESSIONS DE MINAGE ---
    with tab_sessions:
        st.subheader("📋 Sessions de minage")

        # Créer une nouvelle session
        with st.expander("➕ Créer une nouvelle session", expanded=False):
            sc1, sc2 = st.columns(2)
            with sc1:
                new_sys = st.selectbox("Système :", STAR_SYSTEMS, key="new_session_system")
            with sc2:
                st.write("")
                st.write("")
                if st.button("🚀 Créer la session", type="primary", use_container_width=True):
                    s = uex.create_mining_session(user['username'], new_sys)
                    st.success(f"Session **{s['numero']}** créée !")
                    st.rerun()

        # Liste des sessions
        sessions_df = uex.get_mining_sessions()
        if sessions_df.empty:
            st.info("Aucune session de minage.")
        else:
            STATUS_LABELS = {
                'open': '🟡 En cours',
                'completed': '✅ Terminée',
                'cancelled': '❌ Annulée',
            }
            for _, sess in sessions_df.iterrows():
                sess_id = int(sess['id'])
                label = f"**{sess['numero']}** — {sess['star_system']} — {STATUS_LABELS.get(sess['status'], sess['status'])} — {sess['date_created'][:10]}"
                with st.expander(label, expanded=(sess['status'] == 'open')):
                    detail = uex.get_mining_session(sess_id)

                    # Statut
                    col_st, col_close = st.columns([3, 1])
                    with col_st:
                        st.caption(f"Créée par {detail['created_by']} le {detail['date_created'][:10]}")
                    with col_close:
                        if detail['status'] == 'open':
                            if st.button("✅ Clore la session", key=f"close_{sess_id}", use_container_width=True):
                                uex.set_session_status(sess_id, 'completed')
                                st.rerun()

                    st.divider()

                    # --- Vaisseaux ---
                    st.markdown("**⚓ Vaisseaux**")
                    for ship in detail['ships']:
                        ship_id = int(ship['id'])
                        role_icon = "⛏️" if ship['ship_role'] == 'mining' else "🛡️"
                        with st.container():
                            sh1, sh2, sh3 = st.columns([3, 1, 1])
                            sh1.write(f"{role_icon} **{ship['ship_name']}** ({ship['ship_role']})")
                            with sh3:
                                if detail['status'] == 'open':
                                    if st.button("🗑️", key=f"del_ship_{ship_id}", use_container_width=True):
                                        uex.remove_session_ship(ship_id)
                                        st.rerun()

                            # Équipage du vaisseau
                            crew_list = ship['crew']
                            if crew_list:
                                crew_names = ", ".join([c['username'] for c in crew_list])
                                st.caption(f"  Équipage : {crew_names}")
                                if detail['status'] == 'open':
                                    for cm in crew_list:
                                        cc1, cc2 = st.columns([4, 1])
                                        cc1.write(f"  — {cm['username']}")
                                        with cc2:
                                            if st.button("✖", key=f"del_crew_{cm['id']}", use_container_width=True):
                                                uex.remove_crew_member(int(cm['id']))
                                                st.rerun()
                            else:
                                st.caption("  Aucun membre")

                            if detail['status'] == 'open':
                                new_member = st.text_input(
                                    "Ajouter un membre :", key=f"add_crew_{ship_id}",
                                    placeholder="pseudo du joueur")
                                if st.button("➕ Ajouter membre", key=f"btn_crew_{ship_id}"):
                                    if new_member.strip():
                                        uex.add_crew_member(ship_id, new_member.strip())
                                        st.rerun()

                    if detail['status'] == 'open':
                        st.divider()
                        st.markdown("**Ajouter un vaisseau**")
                        av1, av2, av3, av4 = st.columns([2, 2, 1, 1])
                        with av1:
                            all_ships_list = fetch_all_ships()
                            if all_ships_list:
                                ship_choice = st.selectbox("Vaisseau :", all_ships_list, key=f"ship_sel_{sess_id}")
                            else:
                                ship_choice = None
                                st.caption("⚠️ Liste UEX indisponible")
                        with av2:
                            ship_custom = st.text_input("Nom du vaisseau :", key=f"ship_custom_{sess_id}", placeholder="Ex: Prospector")
                        with av3:
                            ship_role_sel = st.selectbox("Rôle :", ["mining", "escort"], key=f"ship_role_{sess_id}")
                        with av4:
                            st.write("")
                            st.write("")
                            if st.button("➕", key=f"btn_ship_{sess_id}", use_container_width=True):
                                ship_name = ship_custom.strip() if ship_custom.strip() else ship_choice
                                if not ship_name:
                                    st.error("Saisis un nom de vaisseau.")
                                else:
                                    uex.add_session_ship(sess_id, ship_name, ship_role_sel)
                                    st.rerun()

                    st.divider()

                    # --- Frais ---
                    st.markdown("**💸 Frais de session**")
                    if detail['expenses']:
                        total_exp = sum(e['amount_auec'] for e in detail['expenses'])
                        for exp in detail['expenses']:
                            fe1, fe2, fe3 = st.columns([3, 2, 1])
                            fe1.write(exp['description'])
                            fe2.write(f"{exp['amount_auec']:,.0f} aUEC")
                            with fe3:
                                if detail['status'] == 'open':
                                    if st.button("🗑️", key=f"del_exp_{exp['id']}", use_container_width=True):
                                        uex.remove_session_expense(int(exp['id']))
                                        st.rerun()
                        st.caption(f"Total frais : **{total_exp:,.0f} aUEC**")
                    else:
                        st.caption("Aucun frais saisi.")

                    if detail['status'] == 'open':
                        ef1, ef2, ef3 = st.columns([3, 2, 1])
                        with ef1:
                            exp_desc = st.text_input("Description :", key=f"exp_desc_{sess_id}", placeholder="Carburant Prospector")
                        with ef2:
                            exp_amt = st.number_input("Montant (aUEC) :", min_value=0, value=0, key=f"exp_amt_{sess_id}")
                        with ef3:
                            st.write("")
                            st.write("")
                            if st.button("➕", key=f"btn_exp_{sess_id}", use_container_width=True):
                                if exp_desc.strip() and exp_amt > 0:
                                    uex.add_session_expense(sess_id, exp_desc.strip(), exp_amt)
                                    st.rerun()

                    st.divider()

                    # --- Rapport financier ---
                    st.markdown("**📊 Rapport financier**")
                    summary = uex.get_session_financial_summary(sess_id)
                    if not summary['orders_vente'] and not summary['orders_stock_fed']:
                        st.caption("Aucun bon de transport rattaché à cette session.")
                    else:
                        # Map nom nettoyé -> id du minerai RAFFINÉ (priorité aux entrées sans suffixe)
                        # Les IDs en DB sont ceux du brut (ex: Stileron Raw id=162) sans prix
                        # Il faut mapper vers le raffiné (ex: Stileron id=122) qui lui a des prix
                        all_comms = fetch_commodities() or []
                        comm_name_map = {}
                        for c in all_comms:
                            name = c.get('name', '')
                            name_lower = name.lower()
                            clean = name_lower.replace(' (ore)', '').replace(' (raw)', '').strip()
                            if clean == name_lower:
                                # Entrée sans suffixe = minerai raffiné → priorité absolue
                                comm_name_map[clean] = c.get('id')
                            else:
                                # Entrée brute → seulement si pas déjà mappé par le raffiné
                                if clean not in comm_name_map:
                                    comm_name_map[clean] = c.get('id')

                        # Estimer revenus depuis UEX selon le système de la session
                        system_name = detail['star_system']
                        total_vente_auec = 0
                        vente_lines = []
                        for order in summary['orders_vente']:
                            # Toujours chercher par nom nettoyé — l'ID en DB est celui du brut (sans prix)
                            name_clean = order['commodity_name'].lower().replace(' (ore)', '').replace(' (raw)', '').strip()
                            comm_id = comm_name_map.get(name_clean)
                            if comm_id:
                                prices = uex.get_prices_for_item(int(comm_id))
                                buyers_sys = [p for p in prices
                                              if p.get('price_sell', 0) > 0
                                              and p.get('star_system_name') == system_name]
                                if not buyers_sys:
                                    buyers_sys = [p for p in prices if p.get('price_sell', 0) > 0]
                                best_price = max((p['price_sell'] for p in buyers_sys), default=0)
                            else:
                                best_price = 0
                            rev = best_price * order['quantity']
                            total_vente_auec += rev
                            vente_lines.append({
                                'Minerai': order['commodity_name'],
                                'SCU': order['quantity'],
                                'Prix/SCU': f"{best_price:,} aUEC",
                                'Recette estimée': f"{rev:,.0f} aUEC",
                            })

                        if vente_lines:
                            st.dataframe(pd.DataFrame(vente_lines), use_container_width=True, hide_index=True)

                        total_exp = summary['total_expenses']
                        part_fed = total_vente_auec * 0.20
                        part_transport = total_vente_auec * 0.15
                        reste = total_vente_auec - part_fed - part_transport - total_exp
                        nb = summary['nb_joueurs']
                        salaire = reste / nb if nb > 0 else 0

                        r1, r2, r3 = st.columns(3)
                        r1.metric("Recette totale estimée", f"{total_vente_auec:,.0f} aUEC")
                        r2.metric("Part Fédération (20%)", f"{part_fed:,.0f} aUEC")
                        r3.metric("Part Transporteurs (15%)", f"{part_transport:,.0f} aUEC")

                        r4, r5, r6 = st.columns(3)
                        r4.metric("Frais vaisseaux", f"{total_exp:,.0f} aUEC")
                        r5.metric("Reste à partager", f"{reste:,.0f} aUEC")
                        r6.metric(f"Salaire/joueur ({nb} joueurs)", f"{salaire:,.0f} aUEC")

                        if summary['crew']:
                            st.caption(f"Mineurs présents : {', '.join(summary['crew'])}")

    # --- ONGLET ESTIMATION ---
    with tab_estim:
        st.subheader("🔬 Estimation de rendement")

        refinable = uex.get_refinable_commodities()
        terminals = uex.get_refinery_terminals()
        methods = uex.get_refinery_methods()

        if not (refinable and terminals and methods):
            st.warning("Impossible de charger les données UEX.")
        else:
            comm_map_ref = {c['name']: c for c in refinable if c.get('name')}
            method_map = {m['name']: m for m in methods}

            # Init session state
            if 'refinery_lines' not in st.session_state:
                st.session_state['refinery_lines'] = []
            if 'refinery_estimates' not in st.session_state:
                st.session_state['refinery_estimates'] = []
            if 'processing_time_minutes' not in st.session_state:
                st.session_state['processing_time_minutes'] = None
            if 'screenshot_key' not in st.session_state:
                st.session_state['screenshot_key'] = 0
            if 'vision_orders' not in st.session_state:
                st.session_state['vision_orders'] = None

            # --- ANALYSE SCREENSHOT ---
            with st.expander("📸 Importer depuis un screenshot in-game", expanded=False):
                uploaded = st.file_uploader(
                    "Screenshot de l'interface raffinerie SC (PNG/JPG)",
                    type=['png', 'jpg', 'jpeg'],
                    key=f"refinery_screenshot_{st.session_state['screenshot_key']}"
                )
                if uploaded:
                    st.image(uploaded, use_container_width=True)
                    if st.button("🔍 Analyser le screenshot", type="primary", use_container_width=True):
                        with st.spinner("Claude analyse le screenshot…"):
                            try:
                                result = uex.analyze_refinery_screenshot(uploaded.getvalue())
                            except Exception as _e:
                                st.error(f"Erreur détaillée : {type(_e).__name__}: {_e}")
                                result = {'error': str(_e)}
                        st.session_state['_debug_vision'] = result.get('_raw_response', str(result))
                        if 'error' in result:
                            st.error(f"Erreur : {result['error']}")
                        else:
                            # Pour terminal/méthode : utilise le premier ordre si réponse multi
                            first_res = (result.get('orders') or [result])[0]

                            # Auto-sélection terminal
                            if first_res.get('terminal_name'):
                                detected_t = first_res['terminal_name'].lower()
                                all_terminal_map = {f"{t['name']} ({t.get('star_system_name', '?')})": t for t in terminals if t.get('name')}
                                detected_words = [w for w in detected_t.split() if len(w) >= 3]
                                def terminal_score(k):
                                    kl = k.lower()
                                    return sum(1 for w in detected_words if w in kl)
                                best = max(all_terminal_map.keys(), key=terminal_score, default=None)
                                if best and terminal_score(best) >= max(1, len(detected_words) // 2):
                                    st.session_state['ref_terminal'] = best
                                    st.success(f"📍 Terminal auto-sélectionné : **{best}**")
                                else:
                                    st.info(f"📍 Terminal détecté : **{first_res['terminal_name']}** — introuvable dans UEX, sélectionne manuellement.")
                            # Auto-sélection méthode
                            if first_res.get('method'):
                                detected_m = first_res['method'].lower()
                                all_method_map = {m['name']: m for m in methods}
                                match_m = next((k for k in all_method_map if detected_m in k.lower() or k.lower() in detected_m), None)
                                if match_m:
                                    st.session_state['ref_method'] = match_m
                                    st.success(f"⚙️ Méthode auto-sélectionnée : **{match_m}**")

                            def _strip_suffix(cname):
                                for s in [' (Raw)', ' (Ore)', ' (Brut)', ' (Mined)', '(Raw)', '(Ore)', '(Brut)']:
                                    cname = cname.replace(s, '').strip()
                                return cname

                            def _build_type_a_lines(order_data):
                                built = []
                                for line in order_data.get('lines', []):
                                    cname = _strip_suffix(line.get('commodity_name') or line.get('name', ''))
                                    q = line.get('quality')
                                    # Le jeu affiche QUALITÉ en 0-100 → on convertit en 0-1000
                                    if q is not None:
                                        quality_norm = max(1, min(1000, int(q * 10) if q <= 100 else int(q)))
                                    else:
                                        quality_norm = 500
                                    built.append({
                                        'commodity_name': cname,
                                        'quality': quality_norm,
                                        'quantity_raw': line.get('quantity_raw'),
                                        'quantity_refined': line.get('quantity_refined'),
                                        'active': True
                                    })
                                return built

                            # --- CAS MULTI-ORDRES (Claude a renvoyé un array) ---
                            if result.get('orders'):
                                orders_list = result['orders']
                                for i, order_data in enumerate(orders_list):
                                    onum = i + 1
                                    if order_data.get('screen_type') == 'A':
                                        lines_built = _build_type_a_lines(order_data)
                                        if lines_built:
                                            order_entry = {
                                                'order_num': onum,
                                                'processing_time_minutes': order_data.get('processing_time_minutes'),
                                                'lines': lines_built,
                                                'label': f"Ordre {onum}"
                                            }
                                            existing = [o for o in (st.session_state.get('vision_orders') or []) if o.get('order_num') != onum]
                                            existing.append(order_entry)
                                            st.session_state['vision_orders'] = existing
                                if st.session_state.get('vision_orders'):
                                    st.session_state['vision_orders'].sort(key=lambda o: o['order_num'])
                                st.session_state['refinery_estimates'] = []
                                n = len(st.session_state.get('vision_orders', []))
                                st.success(f"✅ {n} ordre(s) extraits depuis le screenshot. Importe-les ci-dessous.")

                            # --- CAS ORDRE UNIQUE TYPE A ---
                            elif first_res.get('screen_type') == 'A' and first_res.get('lines'):
                                lines_built = _build_type_a_lines(first_res)
                                onum = 1
                                order_entry = {
                                    'order_num': onum,
                                    'processing_time_minutes': first_res.get('processing_time_minutes'),
                                    'lines': lines_built,
                                    'label': f"Ordre {onum}"
                                }
                                existing = [o for o in (st.session_state.get('vision_orders') or []) if o.get('order_num') != onum]
                                existing.append(order_entry)
                                existing.sort(key=lambda o: o['order_num'])
                                st.session_state['vision_orders'] = existing
                                st.session_state['refinery_estimates'] = []
                                st.success(f"✅ Ordre {onum} extrait ({len(lines_built)} minerais). Analyse les autres ordres si besoin, puis importe.")

                            # TYPE B (configuration d'un nouvel ordre)
                            elif first_res.get('screen_type') == 'B' and first_res.get('lines'):
                                added = 0
                                for line in first_res['lines']:
                                    cname = _strip_suffix(line.get('name') or line.get('commodity_name', ''))
                                    qty = line.get('quantity_raw')
                                    quality_raw = line.get('quality')
                                    qty_refined = line.get('rendem') or line.get('quantity_refined')
                                    if not line.get('active', True):
                                        continue
                                    match = next((n for n in comm_map_ref if cname.lower() in n.lower() or n.lower() in cname.lower()), None)
                                    if match and qty:
                                        quality_val = max(1, min(1000, int(quality_raw) if quality_raw else 500))
                                        st.session_state['refinery_lines'].append({
                                            'commodity_id': comm_map_ref[match]['id'],
                                            'commodity_name': match,
                                            'quantity': int(qty),
                                            'quality': quality_val,
                                            'quantity_refined': float(qty_refined) if qty_refined else None
                                        })
                                        added += 1
                                    else:
                                        st.warning(f"Minerai non reconnu : **{cname}** — ajoute-le manuellement.")
                                if added:
                                    pt = first_res.get('processing_time_minutes')
                                    if pt:
                                        st.session_state['processing_time_minutes'] = int(pt)
                                        h, m = divmod(int(pt), 60)
                                        st.info(f"⏱️ Temps de traitement détecté : **{h}h {m:02d}m** — sera stocké à l'enregistrement.")
                                    st.success(f"✅ {added} lot(s) importé(s) depuis le screenshot !")
                                    st.session_state['refinery_estimates'] = []
                                    st.rerun()

                # --- Sélecteur d'ordre TYPE A (affiché hors du bouton, persiste après le clic) ---
                if st.session_state.get('vision_orders'):
                    orders = st.session_state['vision_orders']
                    st.divider()
                    st.write(f"**{len(orders)} ordre(s) détecté(s) — lequel importer ?**")
                    order_labels = []
                    for o in orders:
                        pt = o.get('processing_time_minutes')
                        timer_str = f" — ⏱️ {pt//60}h {pt%60:02d}m restant" if pt else ""
                        minerals = ", ".join(dict.fromkeys(l['commodity_name'] for l in o.get('lines', [])))
                        order_labels.append(f"Ordre {o['order_num']}{timer_str}  ({minerals})")
                    sel_idx = st.radio(
                        "Ordre à importer :",
                        range(len(orders)),
                        format_func=lambda i: order_labels[i],
                        key="vision_order_radio"
                    )
                    if st.button("📥 Importer cet ordre", type="primary", use_container_width=True):
                        selected_order = orders[sel_idx]
                        added = 0
                        for line in selected_order.get('lines', []):
                            cname = line.get('commodity_name', '')
                            for suffix in [' (Raw)', ' (Ore)', ' (Brut)', ' (Mined)', '(Raw)', '(Ore)', '(Brut)']:
                                cname = cname.replace(suffix, '').strip()
                            quality_raw = line.get('quality')
                            qty_refined = line.get('quantity_refined')
                            match = next((n for n in comm_map_ref if cname.lower() in n.lower() or n.lower() in cname.lower()), None)
                            if match:
                                quality_val = max(1, min(1000, int(quality_raw) if quality_raw else 500))
                                qty_raw_val = line.get('quantity_raw')
                                st.session_state['refinery_lines'].append({
                                    'commodity_id': comm_map_ref[match]['id'],
                                    'commodity_name': match,
                                    'quantity': int(qty_raw_val) if qty_raw_val else 1,
                                    'quality': quality_val,
                                    'quantity_refined': float(qty_refined) if qty_refined else None
                                })
                                added += 1
                            else:
                                st.warning(f"Minerai non reconnu : **{cname}** — ajoute-le manuellement.")
                        pt = selected_order.get('processing_time_minutes')
                        if pt:
                            st.session_state['processing_time_minutes'] = int(pt)
                        if added:
                            st.session_state['vision_orders'] = None
                            st.session_state['refinery_estimates'] = []
                            st.success(f"✅ {added} lot(s) importé(s). Vérifie les quantités et lance l'estimation.")
                            st.rerun()

            if st.session_state.get('_debug_vision'):
                with st.expander("🔍 Debug JSON brut (temporaire)", expanded=True):
                    st.code(st.session_state['_debug_vision'], language='json')

            st.divider()

            # --- Session rattachée ---
            open_sessions_df = uex.get_mining_sessions(status='open')
            session_options = {"(aucune)": None}
            session_systems = {}
            if not open_sessions_df.empty:
                for _, sr in open_sessions_df.iterrows():
                    label = f"{sr['numero']} — {sr['star_system']}"
                    session_options[label] = int(sr['id'])
                    session_systems[label] = sr['star_system']
            sel_session_label = st.selectbox(
                "Rattacher à une session de minage :", list(session_options.keys()), key="ref_session")
            sel_session_id = session_options[sel_session_label]
            sel_session_system = session_systems.get(sel_session_label)

            st.divider()

            # Filtrer les terminaux selon le système de la session
            filtered_terminals = terminals
            if sel_session_system:
                filtered_terminals = [t for t in terminals if t.get('star_system_name') == sel_session_system]
                if not filtered_terminals:
                    filtered_terminals = terminals
                st.caption(f"📍 Raffineries filtrées sur **{sel_session_system}**")
            terminal_map = {f"{t['name']} ({t.get('star_system_name', '?')})": t for t in filtered_terminals if t.get('name')}

            # --- Station + Méthode (partagées pour tout le batch) ---
            c1, c2 = st.columns(2)
            with c1:
                sel_terminal_name = st.selectbox("Station de raffinage :", sorted(terminal_map.keys()), key="ref_terminal")
            with c2:
                sel_method_name = st.selectbox("Méthode :", list(method_map.keys()), key="ref_method")
                m = method_map[sel_method_name]
                st.caption(f"Rendement : {'⭐'*m['rating_yield']} | Coût : {'⭐'*m['rating_cost']} | Vitesse : {'⭐'*m['rating_speed']}")

            st.divider()

            # --- Ajout d'une ligne ---
            st.write("**Ajouter un lot à raffiner**")
            ca, cb, cc, cd = st.columns([3, 2, 2, 1])
            with ca:
                sel_comm_name = st.selectbox("Minerai brut :", sorted(comm_map_ref.keys()), key="ref_comm")
            with cb:
                line_qty = st.number_input("Quantité (SCU) :", min_value=1, value=100, key="ref_qty")
            with cc:
                line_quality = st.number_input("Qualité (1–1000) :", min_value=1, max_value=1000, value=500, key="ref_quality")
                ql = "🟢" if line_quality >= 700 else "🟡" if line_quality >= 400 else "🔴"
                st.caption(f"{ql} {line_quality}/1000")
            with cd:
                st.write("")
                st.write("")
                if st.button("➕ Ajouter", use_container_width=True):
                    st.session_state['refinery_lines'].append({
                        'commodity_id': comm_map_ref[sel_comm_name]['id'],
                        'commodity_name': sel_comm_name,
                        'quantity': line_qty,
                        'quality': line_quality
                    })
                    st.session_state['refinery_estimates'] = []
                    st.rerun()

            # --- Tableau des lignes ---
            if st.session_state['refinery_lines']:
                st.divider()
                st.write("**Lots à raffiner :**")
                for i, line in enumerate(st.session_state['refinery_lines']):
                    r1, r2, r3, r4 = st.columns([3, 2, 2, 1])
                    r1.write(f"**{line['commodity_name']}**")
                    new_qty = r2.number_input("SCU brut", min_value=1, value=line['quantity'], key=f"edit_qty_{i}", label_visibility="collapsed")
                    new_qual = r3.number_input("Qualité", min_value=1, max_value=1000, value=line['quality'], key=f"edit_qual_{i}", label_visibility="collapsed")
                    if new_qty != line['quantity'] or new_qual != line['quality']:
                        st.session_state['refinery_lines'][i]['quantity'] = new_qty
                        st.session_state['refinery_lines'][i]['quality'] = new_qual
                        st.session_state['refinery_estimates'] = []
                    with r4:
                        if st.button("🗑️", key=f"del_line_{i}", use_container_width=True):
                            st.session_state['refinery_lines'].pop(i)
                            st.session_state['refinery_estimates'] = []
                            st.rerun()

                st.divider()
                if st.button("🔬 Calculer l'estimation pour tous les lots", type="primary", use_container_width=True):
                    sel_terminal = terminal_map[sel_terminal_name]
                    method_code = sel_method_name.lower().replace(' ', '_')
                    estimates = []
                    for line in st.session_state['refinery_lines']:
                        est = uex.calculate_refinery_estimate(
                            line['commodity_id'], sel_terminal['id'], method_code, line['quantity']
                        )
                        estimates.append({
                            **line,
                            'terminal_id': sel_terminal['id'],
                            'terminal_name': sel_terminal_name,
                            'method': method_code,
                            'method_display': sel_method_name,
                            **est
                        })
                    st.session_state['refinery_estimates'] = estimates
                    st.rerun()

            # --- Résultats ---
            if st.session_state.get('refinery_estimates'):
                st.subheader("📊 Résultats de l'estimation")
                all_saved = True
                for i, est in enumerate(st.session_state['refinery_estimates']):
                    conf_color = {"Élevée": "✅", "Moyenne": "🟡", "Faible": "🟠"}.get(est['confidence'], "🔴")
                    ql = "🟢" if est['quality'] >= 700 else "🟡" if est['quality'] >= 400 else "🔴"
                    qty_refined_from_game = est.get('quantity_refined')
                    display_output = qty_refined_from_game if qty_refined_from_game else est['estimated_output']
                    game_tag = " 🎮" if qty_refined_from_game else ""
                    with st.expander(f"**{est['commodity_name']}** — {est['quantity']} SCU brut | {ql} Qualité {est['quality']} → {display_output} SCU raffiné{game_tag}", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("SCU brut", f"{est['quantity']} SCU")
                        col2.metric("SCU raffiné" + (" 🎮" if qty_refined_from_game else " estimé"), f"{display_output} SCU")
                        real_yield = round(display_output / est['quantity'] * 100, 1) if est['quantity'] else est['yield_pct']
                        col3.metric("Rendement", f"{real_yield}%")
                        local_info = f" dont {est.get('local_count', 0)} locaux" if est.get('local_count', 0) > 0 else ""
                        st.caption(f"{conf_color} Confiance : {est['confidence']} ({est['audit_count']} audits{local_info}) | {est['method_display']} | {est['terminal_name']}")

                        # Valeur pré-remplie : rendement jeu si dispo, sinon estimation calculée
                        default_output = float(qty_refined_from_game) if qty_refined_from_game else float(est['estimated_output'])

                        col_corr, col_qual = st.columns(2)
                        with col_corr:
                            label_corr = "✅ SCU raffiné (depuis le jeu) :" if qty_refined_from_game else "Corriger SCU raffiné :"
                            corrected = st.number_input(
                                label_corr,
                                min_value=0.0, value=default_output, step=0.5,
                                key=f"corr_{i}"
                            )
                            if qty_refined_from_game:
                                st.caption(f"🎮 Valeur extraite du jeu : {qty_refined_from_game} SCU (estimation app : {est['estimated_output']} SCU)")
                        with col_qual:
                            quality_final = st.number_input(
                                "Corriger qualité :",
                                min_value=1, max_value=1000, value=est['quality'],
                                key=f"qual_{i}"
                            )

                        if not est.get('saved'):
                            if st.button(f"✅ Enregistrer ce lot", type="primary", use_container_width=True, key=f"save_{i}"):
                                uex.create_refinery_job(
                                    user['username'],
                                    est['commodity_id'], est['commodity_name'],
                                    est['terminal_id'], est['terminal_name'],
                                    est['method'], est['quantity'],
                                    corrected, est['yield_pct'],
                                    est['confidence'], est['audit_count'],
                                    session_id=sel_session_id,
                                    quality=quality_final,
                                    processing_time_minutes=st.session_state.get('processing_time_minutes')
                                )
                                st.session_state['refinery_estimates'][i]['saved'] = True
                                st.toast(f"✅ Lot {est['commodity_name']} enregistré !")
                                st.rerun()
                        else:
                            st.success("✅ Enregistré")

                if st.button("✅ Enregistrer tous les lots restants", use_container_width=True):
                    for i, est in enumerate(st.session_state['refinery_estimates']):
                        if not est.get('saved'):
                            best_output = est.get('quantity_refined') or est['estimated_output']
                            real_yield = round(best_output / est['quantity'] * 100, 1) if est['quantity'] else est['yield_pct']
                            uex.create_refinery_job(
                                user['username'],
                                est['commodity_id'], est['commodity_name'],
                                est['terminal_id'], est['terminal_name'],
                                est['method'], est['quantity'],
                                best_output, real_yield,
                                est['confidence'], est['audit_count'],
                                session_id=sel_session_id,
                                quality=est['quality'],
                                processing_time_minutes=st.session_state.get('processing_time_minutes')
                            )
                    st.session_state['refinery_lines'] = []
                    st.session_state['refinery_estimates'] = []
                    st.session_state['processing_time_minutes'] = None
                    st.session_state['screenshot_key'] = st.session_state.get('screenshot_key', 0) + 1
                    st.toast("✅ Tous les lots enregistrés !")
                    st.rerun()

    # --- ONGLET CONFIRMATION ---
    with tab_confirm:
        st.subheader("⏳ Jobs en attente de confirmation")

        can_see_all = has_permission("page_gestion_stock")
        pending_df = uex.get_pending_refinery_jobs(user=None if can_see_all else user['username'])

        if pending_df.empty:
            st.info("Aucun job en attente.")
        else:
            for _, job in pending_df.iterrows():
                # Calcul countdown
                timer_str = ""
                timer_icon = ""
                dt_comp = job.get('datetime_completion')
                if dt_comp and str(dt_comp) not in ('', 'nan', 'None'):
                    from datetime import datetime as dt_cls
                    try:
                        comp = dt_cls.strptime(str(dt_comp), "%Y-%m-%d %H:%M:%S")
                        delta = comp - dt_cls.now()
                        if delta.total_seconds() > 0:
                            h, rem = divmod(int(delta.total_seconds()), 3600)
                            m = rem // 60
                            timer_str = f" | ⏱️ {h}h {m:02d}m restant"
                            timer_icon = "⏳ "
                        else:
                            timer_str = " | ✅ TERMINÉ"
                            timer_icon = "✅ "
                    except Exception:
                        pass
                label = f"⛏️ {timer_icon}{job['commodity_name']} — {job['quantity_raw']} SCU → ~{job['quantity_estimated']} SCU | {job['user']} | {job['date_created'][:16]}{timer_str}"
                with st.expander(label):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Brut entré", f"{job['quantity_raw']} SCU")
                    col2.metric("Estimé raffiné", f"{job['quantity_estimated']} SCU")
                    col3.metric("Rendement", f"{job['yield_rate']}%")
                    if dt_comp and str(dt_comp) not in ('', 'nan', 'None'):
                        try:
                            comp = dt_cls.strptime(str(dt_comp), "%Y-%m-%d %H:%M:%S")
                            delta = comp - dt_cls.now()
                            if delta.total_seconds() > 0:
                                st.info(f"⏱️ Fin estimée : **{comp.strftime('%d/%m %H:%M')}** (dans {int(delta.total_seconds()//3600)}h {int((delta.total_seconds()%3600)//60):02d}m)")
                            else:
                                st.success("✅ Temps de traitement écoulé — job probablement terminé en jeu !")
                        except Exception:
                            pass
                    st.caption(f"Station : {job['terminal_name']} | Méthode : {job['method']} | Confiance : {job['confidence']} ({job['audit_count']} audits)")
                    st.divider()

                    col_qty, col_qual = st.columns(2)
                    with col_qty:
                        actual_qty = st.number_input(
                            "Quantité réellement obtenue (SCU) :",
                            min_value=0.0, value=float(job['quantity_estimated']), step=0.5,
                            key=f"actual_{job['id']}"
                        )
                    with col_qual:
                        stored_quality = int(job['quality']) if pd.notna(job.get('quality')) and job.get('quality') else 500
                        quality = st.number_input(
                            "Qualité du lot (1–1000) :",
                            min_value=1, max_value=1000, value=stored_quality,
                            key=f"quality_{job['id']}"
                        )
                        ql = "🟢" if quality >= 700 else "🟡" if quality >= 400 else "🔴"
                        st.caption(f"{ql} {quality}/1000")

                    # Destination : auto selon qualité, modifiable
                    default_dest = "stock_federal" if quality >= 750 else "vente"
                    dest_label = st.radio(
                        "Destination :",
                        ["vente", "stock_federal", "personnel"],
                        format_func=lambda x: {"vente": "💰 Vente", "stock_federal": "🏛️ Stock Fédéral", "personnel": "👤 Personnel"}.get(x, x),
                        index={"vente": 0, "stock_federal": 1, "personnel": 2}[default_dest] if default_dest in ["vente", "stock_federal", "personnel"] else 0,
                        horizontal=True,
                        key=f"dest_{job['id']}"
                    )
                    if dest_label == "stock_federal":
                        st.caption("🏛️ Qualité ≥ 750 → Stock Fédéral par défaut")
                    elif dest_label == "personnel":
                        st.caption("👤 Pas de bon de transport — les minerais vont dans ton stock personnel.")
                    delivery_loc = {"vente": "Marché (à définir)", "stock_federal": "Stock Fédération", "personnel": "Personnel"}.get(dest_label, "Marché")

                    # Session associée au job
                    job_session_id = job.get('session_id')
                    if pd.notna(job_session_id) and job_session_id:
                        st.caption(f"Session : MIN{int(job_session_id):03d}")

                    pickup_loc = st.text_input(
                        "Lieu de pickup :",
                        value=job['terminal_name'].split(' (')[0],
                        key=f"pickup_{job['id']}"
                    )
                    notes = st.text_input("Notes (optionnel) :", key=f"notes_{job['id']}")

                    if dest_label == "personnel":
                        default_loc = job['terminal_name'].split(' (')[0] if pd.notna(job.get('terminal_name')) and job.get('terminal_name') else ""
                        personal_location = st.text_input(
                            "📍 Localisation des minerais :",
                            value=default_loc,
                            placeholder="ex: Aspis Station…",
                            key=f"pers_loc_{job['id']}"
                        )
                    else:
                        personal_location = None
                        st.info("Un bon de transport sera automatiquement généré pour Camus68.")

                    col_ok, col_ko = st.columns(2)
                    with col_ok:
                        if st.button("✅ Confirmer le raffinage", type="primary", use_container_width=True, key=f"confirm_{job['id']}"):
                            result = uex.confirm_refinery_job(int(job['id']), actual_qty, quality)
                            if result:
                                if dest_label == "personnel":
                                    uex.add_personal_stock(
                                        owner=user['username'],
                                        commodity_name=result['commodity_name'],
                                        quantity=actual_qty,
                                        quality=quality,
                                        refinery_job_id=int(job['id']),
                                        location=personal_location or None
                                    )
                                    st.toast(f"✅ Raffinage confirmé — {actual_qty} SCU ajoutés à ton stock personnel !")
                                else:
                                    sess_id_for_order = int(job_session_id) if (pd.notna(job_session_id) and job_session_id) else None
                                    uex.create_transport_order(
                                        created_by=user['username'],
                                        assigned_to='Camus68',
                                        commodity_name=result['commodity_name'],
                                        quantity=actual_qty,
                                        quality=quality,
                                        pickup_location=pickup_loc,
                                        delivery_location=delivery_loc,
                                        refinery_job_id=int(job['id']),
                                        lot_id=result['lot_id'],
                                        notes=notes,
                                        session_id=sess_id_for_order,
                                        destination=dest_label
                                    )
                                    st.toast(f"✅ Raffinage confirmé — bon de transport émis pour Camus68 !")
                                st.rerun()
                    with col_ko:
                        if st.button("❌ Annuler", use_container_width=True, key=f"cancel_{job['id']}"):
                            uex.cancel_refinery_job(int(job['id']))
                            st.toast("Job annulé.")
                            st.rerun()

        # --- Stock personnel du mineur connecté ---
        st.divider()
        st.subheader("👤 Mon stock personnel")
        personal_df = uex.get_personal_stock(user['username'])
        if personal_df.empty:
            st.caption("Aucun minerai dans ton stock personnel.")
        else:
            for _, row in personal_df.iterrows():
                stock_id = int(row['id'])
                qual = int(row['quality']) if pd.notna(row['quality']) else 500
                color = "🟢" if qual >= 700 else "🟡" if qual >= 400 else "🔴"
                loc = row['location'] if pd.notna(row.get('location')) and row.get('location') else "—"
                with st.container(border=True):
                    h1, h2, h3 = st.columns([3, 1, 1])
                    h1.write(f"**{row['commodity_name']}**")
                    h2.write(f"{row['quantity']} SCU")
                    h3.write(f"{color} {qual}/1000")

                    st.caption(f"📍 **{loc}**")

                    with st.expander("🚀 Transporter vers…"):
                        dest_station = st.selectbox(
                            "Nouvelle station :",
                            _terminal_labels,
                            key=f"ps_move_{stock_id}"
                        )
                        if st.button("✔️ Confirmer le transport", key=f"ps_moveloc_{stock_id}", use_container_width=True):
                            uex.update_personal_stock_location(stock_id, dest_station.split(' (')[0])
                            st.toast(f"Minéraux déplacés vers {dest_station.split(' (')[0]}.")
                            st.rerun()

                    with st.expander("🗑️ Marquer comme consommé"):
                        consume_reason = st.selectbox(
                            "Raison :",
                            ["Vendu", "Détruit", "Perdu", "Donné", "Autre"],
                            key=f"ps_reason_{stock_id}"
                        )
                        if st.button("✔️ Confirmer", key=f"ps_consume_{stock_id}", use_container_width=True):
                            uex.consume_personal_stock(stock_id, consume_reason)
                            st.toast(f"Stock marqué '{consume_reason}'.")
                            st.rerun()

    st.divider()
    st.subheader("⛏️ Minerais en Stock")
    lots_df = uex.get_commodity_lots()
    if not lots_df.empty:
        can_block = has_permission("page_gestion_stock")
        if can_block:
            st.caption("🔒 Tu peux bloquer des lots pour le crafting — ils resteront réservés jusqu'à débloquage.")
            for _, lot in lots_df.iterrows():
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                with c1:
                    badge = "🔒" if lot['Bloqué'] else "✅"
                    st.write(f"{badge} **{lot['Minerai']}**")
                with c2:
                    st.write(f"{lot['SCU']} SCU")
                with c3:
                    qual = lot['Qualité']
                    color = "🟢" if qual >= 700 else "🟡" if qual >= 400 else "🔴"
                    st.write(f"{color} {qual}/1000")
                with c4:
                    st.caption(lot['Bloqué par'] if lot['Bloqué'] else "")
                with c5:
                    is_blocked = bool(lot['Bloqué'])
                    label = "Débloquer" if is_blocked else "Bloquer"
                    if st.button(label, key=f"block_{lot['id']}", use_container_width=True):
                        uex.toggle_lot_blocked(int(lot['id']), not is_blocked, user['username'])
                        st.rerun()
        else:
            display = lots_df[['Minerai', 'SCU', 'Qualité', 'Bloqué']].copy()
            display['Qualité'] = display['Qualité'].astype(str) + "/1000"
            display['Bloqué'] = display['Bloqué'].apply(lambda x: "🔒 Réservé" if x else "✅ Disponible")
            st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun minerai en stock.")

# --- PAGE 2 : COMMERCE ---
elif selected_page == "💰 Commerce":
    st.header("💰 Marché Public")
    comms = fetch_commodities()
    if comms:
        comm_map = {c.get('name'): c.get('id') for c in comms}
        c1, c2 = st.columns(2)
        with c1: sel_st = st.selectbox("Ressource :", sorted(comm_map.keys()), key="st_sel")
        with c2: vol_st = st.number_input("Volume (SCU) :", min_value=1, value=32, key="st_vol")

        if st.button("Calculer les points de vente", use_container_width=True):
            prices = uex.get_prices_for_item(comm_map[sel_st])
            buyers = [p for p in prices if p.get('price_sell', 0) > 0]
            st.session_state['commerce_results'] = buyers
            st.rerun()

        if st.session_state.get('commerce_results'):
            buyers = st.session_state['commerce_results']
            df_all = pd.DataFrame(buyers).sort_values(by="price_sell", ascending=False)

            systems = sorted(df_all['star_system_name'].dropna().unique().tolist())
            sys_options = ["Tous"] + systems
            sel_sys = st.radio("Système :", sys_options, horizontal=True, key="commerce_sys_filter")

            df = df_all if sel_sys == "Tous" else df_all[df_all['star_system_name'] == sel_sys]

            if df.empty:
                st.info("Aucun acheteur dans ce système.")
            else:
                scu_price_max = df.iloc[0]['price_sell']
                total_val = scu_price_max * vol_st
                st.metric(f"Valeur Marché Max ({vol_st} SCU)", f"{total_val:,} aUEC")

                def fmt_containers(s):
                    if not s:
                        return "?"
                    sizes = [int(x) for x in str(s).split(',') if x.strip().isdigit()]
                    return f"1–{max(sizes)} SCU" if sizes else "?"

                display = df[['terminal_name', 'price_sell', 'star_system_name', 'container_sizes', 'scu_sell_stock']].copy()
                display['container_sizes'] = display['container_sizes'].apply(fmt_containers)
                display['scu_sell_stock'] = display['scu_sell_stock'].apply(lambda x: f"{int(x)} SCU" if x else "—")
                display = display.rename(columns={
                    'terminal_name': 'Terminal',
                    'price_sell': 'Prix/SCU (aUEC)',
                    'star_system_name': 'Système',
                    'container_sizes': 'Caisses',
                    'scu_sell_stock': 'Qté présente',
                })
                st.dataframe(display, use_container_width=True, hide_index=True)

# --- PAGE 3 : GESTION DE STOCK FÉDÉRATION ---
elif selected_page == "📦 Gestion de stock Fédération":
    st.header("📦 Gestion de Stock Fédération")

    ca, cb = st.columns(2)
    with ca: label = st.selectbox("Catégorie :", list(CAT_MAP.keys()))
    all_items = []
    for cid in CAT_MAP[label]: all_items.extend(uex.get_items_by_category(cid))
    if all_items:
        item_data = {f"{i.get('name')} (S{i.get('size') if i.get('size') else '?'})": i for i in all_items}
        with cb: sel_item_label = st.selectbox("Modèle :", sorted(item_data.keys()))
        target = item_data[sel_item_label]
        st.divider()
        c_info, c_stock = st.columns([2, 1])
        with c_info:
            if st.button(f"🔍 Prix UEX pour {target['name']}", use_container_width=True):
                ps = uex.get_item_prices_by_id(target['id'])
                if ps: st.table(pd.DataFrame(ps).sort_values('price_buy')[['terminal_name', 'price_buy', 'star_system_name']])
        with c_stock:
            qty = st.number_input("Quantité trouvée :", min_value=1, value=1)
            if st.button("Ajouter au Stock", type="primary", use_container_width=True):
                uex.update_stock(user['username'], target['id'], target['name'], label, target.get('size', '?'), qty)
                st.toast("Inventaire mis à jour.")

    st.divider()
    st.subheader("📋 Composants en Stock")
    inventory_df = uex.get_full_inventory(can_see_hidden=True)
    if not inventory_df.empty:
        display_df = inventory_df[['Nom', 'Type', 'Qté']].rename(columns={'Type': 'Catégorie', 'Qté': 'Disponible'})
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        with st.expander("⚙️ Gérer la visibilité des composants"):
            for idx, row in inventory_df.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = "👁️" if not row['Caché'] else "🚫"
                    st.write(f"{icon} {row['Nom']}")
                with col2:
                    if st.checkbox(
                        "Caché",
                        value=bool(row['Caché']),
                        key=f"hide_item_{row['item_id']}",
                        label_visibility="collapsed"
                    ):
                        if not row['Caché']:
                            uex.toggle_item_hidden(row['item_id'], True)
                            st.toast(f"✅ {row['Nom']} caché")
                            st.rerun()
                    else:
                        if row['Caché']:
                            uex.toggle_item_hidden(row['item_id'], False)
                            st.toast(f"✅ {row['Nom']} visible")
                            st.rerun()
    else:
        st.info("Aucun composant en stock.")

    st.divider()
    st.subheader("📋 Activité des entrées")
    st.dataframe(uex.get_logs(), use_container_width=True, hide_index=True)

# --- PAGE 4 : STOCK FÉDÉRATION ---
elif selected_page == "📦 Stock Fédération":
    st.header("📦 État des Stocks & Historique")

    # Check if user can see and manage hidden items
    can_see_hidden = has_permission("page_gestion_stock")  # Only Admins and stock managers

    inventory_df = uex.get_full_inventory(can_see_hidden=can_see_hidden)
    total_components = int(inventory_df['Qté'].sum()) if not inventory_df.empty and 'Qté' in inventory_df.columns else 0
    lots_df_metric = uex.get_commodity_lots()
    total_minerals = round(lots_df_metric[lots_df_metric['Bloqué'] == 0]['SCU'].sum(), 1) if not lots_df_metric.empty else 0

    wallet = uex.get_wallet()
    fed_balance = wallet.get('balance', 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Composants en stock", f"{total_components:,}")
    m2.metric("Minerais en stock (SCU)", f"{total_minerals:,}")
    m3.metric("Solde Fédération", f"{fed_balance:,} aUEC")
    st.divider()

    inv, log = st.columns([3, 2])
    with inv:
        st.write("**🔧 Composants**")
        if not inventory_df.empty:
            display_df = inventory_df[['Nom', 'Type', 'Qté']].rename(columns={'Type': 'Catégorie', 'Qté': 'Quantité'})
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun composant en stock.")

        st.divider()
        st.write("**⛏️ Minerais**")
        lots_df = uex.get_commodity_lots()
        if not lots_df.empty:
            # N'afficher que les lots non bloqués (disponibles pour la fédé)
            dispo = lots_df[lots_df['Bloqué'] == 0][['Minerai', 'SCU', 'Qualité']].copy()
            dispo['Qualité'] = dispo['Qualité'].apply(
                lambda q: f"{'🟢' if q >= 700 else '🟡' if q >= 400 else '🔴'} {q}/1000"
            )
            st.dataframe(dispo, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun minerai en stock.")

    with log:
        st.write("**Activité des entrées**")
        st.dataframe(uex.get_logs(), use_container_width=True, hide_index=True)

# --- PAGE 5 : COMMERCE FÉDÉRATION ---
elif selected_page == "🤝 Commerce Fédération":
    st.header("🤝 Pilotage Commercial des Irréguliers")
    comms = fetch_commodities()
    fed_prices = uex.get_all_fed_prices()
    if comms:
        comm_map = {c.get('name'): c.get('id') for c in comms}

        # Inputs alignés horizontalement
        c1, c2 = st.columns(2)
        with c1:
            sel_fed = st.selectbox("Ressource à réguler :", sorted(comm_map.keys()), key="fed_sel")
        with c2:
            new_p = st.number_input("Prix d'achat Fed :", value=float(fed_prices.get(comm_map.get(sel_fed, 0), 0.0)))

        st.divider()

        # Boutons d'action
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Comparer au meilleur cours Stanton", use_container_width=True):
                prices = uex.get_prices_for_item(comm_map[sel_fed])
                buyers = [p for p in prices if p.get('price_sell', 0) > 0]
                if buyers:
                    best = max(buyers, key=lambda x: x['price_sell'])
                    st.info(f"**Référence Stanton (au SCU) :** {best['price_sell']} aUEC")
        with b2:
            if st.button("Mettre à jour le tarif Fed", type="primary", use_container_width=True):
                uex.set_fed_price(comm_map[sel_fed], new_p)
                st.rerun()

        st.divider()
        st.subheader("📋 Grille Tarifaire Interne")
        if fed_prices:
            inv_map = {v: k for k, v in comm_map.items()}
            df_fed = [{"Ressource": inv_map[id], "Prix Fédération": f"{p:,} aUEC"} for id, p in fed_prices.items()]
            st.table(pd.DataFrame(df_fed))

# --- PAGE 6 : TRANSPORT ---
elif selected_page == "🚚 Transport":
    st.header("🚚 Bons de Transport")

    can_see_all = has_permission("admin_panel")

    transport_tabs = st.tabs(["📋 Bons en attente", "🔄 En cours", "✅ Livrés"])

    status_map = {'pending': '📋 En attente', 'in_progress': '🔄 En cours', 'delivered': '✅ Livré'}

    def render_transport_orders(orders_df, show_action):
        if orders_df.empty:
            st.info("Aucun bon.")
            return
        for _, order in orders_df.iterrows():
            ql = "🟢" if order['quality'] >= 700 else "🟡" if order['quality'] >= 400 else "🔴"
            label = f"📦 {order['commodity_name']} — {order['quantity']} SCU | {ql} Q{order['quality']} | {order['created_by']} → {order['assigned_to']}"
            with st.expander(label):
                c1, c2, c3 = st.columns(3)
                c1.metric("Minerai", order['commodity_name'])
                c2.metric("Quantité", f"{order['quantity']} SCU")
                c3.metric("Qualité", f"{order['quality']}/1000")
                st.write(f"📍 **Pickup :** {order['pickup_location']}")
                st.write(f"🏁 **Livraison :** {order['delivery_location']}")
                st.write(f"👤 **Assigné à :** {order['assigned_to']} | **Émis par :** {order['created_by']}")
                if order['notes']:
                    st.caption(f"Notes : {order['notes']}")
                st.caption(f"Créé le : {order['date_created']}")

                if show_action == 'take':
                    if st.button("🚚 Prendre en charge", type="primary", use_container_width=True, key=f"take_{order['id']}"):
                        uex.update_transport_status(int(order['id']), 'in_progress', user['username'])
                        st.toast("Bon pris en charge !")
                        st.rerun()
                elif show_action == 'deliver':
                    if st.button("✅ Confirmer la livraison", type="primary", use_container_width=True, key=f"deliver_{order['id']}"):
                        uex.update_transport_status(int(order['id']), 'delivered', user['username'])
                        st.toast("Livraison confirmée — minerais ajoutés au stock Fédération !")
                        st.rerun()

    with transport_tabs[0]:
        orders = uex.get_transport_orders(
            assignee=None if can_see_all else user['username'],
            status='pending'
        )
        render_transport_orders(orders, show_action='take')

    with transport_tabs[1]:
        orders = uex.get_transport_orders(
            assignee=None if can_see_all else user['username'],
            status='in_progress'
        )
        render_transport_orders(orders, show_action='deliver')

    with transport_tabs[2]:
        orders = uex.get_transport_orders(
            assignee=None if can_see_all else user['username'],
            status='delivered'
        )
        render_transport_orders(orders, show_action=None)

# --- PAGE 7 : CRAFTING ---
elif selected_page == "🔧 Crafting":
    st.header("🔧 Crafting")

    craft_tab1, craft_tab2 = st.tabs(["🔍 Rechercher un blueprint", "🔒 Lots réservés"])

    # --- ONGLET RECHERCHE ---
    with craft_tab1:
        st.subheader("🔍 Recherche de blueprints")

        col_s, col_b = st.columns([4, 1])
        with col_s:
            search_q = st.text_input("Blueprint :", placeholder="Sniper, Shield, Quantum Drive, Armor...", label_visibility="collapsed", key="craft_search")
        with col_b:
            st.write("")
            do_search = st.button("🔍 Rechercher", use_container_width=True)

        if do_search or search_q:
            with st.spinner("Chargement depuis sc-craft.tools..."):
                data = uex.get_blueprints_from_api(search=search_q, limit=20)

            blueprints = data.get("items", [])
            total = data.get("pagination", {}).get("total", 0)

            if not blueprints:
                st.warning("Aucun blueprint trouvé. Essaie un autre terme.")
            else:
                st.caption(f"**{total}** résultat(s) — affichage des {len(blueprints)} premiers")
                st.divider()

                can_block = has_permission("crafting_stock_view")
                can_see_stock = has_permission("crafting_stock_view")

                for bp in blueprints:
                    craft_secs = bp.get("craft_time_seconds", 0)
                    if craft_secs >= 3600:
                        craft_time = f"{craft_secs//3600}h{(craft_secs%3600)//60}min"
                    elif craft_secs >= 60:
                        craft_time = f"{craft_secs//60}min {craft_secs%60}s"
                    else:
                        craft_time = f"{craft_secs}s"

                    ingredients = bp.get("ingredients", [])
                    category = bp.get("category", "?")
                    tiers = bp.get("tiers", 1)

                    # Analyse stock globale pour le badge (gradés uniquement)
                    if can_see_stock:
                        all_ok = True
                        any_missing = False
                        for ing in ingredients:
                            lots = uex.get_lots_for_ingredient(ing.get('name', ''))
                            min_q = int(ing.get('min_quality', 0))
                            required = float(ing.get('quantity_scu', 0))
                            if not lots.empty:
                                dispo = float(lots[(lots['Bloqué'] == 0) & (lots['Qualité'] >= min_q if min_q > 0 else True)]['SCU'].sum())
                            else:
                                dispo = 0
                            if dispo < required:
                                all_ok = False
                                if dispo == 0:
                                    any_missing = True
                        stock_badge = "✅" if all_ok else ("⚠️" if not any_missing else "❌")
                        label = f"{stock_badge} **{bp['name']}** — {category} | ⏱️ {craft_time} | {len(ingredients)} ingrédient(s)"
                    else:
                        label = f"**{bp['name']}** — {category} | ⏱️ {craft_time} | {len(ingredients)} ingrédient(s)"

                    if tiers > 1:
                        label += f" | 🔢 Tier {tiers}"

                    with st.expander(label):
                        if not ingredients:
                            st.info("Aucun ingrédient renseigné pour ce blueprint.")
                        else:
                            if can_see_stock:
                                # Tableau d'analyse des ingrédients avec état des stocks
                                rows = []
                                for ing in ingredients:
                                    ing_name = ing.get('name', '')
                                    required = float(ing.get('quantity_scu', 0))
                                    min_q = int(ing.get('min_quality', 0))
                                    lots = uex.get_lots_for_ingredient(ing_name)

                                    if not lots.empty:
                                        mask_qual = (lots['Qualité'] >= min_q) if min_q > 0 else pd.Series([True] * len(lots))
                                        dispo_ok = float(lots[(lots['Bloqué'] == 0) & mask_qual]['SCU'].sum())
                                        dispo_total = float(lots[lots['Bloqué'] == 0]['SCU'].sum())
                                    else:
                                        dispo_ok = 0
                                        dispo_total = 0

                                    if dispo_ok >= required:
                                        status = f"✅ {dispo_ok:.2f} SCU"
                                    elif dispo_total > 0:
                                        status = f"⚠️ {dispo_ok:.2f} SCU (qualité insuff.)"
                                    else:
                                        status = "❌ Manquant"

                                    rows.append({
                                        "Slot": ing.get("slot", "—"),
                                        "Matière": ing_name,
                                        "Requis (SCU)": required,
                                        "Qualité min": min_q if min_q > 0 else "—",
                                        "Stock disponible": status,
                                    })

                                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                            else:
                                # Vue simplifiée — ingrédients sans état des stocks
                                rows = [{"Slot": ing.get("slot", "—"), "Matière": ing.get("name", ""), "Requis (SCU)": float(ing.get("quantity_scu", 0)), "Qualité min": ing.get("min_quality", "—") or "—"} for ing in ingredients]
                                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                            # Blocage des lots pour ce craft
                            if can_block:
                                st.divider()
                                st.caption("🔒 Bloquer des lots pour ce craft :")
                                for ing in ingredients:
                                    ing_name = ing.get('name', '')
                                    required = float(ing.get('quantity_scu', 0))
                                    min_q = int(ing.get('min_quality', 0))
                                    lots = uex.get_lots_for_ingredient(ing_name)
                                    if lots.empty:
                                        continue

                                    available = lots[lots['Bloqué'] == 0]
                                    blocked = lots[lots['Bloqué'] == 1]
                                    if available.empty and blocked.empty:
                                        continue

                                    st.write(f"**{ing_name}** — requis : {required} SCU" + (f" | qualité min : {min_q}" if min_q > 0 else ""))

                                    for _, lot in lots.iterrows():
                                        color = "🟢" if lot['Qualité'] >= 700 else "🟡" if lot['Qualité'] >= 400 else "🔴"
                                        is_blocked = bool(lot['Bloqué'])
                                        c_info, c_btn = st.columns([4, 1])
                                        with c_info:
                                            locked_info = f" — 🔒 {lot['Bloqué par']}" if is_blocked else ""
                                            st.write(f"Lot #{int(lot['id'])} — {lot['SCU']} SCU | {color} Q{lot['Qualité']}{locked_info}")
                                        with c_btn:
                                            btn_label = "Débloquer" if is_blocked else "🔒 Bloquer"
                                            key = f"craftblock_{int(lot['id'])}_{bp.get('id', 0)}"
                                            if st.button(btn_label, key=key, use_container_width=True):
                                                uex.toggle_lot_blocked(int(lot['id']), not is_blocked, user['username'])
                                                st.rerun()

        else:
            st.info("Entre un terme de recherche pour trouver des blueprints (ex : Shield, Sniper, Laranite...)")

    # --- ONGLET LOTS RÉSERVÉS ---
    with craft_tab2:
        st.subheader("🔒 Lots réservés pour crafting")

        blocked_df = uex.get_blocked_lots()

        if blocked_df.empty:
            st.info("Aucun lot bloqué pour le moment.")
        else:
            # Grouper par crafteur
            crafteurs = blocked_df['Bloqué par'].dropna().unique()
            total_bloque = round(blocked_df['SCU'].sum(), 2)
            st.metric("Total SCU bloqués", f"{total_bloque} SCU")
            st.divider()

            for crafteur in crafteurs:
                lots_crafteur = blocked_df[blocked_df['Bloqué par'] == crafteur]
                total_crafteur = round(lots_crafteur['SCU'].sum(), 2)

                with st.expander(f"🔒 **{crafteur}** — {len(lots_crafteur)} lot(s) | {total_crafteur} SCU"):
                    for _, lot in lots_crafteur.iterrows():
                        color = "🟢" if lot['Qualité'] >= 700 else "🟡" if lot['Qualité'] >= 400 else "🔴"
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                        c1.write(f"**{lot['Minerai']}**")
                        c2.write(f"{lot['SCU']} SCU")
                        c3.write(f"{color} {lot['Qualité']}/1000")
                        with c4:
                            if has_permission("admin_panel"):
                                if st.button("Débloquer", key=f"unblock_admin_{int(lot['id'])}", use_container_width=True):
                                    uex.toggle_lot_blocked(int(lot['id']), False, user['username'])
                                    st.rerun()

# --- PAGE 8 : ADMIN PANEL ---
elif selected_page == "👤 Gestion Utilisateurs":
    st.header("👤 Gestion Utilisateurs")
    st.info("La gestion des utilisateurs et des rôles se fait directement sur WordPress.")
    st.markdown("[🔗 Ouvrir le panneau admin WordPress](https://darkslategray-kangaroo-550457.hostingersite.com/wp-admin/users.php)")
