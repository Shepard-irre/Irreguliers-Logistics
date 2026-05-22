import requests
import os
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from wp_auth import WPAuth

load_dotenv()

_wp_auth = WPAuth() if os.getenv('WP_URL') else None

class UEXManager:
    def __init__(self):
        self.base_url = "https://api.uexcorp.space/2.0"
        self.headers = {
            "Authorization": f"Bearer {os.getenv('UEX_BEARER_TOKEN')}",
            "secret-key": os.getenv('UEX_SECRET_KEY')
        }
        self.db_path = 'irr_inventory.db'

        # Permission and role constants
        self.PERMISSIONS = {
            "page_raffineries": "Raffineries",
            "page_commerce": "Commerce",
            "page_gestion_stock": "Gestion de Stock Fédération",
            "page_stock_federation": "Stock Fédération",
            "page_commerce_federation": "Commerce Fédération",
            "page_transport": "Transport",
            "page_crafting": "Crafting",
            "admin_panel": "Admin Panel"
        }

        self.ROLE_DEFAULTS = {
            "Administrateurs": ["admin_panel", "page_raffineries", "page_commerce", "page_gestion_stock", "page_stock_federation", "page_commerce_federation", "page_transport", "page_crafting"],
            "Amiraux": ["page_raffineries", "page_commerce", "page_gestion_stock", "page_stock_federation", "page_commerce_federation", "page_crafting"],
            "Lieutenants": ["page_commerce", "page_stock_federation", "page_commerce_federation"],
            "Membres": ["page_stock_federation", "page_commerce"],
            "Mineurs": ["page_raffineries", "page_gestion_stock", "page_stock_federation", "page_commerce"],
            "Crafteurs": ["page_gestion_stock", "page_commerce", "page_crafting"],
            "Commerciaux": ["page_commerce", "page_commerce_federation"],
            "Gestion des stocks federation": ["page_gestion_stock", "page_stock_federation", "page_commerce"],
            "Marine Marchande": ["page_transport", "page_stock_federation", "page_commerce"]
        }

        self.init_db()

    def _get_data(self, endpoint, params=None):
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception:
            return []

    # --- API ACCESS ---
    def get_items_by_category(self, cat_id):
        return self._get_data("items", params={"id_category": cat_id})

    def get_item_prices_by_id(self, item_id):
        return self._get_data("items_prices", params={"id_item": item_id})

    def get_commodities(self):
        return self._get_data("commodities")

    def get_prices_for_item(self, commodity_id):
        return self._get_data("commodities_prices", params={"id_commodity": commodity_id})

    def get_wallet(self):
        data = self._get_data("wallet_balance")
        return data if isinstance(data, dict) else {"balance": 0}

    # --- DATABASE ENGINE ---
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            # Create existing tables if they don't exist
            c.execute('''CREATE TABLE IF NOT EXISTS inventory
                         (item_id INTEGER PRIMARY KEY, name TEXT, category TEXT, size TEXT, quantity INTEGER, is_hidden INTEGER DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS logs
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, item_name TEXT, qty INTEGER, timestamp DATETIME)''')
            c.execute('''CREATE TABLE IF NOT EXISTS fed_prices
                         (commodity_id INTEGER PRIMARY KEY, price_fed REAL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS commodity_stock
                         (commodity_id INTEGER PRIMARY KEY, name TEXT, quantity REAL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS commodity_lots
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          commodity_id INTEGER NOT NULL,
                          commodity_name TEXT NOT NULL,
                          quantity REAL NOT NULL,
                          quality INTEGER NOT NULL DEFAULT 500,
                          is_blocked INTEGER DEFAULT 0,
                          blocked_by TEXT,
                          refinery_job_id INTEGER,
                          date_added DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS transport_orders
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          created_by TEXT NOT NULL,
                          assigned_to TEXT DEFAULT 'Camus68',
                          commodity_name TEXT NOT NULL,
                          quantity REAL NOT NULL,
                          quality INTEGER NOT NULL,
                          pickup_location TEXT NOT NULL,
                          delivery_location TEXT NOT NULL,
                          refinery_job_id INTEGER,
                          lot_id INTEGER,
                          status TEXT DEFAULT 'pending',
                          notes TEXT,
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                          date_taken DATETIME,
                          date_delivered DATETIME)''')
            c.execute('''CREATE TABLE IF NOT EXISTS refinery_jobs
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user TEXT NOT NULL,
                          commodity_id INTEGER NOT NULL,
                          commodity_name TEXT NOT NULL,
                          terminal_id INTEGER NOT NULL,
                          terminal_name TEXT NOT NULL,
                          method TEXT NOT NULL,
                          quantity_raw REAL NOT NULL,
                          quantity_estimated REAL NOT NULL,
                          yield_rate REAL NOT NULL,
                          confidence TEXT,
                          audit_count INTEGER DEFAULT 0,
                          status TEXT DEFAULT 'pending',
                          quantity_actual REAL,
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                          date_confirmed DATETIME)''')

            # Create new multi-role tables
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE NOT NULL,
                          password_hash TEXT NOT NULL,
                          email TEXT,
                          is_active INTEGER DEFAULT 1,
                          date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            c.execute('''CREATE TABLE IF NOT EXISTS roles
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT UNIQUE NOT NULL,
                          description TEXT,
                          is_system INTEGER DEFAULT 0,
                          is_active INTEGER DEFAULT 1,
                          date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            c.execute('''CREATE TABLE IF NOT EXISTS user_roles
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          user_id INTEGER NOT NULL,
                          role_id INTEGER NOT NULL,
                          date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          UNIQUE(user_id, role_id),
                          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                          FOREIGN KEY(role_id) REFERENCES roles(id))''')

            c.execute('''CREATE TABLE IF NOT EXISTS role_permissions
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          role_id INTEGER NOT NULL,
                          permission TEXT NOT NULL,
                          UNIQUE(role_id, permission),
                          FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE)''')

            conn.commit()

        # Migrate existing schema if needed
        self._migrate_schema()

        # Initialize roles and migrate data if needed
        self._init_roles_and_migrate()

    def _migrate_schema(self):
        """Add missing columns to existing tables"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Check if is_hidden column exists in inventory table
            c.execute("PRAGMA table_info(inventory)")
            columns = [row[1] for row in c.fetchall()]

            if 'is_hidden' not in columns:
                try:
                    c.execute("ALTER TABLE inventory ADD COLUMN is_hidden INTEGER DEFAULT 0")
                    conn.commit()
                except Exception:
                    pass  # Column might already exist

            # Nettoyer le suffixe "(raw)" / "(Raw)" / "(Ore)" dans toutes les tables
            for table, col in [
                ("commodity_lots", "commodity_name"),
                ("commodity_stock", "name"),
                ("transport_orders", "commodity_name"),
                ("refinery_jobs", "commodity_name"),
            ]:
                try:
                    c.execute(f"""UPDATE {table}
                                  SET {col} = TRIM(
                                      REPLACE(REPLACE(REPLACE(REPLACE(
                                          {col},
                                          ' (Raw)', ''), '(Raw)', ''),
                                          ' (raw)', ''), '(raw)', '')
                                  )
                                  WHERE LOWER({col}) LIKE '%(raw)%'""")
                except Exception:
                    pass
            conn.commit()

            # Sync permissions pour tous les rôles système selon ROLE_DEFAULTS
            for role_name, perms in self.ROLE_DEFAULTS.items():
                c.execute("SELECT id FROM roles WHERE name=?", (role_name,))
                result = c.fetchone()
                if result:
                    role_id = result[0]
                    for perm in perms:
                        c.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission) VALUES (?, ?)",
                                 (role_id, perm))
            conn.commit()

    def _init_roles_and_migrate(self):
        """Initialize system roles and migrate old data if present"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            # Check if roles table is empty
            c.execute("SELECT COUNT(*) FROM roles")
            roles_count = c.fetchone()[0]

            if roles_count == 0:
                # Create system roles
                for role_name, permissions in self.ROLE_DEFAULTS.items():
                    c.execute("INSERT INTO roles (name, description, is_system) VALUES (?, ?, 1)",
                             (role_name, f"System role: {role_name}"))
                    role_id = c.lastrowid

                    # Add permissions for this role
                    for perm in permissions:
                        c.execute("INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
                                 (role_id, perm))

                conn.commit()

            # Check for old migration (users with 'role' column)
            c.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in c.fetchall()]

            if 'role' in columns:
                # Migrate old data to new structure
                c.execute("SELECT id, username, password_hash, role, is_active FROM users")
                old_users = c.fetchall()

                for user_id, username, password_hash, old_role, is_active in old_users:
                    # Update user record (remove role field)
                    c.execute("UPDATE users SET is_active=? WHERE id=?", (is_active, user_id))

                    # Assign appropriate role
                    if old_role == "admin":
                        role_name = "Administrateurs"
                    else:
                        role_name = "Membres"

                    c.execute("SELECT id FROM roles WHERE name=?", (role_name,))
                    role_result = c.fetchone()
                    if role_result:
                        role_id = role_result[0]
                        c.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                                 (user_id, role_id))

                conn.commit()

        # Initialize default users if none exist
        self._init_default_users()

    def _init_default_users(self):
        """Create default users if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            if c.fetchone()[0] == 0:
                # Create default users
                default_users = [
                    ("Shepard40", self._hash_password("sc1234"), None),
                    ("Darkias", self._hash_password("sc1234"), None),
                    ("Camus", self._hash_password("sc1234"), None)
                ]

                for username, password_hash, email in default_users:
                    c.execute("INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, 1)",
                             (username, password_hash, email))
                    user_id = c.lastrowid

                    # Assign roles
                    if username in ["Shepard40", "Darkias"]:
                        role_name = "Administrateurs"
                    else:
                        role_name = "Membres"

                    c.execute("SELECT id FROM roles WHERE name=?", (role_name,))
                    role_result = c.fetchone()
                    if role_result:
                        role_id = role_result[0]
                        c.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                                 (user_id, role_id))

                conn.commit()

    def update_stock(self, user, item_id, name, category, size, delta):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT quantity FROM inventory WHERE item_id=?", (item_id,))
            row = c.fetchone()
            if row:
                new_qty = max(0, row[0] + delta)
                c.execute("UPDATE inventory SET quantity=? WHERE item_id=?", (new_qty, item_id))
            else:
                if delta > 0:
                    c.execute("INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?)", (item_id, name, category, str(size), delta, 0))

            action_type = "ENTRÉE" if delta > 0 else "SORTIE"
            c.execute("INSERT INTO logs (user, action, item_name, qty, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (user, action_type, name, abs(delta), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    # --- REFINERY API ---
    def get_refinable_commodities(self):
        comms = self._get_data("commodities")
        return [c for c in comms if c.get('is_refinable') == 1]

    def get_refinery_terminals(self):
        return self._get_data("terminals", params={"type": "refinery"})

    def get_refinery_methods(self):
        return self._get_data("refineries_methods")

    def calculate_refinery_estimate(self, commodity_id, terminal_id, method_code, quantity):
        # --- Données locales (jobs confirmés par nos mineurs) ---
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Exact : même terminal + méthode + minerai
            c.execute("""SELECT quantity_raw, quantity_actual FROM refinery_jobs
                         WHERE commodity_id=? AND terminal_id=? AND method=?
                         AND status='confirmed' AND quantity_actual > 0 AND quantity_raw > 0""",
                      (commodity_id, terminal_id, method_code))
            local_specific = c.fetchall()
            # Moins précis : même méthode + minerai, toutes stations
            c.execute("""SELECT quantity_raw, quantity_actual FROM refinery_jobs
                         WHERE commodity_id=? AND method=?
                         AND status='confirmed' AND quantity_actual > 0 AND quantity_raw > 0""",
                      (commodity_id, method_code))
            local_general = c.fetchall()

        local_specific_rates = [r[1] / r[0] for r in local_specific]
        local_general_rates  = [r[1] / r[0] for r in local_general]

        # --- Audits UEX (communauté) ---
        all_audits = self._get_data("refineries_audits")
        uex_relevant = [a for a in all_audits
                        if a.get('id_commodity') == commodity_id
                        and a.get('method') == method_code]
        uex_rates = [a['quantity_yield'] / a['quantity']
                     for a in uex_relevant if a.get('quantity', 0) > 0]

        # --- Calcul du rendement de base ---
        # Priorité : local exact > local général > UEX > fallback méthode
        local_count = 0
        if local_specific_rates:
            # Données locales exactes : poids triple vs UEX
            all_rates = local_specific_rates * 3 + uex_rates
            base_yield = sum(all_rates) / len(all_rates)
            local_count = len(local_specific_rates)
            n = local_count + len(uex_rates)
            confidence = "🏆 Locale (même station)" if local_count >= 3 else "📍 Locale (données initiales)"
        elif local_general_rates:
            # Données locales autres stations : poids double
            all_rates = local_general_rates * 2 + uex_rates
            base_yield = sum(all_rates) / len(all_rates)
            local_count = len(local_general_rates)
            n = local_count + len(uex_rates)
            confidence = "📊 Locale (autres stations)"
        elif uex_rates:
            base_yield = sum(uex_rates) / len(uex_rates)
            n = len(uex_rates)
            confidence = "Élevée" if n >= 10 else "Moyenne" if n >= 3 else "Faible"
        else:
            methods = self.get_refinery_methods()
            m = next((x for x in methods
                      if x.get('name', '').lower().replace(' ', '_') == method_code), None)
            base_yield = 0.70 + (m.get('rating_yield', 2) - 1) * 0.07 if m else 0.80
            n = 0
            confidence = "Très faible (aucune donnée)"

        # --- Modificateur de la station (UEX) ---
        yields_data = self._get_data("refineries_yields")
        terminal_yield = next((y for y in yields_data
                               if y.get('id_terminal') == terminal_id
                               and y.get('id_commodity') == commodity_id), None)
        modifier = (terminal_yield.get('value', 0) / 100) if terminal_yield else 0.0

        final_yield = max(0.0, min(1.0, base_yield + modifier))
        return {
            'estimated_output': round(quantity * final_yield, 1),
            'yield_pct': round(final_yield * 100, 1),
            'base_yield_pct': round(base_yield * 100, 1),
            'terminal_modifier': terminal_yield.get('value', 0) if terminal_yield else 0,
            'confidence': confidence,
            'audit_count': n,
            'local_count': local_count
        }

    # --- REFINERY JOBS ---
    def create_refinery_job(self, user, commodity_id, commodity_name, terminal_id,
                            terminal_name, method, quantity_raw, quantity_estimated,
                            yield_rate, confidence, audit_count):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO refinery_jobs
                         (user, commodity_id, commodity_name, terminal_id, terminal_name,
                          method, quantity_raw, quantity_estimated, yield_rate, confidence,
                          audit_count, status, date_created)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                      (user, commodity_id, commodity_name, terminal_id, terminal_name,
                       method, quantity_raw, quantity_estimated, yield_rate, confidence,
                       audit_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return c.lastrowid

    def get_pending_refinery_jobs(self, user=None):
        with sqlite3.connect(self.db_path) as conn:
            if user:
                df = pd.read_sql_query(
                    "SELECT * FROM refinery_jobs WHERE status='pending' AND user=? ORDER BY date_created DESC",
                    conn, params=(user,))
            else:
                df = pd.read_sql_query(
                    "SELECT * FROM refinery_jobs WHERE status='pending' ORDER BY date_created DESC",
                    conn)
        return df

    def confirm_refinery_job(self, job_id, quantity_actual, quality):
        """Confirme le job et crée le lot — NE stocke PAS automatiquement, la décision se fait après."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM refinery_jobs WHERE id=?", (job_id,))
            row = c.fetchone()
            if not row:
                return None
            cols = [d[0] for d in c.description]
            job = dict(zip(cols, row))
            c.execute("""UPDATE refinery_jobs
                         SET status='confirmed', quantity_actual=?, date_confirmed=?
                         WHERE id=?""",
                      (quantity_actual, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_id))
            conn.commit()
        # Nettoyer le suffixe "(raw)" / "(Raw)" de l'API UEX pour le nom du lot raffiné
        clean_name = job['commodity_name'].replace(" (Raw)", "").replace("(Raw)", "").replace(" (raw)", "").replace("(raw)", "").strip()
        lot_id = self.add_commodity_lot(job['commodity_id'], clean_name, quantity_actual, quality, job_id)
        return {'job': job, 'lot_id': lot_id, 'commodity_name': clean_name}

    def dispatch_lot(self, user, lot_id, commodity_id, commodity_name, quantity, quality,
                     pickup_location, delivery_location, to_stock=True, transport_assignee='Camus68',
                     refinery_job_id=None, notes=None):
        """Envoie un lot en stock fédération et/ou génère un bon de transport."""
        if to_stock:
            self.update_commodity_stock(user, commodity_id, commodity_name, quantity)
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE commodity_lots SET is_blocked=0 WHERE id=?", (lot_id,))
                conn.commit()
        else:
            # Bloquer le lot en attente de transport
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE commodity_lots SET is_blocked=1, blocked_by=? WHERE id=?",
                          (transport_assignee, lot_id))
                conn.commit()
            self.create_transport_order(
                created_by=user,
                assigned_to=transport_assignee,
                commodity_name=commodity_name,
                quantity=quantity,
                quality=quality,
                pickup_location=pickup_location,
                delivery_location=delivery_location,
                refinery_job_id=refinery_job_id,
                lot_id=lot_id,
                notes=notes
            )

    def create_transport_order(self, created_by, assigned_to, commodity_name, quantity, quality,
                               pickup_location, delivery_location, refinery_job_id=None,
                               lot_id=None, notes=None):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO transport_orders
                         (created_by, assigned_to, commodity_name, quantity, quality,
                          pickup_location, delivery_location, refinery_job_id, lot_id, notes, date_created)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (created_by, assigned_to, commodity_name, quantity, quality,
                       pickup_location, delivery_location, refinery_job_id, lot_id, notes,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return c.lastrowid

    def get_transport_orders(self, assignee=None, status=None):
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM transport_orders WHERE 1=1"
            params = []
            if assignee:
                query += " AND assigned_to=?"
                params.append(assignee)
            if status:
                query += " AND status=?"
                params.append(status)
            query += " ORDER BY date_created DESC"
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def update_transport_status(self, order_id, status, user):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if status == 'in_progress':
                c.execute("UPDATE transport_orders SET status=?, date_taken=?, assigned_to=? WHERE id=?",
                          (status, now, user, order_id))
            elif status == 'delivered':
                c.execute("UPDATE transport_orders SET status=?, date_delivered=? WHERE id=?",
                          (status, now, order_id))
                # Libérer le lot et ajouter au stock fédération
                c.execute("SELECT lot_id, commodity_name FROM transport_orders WHERE id=?", (order_id,))
                row = c.fetchone()
                if row and row[0]:
                    c.execute("SELECT commodity_id, quantity FROM commodity_lots WHERE id=?", (row[0],))
                    lot = c.fetchone()
                    if lot:
                        c.execute("UPDATE commodity_lots SET is_blocked=0 WHERE id=?", (row[0],))
                        conn.commit()
                        self.update_commodity_stock(user, lot[0], row[1], lot[1])
                        return
            conn.commit()

    def add_commodity_lot(self, commodity_id, commodity_name, quantity, quality, refinery_job_id=None):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO commodity_lots
                         (commodity_id, commodity_name, quantity, quality, refinery_job_id, date_added)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (commodity_id, commodity_name, quantity, quality, refinery_job_id,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return c.lastrowid

    def get_commodity_lots(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                """SELECT id, commodity_name as Minerai, quantity as SCU,
                          quality as Qualité, is_blocked as Bloqué, blocked_by as 'Bloqué par',
                          date_added as Date
                   FROM commodity_lots
                   WHERE quantity > 0
                   ORDER BY commodity_name, quality DESC""",
                conn)
        return df

    def toggle_lot_blocked(self, lot_id, is_blocked, blocked_by):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""UPDATE commodity_lots
                         SET is_blocked=?, blocked_by=?
                         WHERE id=?""",
                      (1 if is_blocked else 0, blocked_by if is_blocked else None, lot_id))
            conn.commit()
        return True

    def cancel_refinery_job(self, job_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE refinery_jobs SET status='cancelled' WHERE id=?", (job_id,))
            conn.commit()
        return True

    def update_commodity_stock(self, user, commodity_id, name, delta):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT quantity FROM commodity_stock WHERE commodity_id=?", (commodity_id,))
            row = c.fetchone()
            if row:
                new_qty = max(0, row[0] + delta)
                c.execute("UPDATE commodity_stock SET quantity=? WHERE commodity_id=?", (new_qty, commodity_id))
            else:
                if delta > 0:
                    c.execute("INSERT INTO commodity_stock VALUES (?, ?, ?)", (commodity_id, name, delta))

            action_type = "ENTRÉE" if delta > 0 else "SORTIE"
            c.execute("INSERT INTO logs (user, action, item_name, qty, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (user, action_type, name, abs(delta), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    def get_commodity_stock(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                "SELECT name as Minerai, quantity as SCU FROM commodity_stock WHERE quantity > 0 ORDER BY name",
                conn
            )
        return df

    def set_fed_price(self, comm_id, price):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO fed_prices (commodity_id, price_fed) VALUES (?, ?)", (comm_id, price))
            conn.commit()

    def get_all_fed_prices(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM fed_prices", conn)
        return dict(zip(df['commodity_id'], df['price_fed'])) if not df.empty else {}

    def get_full_inventory(self, can_see_hidden=False):
        """Get inventory. If can_see_hidden=False, only show visible items"""
        with sqlite3.connect(self.db_path) as conn:
            if can_see_hidden:
                # Admins and stock managers can see all items
                df = pd.read_sql_query("SELECT item_id, name as Nom, category as Type, size as Taille, quantity as Qté, is_hidden as Caché FROM inventory WHERE quantity > 0", conn)
            else:
                # Regular members only see non-hidden items
                df = pd.read_sql_query("SELECT item_id, name as Nom, category as Type, size as Taille, quantity as Qté, is_hidden as Caché FROM inventory WHERE quantity > 0 AND is_hidden = 0", conn)
        return df

    def get_logs(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT timestamp as Date, user as Pilote, action as Action, qty as Qté, item_name as Article FROM logs ORDER BY id DESC LIMIT 50", conn)
        return df

    def toggle_item_hidden(self, item_id, is_hidden):
        """Toggle item visibility (hide/show)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE inventory SET is_hidden=? WHERE item_id=?", (1 if is_hidden else 0, item_id))
                conn.commit()
                return True
        except Exception:
            return False

    def get_item_visibility(self, item_id):
        """Get visibility status of an item"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT is_hidden FROM inventory WHERE item_id=?", (item_id,))
                row = c.fetchone()
                return row[0] == 1 if row else False
        except Exception:
            return False

    # --- AUTHENTICATION ---
    def _hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, username, password):
        """Authenticate user — WP JWT si WP_URL configuré, sinon SQLite local."""
        if _wp_auth:
            return _wp_auth.authenticate(username, password)
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                password_hash = self._hash_password(password)
                c.execute("SELECT id, username FROM users WHERE username=? AND password_hash=? AND is_active=1",
                         (username, password_hash))
                row = c.fetchone()
                if row:
                    user_id, username = row
                    roles = self.get_user_roles(user_id)
                    return {"id": user_id, "username": username, "roles": roles}
                return None
        except Exception:
            return None

    def get_user_roles(self, user_id):
        """Get list of roles for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""SELECT r.id, r.name FROM roles r
                           INNER JOIN user_roles ur ON r.id = ur.role_id
                           WHERE ur.user_id=? AND r.is_active=1""", (user_id,))
                roles = [{"id": row[0], "name": row[1]} for row in c.fetchall()]
                return roles
        except Exception:
            return []

    def get_role_permissions(self, role_id):
        """Get list of permissions for a role"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT permission FROM role_permissions WHERE role_id=?", (role_id,))
                perms = [row[0] for row in c.fetchall()]
                return perms
        except Exception:
            return []

    def get_user_permissions(self, user_id):
        """Get all permissions for a user (flattened from all their roles)"""
        roles = self.get_user_roles(user_id)
        all_perms = set()
        for role in roles:
            perms = self.get_role_permissions(role["id"])
            all_perms.update(perms)
        return list(all_perms)

    # --- USER MANAGEMENT ---
    def create_user(self, username, password, email=None):
        """Create new user with no roles assigned"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                password_hash = self._hash_password(password)
                c.execute("INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, 1)",
                         (username, password_hash, email))
                conn.commit()
                return c.lastrowid
        except sqlite3.IntegrityError:
            return None  # Username already exists
        except Exception:
            return None

    def update_user(self, user_id, username=None, email=None):
        """Update user info"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                if username:
                    c.execute("UPDATE users SET username=?, date_modified=CURRENT_TIMESTAMP WHERE id=?",
                             (username, user_id))
                if email is not None:
                    c.execute("UPDATE users SET email=?, date_modified=CURRENT_TIMESTAMP WHERE id=?",
                             (email, user_id))
                conn.commit()
                return True
        except Exception:
            return False

    def delete_user(self, user_id):
        """Delete user and remove from all roles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM user_roles WHERE user_id=?", (user_id,))
                c.execute("DELETE FROM users WHERE id=?", (user_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def change_password(self, user_id, new_password):
        """Change user password"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                password_hash = self._hash_password(new_password)
                c.execute("UPDATE users SET password_hash=?, date_modified=CURRENT_TIMESTAMP WHERE id=?",
                         (password_hash, user_id))
                conn.commit()
                return True
        except Exception:
            return False

    def toggle_user_active(self, user_id, is_active):
        """Activate or deactivate user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET is_active=?, date_modified=CURRENT_TIMESTAMP WHERE id=?",
                         (1 if is_active else 0, user_id))
                conn.commit()
                return True
        except Exception:
            return False

    # --- ROLE MANAGEMENT ---
    def add_user_role(self, user_id, role_id):
        """Assign a role to a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)",
                         (user_id, role_id))
                conn.commit()
                return True
        except Exception:
            return False

    def remove_user_role(self, user_id, role_id):
        """Remove a role from a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM user_roles WHERE user_id=? AND role_id=?",
                         (user_id, role_id))
                conn.commit()
                return True
        except Exception:
            return False

    def create_role(self, name, description, permissions=None):
        """Create a new custom role"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO roles (name, description, is_system) VALUES (?, ?, 0)",
                         (name, description))
                role_id = c.lastrowid

                if permissions:
                    for perm in permissions:
                        c.execute("INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
                                 (role_id, perm))

                conn.commit()
                return role_id
        except sqlite3.IntegrityError:
            return None  # Role name already exists
        except Exception:
            return None

    def update_role(self, role_id, name=None, description=None):
        """Update role info"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                if name:
                    c.execute("UPDATE roles SET name=? WHERE id=?", (name, role_id))
                if description is not None:
                    c.execute("UPDATE roles SET description=? WHERE id=?", (description, role_id))
                conn.commit()
                return True
        except Exception:
            return False

    def delete_role(self, role_id):
        """Delete a custom role (not system roles)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                # Check if it's a system role
                c.execute("SELECT is_system FROM roles WHERE id=?", (role_id,))
                result = c.fetchone()
                if result and result[0] == 1:
                    return False  # Cannot delete system roles

                c.execute("DELETE FROM role_permissions WHERE role_id=?", (role_id,))
                c.execute("DELETE FROM user_roles WHERE role_id=?", (role_id,))
                c.execute("DELETE FROM roles WHERE id=?", (role_id,))
                conn.commit()
                return True
        except Exception:
            return False

    def set_role_permissions(self, role_id, permissions):
        """Set permissions for a role (replaces existing)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                # Delete old permissions
                c.execute("DELETE FROM role_permissions WHERE role_id=?", (role_id,))

                # Add new permissions
                for perm in permissions:
                    c.execute("INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)",
                             (role_id, perm))

                conn.commit()
                return True
        except Exception:
            return False

    # --- CRAFTING ---
    def get_blueprints_from_api(self, search='', page=1, limit=20):
        """Fetch blueprints from sc-craft.tools (no auth required)"""
        try:
            params = {"page": page, "limit": limit}
            if search:
                params["search"] = search
            response = requests.get(
                "https://sc-craft.tools/api/blueprints",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                },
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {"items": [], "pagination": {"total": 0}}
        except Exception:
            return {"items": [], "pagination": {"total": 0}}

    def get_lots_for_ingredient(self, ingredient_name):
        """Retourne les lots en stock correspondant à un nom d'ingrédient (insensible à la casse)"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                """SELECT id, commodity_name as Minerai, quantity as SCU,
                          quality as Qualité, is_blocked as Bloqué, blocked_by as 'Bloqué par',
                          date_added as Date
                   FROM commodity_lots
                   WHERE LOWER(commodity_name) = LOWER(?) AND quantity > 0
                   ORDER BY is_blocked ASC, quality DESC""",
                conn, params=(ingredient_name,))
        return df

    def get_blocked_lots(self):
        """Retourne tous les lots actuellement bloqués pour crafting"""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                """SELECT id, commodity_name as Minerai, quantity as SCU,
                          quality as Qualité, blocked_by as 'Bloqué par', date_added as Date
                   FROM commodity_lots
                   WHERE is_blocked = 1 AND quantity > 0
                   ORDER BY blocked_by, commodity_name""",
                conn)
        return df

    # --- UTILITY METHODS ---
    def get_all_users(self):
        """Get list of all users with their roles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""SELECT id, username, email, is_active, date_created FROM users ORDER BY username""")
                users = []
                for row in c.fetchall():
                    user_id, username, email, is_active, date_created = row
                    roles = self.get_user_roles(user_id)
                    users.append({
                        "id": user_id,
                        "username": username,
                        "email": email,
                        "is_active": is_active,
                        "roles": roles,
                        "date_created": date_created
                    })
                return users
        except Exception:
            return []

    def get_all_roles(self):
        """Get list of all roles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""SELECT id, name, description, is_system, is_active FROM roles ORDER BY name""")
                roles = []
                for row in c.fetchall():
                    role_id, name, description, is_system, is_active = row
                    perms = self.get_role_permissions(role_id)
                    roles.append({
                        "id": role_id,
                        "name": name,
                        "description": description,
                        "is_system": is_system,
                        "is_active": is_active,
                        "permissions": perms
                    })
                return roles
        except Exception:
            return []

    def get_user_by_id(self, user_id):
        """Get user info by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT id, username, email, is_active, date_created FROM users WHERE id=?", (user_id,))
                row = c.fetchone()
                if row:
                    user_id, username, email, is_active, date_created = row
                    roles = self.get_user_roles(user_id)
                    return {
                        "id": user_id,
                        "username": username,
                        "email": email,
                        "is_active": is_active,
                        "roles": roles,
                        "date_created": date_created
                    }
                return None
        except Exception:
            return None

    def get_default_permissions(self):
        """Get available permissions constant"""
        return self.PERMISSIONS
