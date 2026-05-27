"""
Module d'authentification WordPress — remplace la couche SQLite users/roles.
Utilise JWT Authentication for WP REST API.

Usage dans uex_library.py :
    from wp_auth import WPAuth
    wp_auth = WPAuth()
    user = wp_auth.authenticate(username, password)
"""

import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

# Mapping rôles WP/UM → labels lisibles pour l'UI
# Généré depuis wp_options (um_role_*_meta) le 28/05/2026
UM_ROLE_LABELS = {
    "administrator":                    "Administrateur",
    # Grades
    "um_sky-marshall":                  "Sky Marshall",
    "um_amiral":                        "Amiral",
    "um_star-commander":                "Star Commander",
    "um_commander":                     "Commander",
    "um_lieutenant":                    "Lieutenant",
    "um_sous-lieutenant":               "Sous-Lieutenant",
    "um_enseigne":                      "Enseigne",
    "um_cadet":                         "Cadet",
    "um_recrue":                        "Recrue",
    "um_voyageur":                      "Voyageur",
    "um_civil":                         "Civil",
    "um_armurier":                      "Armurier",
    # Divisions nommées
    "um_industrie":                     "Industrie",
    "um_navale":                        "Navale",
    "um_infanterie-mobile":             "Infanterie Mobile",
    "um_division_marine-marchande":     "Marine Marchande",
    "um_division_pilotes":              "Pilotes",
    "um_division_maraudeurs":           "Maraudeurs",
    "um_genie_industriel":              "Génie Industriel",
    "um_entretien":                     "Entretien",
    # Métiers nommés
    "metier_transport":                 "Transport",
    "metier_mecanicien":                "Mécanicien",
    # Divisions custom (um_role_custom_role_X_meta → name = division_*)
    "um_custom_role_1":                 "Recherche & Développement",
    "um_custom_role_2":                 "Génie Industriel",
    "um_custom_role_3":                 "Médical Core",
    "um_custom_role_4":                 "Opérateurs",
    # Métiers custom (um_role_custom_role_X_meta → name = métier_*)
    "um_custom_role_5":                 "Mineur",
    "um_custom_role_6":                 "Support",
    "um_custom_role_7":                 "Recycleur",
    "um_custom_role_8":                 "Constructeur",
    "um_custom_role_9":                 "Technicien Réparateur",
    "um_custom_role_10":                "Chercheur",
    "um_custom_role_11":                "Trappeur",
    "um_custom_role_12":                "Sauveteur",
    "um_custom_role_13":                "Explorateur",
    "um_custom_role_14":                "Producteur",
    "um_custom_role_15":                "Transporteur",
    "um_custom_role_16":                "Commerçant",
    "um_custom_role_17":                "Expert en Récupération",
    "um_custom_role_18":                "Star Marine",
    "um_custom_role_19":                "Appui Observateur",
    "um_custom_role_20":                "Force Spéciale",
    "um_custom_role_21":                "U.D.I.C",
    "um_custom_role_22":                "B.V.M",
    "um_custom_role_23":                "U.D.I.M",
    "um_custom_role_24":                "Médecin de Bord",
    "um_custom_role_25":                "Pilote de Combat / Escorteur",
    "um_custom_role_26":                "Dropship",
    "um_custom_role_27":                "Pilote Capitalship",
    "um_custom_role_28":                "Navigateur / Technicien de Bord",
    "um_custom_role_29":                "Ingénieur",
    "um_custom_role_30":                "Crafteur",
}

# Mapping rôles Ultimate Member → permissions app
UM_ROLE_PERMISSIONS = {
    # Grades militaires
    "administrator":            ["admin_panel", "page_raffineries", "page_commerce", "page_gestion_stock",
                                 "page_stock_federation", "page_commerce_federation", "page_transport", "page_crafting"],
    "um_amiral":                ["page_raffineries", "page_commerce", "page_gestion_stock",
                                 "page_stock_federation", "page_commerce_federation", "page_crafting"],
    "um_star-commander":        ["page_raffineries", "page_commerce", "page_gestion_stock",
                                 "page_stock_federation", "page_commerce_federation", "page_crafting"],
    "um_commander":             ["page_raffineries", "page_commerce", "page_gestion_stock",
                                 "page_stock_federation", "page_commerce_federation", "page_crafting"],
    "um_lieutenant":            ["page_commerce", "page_stock_federation", "page_commerce_federation"],
    "um_sous-lieutenant":       ["page_commerce", "page_stock_federation", "page_commerce_federation"],
    "um_enseigne":              ["page_stock_federation", "page_commerce"],
    "um_cadet":                 ["page_stock_federation", "page_commerce"],
    "um_recrue":                ["page_stock_federation"],
    "um_voyageur":              ["page_stock_federation"],

    # Divisions
    "um_industrie":             ["page_raffineries", "page_gestion_stock", "page_crafting"],
    "um_navale":                ["page_stock_federation", "page_commerce"],
    "um_infanterie-mobile":     ["page_stock_federation", "page_commerce"],
    "um_division_marine-marchande": ["page_transport", "page_stock_federation"],
    "um_division_pilotes":      ["page_stock_federation", "page_commerce"],
    "um_entretien":             ["page_stock_federation"],

    # Métiers
    "metier_transport":         ["page_transport", "page_stock_federation"],
    "metier_mecanicien":        ["page_gestion_stock", "page_stock_federation"],
}


