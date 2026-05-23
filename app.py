import streamlit as st
from uex_library import UEXManager
import pandas as pd

st.set_page_config(page_title="Irréguliers Logistics", page_icon="🚀", layout="wide")

# Cache les appels API pour éviter les requêtes répétées
@st.cache_resource
def get_uex_manager():
    return UEXManager()

@st.cache_data(ttl=300)  # Cache 5 minutes
def fetch_commodities():
    return uex.get_commodities()

uex = get_uex_manager()

# --- SESSION STATE INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Raffineries"
if "permissions" not in st.session_state:
    st.session_state.permissions = []

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
wallet = uex.get_wallet()

st.sidebar.metric(f"Solde {user['username']}", f"{wallet.get('balance', 0):,} aUEC")
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
st.sidebar.success(f"Pilote : {user['username']}")

# Display roles
roles_str = ", ".join([r['name'] for r in user['roles']])
st.sidebar.info(f"Rôles : {roles_str}")

if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_page = "Raffineries"
    st.session_state.permissions = []
    st.rerun()

# --- MAIN CONTENT ---
st.title("🛸 Les Irréguliers - Hub Logistique")

# --- PAGE 1 : RAFFINERIES ---
if selected_page == "🏗️ Raffineries":
    st.header("🏗️ Raffineries")

    tab_estim, tab_confirm = st.tabs(["🔬 Nouvelle estimation", "⏳ Jobs en attente"])

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
            terminal_map = {f"{t['name']} ({t.get('star_system_name', '?')})": t for t in terminals if t.get('name')}
            method_map = {m['name']: m for m in methods}

            # Init session state
            if 'refinery_lines' not in st.session_state:
                st.session_state['refinery_lines'] = []
            if 'refinery_estimates' not in st.session_state:
                st.session_state['refinery_estimates'] = []

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
                    ql = "🟢" if line['quality'] >= 700 else "🟡" if line['quality'] >= 400 else "🔴"
                    r1, r2, r3, r4 = st.columns([3, 2, 2, 1])
                    r1.write(f"**{line['commodity_name']}**")
                    r2.write(f"{line['quantity']} SCU brut")
                    r3.write(f"{ql} Qualité {line['quality']}/1000")
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
                    with st.expander(f"**{est['commodity_name']}** — {est['quantity']} SCU brut | {ql} Qualité {est['quality']} → ~{est['estimated_output']} SCU raffiné", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("SCU brut", f"{est['quantity']} SCU")
                        col2.metric("SCU raffiné estimé", f"{est['estimated_output']} SCU")
                        col3.metric("Rendement", f"{est['yield_pct']}%")
                        local_info = f" dont {est.get('local_count', 0)} locaux" if est.get('local_count', 0) > 0 else ""
                        st.caption(f"{conf_color} Confiance : {est['confidence']} ({est['audit_count']} audits{local_info}) | {est['method_display']} | {est['terminal_name']}")

                        col_corr, col_qual = st.columns(2)
                        with col_corr:
                            corrected = st.number_input(
                                "Corriger SCU raffiné :",
                                min_value=0.0, value=float(est['estimated_output']), step=0.5,
                                key=f"corr_{i}"
                            )
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
                                    est['confidence'], est['audit_count']
                                )
                                st.session_state['pending_quality'] = st.session_state.get('pending_quality', {})
                                st.session_state['pending_quality'][est['commodity_id']] = quality_final
                                st.session_state['refinery_estimates'][i]['saved'] = True
                                st.toast(f"✅ Lot {est['commodity_name']} enregistré !")
                                st.rerun()
                        else:
                            st.success("✅ Enregistré")

                if st.button("✅ Enregistrer tous les lots restants", use_container_width=True):
                    for i, est in enumerate(st.session_state['refinery_estimates']):
                        if not est.get('saved'):
                            uex.create_refinery_job(
                                user['username'],
                                est['commodity_id'], est['commodity_name'],
                                est['terminal_id'], est['terminal_name'],
                                est['method'], est['quantity'],
                                est['estimated_output'], est['yield_pct'],
                                est['confidence'], est['audit_count']
                            )
                    st.session_state['refinery_lines'] = []
                    st.session_state['refinery_estimates'] = []
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
                label = f"⛏️ {job['commodity_name']} — {job['quantity_raw']} SCU → ~{job['quantity_estimated']} SCU | {job['user']} | {job['date_created']}"
                with st.expander(label):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Brut entré", f"{job['quantity_raw']} SCU")
                    col2.metric("Estimé raffiné", f"{job['quantity_estimated']} SCU")
                    col3.metric("Rendement", f"{job['yield_rate']}%")
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
                        default_quality = st.session_state.get('pending_quality', {}).get(int(job['commodity_id']), 500)
                        quality = st.number_input(
                            "Qualité du lot (1–1000) :",
                            min_value=1, max_value=1000, value=default_quality,
                            key=f"quality_{job['id']}"
                        )
                        ql = "🟢" if quality >= 700 else "🟡" if quality >= 400 else "🔴"
                        st.caption(f"{ql} {quality}/1000")

                    pickup_loc = st.text_input(
                        "Lieu de pickup :",
                        value=job['terminal_name'].split(' (')[0],
                        key=f"pickup_{job['id']}"
                    )
                    notes = st.text_input("Notes (optionnel) :", key=f"notes_{job['id']}")

                    st.info("Un bon de transport sera automatiquement généré pour Camus68.")

                    col_ok, col_ko = st.columns(2)
                    with col_ok:
                        if st.button("✅ Confirmer le raffinage", type="primary", use_container_width=True, key=f"confirm_{job['id']}"):
                            result = uex.confirm_refinery_job(int(job['id']), actual_qty, quality)
                            if result:
                                uex.create_transport_order(
                                    created_by=user['username'],
                                    assigned_to='Camus68',
                                    commodity_name=result['commodity_name'],
                                    quantity=actual_qty,
                                    quality=quality,
                                    pickup_location=pickup_loc,
                                    delivery_location="Stock Fédération",
                                    refinery_job_id=int(job['id']),
                                    lot_id=result['lot_id'],
                                    notes=notes
                                )
                                st.toast(f"✅ Raffinage confirmé — bon de transport émis pour Camus68 !")
                                st.rerun()
                    with col_ko:
                        if st.button("❌ Annuler", use_container_width=True, key=f"cancel_{job['id']}"):
                            uex.cancel_refinery_job(int(job['id']))
                            st.toast("Job annulé.")
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
            if buyers:
                df = pd.DataFrame(buyers).sort_values(by="price_sell", ascending=False)
                scu_price_max = df.iloc[0]['price_sell']
                total_val = scu_price_max * vol_st

                st.metric(f"Valeur Marché Max ({vol_st} SCU)", f"{total_val:,} aUEC")
                st.table(df[['terminal_name', 'price_sell', 'star_system_name']].rename(columns={'terminal_name':'Terminal', 'price_sell':'Prix Unit'}))

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

    m1, m2 = st.columns(2)
    m1.metric("Composants en stock", f"{total_components:,}")
    m2.metric("Minerais en stock (SCU)", f"{total_minerals:,}")
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

                can_block = has_permission("page_crafting")

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

                    # Analyse stock globale pour le badge
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
                    if tiers > 1:
                        label += f" | 🔢 Tier {tiers}"

                    with st.expander(label):
                        if not ingredients:
                            st.info("Aucun ingrédient renseigné pour ce blueprint.")
                        else:
                            # Tableau d'analyse des ingrédients
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
