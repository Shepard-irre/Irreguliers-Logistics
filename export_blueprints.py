import urllib.request
import urllib.parse
import json
import csv
import time

BASE_URL = "https://sc-craft.tools/api/blueprints"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

OUTPUT_FILE = "blueprints_export.csv"
LIMIT = 100  # 100 par page = ~11 requêtes pour 1040 blueprints


def fetch_page(page):
    params = urllib.parse.urlencode({"page": page, "limit": LIMIT})
    url = f"{BASE_URL}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_blueprints():
    all_items = []
    page = 1

    while True:
        data = fetch_page(page)
        items = data.get("items", [])
        if not items:
            break

        all_items.extend(items)
        total = data.get("pagination", {}).get("total", 0)
        print(f"Page {page} — {len(all_items)}/{total} blueprints récupérés")

        if len(all_items) >= total:
            break

        page += 1
        time.sleep(0.2)

    return all_items


def export_to_csv(blueprints):
    rows = []

    for bp in blueprints:
        bp_blueprint_id = bp.get("blueprint_id", "")
        bp_name = bp.get("name", "")
        bp_category = bp.get("category", "")
        bp_craft_time = bp.get("craft_time_seconds", "")
        bp_tiers = bp.get("tiers", "")
        bp_version = bp.get("version", "")

        ingredients = bp.get("ingredients", [])

        if not ingredients:
            rows.append({
                "blueprint_id": bp_blueprint_id,
                "name": bp_name,
                "category": bp_category,
                "craft_time_seconds": bp_craft_time,
                "tiers": bp_tiers,
                "version": bp_version,
                "ingredient_slot": "",
                "ingredient_name": "",
                "ingredient_quantity_scu": "",
                "ingredient_min_quality": "",
                "ingredient_unit": "",
            })
        else:
            for ing in ingredients:
                rows.append({
                    "blueprint_id": bp_blueprint_id,
                    "name": bp_name,
                    "category": bp_category,
                    "craft_time_seconds": bp_craft_time,
                    "tiers": bp_tiers,
                    "version": bp_version,
                    "ingredient_slot": ing.get("slot", ""),
                    "ingredient_name": ing.get("name", ""),
                    "ingredient_quantity_scu": ing.get("quantity_scu", ""),
                    "ingredient_min_quality": ing.get("min_quality", ""),
                    "ingredient_unit": ing.get("unit", ""),
                })

    fieldnames = [
        "blueprint_id", "name", "category", "craft_time_seconds", "tiers", "version",
        "ingredient_slot", "ingredient_name", "ingredient_quantity_scu",
        "ingredient_min_quality", "ingredient_unit"
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Export terminé : {len(rows)} lignes dans {OUTPUT_FILE}")
    print(f"   ({len(blueprints)} blueprints, séparateur ';', encodage UTF-8 BOM pour Excel)")


if __name__ == "__main__":
    print("Récupération des blueprints sc-craft.tools...")
    blueprints = fetch_all_blueprints()
    print(f"\nTotal récupéré : {len(blueprints)} blueprints")
    export_to_csv(blueprints)
