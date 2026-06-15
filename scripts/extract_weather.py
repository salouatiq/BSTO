# Script d'extraction des données météo pour Briançon
# Ce script fait une requête à l'API Open-Meteo pour récupérer les données météo historiques des 10 derniers jours pour Briançon, et upload directement dans MinIO bronze (archive brute).
# Note 1:
# ------
    # Assurez-vous d'avoir une connexion internet pour que le script puisse accéder à l'API Open-Meteo.
    # Pour exécuter ce script, utilisez la commande : python scripts/extract_weather.py
    # Ce script est un point de départ pour votre pipeline d'extraction. En production, vous pourriez vouloir ajouter des fonctionnalités comme la gestion des erreurs plus avancée, les notifications en cas d'échec, ou l'intégration avec d'autres sources de données météo pour un enrichissement plus complet.
# Note 2:
# ------
    # Ce script utilise la bibliothèque requests pour faire des appels HTTP, et minio pour l'upload. Assurez-vous d'avoir ces bibliothèques installées dans votre environnement Python : pip install requests minio python-dotenv
    # N'hésitez pas à consulter la documentation de l'API Open-Meteo pour découvrir toutes les fonctionnalités disponibles et personnaliser votre requête selon vos besoins spécifiques en matière de données météo !
# Documentation de l'API Open-Meteo : https://open-meteo.com/en/docs
import requests
import json
import os
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv
import logging
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# 1. CONFIGURATION
# ==========================================
# Coordonnées GPS de Briançon
LATITUDE = 44.89
LONGITUDE = 6.64

# URL de l'API Open-Meteo (Historique des 10 derniers jours)
API_URL = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&past_days=10&hourly=temperature_2m,precipitation&timezone=Europe%2FParis"

# Configuration MinIO Bronze 
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")  # L'adresse de notre stockage
MINIO_ACCESS_KEY = os.getenv("MINIO_USER", "admin")             # L'identifiant défini dans mon docker-compose
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "briancon2026")  # Le mot de passe défini dans mon docker-compose
MINIO_BUCKET = "briancon-bronze"                                # Notre bucket cible pour le brut
MINIO_SECURE = False                                            # En local, on n'utilise pas le protocole HTTPS sécurisé

# ==========================================
# 2. FONCTIONS
# ==========================================
# Configuration de notre client MinIO (notre GCS local)
def create_minio_client():
    client = Minio(MINIO_ENDPOINT,                  # L'adresse de notre stockage
                   access_key=MINIO_ACCESS_KEY,     # L'identifiant défini dans mon docker-compose
                   secret_key=MINIO_SECRET_KEY,     # Le mot de passe défini dans mon docker-compose
                   secure=MINIO_SECURE)             # En local, on n'utilise pas le protocole HTTPS sécurisé
    return client

def ensure_bucket_exists(client, bucket_name):
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info(f"Bucket {bucket_name} créé")

def extract_weather_data():
    """Fait l'appel à l'API et upload directement dans MinIO bronze."""
    print("🌍 Lancement de l'extraction des données météo...")
    
    try:
        # Appel à l'API Open-Meteo
        response = requests.get(API_URL)  
        # Vérifie si la requête a réussi (Code 200). Sinon, lève une erreur.
        response.raise_for_status()
        # Convertit la réponse en dictionnaire Python
        data = response.json()
        
        # Génère un nom de fichier unique basé sur la date du jour
        today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"briancon_weather_raw_{today_str}.json"
        
        # Upload directement dans MinIO bronze (pas de sauvegarde locale)
        client = create_minio_client()
        ensure_bucket_exists(client, MINIO_BUCKET)
        
        # Convertir en JSON string pour upload
        json_data = json.dumps(data, ensure_ascii=False, indent=4)
        json_bytes = json_data.encode('utf-8')
        
        # Upload
        client.put_object(
            MINIO_BUCKET,
            filename,
            data=io.BytesIO(json_bytes),
            length=len(json_bytes),
            content_type='application/json'
        )
        
        print(f"✅ Succès ! Données brutes uploadées dans MinIO bronze : {filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de l'appel API : {e}")
    except S3Error as e:
        print(f"❌ Erreur MinIO : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")

# ==========================================
# 3. EXÉCUTION DU SCRIPT
# ==========================================
if __name__ == "__main__":
    extract_weather_data()