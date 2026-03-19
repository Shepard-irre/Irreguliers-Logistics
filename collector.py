import requests
import config
import json

HEADERS = {"Authorization": f"Bearer {config.API_TOKEN}"}

def surgical_debug():
    print("--- DEBUG CHIRURGICAL API UEX ---")
    try:
        # On tente l'appel le plus simple possible
        response = requests.get(f"{config.BASE_URL}/commodities", headers=HEADERS)
        data = response.json()
        
        if data.get('status') == 'ok' and data.get('data'):
            first_item = data['data'][0]
            print("Structure du premier objet reçu :")
            print(json.dumps(first_item, indent=4)) # Affiche l'objet proprement
            
            # On cherche les objets qui ont un prix
            priced_items = [i for i in data['data'] if i.get('price_buy') or i.get('price_sell')]
            print(f"\nNombre d'objets avec un prix détecté : {len(priced_items)}")
        else:
            print("L'API a répondu 'ok' mais la liste 'data' est vide ou mal formée.")
            print(f"Réponse brute : {data}")
            
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    surgical_debug()