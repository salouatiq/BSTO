#!/usr/bin/env python3
"""
Script Bronze : Extrait les données de population de Briançon depuis l'API Geo (données INSEE)
et les sauvegarde au format brut dans MinIO (Bronze).
"""

import os
import io
import json
import requests
import logging
from datetime import datetime
from minio import Minio
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "briancon2026")
MINIO_BUCKET = "briancon-bronze"

# Code INSEE de Briançon : 05023
# On demande le nom, le code, la population et la surface (très utile pour calculer la densité !)
API_URL = "https://geo.api.gouv.fr/communes/05023?fields=nom,code,population,surface"

def extract_and_load_population():
    logger.info("👨‍👩‍👧‍👦 Lancement de l'extraction de la population (INSEE)...")
    
    try:
        # 1. Appel à l'API du gouvernement
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        pop_data = response.json()
        
        logger.info(f"📥 Données récupérées pour : {pop_data.get('nom')} (Pop: {pop_data.get('population')} habitants)")
        
        # 2. Préparation de la sauvegarde dans MinIO
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Remarque bien le dossier 'population/'
        object_name = f"population/briancon_population_raw_{timestamp}.json"
        
        json_bytes = json.dumps(pop_data, indent=2, ensure_ascii=False).encode('utf-8')
        
        # 3. Connexion et Envoi vers MinIO (Bronze)
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
        
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            
        client.put_object(
            MINIO_BUCKET,
            object_name,
            data=io.BytesIO(json_bytes),
            length=len(json_bytes),
            content_type='application/json'
        )
        
        logger.info(f"✅ Succès ! Fichier brut sauvegardé dans Bronze : {object_name}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur lors de l'appel API : {e}")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue : {e}")

if __name__ == "__main__":
    extract_and_load_population()