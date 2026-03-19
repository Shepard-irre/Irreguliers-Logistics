import streamlit as st
from uex_library import UEXManager
import pandas as pd

st.set_page_config(page_title="Irréguliers Logistics", page_icon="🚀", layout="wide")
uex = UEXManager()

# --- CONFIGURATION ---
CURRENT_USER = "Shepard40"
USER_GROUPS = ["Commercial", "Industrie"] 
CAT_MAP = {
    "🌌 Moteurs Quantum (QT Drive)": [22, 86],
    "🛡️ Boucliers (Shields)": [23],
    "⚡ Générateurs (Power Plants)": [21, 83],
    "⚔️ Armement Vaisseaux": [32, 70, 79, 90],
    "⛏️ Minage (Lasers & Modules)": [29, 30, 74],
    "🛰️ Avionique & Radar": [82, 65]
}

# --- SIDEBAR ---
wallet = uex.get_wallet()
st.sidebar.metric(f"Solde {CURRENT_USER}", f"{wallet.get('balance', 0):,} aUEC")
st.sidebar.divider()
st.sidebar.success(f"Pilote : {CURRENT_USER}")
st.sidebar.info(f"Accès : {', '.join(USER_GROUPS)}")

# --- MAIN ---
st.title("🛸 Les Irréguliers - Hub Logistique")
tabs = st.tabs(["🏗️ Raffineries", "💰 Commerce Stanton", "💹 Bourse & Entrées", "📦 Stock Fédération", "🤝 Commerce Fédération"])

# --- TAB 2 : COMMERCE STANTON ---
with tabs[1]:
    st.header("💰 Marché Public de Stanton")
    comms = uex.get_commodities()
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
                st.metric(f"Valeur Marché Max", f"{df.iloc[0]['price_sell'] * 100 * vol_st:,} aUEC")
                st.table(df[['terminal_name', 'price_sell', 'star_system_name']].rename(columns={'terminal_name':'Terminal', 'price_sell':'Prix Unit'}))

# --- TAB 3 : BOURSE & ENTRÉES ---
with tabs[2]:
    st.header("💹 Recherche & Entrée en Stock")
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
            if st.button("Ajouter au stock Camus68", type="primary", use_container_width=True):
                uex.update_stock(CURRENT_USER, target['id'], target['name'], label, target.get('size', '?'), qty)
                st.toast("Inventaire mis à jour.")

# --- TAB 4 : STOCK FÉDÉRATION ---
with tabs[3]:
    st.header("📦 État des Stocks & Historique")
    inv, log = st.columns([3, 2])
    with inv: st.dataframe(uex.get_full_inventory(), use_container_width=True, hide_index=True)
    with log: st.dataframe(uex.get_logs(), use_container_width=True, hide_index=True)

# --- TAB 5 : COMMERCE FÉDÉRATION ---
with tabs[4]:
    st.header("🤝 Pilotage Commercial des Irréguliers")
    comms = uex.get_commodities()
    fed_prices = uex.get_all_fed_prices()
    if comms:
        comm_map = {c.get('name'): c.get('id') for c in comms}
        c_search, c_admin = st.columns([2, 1])
        with c_search:
            sel_fed = st.selectbox("Ressource à réguler :", sorted(comm_map.keys()), key="fed_sel")
            if st.button("Comparer au meilleur cours Stanton", use_container_width=True):
                prices = uex.get_prices_for_item(comm_map[sel_fed])
                buyers = [p for p in prices if p.get('price_sell', 0) > 0]
                if buyers:
                    best = max(buyers, key=lambda x: x['price_sell'])
                    st.info(f"**Référence Stanton :** {best['price_sell']} aUEC (à {best['terminal_name']})")
        with c_admin:
            if "Commercial" in USER_GROUPS:
                st.subheader("🛠️ Régulation")
                new_p = st.number_input("Prix d'achat Fed :", value=float(fed_prices.get(comm_map[sel_fed], 0.0)))
                if st.button("Mettre à jour le tarif Fed", type="primary"):
                    uex.set_fed_price(comm_map[sel_fed], new_p)
                    st.rerun()
    st.divider()
    st.subheader("📋 Grille Tarifaire Interne")
    if fed_prices:
        inv_map = {v: k for k, v in comm_map.items()}
        df_fed = [{"Ressource": inv_map[id], "Prix Fédération": f"{p:,} aUEC"} for id, p in fed_prices.items()]
        st.table(pd.DataFrame(df_fed))