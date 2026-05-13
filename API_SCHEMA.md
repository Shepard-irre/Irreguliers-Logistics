# Schéma API UEX Corp 2.0

**Base URL** : `https://api.uexcorp.space/2.0`

**Headers requis** :
```
Authorization: Bearer {token}
secret-key: {secret_key}
```

---

## Endpoints Disponibles

### 1. **COMMODITIES** - Ressources/Matières brutes
```
GET /commodities?limit=100&offset=0
```

**Réponse** : Liste de commodités

**Structure d'une commodité** :
```json
{
  "id": 1,
  "id_parent": 2,
  "name": "Agricium",
  "code": "AGRI",
  "kind": "Metal",
  "weight_scu": 1.2,
  "price_buy": 8841,
  "price_sell": 9917,
  "is_available": 1,
  "is_available_live": 1,
  "is_visible": 1,
  "is_extractable": 1,
  "is_mineral": 1,
  "is_raw": 0,
  "is_pure": 0,
  "is_refined": 1,
  "is_refinable": 0,
  "is_harvestable": 0,
  "is_buyable": 1,
  "is_sellable": 1,
  "is_temporary": 0,
  "is_illegal": 0,
  "is_volatile_qt": 0,
  "is_volatile_time": 0,
  "is_inert": 0,
  "is_explosive": 0,
  "is_fuel": 0,
  "is_buggy": 0,
  "wiki": "https://starcitizen.tools/Agricium",
  "date_added": 1703505653,
  "date_modified": 1733508315
}
```

**Champs importants** : 
- Flags `is_*` : Boolean pour les propriétés de la ressource
- `price_buy` / `price_sell` : Prix moyen
- `kind` : Type (Metal, Gas, etc)


---

### 2. **ITEMS** - Équipements/Modules
```
GET /items?id_category=22&limit=100
```

**Paramètres requis** (au moins un) :
- `id_category` : Catégorie d'items (ex: 22=Quantum Drives)
- `id_company` : Fabricant
- `uuid` : ID unique
- `id_vehicle` : Véhicule

**Structure d'un item** :
```json
{
  "id": 144,
  "id_parent": 0,
  "id_category": 22,
  "id_company": 17,
  "id_vehicle": 0,
  "name": "Burst",
  "date_added": 1703520914,
  "date_modified": 1767493949,
  "section": "Systems",
  "category": "Quantum Drives",
  "company_name": "ArcCorp",
  "vehicle_name": null,
  "slug": "burst",
  "size": "1",
  "uuid": "4a8d0265-7476-401a-a50f-5780cd212656",
  "color": null,
  "color2": null,
  "url_store": "",
  "quality": 0,
  "is_exclusive_pledge": 0,
  "is_exclusive_subscriber": 0,
  "is_exclusive_concierge": 0,
  "is_commodity": 0,
  "is_harvestable": 0,
  "screenshot": "",
  "game_version": "4.1",
  "notification": null
}
```

**Catégories principales utilisées dans l'app** :
- 22 : Quantum Drives (🌌)
- 23 : Shields (🛡️)
- 21 : Power Plants (⚡)
- 32, 70, 79, 90 : Armement (⚔️)
- 29, 30, 74 : Minage (⛏️)
- 82, 65 : Avionique (🛰️)


---

### 3. **COMMODITIES_PRICES** - Prix des commodités par terminal
```
GET /commodities_prices?id_commodity=1&limit=100
```

**Paramètres requis** :
- `id_commodity` : ID de la commodité

**Structure d'un prix** :
```json
{
  "id": 4,
  "id_commodity": 1,
  "id_terminal": 12,
  "id_star_system": 68,
  "id_planet": 4,
  "id_city": 1,
  "price_buy": 0,
  "price_sell": 10000,
  "price_buy_min": 0,
  "price_buy_max": 0,
  "price_sell_min": 10000,
  "price_sell_max": 10000,
  "scu_buy": 0,
  "scu_sell": 112,
  "scu_sell_stock": 16,
  "volatility_buy": 0,
  "volatility_sell": 52.5,
  "container_sizes": "1,2,4,8,16,24,32",
  "game_version": "4.7.1",
  "date_added": 1703514825,
  "date_modified": 1775694464,
  "commodity_name": "Agricium",
  "commodity_code": "AGRI",
  "star_system_name": "Stanton",
  "planet_name": "ArcCorp",
  "city_name": "Area 18",
  "terminal_name": "TDD - Trade and Development Division - Area 18",
  "terminal_code": "TDA18"
}
```

