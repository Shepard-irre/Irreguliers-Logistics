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
from dotenv import load_dotenv

load_dotenv()

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


class WPAuth:
    def __init__(self, wp_url=None):
        self.wp_url = (wp_url or os.getenv('WP_URL', '')).rstrip('/')
        self.jwt_endpoint = f"{self.wp_url}/wp-json/jwt-auth/v1/token"
        self.users_endpoint = f"{self.wp_url}/wp-json/wp/v2/users/me"

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

            # Mappe les rôles WP/UM → permissions app
            perms = set()
            role_names = []
            for role in wp_roles:
                if role in UM_ROLE_PERMISSIONS:
                    perms.update(UM_ROLE_PERMISSIONS[role])
                    role_names.append(role)

            return {
                "id": user_id,
                "username": display_name,
                "email": email,
                "roles": [{"id": r, "name": r} for r in role_names],
                "permissions": list(perms),
                "token": token
            }

        except Exception as e:
            return None

    def get_permissions_from_roles(self, wp_roles):
        """Calcule les permissions à partir d'une liste de rôles WP/UM."""
        perms = set()
        for role in wp_roles:
            perms.update(UM_ROLE_PERMISSIONS.get(role, []))
        return list(perms)
