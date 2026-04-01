# Script d'extraction des données météo pour Briançon
# Ce script fait une requête à l'API Open-Meteo pour récupérer les données météo historiques des 10 derniers jours pour Briançon, et sauvegarde les données brutes dans un dossier local (notre équivalent de GCS).
# Note 1:
# ------
    # Assurez-vous d'avoir une connexion internet pour que le script puisse accéder à l'API Open-Meteo.
    # Pour exécuter ce script, utilisez la commande : python scripts/extract_weather.py
    # Ce script est un point de départ pour votre pipeline d'extraction. En production, vous pourriez vouloir ajouter des fonctionnalités comme la gestion des erreurs plus avancée, les notifications en cas d'échec, ou l'intégration avec d'autres sources de données météo pour un enrichissement plus complet.
# Note 2:
# ------
    # Ce script utilise la bibliothèque requests pour faire des appels HTTP, et json pour manipuler les données. Assurez-vous d'avoir ces bibliothèques installées dans votre environnement Python : pip install requests
    # N'hésitez pas à consulter la documentation de l'API Open-Meteo pour découvrir toutes les fonctionnalités disponibles et personnaliser votre requête selon vos besoins spécifiques en matière de données météo !
# Documentation de l'API Open-Meteo : https://open-meteo.com/en/docs
import requests
import json
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Coordonnées GPS de Briançon
LATITUDE = 44.89
LONGITUDE = 6.64

# URL de l'API Open-Meteo (Historique des 10 derniers jours)
API_URL = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&past_days=10&hourly=temperature_2m,precipitation&timezone=Europe%2FParis"

# Chemins des dossiers locaux (notre équivalent GCS)
RAW_DATA_DIR = "../data/raw"

# ==========================================
# 2. FONCTIONS
# ==========================================
def create_directories():
    """Vérifie que le dossier data/raw existe, sinon le crée."""
    # os.makedirs crée le dossier. exist_ok=True évite l'erreur si le dossier est déjà là.
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    print(f"📁 Dossier cible vérifié/créé : {RAW_DATA_DIR}")

def extract_weather_data():
    """Fait l'appel à l'API et sauvegarde les données brutes."""
    print("🌍 Lancement de l'extraction des données météo...")
    
    try:
        # Appel à l'API
        response = requests.get(API_URL)
        
        # Vérifie si la requête a réussi (Code 200). Sinon, lève une erreur.
        response.raise_for_status()
        
        # Convertit la réponse en dictionnaire Python
        data = response.json()
        
        # Génère un nom de fichier unique basé sur la date du jour
        today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{RAW_DATA_DIR}/briancon_weather_raw_{today_str}.json"
        
        # Sauvegarde (Équivalent : Upload vers GCS)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Succès ! Données brutes sauvegardées dans : {filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération des données : {e}")

# ==========================================
# 3. EXÉCUTION DU SCRIPT
# ==========================================
if __name__ == "__main__":
    create_directories()
    extract_weather_data()