**Champs clés** :
- `price_buy` / `price_sell` : Prix actuel
- `scu_buy` / `scu_sell` : Volume disponible (Quantum Units)
- `volatility_sell` : Volatilité des prix
- `terminal_name` : Point de vente


---

### 4. **ITEMS_PRICES** - Prix des items par terminal
```
GET /items_prices?id_category=22&limit=100
```

**Paramètres requis** (au moins un) :
- `id_category` : Catégorie
- `id_item` : Item spécifique
- `id_terminal` : Terminal

**Structure similaire à commodities_prices** :
```json
{
  "id": 144,
  "id_item": 144,
  "id_category": 22,
  "id_terminal": 114,
  "price_buy": 29925,
  "price_sell": 0,
  "durability": 100,
  "game_version": "4.7",
  "item_name": "Burst",
  "star_system_name": "Stanton",
  "terminal_name": "Dumper's Depot - Area 18",
  "terminal_code": "DDA18"
}
```


---

### 5. **WALLET_BALANCE** - Solde du compte
```
GET /wallet_balance
```

**Réponse** :
```json
{
  "status": "ok",
  "http_code": 200,
  "data": {
    "balance": 0
  }
}
```


---

### 6. **TERMINALS** - Points de vente
```
GET /terminals?limit=100
```

**Structure d'un terminal** :
```json
{
  "id": 1,
  "id_star_system": 68,
  "id_planet": 4,
  "id_city": 1,
  "name": "Admin - ARC-L1",
  "fullname": "Commodity Shop - Admin - ARC-L1",
  "code": "ARCL1",
  "type": "commodity",
  "mcs": 0,
  "is_available": 1,
  "is_available_live": 1,
  "is_visible": 1,
  "is_player_owned": 0,
  "has_loading_dock": 0,
  "has_freight_elevator": 1,
  "game_version": "3.24.2",
  "star_system_name": "Stanton",
  "planet_name": "ArcCorp",
  "city_name": "Area 18",
  "faction_name": "United Empire of Earth",
  "company_name": "Rest & Relax",
  "max_container_size": 32
}
```

**Types de terminals** : `commodity`, `refinery`, `medical`, `shop_fps`, `shop_vehicle`, etc


---

### 7. **STAR_SYSTEMS** - Systèmes stellaires
```
GET /star_systems?limit=100
```

**Structure** :
```json
{
  "id": 1,
  "name": "78 Leonis",
  "code": "78",
  "is_available": 0,
  "is_available_live": 0,
  "is_visible": 0,
  "is_default": 0,
  "wiki": "https://starcitizen.tools/78_Leonis"
}
```


---

## Format de Réponse Standard

Toutes les réponses suivent le même format :

```json
{
  "status": "ok",
  "http_code": 200,
  "data": [...],
  "message": ""
}
```

**Statuts possibles** :
- `ok` : Succès
- `requires_id_*` : Paramètre manquant
- `missing_required_input` : Entrée requise manquante


---

## Paramètres Communs

- `limit` : Nombre de résultats (défaut: 100, max: ?)
- `offset` : Pagination
- `sort` : Colonne de tri
- `order` : `asc` ou `desc`


---

## Optimisations Possibles

1. **Caching** : Les données changent peu, cache 5-30 minutes
2. **Recherche par nom** : Ajouter search/filter sur les commodity names
3. **Historique de prix** : Utiliser `price_*_week` / `price_*_month`
4. **Volatilité** : Déterminer les meilleures ventes/achats
5. **Filtres additionnels** : Par système, par type, par disponibilité


---

## Exemples d'Utilisation

### Obtenir le prix meilleur de vente d'une commodité
```python
commodity_id = 1
prices = requests.get(
    "https://api.uexcorp.space/2.0/commodities_prices",
    params={"id_commodity": commodity_id},
    headers=headers
).json()

best_sellers = sorted(
    [p for p in prices['data'] if p['price_sell'] > 0],
    key=lambda x: x['price_sell'],
    reverse=True
)
```

### Chercher un item par catégorie
```python
items = requests.get(
    "https://api.uexcorp.space/2.0/items",
    params={"id_category": 22, "limit": 50},  # Quantum Drives
    headers=headers
).json()
```

### Obtenir les prix d'un item
```python
item_prices = requests.get(
    "https://api.uexcorp.space/2.0/items_prices",
    params={"id_item": 144, "limit": 100},
    headers=headers
).json()
```