def _load_dynamic_labels_from_db():
    """
    Charge les labels de rôles depuis la DB WP si les vars WP_DB_* sont définies.
    Retourne un dict {wp_slug: label} ou None si indisponible.
    """
    host = os.getenv('WP_DB_HOST')
    user = os.getenv('WP_DB_USER')
    password = os.getenv('WP_DB_PASSWORD')
    database = os.getenv('WP_DB_NAME')
    if not all([host, user, password, database]):
        return None
    try:
        import pymysql
        conn = pymysql.connect(
            host=host, user=user, password=password, database=database,
            connect_timeout=5, charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT option_name, option_value FROM wp_options "
            "WHERE option_name LIKE 'um_role_%_meta'"
        )
        rows = cursor.fetchall()
        conn.close()

        labels = {}
        for option_name, option_value in rows:
            slug = option_name[len('um_role_'):-len('_meta')]
            wp_slug = 'um_' + slug
            m = re.search(r's:4:"name";s:\d+:"([^"]+)"', option_value)
            if not m:
                continue
            raw = m.group(1)
            try:
                raw = raw.encode('latin1').decode('utf-8')
            except Exception:
                pass
            for prefix in ('division_', 'métier_', 'metier_'):
                if raw.lower().startswith(prefix):
                    raw = raw[len(prefix):]
                    break
            raw = raw.strip()
            if raw:
                labels[wp_slug] = raw[0].upper() + raw[1:]
        return labels if labels else None
    except Exception:
        return None


class WPAuth:
    def __init__(self, wp_url=None):
        self.wp_url = (wp_url or os.getenv('WP_URL', '')).rstrip('/')
        self.jwt_endpoint = f"{self.wp_url}/wp-json/jwt-auth/v1/token"
        self.users_endpoint = f"{self.wp_url}/wp-json/wp/v2/users/me"
        # Tente de charger les labels dynamiquement depuis la DB WP
        dynamic = _load_dynamic_labels_from_db()
        self._role_labels = dict(UM_ROLE_LABELS)
        if dynamic:
            self._role_labels.update(dynamic)

    def authenticate(self, username, password):
        """
        Authentifie via JWT WP REST API.
        Retourne dict {id, username, roles, email} ou None.
        """
        try:
            resp = requests.post(
                self.jwt_endpoint,
                json={"username": username, "password": password},
                timeout=10
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            token = data.get('token')
            if not token:
                return None

            # Récupère les infos utilisateur avec le token (context=edit pour avoir les rôles)
            me = requests.get(
                self.users_endpoint + "?context=edit",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            ).json()

            user_id = me.get('id')
            display_name = me.get('name', username)
            email = me.get('email', '')
            wp_roles = me.get('roles', [])

            # Tous les rôles pour l'affichage, permissions calculées séparément
            perms = set()
            for role in wp_roles:
                perms.update(UM_ROLE_PERMISSIONS.get(role, []))

            return {
                "id": user_id,
                "username": display_name,
                "email": email,
                "roles": [{"id": r, "name": self._role_labels.get(r, r)} for r in wp_roles],
                "permissions": list(perms),
                "token": token
            }

        except Exception as e:
            return None

    def authenticate_with_token(self, token):
        """
        Valide un JWT existant via /users/me — utilisé pour le SSO WP → Streamlit.
        Retourne dict {id, username, roles, email} ou None.
        """
        try:
            me = requests.get(
                self.users_endpoint + "?context=edit",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if me.status_code != 200:
                return None
            me = me.json()

            user_id = me.get('id')
            display_name = me.get('name', '')
            email = me.get('email', '')
            wp_roles = me.get('roles', [])

            perms = set()
            for role in wp_roles:
                perms.update(UM_ROLE_PERMISSIONS.get(role, []))

            return {
                "id": user_id,
                "username": display_name,
                "email": email,
                "roles": [{"id": r, "name": self._role_labels.get(r, r)} for r in wp_roles],
                "permissions": list(perms),
                "token": token
            }
        except Exception:
            return None

    def get_permissions_from_roles(self, wp_roles):
        """Calcule les permissions à partir d'une liste de rôles WP/UM."""
        perms = set()
        for role in wp_roles:
            perms.update(UM_ROLE_PERMISSIONS.get(role, []))
        return list(perms)
