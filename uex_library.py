import requests
import os
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class UEXManager:
    def __init__(self):
        self.base_url = "https://api.uexcorp.space/2.0"
        self.headers = {
            "Authorization": f"Bearer {os.getenv('UEX_BEARER_TOKEN')}",
            "secret-key": os.getenv('UEX_SECRET_KEY')
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
        conn = sqlite3.connect('irr_inventory.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS inventory
                     (item_id INTEGER PRIMARY KEY, name TEXT, category TEXT, size TEXT, quantity INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, action TEXT, item_name TEXT, qty INTEGER, timestamp DATETIME)''')
        c.execute('''CREATE TABLE IF NOT EXISTS fed_prices
                     (commodity_id INTEGER PRIMARY KEY, price_fed REAL)''')
        conn.commit()
        conn.close()

    def update_stock(self, user, item_id, name, category, size, delta):
        conn = sqlite3.connect('irr_inventory.db')
        c = conn.cursor()
        c.execute("SELECT quantity FROM inventory WHERE item_id=?", (item_id,))
        row = c.fetchone()
        if row:
            new_qty = max(0, row[0] + delta)
            c.execute("UPDATE inventory SET quantity=? WHERE item_id=?", (new_qty, item_id))
        else:
            if delta > 0:
                c.execute("INSERT INTO inventory VALUES (?, ?, ?, ?, ?)", (item_id, name, category, str(size), delta))
        
        action_type = "ENTRÉE" if delta > 0 else "SORTIE"
        c.execute("INSERT INTO logs (user, action, item_name, qty, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (user, action_type, name, abs(delta), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def set_fed_price(self, comm_id, price):
        conn = sqlite3.connect('irr_inventory.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO fed_prices (commodity_id, price_fed) VALUES (?, ?)", (comm_id, price))
        conn.commit()
        conn.close()

    def get_all_fed_prices(self):
        conn = sqlite3.connect('irr_inventory.db')
        df = pd.read_sql_query("SELECT * FROM fed_prices", conn)
        conn.close()
        return dict(zip(df['commodity_id'], df['price_fed']))

    def get_full_inventory(self):
        conn = sqlite3.connect('irr_inventory.db')
        df = pd.read_sql_query("SELECT name as Nom, category as Type, size as Taille, quantity as Qté FROM inventory WHERE quantity > 0", conn)
        conn.close()
        return df

    def get_logs(self):
        conn = sqlite3.connect('irr_inventory.db')
        df = pd.read_sql_query("SELECT timestamp as Date, user as Pilote, action as Action, qty as Qté, item_name as Article FROM logs ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        return df