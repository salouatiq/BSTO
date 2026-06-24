#!/usr/bin/env python3
"""
Script Bronze : Extrait les infrastructures d'hébergement depuis OpenStreetMap
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

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Requête ciblée sur les hébergements touristiques à Briançon
overpass_query = """
[out:json][timeout:50];
area["name"="Briançon"]->.searchArea;
(
  node["tourism"~"hotel|hostel|motel|guest_house|chalet|camp_site|alpine_hut|apartment"](area.searchArea);
  way["tourism"~"hotel|hostel|motel|guest_house|chalet|camp_site|alpine_hut|apartment"](area.searchArea);
  relation["tourism"~"hotel|hostel|motel|guest_house|chalet|camp_site|alpine_hut|apartment"](area.searchArea);
);
out center;
"""

def extract_and_load_accommodation():
    logger.info("🏨 Lancement de l'extraction des hébergements (OSM)...")
    
    try:
        headers = {
            'User-Agent': 'Projet_BSTO_Data_Engineering/1.0 (Analyse de la pression touristique)'
        }
        
        response = requests.post(OVERPASS_URL, data={'data': overpass_query}, headers=headers, timeout=60)
        response.raise_for_status()
        acc_data = response.json()
        
        count_elements = len(acc_data.get('elements', []))
        logger.info(f"📥 {count_elements} hébergements trouvés dans OpenStreetMap.")
        
        # Préparation de la sauvegarde dans MinIO
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"accommodation/briancon_accommodation_raw_{timestamp}.json"
        
        json_bytes = json.dumps(acc_data, indent=2, ensure_ascii=False).encode('utf-8')
        
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
        logger.info(f"✅ Succès ! Fichier brut sauvegardé : {object_name}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur de l'API Overpass : {e}")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue : {e}")

if __name__ == "__main__":
    extract_and_load_accommodation()