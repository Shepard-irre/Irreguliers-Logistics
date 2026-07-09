import requests
import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from wp_auth import WPAuth

load_dotenv(Path(__file__).parent / '.env', override=True)

_wp_auth = WPAuth() if os.getenv('WP_URL') else None

class UEXManager:
    def __init__(self):
        self.base_url = "https://api.uexcorp.space/2.0"
        self.db_path = 'irr_inventory.db'
        self._cache = {}

        self.init_db()

    @property
    def headers(self):
        from dotenv import dotenv_values
        cfg = dotenv_values(Path(__file__).parent / '.env')
        return {
            "Authorization": f"Bearer {cfg.get('UEX_BEARER_TOKEN', '')}",
            "secret-key": cfg.get('UEX_SECRET_KEY', '')
        }

    def _get_data(self, endpoint, params=None):
        cache_key = (endpoint, str(params))
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json().get('data', [])
                if data:
                    self._cache[cache_key] = data
                return data
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

            conn.commit()

        self._migrate_schema()

    def _migrate_schema(self):
        """Add missing columns to existing tables"""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            # --- inventory.is_hidden ---
            c.execute("PRAGMA table_info(inventory)")
            columns = [row[1] for row in c.fetchall()]
            if 'is_hidden' not in columns:
                try:
                    c.execute("ALTER TABLE inventory ADD COLUMN is_hidden INTEGER DEFAULT 0")
                except Exception:
                    pass

            # --- refinery_jobs.session_id + quality + timer ---
            c.execute("PRAGMA table_info(refinery_jobs)")
            cols_rj = [row[1] for row in c.fetchall()]
            for col, definition in [
                ('session_id',             'INTEGER'),
                ('quality',                'INTEGER DEFAULT 500'),
                ('processing_time_minutes','INTEGER'),
                ('datetime_completion',    'TEXT'),
                ('notified',               'INTEGER DEFAULT 0'),
            ]:
                if col not in cols_rj:
                    try:
                        c.execute(f"ALTER TABLE refinery_jobs ADD COLUMN {col} {definition}")
                    except Exception:
                        pass

            # --- transport_orders.session_id + destination ---
            c.execute("PRAGMA table_info(transport_orders)")
            cols_to = [row[1] for row in c.fetchall()]
            if 'session_id' not in cols_to:
                try:
                    c.execute("ALTER TABLE transport_orders ADD COLUMN session_id INTEGER")
                except Exception:
                    pass
            if 'destination' not in cols_to:
                try:
                    c.execute("ALTER TABLE transport_orders ADD COLUMN destination TEXT DEFAULT 'vente'")
                except Exception:
                    pass

            # --- Tables sessions de minage ---
            c.execute('''CREATE TABLE IF NOT EXISTS mining_sessions
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          numero TEXT UNIQUE,
                          star_system TEXT NOT NULL,
                          status TEXT DEFAULT 'open',
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                          created_by TEXT NOT NULL)''')

            c.execute('''CREATE TABLE IF NOT EXISTS session_ships
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          session_id INTEGER NOT NULL,
                          ship_name TEXT NOT NULL,
                          ship_role TEXT DEFAULT 'mining')''')

            c.execute('''CREATE TABLE IF NOT EXISTS session_crew
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          ship_id INTEGER NOT NULL,
                          username TEXT NOT NULL)''')

            c.execute('''CREATE TABLE IF NOT EXISTS session_expenses
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          session_id INTEGER NOT NULL,
                          description TEXT NOT NULL,
                          amount_auec REAL NOT NULL)''')

            # --- Stock personnel ---
            c.execute('''CREATE TABLE IF NOT EXISTS personal_stock
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          owner TEXT NOT NULL,
                          commodity_name TEXT NOT NULL,
                          quantity REAL NOT NULL,
                          quality INTEGER DEFAULT 500,
                          refinery_job_id INTEGER,
                          location TEXT,
                          status TEXT DEFAULT 'active',
                          consumed_reason TEXT,
                          consumed_at DATETIME,
                          date_added DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            for col, coldef in [
                ("location",        "TEXT"),
                ("status",          "TEXT DEFAULT 'active'"),
                ("consumed_reason", "TEXT"),
                ("consumed_at",     "DATETIME"),
            ]:
                try:
                    c.execute(f"ALTER TABLE personal_stock ADD COLUMN {col} {coldef}")
                except Exception:
                    pass

            # --- Nettoyage suffixes "(Raw)" et "(Ore)" ---
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
                                      REPLACE(REPLACE(REPLACE(REPLACE(
                                          {col},
                                          ' (Raw)', ''), '(Raw)', ''),
                                          ' (raw)', ''), '(raw)', ''),
                                          ' (Ore)', ''), '(Ore)', ''),
                                          ' (ore)', ''), '(ore)', '')
                                  )
                                  WHERE LOWER({col}) LIKE '%(raw)%' OR LOWER({col}) LIKE '%(ore)%'""")
                except Exception:
                    pass
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

    def get_vehicles(self, is_mining=None):
        data = self._get_data("vehicles")
        if is_mining is not None:
            data = [v for v in data if v.get('is_mining') == (1 if is_mining else 0)]
        return sorted(data, key=lambda v: v.get('name', ''))

    # --- SCREENSHOT ANALYSIS ---
    def analyze_refinery_screenshot(self, image_bytes: bytes, order_num: int = None) -> dict:
        """Envoie un screenshot de raffinerie SC à Claude Vision et retourne les données extraites."""
        import base64
        import anthropic

        from dotenv import dotenv_values
        cfg = dotenv_values(Path(__file__).parent / '.env')
        api_key = cfg.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return {'error': 'ANTHROPIC_API_KEY manquante dans .env ou secrets Streamlit'}

        # Détection du vrai format image
        if image_bytes[:3] == b'\xff\xd8\xff':
            media_type = "image/jpeg"
        elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        elif image_bytes[:4] == b'GIF8':
            media_type = "image/gif"
        else:
            media_type = "image/jpeg"

        b64 = base64.standard_b64encode(image_bytes).decode('utf-8')

        positions = {1: "colonne de GAUCHE", 2: "colonne du MILIEU", 3: "colonne de DROITE"}
        order_hint = f"\nFocalise-toi UNIQUEMENT sur la {positions[order_num]} (ORDRE DE {order_num}). Ignore les autres colonnes." if order_num else ""

        prompt = f"""Analyse ce screenshot de l'interface de raffinage de Star Citizen.

=== TYPE D'ÉCRAN ===
TYPE A : tu vois des blocs "TRAITEMENT EN COURS" ou "TERMINÉ" avec "ORDRE DE X" en haut.
TYPE B : tu vois un bouton "CONFIRMER" et un menu de méthode (Cormack, Dinyx…).

=== POUR TYPE A ==={order_hint}
Extrais les lignes de minerais avec ces colonnes dans l'ordre : [Nom] [QUALITÉ] [RENDEM] [À FAIRE] [TERMIN]
Pour chaque ligne retourne :
  commodity_name : nom en anglais sans suffixe
  quantity_raw   : valeur QUALITÉ (1er nombre)
  quality        : valeur RENDEM (2ème nombre)
  quantity_refined: valeur TERMIN (4ème nombre)
  active         : true
Retourne aussi processing_time_minutes = TEMPS RESTANT en minutes (ex: "18h 25m" → 1105).

=== POUR TYPE B ===
Colonnes : [Nom] [QUALITÉ] [QTE] [RENDEM] [puce AFFINER]
  commodity_name : nom en anglais sans suffixe
  quantity_raw   : valeur QTE (2ème nombre)
  quality        : valeur QUALITÉ (1er nombre)
  quantity_refined: valeur RENDEM (3ème nombre) si puce orange (active=true), sinon null
  active         : true si puce AFFINER orange, false si rouge

=== FORMAT JSON (identique TYPE A et TYPE B) ===
{{
  "screen_type": "A" ou "B",
  "terminal_name": "nom station ou null",
  "method": "méthode si visible sinon null",
  "processing_time_minutes": <minutes ou null>,
  "lines": [
    {{"commodity_name": "...", "quantity_raw": ..., "quality": ..., "active": true, "quantity_refined": ...}}
  ]
}}

Retourne UNIQUEMENT le JSON."""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )

        import json
        raw = response.content[0].text.strip()
        # Nettoie les balises markdown si Claude en met
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        try:
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                return {'orders': parsed, '_raw_response': raw}
            parsed['_raw_response'] = raw
            return parsed
        except json.JSONDecodeError:
            return {'error': f'Réponse non parseable : {raw[:200]}'}

    # --- REFINERY API ---
    def get_refinable_commodities(self):
        comms = self._get_data("commodities")
        return [c for c in comms if c.get('is_refinable') == 1]

    def get_refinery_terminals(self):
        return self._get_data("terminals", params={"type": "refinery"})

    def get_all_terminals(self):
        return self._get_data("terminals") or []

    def get_refinery_methods(self):
        # Ratings UEX incorrects sur plusieurs méthodes — on overwrite avec les vraies valeurs in-game
        # Faible=1, Modéré=2, Élevé=3
        CORRECT_RATINGS = {
            "Cormack":                 {"rating_yield": 1, "rating_cost": 2, "rating_speed": 2},
            "Dinyx Solventation":      {"rating_yield": 3, "rating_cost": 1, "rating_speed": 1},
            "Electrostarolysis":       {"rating_yield": 2, "rating_cost": 2, "rating_speed": 2},
            "Ferron Exchange":         {"rating_yield": 3, "rating_cost": 2, "rating_speed": 2},
            "Gaskin Process":          {"rating_yield": 2, "rating_cost": 3, "rating_speed": 3},
            "Kazen Winnowing":         {"rating_yield": 1, "rating_cost": 1, "rating_speed": 1},
            "Pyrometric Chromalysis":  {"rating_yield": 3, "rating_cost": 3, "rating_speed": 3},
            "Thermonatic Deposition":  {"rating_yield": 2, "rating_cost": 1, "rating_speed": 1},
            "XCR Reaction":            {"rating_yield": 1, "rating_cost": 3, "rating_speed": 3},
        }
        methods = self._get_data("refineries_methods")
        for m in methods:
            if m.get('name') in CORRECT_RATINGS:
                m.update(CORRECT_RATINGS[m['name']])
        return methods

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
                            yield_rate, confidence, audit_count, session_id=None, quality=500,
                            processing_time_minutes=None):
        from datetime import timedelta
        now = datetime.now()
        datetime_completion = None
        if processing_time_minutes:
            datetime_completion = (now + timedelta(minutes=processing_time_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO refinery_jobs
                         (user, commodity_id, commodity_name, terminal_id, terminal_name,
                          method, quantity_raw, quantity_estimated, yield_rate, confidence,
                          audit_count, status, date_created, session_id, quality,
                          processing_time_minutes, datetime_completion, notified)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, 0)""",
                      (user, commodity_id, commodity_name, terminal_id, terminal_name,
                       method, quantity_raw, quantity_estimated, yield_rate, confidence,
                       audit_count, now.strftime("%Y-%m-%d %H:%M:%S"), session_id, quality,
                       processing_time_minutes, datetime_completion))
            conn.commit()
            return c.lastrowid

    def add_personal_stock(self, owner, commodity_name, quantity, quality, refinery_job_id=None, location=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""INSERT INTO personal_stock
                            (owner, commodity_name, quantity, quality, refinery_job_id, location, status, date_added)
                            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)""",
                         (owner, commodity_name, quantity, quality, refinery_job_id, location,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    def get_personal_stock(self, owner):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                "SELECT * FROM personal_stock WHERE owner=? AND status='active' ORDER BY date_added DESC",
                conn, params=(owner,)
            )

    def consume_personal_stock(self, stock_id, reason):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""UPDATE personal_stock
                            SET status='consumed', consumed_reason=?, consumed_at=?
                            WHERE id=?""",
                         (reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), stock_id))
            conn.commit()

    def update_personal_stock_location(self, stock_id, location):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE personal_stock SET location=? WHERE id=?", (location, stock_id))
            conn.commit()

    def get_jobs_due_for_notification(self):
        """Retourne les jobs terminés non encore notifiés."""
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(
                """SELECT * FROM refinery_jobs
                   WHERE status='pending' AND notified=0
                   AND datetime_completion IS NOT NULL
                   AND datetime_completion <= ?""",
                conn, params=(datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
            )
        return df

    def mark_job_notified(self, job_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE refinery_jobs SET notified=1 WHERE id=?", (job_id,))
            conn.commit()

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
        clean_name = job['commodity_name'].replace(" (Raw)", "").replace("(Raw)", "").replace(" (raw)", "").replace("(raw)", "").replace(" (Ore)", "").replace("(Ore)", "").replace(" (ore)", "").replace("(ore)", "").strip()
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
                               lot_id=None, notes=None, session_id=None, destination='vente'):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO transport_orders
                         (created_by, assigned_to, commodity_name, quantity, quality,
                          pickup_location, delivery_location, refinery_job_id, lot_id, notes,
                          date_created, session_id, destination)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (created_by, assigned_to, commodity_name, quantity, quality,
                       pickup_location, delivery_location, refinery_job_id, lot_id, notes,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session_id, destination))
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
                c.execute("SELECT lot_id, commodity_name, destination FROM transport_orders WHERE id=?", (order_id,))
                row = c.fetchone()
                if row and row[0]:
                    lot_id, commodity_name, destination = row
                    c.execute("SELECT commodity_id, quantity FROM commodity_lots WHERE id=?", (lot_id,))
                    lot = c.fetchone()
                    if lot:
                        c.execute("UPDATE commodity_lots SET is_blocked=0, quantity=0 WHERE id=?", (lot_id,))
                        conn.commit()
                        # Vente → lot liquidé, pas de stock fédé
                        # Stock fédéral → ajout au stock
                        if destination == 'stock_federal':
                            self.update_commodity_stock(user, lot[0], commodity_name, lot[1])
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

    # --- SESSIONS DE MINAGE ---

    def create_mining_session(self, created_by, star_system):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO mining_sessions (star_system, created_by) VALUES (?, ?)",
                      (star_system, created_by))
            session_id = c.lastrowid
            numero = f"MIN{session_id:03d}"
            c.execute("UPDATE mining_sessions SET numero=? WHERE id=?", (numero, session_id))
            conn.commit()
        return {'id': session_id, 'numero': numero}

    def get_mining_sessions(self, status=None):
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM mining_sessions"
            params = []
            if status:
                query += " WHERE status=?"
                params.append(status)
            query += " ORDER BY id DESC"
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def get_mining_session(self, session_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM mining_sessions WHERE id=?", (session_id,))
            row = c.fetchone()
            if not row:
                return None
            cols = [d[0] for d in c.description]
            session = dict(zip(cols, row))

            ships_df = pd.read_sql_query(
                "SELECT * FROM session_ships WHERE session_id=? ORDER BY id", conn, params=(session_id,))
            ships = []
            for _, ship in ships_df.iterrows():
                crew_df = pd.read_sql_query(
                    "SELECT * FROM session_crew WHERE ship_id=? ORDER BY id", conn, params=(int(ship['id']),))
                ships.append({**ship.to_dict(), 'crew': crew_df.to_dict('records')})

            expenses_df = pd.read_sql_query(
                "SELECT * FROM session_expenses WHERE session_id=? ORDER BY id", conn, params=(session_id,))

            jobs_df = pd.read_sql_query(
                "SELECT * FROM refinery_jobs WHERE session_id=? ORDER BY date_created", conn, params=(session_id,))

        session['ships'] = ships
        session['expenses'] = expenses_df.to_dict('records')
        session['jobs'] = jobs_df.to_dict('records')
        return session

    def add_session_ship(self, session_id, ship_name, ship_role='mining'):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO session_ships (session_id, ship_name, ship_role) VALUES (?, ?, ?)",
                      (session_id, ship_name, ship_role))
            conn.commit()
            return c.lastrowid

    def remove_session_ship(self, ship_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM session_crew WHERE ship_id=?", (ship_id,))
            c.execute("DELETE FROM session_ships WHERE id=?", (ship_id,))
            conn.commit()

    def add_crew_member(self, ship_id, username):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM session_crew WHERE ship_id=? AND username=?", (ship_id, username))
            if not c.fetchone():
                c.execute("INSERT INTO session_crew (ship_id, username) VALUES (?, ?)", (ship_id, username))
                conn.commit()

    def remove_crew_member(self, crew_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM session_crew WHERE id=?", (crew_id,))
            conn.commit()

    def add_session_expense(self, session_id, description, amount_auec):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO session_expenses (session_id, description, amount_auec) VALUES (?, ?, ?)",
                      (session_id, description, amount_auec))
            conn.commit()
            return c.lastrowid

    def remove_session_expense(self, expense_id):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM session_expenses WHERE id=?", (expense_id,))
            conn.commit()

    def set_session_status(self, session_id, status):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE mining_sessions SET status=? WHERE id=?", (status, session_id))
            conn.commit()

    def get_session_financial_summary(self, session_id):
        """Retourne les données brutes pour le calcul financier — les prix UEX sont injectés par app.py."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM mining_sessions WHERE id=?", (session_id,))
            row = c.fetchone()
            if not row:
                return None
            cols = [d[0] for d in c.description]
            session = dict(zip(cols, row))

            # Membres présents (vaisseaux de minage uniquement)
            crew_df = pd.read_sql_query("""
                SELECT DISTINCT sc.username
                FROM session_crew sc
                JOIN session_ships ss ON sc.ship_id = ss.id
                WHERE ss.session_id = ? AND ss.ship_role = 'mining'
            """, conn, params=(session_id,))

            # Frais
            exp_df = pd.read_sql_query(
                "SELECT description, amount_auec FROM session_expenses WHERE session_id=?",
                conn, params=(session_id,))

            # Bons de transport de la session
            orders_df = pd.read_sql_query("""
                SELECT t.id, t.commodity_name, t.quantity, t.quality, t.destination,
                       t.status, t.lot_id,
                       COALESCE(cl.commodity_id, rj.commodity_id) as commodity_id
                FROM transport_orders t
                LEFT JOIN commodity_lots cl ON t.lot_id = cl.id
                LEFT JOIN refinery_jobs rj ON t.refinery_job_id = rj.id
                WHERE t.session_id = ?
            """, conn, params=(session_id,))

        crew = crew_df['username'].tolist() if not crew_df.empty else []
        total_expenses = float(exp_df['amount_auec'].sum()) if not exp_df.empty else 0.0
        orders_vente = orders_df[orders_df['destination'] == 'vente'].to_dict('records') if not orders_df.empty else []
        orders_stock = orders_df[orders_df['destination'] == 'stock_federal'].to_dict('records') if not orders_df.empty else []

        return {
            'session': session,
            'crew': crew,
            'nb_joueurs': len(crew),
            'expenses': exp_df.to_dict('records') if not exp_df.empty else [],
            'total_expenses': total_expenses,
            'orders_vente': orders_vente,
            'orders_stock_fed': orders_stock,
        }

    # --- AUTHENTICATION ---
    def authenticate_user(self, username, password):
        if _wp_auth:
            return _wp_auth.authenticate(username, password)
        return None

    def authenticate_with_token(self, token):
        if _wp_auth:
            return _wp_auth.authenticate_with_token(token)
        return None

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

